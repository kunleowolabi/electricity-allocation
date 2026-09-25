"""
Satellite Feature Extraction — Population, VIIRS, Climate
=============================================================
Reproduces the extraction pipeline described in Section 3.2 of the paper.

Extracts three satellite-derived variables via Google Earth Engine for a
set of administrative boundary polygons:

  - Population: JRC GHS-POP R2023A, epoch 2020, 100m native resolution
  - VIIRS nighttime light radiance: NOAA VIIRS DNB Annual Composite V2.1,
    'average' band, summed at 500m processing scale
  - Climate: ERA5-Land monthly aggregated reanalysis, 2m air temperature,
    converted to heating/cooling degree-days (base 18°C)

Also extracts several additional features referenced in Section 4.5 of
the paper (tested during model selection, not retained in the final
specification): settlement-masked VIIRS, GHSL built-up surface area,
GHS-SMOD urban classification, and lit area fraction. These are included
for reproducibility of the model selection process documented in
docs/model_selection_log.md.

Usage:
  export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")
  python3 gee_extract_features.py --country US --boundary data/boundaries/tl_2025_us_state.shp --id-col GEOID --name-col NAME
  python3 gee_extract_features.py --country France --boundary data/boundaries/regions-20180101-shp/regions-20180101.shp --id-col code --name-col nom
  python3 gee_extract_features.py --country UK --boundary data/boundaries/uk_regions.shp --id-col RGN25CD --name-col RGN25NM
  python3 gee_extract_features.py --country Italy --boundary data/boundaries/Reg01012026_g.shp --id-col COD_REG --name-col DEN_REG
  python3 gee_extract_features.py --country Turkey --boundary data/boundaries/gadm41_TUR_1.shp --id-col GID_1 --name-col NAME_1

Requires: earthengine-api, geopandas, pandas
"""

import argparse
import json
import os

import ee
import geopandas as gpd
import pandas as pd

GEE_PROJECT = "energy-demand"
YEAR = 2019
OUTPUT_DIR = "data/processed/satellite_features"


def load_boundaries(boundary_path, id_col, name_col, simplify_tolerance=0.01):
    """Load a boundary shapefile, reproject to WGS84, simplify for GEE upload."""
    gdf = gpd.read_file(boundary_path)

    if gdf.crs is None:
        raise ValueError(f"{boundary_path} has no CRS defined — set it before extraction")
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    gdf = gdf[[id_col, name_col, "geometry"]].copy()
    gdf = gdf.rename(columns={id_col: "region_id", name_col: "region_name"})
    gdf["region_id"] = gdf["region_id"].astype(str)
    gdf["geometry"] = gdf.geometry.simplify(tolerance=simplify_tolerance, preserve_topology=True)

    # Area in km2, via an equal-area projection
    gdf_proj = gdf.to_crs(epsg=6933)
    gdf["area_km2"] = gdf_proj.geometry.area / 1e6

    print(f"  Loaded {len(gdf)} regions from {boundary_path}")
    return gdf


def gdf_to_ee_fc(gdf):
    """Convert a GeoDataFrame to an Earth Engine FeatureCollection."""
    geojson = json.loads(gdf.to_json())
    features = []
    for feat in geojson["features"]:
        geom = ee.Geometry(feat["geometry"])
        props = {
            "region_id": str(feat["properties"]["region_id"]),
            "region_name": str(feat["properties"]["region_name"]),
        }
        features.append(ee.Feature(geom, props))
    return ee.FeatureCollection(features)


def extract_population(fc):
    """GHS-POP R2023A, epoch 2020, summed per region."""
    pop_img = (
        ee.ImageCollection("JRC/GHSL/P2023A/GHS_POP")
        .filter(ee.Filter.eq("system:index", "2020"))
        .first()
        .select("population_count")
    )
    pop_img = pop_img.updateMask(pop_img.gte(0))  # mask NoData
    result = pop_img.reduceRegions(
        collection=fc,
        reducer=ee.Reducer.sum().setOutputs(["population"]),
        scale=100,
    )
    return result.getInfo()


def extract_viirs_raw(fc, year):
    """VIIRS DNB Annual V2.1, 'average' band, summed per region (raw, unmasked)."""
    viirs = (
        ee.ImageCollection("NOAA/VIIRS/DNB/ANNUAL_V21")
        .filter(ee.Filter.calendarRange(year, year, "year"))
        .first()
        .select("average")
    )
    result = viirs.reduceRegions(
        collection=fc,
        reducer=ee.Reducer.sum().setOutputs(["viirs_sum_raw"])
            .combine(ee.Reducer.mean().setOutputs(["viirs_mean_raw"]), sharedInputs=True),
        scale=500,
    )
    return result.getInfo()


def extract_viirs_settled(fc, year):
    """VIIRS masked to GHSL settlement pixels only (built_surface > 0).

    Tested during model selection (Section 4.5) — not retained in the
    final specification, but extracted here for reproducibility of that
    comparison.
    """
    viirs = (
        ee.ImageCollection("NOAA/VIIRS/DNB/ANNUAL_V21")
        .filter(ee.Filter.calendarRange(year, year, "year"))
        .first()
        .select("average")
    )
    ghsl_built = (
        ee.ImageCollection("JRC/GHSL/P2023A/GHS_BUILT_S")
        .filter(ee.Filter.eq("system:index", "2020"))
        .first()
        .select("built_surface")
    )
    settlement_mask = ghsl_built.gt(0)
    viirs_settled = viirs.updateMask(settlement_mask)

    result = viirs_settled.reduceRegions(
        collection=fc,
        reducer=ee.Reducer.sum().setOutputs(["viirs_sum_settled"])
            .combine(ee.Reducer.mean().setOutputs(["viirs_mean_settled"]), sharedInputs=True),
        scale=500,
    )
    return result.getInfo()


def extract_built_up(fc):
    """GHSL built-up surface area — total and mean per region.

    Tested during model selection (Section 4.5) — not retained.
    """
    ghsl_built = (
        ee.ImageCollection("JRC/GHSL/P2023A/GHS_BUILT_S")
        .filter(ee.Filter.eq("system:index", "2020"))
        .first()
        .select("built_surface")
    )
    result = ghsl_built.reduceRegions(
        collection=fc,
        reducer=ee.Reducer.sum().setOutputs(["built_up_sum"])
            .combine(ee.Reducer.mean().setOutputs(["built_up_mean"]), sharedInputs=True),
        scale=500,
    )
    return result.getInfo()


def extract_smod(fc):
    """GHS-SMOD urban centre / dense urban cluster percentage.

    Tested during model selection (Section 4.5) — not retained. Known to
    misclassify sparse rural settlements as zero urban area outside
    Europe/North America (see docs/model_selection_log.md).
    """
    smod = (
        ee.ImageCollection("JRC/GHSL/P2023A/GHS_SMOD")
        .filter(ee.Filter.eq("system:index", "2020"))
        .first()
        .select("smod_code")
    )
    # Classes 30 (urban centre) and 23 (dense urban cluster)
    urban_mask = smod.eq(30).Or(smod.eq(23))
    result = urban_mask.reduceRegions(
        collection=fc,
        reducer=ee.Reducer.mean().setOutputs(["smod_urban_pct"]),
        scale=1000,
    )
    return result.getInfo()


def extract_lit_area_fraction(fc, year):
    """Fraction of region area with VIIRS radiance > 0.5 nW/cm2/sr.

    Tested during model selection (Section 4.5) — not retained.
    """
    viirs = (
        ee.ImageCollection("NOAA/VIIRS/DNB/ANNUAL_V21")
        .filter(ee.Filter.calendarRange(year, year, "year"))
        .first()
        .select("average")
    )
    lit_mask = viirs.gt(0.5)
    result = lit_mask.reduceRegions(
        collection=fc,
        reducer=ee.Reducer.mean().setOutputs(["lit_area_fraction"]),
        scale=500,
    )
    return result.getInfo()


def extract_climate(fc, year):
    """ERA5-Land monthly temperature -> heating/cooling degree-days (base 18C)."""
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    monthly_temps = {}

    for month in range(1, 13):
        start = f"{year}-{month:02d}-01"
        end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"

        era5 = (
            ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR")
            .filterDate(start, end)
            .first()
        )
        temp_c = era5.select("temperature_2m").subtract(273.15)
        result = temp_c.reduceRegions(
            collection=fc,
            reducer=ee.Reducer.mean(),
            scale=10000,
        )
        for feat in result.getInfo()["features"]:
            rid = feat["properties"]["region_id"]
            monthly_temps.setdefault(rid, {})[month] = feat["properties"].get("mean")

    climate = {}
    for rid, temps in monthly_temps.items():
        hdd = sum(max(0, 18 - (temps.get(m) or 18)) * days_in_month[m - 1] for m in range(1, 13))
        cdd = sum(max(0, (temps.get(m) or 18) - 18) * days_in_month[m - 1] for m in range(1, 13))
        climate[rid] = {"hdd": hdd, "cdd": cdd, "total_dd": hdd + cdd}
    return climate


def properties_to_df(gee_result, prop_names):
    rows = []
    for feat in gee_result["features"]:
        row = {p: feat["properties"].get(p) for p in prop_names}
        rows.append(row)
    return pd.DataFrame(rows)


def settlement_mask_fallback(df):
    """Where GHSL detects zero settlement pixels, fall back to raw VIIRS.

    See Section 3.4 / 4.5 of the paper — required for regions with sparse,
    dispersed rural settlements that GHSL's built-up detection threshold
    (calibrated on European/North American morphology) misses entirely.
    """
    zero_mask = df["viirs_sum_settled"].fillna(0) < 1
    n_fallback = zero_mask.sum()
    if n_fallback > 0:
        print(f"  Settlement mask fallback applied to {n_fallback} region(s) "
              f"with zero detected settlement pixels")
        df.loc[zero_mask, "viirs_sum_settled"] = df.loc[zero_mask, "viirs_sum_raw"]
        df.loc[zero_mask, "viirs_mean_settled"] = (
            df.loc[zero_mask, "viirs_sum_raw"] / df.loc[zero_mask, "area_km2"]
        )
    return df


def main():
    parser = argparse.ArgumentParser(description="Extract satellite features for one country")
    parser.add_argument("--country", required=True, help="Country name, e.g. US, France, UK, Italy, Turkey")
    parser.add_argument("--boundary", required=True, help="Path to boundary shapefile")
    parser.add_argument("--id-col", required=True, help="Column name for region ID in the shapefile")
    parser.add_argument("--name-col", required=True, help="Column name for region name in the shapefile")
    parser.add_argument("--year", type=int, default=YEAR, help="Year for VIIRS and climate extraction (default 2019)")
    parser.add_argument("--simplify", type=float, default=0.01, help="Geometry simplification tolerance in degrees")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Initializing Earth Engine (project: {GEE_PROJECT})...")
    ee.Initialize(project=GEE_PROJECT)

    print(f"\nLoading boundaries for {args.country}...")
    gdf = load_boundaries(args.boundary, args.id_col, args.name_col, args.simplify)
    fc = gdf_to_ee_fc(gdf)

    df = gdf[["region_id", "region_name", "area_km2"]].copy()

    print("Extracting population (GHS-POP 2020)...")
    pop_result = extract_population(fc)
    pop_df = properties_to_df(pop_result, ["region_id", "population"])
    df = df.merge(pop_df, on="region_id", how="left")

    print(f"Extracting VIIRS raw radiance ({args.year})...")
    viirs_result = extract_viirs_raw(fc, args.year)
    viirs_df = properties_to_df(viirs_result, ["region_id", "viirs_sum_raw", "viirs_mean_raw"])
    df = df.merge(viirs_df, on="region_id", how="left")

    print(f"Extracting settlement-masked VIIRS ({args.year}) [for model selection reproducibility]...")
    settled_result = extract_viirs_settled(fc, args.year)
    settled_df = properties_to_df(settled_result, ["region_id", "viirs_sum_settled", "viirs_mean_settled"])
    df = df.merge(settled_df, on="region_id", how="left")
    df = settlement_mask_fallback(df)

    print("Extracting GHSL built-up surface [for model selection reproducibility]...")
    built_result = extract_built_up(fc)
    built_df = properties_to_df(built_result, ["region_id", "built_up_sum", "built_up_mean"])
    df = df.merge(built_df, on="region_id", how="left")

    print("Extracting GHS-SMOD urban classification [for model selection reproducibility]...")
    smod_result = extract_smod(fc)
    smod_df = properties_to_df(smod_result, ["region_id", "smod_urban_pct"])
    df = df.merge(smod_df, on="region_id", how="left")
    df["smod_urban_pct"] = df["smod_urban_pct"].fillna(0)  # GHSL zero-detection default

    print("Extracting lit area fraction [for model selection reproducibility]...")
    lit_result = extract_lit_area_fraction(fc, args.year)
    lit_df = properties_to_df(lit_result, ["region_id", "lit_area_fraction"])
    df = df.merge(lit_df, on="region_id", how="left")

    print(f"Extracting climate ({args.year}, 12 months)...")
    climate = extract_climate(fc, args.year)
    df["hdd"] = df["region_id"].map(lambda x: climate.get(x, {}).get("hdd"))
    df["cdd"] = df["region_id"].map(lambda x: climate.get(x, {}).get("cdd"))
    df["total_dd"] = df["region_id"].map(lambda x: climate.get(x, {}).get("total_dd"))

    df["country"] = args.country
    df["year"] = args.year

    out_path = f"{OUTPUT_DIR}/{args.country.lower()}_features.csv"
    df.to_csv(out_path, index=False)

    print(f"\nDone. {len(df)} regions extracted, saved to {out_path}")
    print(df.head().to_string())


if __name__ == "__main__":
    main()