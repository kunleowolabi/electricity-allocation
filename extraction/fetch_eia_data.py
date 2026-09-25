"""
Fetch US State-Level Electricity Consumption from EIA API
=========================================================
Downloads annual retail electricity sales by state (all sectors)
from the US Energy Information Administration API.

Usage:
  python3 fetch_eia_data.py YOUR_API_KEY

Get a free API key at: https://www.eia.gov/opendata/register.php
"""

import requests
import pandas as pd
import sys
import json

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
API_KEY = sys.argv[1] if len(sys.argv) > 1 else "znRccbh5BkpcEynVqfm7N5FWg5mWV8V2Zi6fWNZt"

if API_KEY == "znRccbh5BkpcEynVqfm7N5FWg5mWV8V2Zi6fWNZt":
    print("ERROR: Please provide your EIA API key as an argument:")
    print("  python3 fetch_eia_data.py YOUR_API_KEY")
    print("\nGet a free key at: https://www.eia.gov/opendata/register.php")
    sys.exit(1)

BASE_URL = "https://api.eia.gov/v2/electricity/retail-sales/data"
OUTPUT_FILE = "consumption_data/us_consumption.csv"

# ─────────────────────────────────────────────
# FETCH DATA
# ─────────────────────────────────────────────
print("Fetching US electricity consumption data from EIA API...")

params = {
    "api_key": API_KEY,
    "data[]": "sales",
    "facets[sectorid][]": "ALL",
    "frequency": "annual",
    "start": "2014",
    "sort[0][column]": "period",
    "sort[0][direction]": "asc",
    "length": 5000,
}

response = requests.get(BASE_URL, params=params)

if response.status_code != 200:
    print(f"ERROR: API returned status {response.status_code}")
    print(response.text)
    sys.exit(1)

data = response.json()

if "response" not in data or "data" not in data["response"]:
    print("ERROR: Unexpected API response format")
    print(json.dumps(data, indent=2)[:500])
    sys.exit(1)

records = data["response"]["data"]
print(f"Received {len(records)} records")

# ─────────────────────────────────────────────
# PROCESS DATA
# ─────────────────────────────────────────────
df = pd.DataFrame(records)

print(f"\nColumns: {df.columns.tolist()}")
print(f"\nSample record:")
print(json.dumps(records[0], indent=2))

# Filter to state-level data (exclude US total)
# EIA uses state abbreviations; filter out aggregates
if "stateDescription" in df.columns:
    state_col = "stateDescription"
    state_id_col = "stateid"
elif "state-name" in df.columns:
    state_col = "state-name"
    state_id_col = "state"
else:
    print(f"\nAvailable columns: {df.columns.tolist()}")
    print("Saving raw data for inspection...")
    import os
    os.makedirs("consumption_data", exist_ok=True)
    df.to_csv(OUTPUT_FILE.replace(".csv", "_raw.csv"), index=False)
    print(f"Saved to {OUTPUT_FILE.replace('.csv', '_raw.csv')}")
    sys.exit(0)

# Filter out US total and territories if present
exclude = ["US", "US Total", "DC"]  # Keep DC actually
df_states = df[~df[state_id_col].isin(["US"])].copy()

# Rename and select columns
df_states = df_states.rename(columns={
    state_col: "region_name",
    state_id_col: "state_code",
    "period": "year",
    "sales": "consumption_million_kwh",
    "sectorName": "sector",
})

# Convert types
df_states["year"] = df_states["year"].astype(int)
df_states["consumption_million_kwh"] = pd.to_numeric(
    df_states["consumption_million_kwh"], errors="coerce"
)

# Convert million kWh to GWh (1 million kWh = 1 GWh)
df_states["consumption_gwh"] = df_states["consumption_million_kwh"]

# Select and sort
cols_to_keep = ["state_code", "region_name", "year", "consumption_gwh", "consumption_million_kwh"]
cols_to_keep = [c for c in cols_to_keep if c in df_states.columns]
df_out = df_states[cols_to_keep].sort_values(["year", "region_name"]).reset_index(drop=True)

# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
import os
os.makedirs("consumption_data", exist_ok=True)
df_out.to_csv(OUTPUT_FILE, index=False)

print(f"\n✓ Saved {len(df_out)} rows to {OUTPUT_FILE}")
print(f"  States: {df_out['region_name'].nunique()}")
print(f"  Years: {sorted(df_out['year'].unique())}")
print(f"\nTop 5 by consumption (latest year):")
latest = df_out["year"].max()
top = df_out[df_out["year"] == latest].nlargest(5, "consumption_gwh")
for _, r in top.iterrows():
    print(f"  {r['region_name']:25s} {r['consumption_gwh']:>10,.1f} GWh")
