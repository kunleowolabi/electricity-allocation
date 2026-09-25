# Administrative Boundary Files

Boundary shapefiles are too large for version control.
Download from the sources below and place in this directory.

## United States
- Source: US Census Bureau TIGER/Line 2025
- URL: https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2025&layergroup=States+%28and+equivalent%29
- File: tl_2025_us_state.shp
- CRS: NAD83 (EPSG:4269)
- Notes: Exclude territories (FIPS 60, 66, 69, 72, 78)

## France
- Source: data.gouv.fr (IGN/AdminExpress)
- URL: https://www.data.gouv.fr/en/datasets/contours-des-regions-francaises-sur-openstreetmap/
- File: regions-20180101-shp/
- CRS: WGS84 (EPSG:4326)
- Notes: 13 metropolitan regions (post-2016 reform). Exclude overseas (codes 01-04, 06)

## United Kingdom
- Source: ONS Open Geography Portal
- URL: https://geoportal.statistics.gov.uk/
- Search: "Regions December 2025 Boundaries EN BFC"
- CRS: British National Grid (EPSG:27700), reproject to EPSG:4326
- Notes: 9 English regions only

## Italy
- Source: Istat
- URL: https://www.istat.it/it/archivio/222527
- File: Limiti01012026_g/Reg01012026_g/
- CRS: UTM zone 32N (EPSG:32632), reproject to EPSG:4326
- Notes: 20 administrative regions

## Turkey
- Source: GADM v4.1
- URL: https://gadm.org/download_country.html (select Turkey, Level 1, Shapefile)
- File: gadm41_TUR_1.shp
- CRS: WGS84 (EPSG:4326)
- Notes: 81 provinces

## Nigeria (for application, not calibration)
- Source: GADM v4.1
- URL: https://gadm.org/download_country.html (select Nigeria, Level 1, Shapefile)
- File: gadm41_NGA_1.shp
- CRS: WGS84 (EPSG:4326)
- Notes: 36 states + FCT = 37 units

## Processing
All non-WGS84 shapefiles were reprojected to EPSG:4326 before use.
All geometries simplified to 0.01-degree tolerance for GEE upload compatibility.