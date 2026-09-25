"""
Merge Consumption Data with Zonal Statistics
=============================================
Combines electricity consumption data from all four calibration
countries with the satellite-derived zonal statistics to create
the analysis-ready dataset.

Input files:
  - zonal_stats_results.csv (from GEE script)
  - consumption_data/us_consumption.csv
  - consumption/Gross_consumption_2026-08-20_18-23.csv (France)
  - consumption/Subnational_electricity_consumption_statistics_2005-2024.xlsx (UK)
  - consumption/Export-DownloadCenterFile-20260903-000744.xlsx (Italy 2024)
  - consumption/Export-DownloadCenterFile-20260903-000755.xlsx (Italy 2022)
  - consumption/Export-DownloadCenterFile-20260903-000804.xlsx (Italy 2019)

Output:
  - analysis_ready_dataset.csv

Usage:
  python3 merge_datasets.py
"""

import pandas as pd
import numpy as np
import sys


# ─────────────────────────────────────────────
# 1. LOAD ZONAL STATISTICS
# ─────────────────────────────────────────────
print("=" * 60)
print("Merging Consumption Data with Zonal Statistics")
print("=" * 60)

zonal = pd.read_csv("zonal_stats_results.csv")
print(f"\nZonal stats: {len(zonal)} rows, {zonal['country'].nunique()} countries")
print(f"  Years: {sorted(zonal['year'].unique())}")


# ─────────────────────────────────────────────
# 2. PROCESS US CONSUMPTION
# ─────────────────────────────────────────────
print(f"\n{'─' * 40}")
print("Processing: US")

us = pd.read_csv("consumption_data/us_consumption.csv")
us = us[us["year"].isin([2019, 2022, 2024])].copy()
us["country"] = "US"
us = us.rename(columns={"consumption_gwh": "consumption_gwh"})
us = us[["country", "region_name", "year", "consumption_gwh"]].copy()
us["consumption_definition"] = "retail_sales_excl_losses"

print(f"  ✓ {len(us)} rows ({us['region_name'].nunique()} states × {us['year'].nunique()} years)")


# ─────────────────────────────────────────────
# 3. PROCESS FRANCE CONSUMPTION
# ─────────────────────────────────────────────
print(f"\n{'─' * 40}")
print("Processing: France")

fr = pd.read_csv(
    "consumption/Gross_consumption_2026-08-20_18-23.csv",
    sep=";",
    quotechar='"',
)

# Parse columns
fr.columns = ["date", "region", "type", "value_twh"]

# Filter to gross consumption only
fr = fr[fr["type"].str.strip() == "Gross consumption"].copy()

# Extract year and month from date
fr["year"] = fr["date"].str[:4].astype(int)
fr["month"] = fr["date"].str[5:7].astype(int)

# Filter to target years
fr = fr[fr["year"].isin([2019, 2022, 2024])].copy()

# Clean region names (remove quotes if present)
fr["region"] = fr["region"].str.strip().str.strip('"')

# Convert value to numeric
fr["value_twh"] = pd.to_numeric(fr["value_twh"].astype(str).str.replace(",", "."), errors="coerce")

# For 2024, check if we have all 12 months (might be incomplete)
month_counts = fr.groupby(["region", "year"])["month"].count()
incomplete = month_counts[month_counts < 12]
if len(incomplete) > 0:
    print(f"  Warning: incomplete years detected:")
    for (region, year), count in incomplete.items():
        print(f"    {region} {year}: {count} months")

# Aggregate monthly to annual (sum TWh)
fr_annual = fr.groupby(["region", "year"])["value_twh"].sum().reset_index()

# Convert TWh to GWh (1 TWh = 1000 GWh)
fr_annual["consumption_gwh"] = fr_annual["value_twh"] * 1000

fr_annual["country"] = "France"
fr_annual = fr_annual.rename(columns={"region": "region_name"})
fr_annual = fr_annual[["country", "region_name", "year", "consumption_gwh"]].copy()
fr_annual["consumption_definition"] = "gross_consumption_incl_losses"

# Filter out overseas territories
overseas = ["La Réunion", "Martinique", "Guadeloupe", "Guyane", "Mayotte"]
fr_annual = fr_annual[~fr_annual["region_name"].isin(overseas)].copy()

print(f"  ✓ {len(fr_annual)} rows ({fr_annual['region_name'].nunique()} regions × {fr_annual['year'].nunique()} years)")


# ─────────────────────────────────────────────
# 4. PROCESS UK CONSUMPTION
# ─────────────────────────────────────────────
print(f"\n{'─' * 40}")
print("Processing: UK")

# Target regions (9 English regions)
uk_target_regions = [
    "North East", "North West", "Yorkshire and The Humber",
    "East Midlands", "West Midlands", "East",
    "London", "South East", "South West"
]

uk_rows = []
for year in [2019, 2022, 2024]:
    sheet = pd.read_excel(
        "consumption/Subnational_electricity_consumption_statistics_2005-2024.xlsx",
        sheet_name=str(year),
        skiprows=4,
    )

    # Find region rows — they have "All local authorities" in the local authority column
    region_data = sheet[
        (sheet["Country or region"].isin(uk_target_regions)) &
        (sheet["Local authority"] == "All local authorities")
    ].copy()

    for _, row in region_data.iterrows():
        region_name = row["Country or region"]

        # Map "East" to "East of England" to match boundary data
        if region_name == "East":
            region_name = "East of England"

        consumption_col = [c for c in sheet.columns if "Total consumption" in str(c) and "All meters" in str(c)]
        if consumption_col:
            consumption_gwh = row[consumption_col[0]]
        else:
            consumption_gwh = np.nan

        uk_rows.append({
            "country": "UK",
            "region_name": region_name,
            "year": year,
            "consumption_gwh": float(consumption_gwh),
            "consumption_definition": "metered_consumption_excl_losses",
        })

uk_df = pd.DataFrame(uk_rows)
print(f"  ✓ {len(uk_df)} rows ({uk_df['region_name'].nunique()} regions × {uk_df['year'].nunique()} years)")


# ─────────────────────────────────────────────
# 5. PROCESS ITALY CONSUMPTION
# ─────────────────────────────────────────────
print(f"\n{'─' * 40}")
print("Processing: Italy")

italy_files = [
    "consumption/Export-DownloadCenterFile-20260903-000804.xlsx",  # 2019
    "consumption/Export-DownloadCenterFile-20260903-000755.xlsx",  # 2022
    "consumption/Export-DownloadCenterFile-20260903-000744.xlsx",  # 2024
]

italy_dfs = []
for f in italy_files:
    df = pd.read_excel(f)
    italy_dfs.append(df)

italy = pd.concat(italy_dfs, ignore_index=True)

# Aggregate by region and year (sum across provinces and sectors)
italy_agg = italy.groupby(["Anno", "Regione"])["Consumo (GWh)"].sum().reset_index()

italy_agg["country"] = "Italy"
italy_agg = italy_agg.rename(columns={
    "Anno": "year",
    "Regione": "region_name",
    "Consumo (GWh)": "consumption_gwh",
})
italy_agg = italy_agg[["country", "region_name", "year", "consumption_gwh"]].copy()
italy_agg["consumption_definition"] = "total_consumption_by_sector"

print(f"  ✓ {len(italy_agg)} rows ({italy_agg['region_name'].nunique()} regions × {italy_agg['year'].nunique()} years)")


# ─────────────────────────────────────────────
# 6. COMBINE ALL CONSUMPTION DATA
# ─────────────────────────────────────────────
print(f"\n{'─' * 40}")
print("Combining all consumption data...")

consumption = pd.concat([us, fr_annual, uk_df, italy_agg], ignore_index=True)
print(f"  Total consumption rows: {len(consumption)}")
print(f"  By country:")
for country, group in consumption.groupby("country"):
    print(f"    {country}: {group['region_name'].nunique()} regions × {group['year'].nunique()} years = {len(group)} rows")


# ─────────────────────────────────────────────
# 7. MERGE WITH ZONAL STATISTICS
# ─────────────────────────────────────────────
print(f"\n{'─' * 40}")
print("Merging with zonal statistics...")

# Check for name mismatches before merging
for country in ["US", "France", "UK", "Italy"]:
    zonal_names = set(zonal[zonal["country"] == country]["region_name"].unique())
    cons_names = set(consumption[consumption["country"] == country]["region_name"].unique())

    only_zonal = zonal_names - cons_names
    only_cons = cons_names - zonal_names

    if only_zonal or only_cons:
        print(f"\n  ⚠ {country} name mismatches:")
        if only_zonal:
            print(f"    In zonal stats only: {only_zonal}")
        if only_cons:
            print(f"    In consumption only: {only_cons}")

# Merge
merged = pd.merge(
    zonal,
    consumption[["country", "region_name", "year", "consumption_gwh", "consumption_definition"]],
    on=["country", "region_name", "year"],
    how="left",
)

# Report merge results
matched = merged["consumption_gwh"].notna().sum()
unmatched = merged["consumption_gwh"].isna().sum()
print(f"\n  Matched: {matched} rows")
print(f"  Unmatched: {unmatched} rows")

if unmatched > 0:
    print(f"\n  Unmatched regions:")
    unmatched_rows = merged[merged["consumption_gwh"].isna()][["country", "region_name", "year"]]
    for _, row in unmatched_rows.drop_duplicates().iterrows():
        print(f"    {row['country']}: {row['region_name']} ({row['year']})")


# ─────────────────────────────────────────────
# 8. COMPUTE DERIVED VARIABLES
# ─────────────────────────────────────────────
print(f"\n{'─' * 40}")
print("Computing derived variables...")

# Per-capita consumption
merged["consumption_per_capita_kwh"] = (merged["consumption_gwh"] * 1e6) / merged["population"]

# Consumption per km²
merged["consumption_per_km2"] = merged["consumption_gwh"] / merged["area_km2"]

# Urban share (built-up land cover percentage)
merged["urban_share"] = merged["lc_built_up_pct"]

# Population density
merged["pop_density"] = merged["population"] / merged["area_km2"]

print("  ✓ Added: consumption_per_capita_kwh, consumption_per_km2, urban_share, pop_density")


# ─────────────────────────────────────────────
# 9. SAVE
# ─────────────────────────────────────────────
OUTPUT = "analysis_ready_dataset.csv"
merged.to_csv(OUTPUT, index=False)

print(f"\n{'=' * 60}")
print(f"✓ Saved {len(merged)} rows to {OUTPUT}")
print(f"\nDataset summary:")
print(f"  Countries: {sorted(merged['country'].unique())}")
print(f"  Years: {sorted(merged['year'].unique())}")
print(f"  Columns: {len(merged.columns)}")
print(f"\n  Rows by country:")
for country in sorted(merged["country"].unique()):
    subset = merged[merged["country"] == country]
    matched_pct = subset["consumption_gwh"].notna().mean() * 100
    print(f"    {country}: {len(subset)} rows ({matched_pct:.0f}% with consumption data)")
print(f"\nDone!")
