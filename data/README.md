# Data

This folder contains all data used to train and validate the electricity
consumption allocation model, plus the frozen dataset the paper's results
are computed from.

## Structure
data/
├── consumption/ Raw subnational electricity consumption files, as downloaded
├── boundaries/ Instructions for obtaining administrative boundary shapefiles
└── processed/ The single frozen, verified dataset used for all results


## consumption/

Raw subnational electricity consumption data for all five countries, in the
format each source agency provides it. No corrections have been applied to
these files; the France gross-to-metered correction and any other
adjustments are applied downstream, not here.

| File | Country | Source | Years covered |
|---|---|---|---|
| `us_consumption.csv` | United States | EIA Open Data API | 2014–2025 |
| `france_consumption.csv` | France | RTE éCO2mix | 2014–2026, monthly |
| `uk_consumption.xlsx` | United Kingdom | DESNZ | 2005–2024 |
| `italy_2019.xlsx` | Italy | Terna Download Centre | 2019 |
| `italy_2022.xlsx` | Italy | Terna Download Centre | 2022 |
| `italy_2024.xlsx` | Italy | Terna Download Centre | 2024 |
| `turkey_consumption.csv` | Turkey | TUIK | 2019, 2022 |

The paper's primary analysis uses 2019 for every country. See Section 3.4
of the paper for the rationale.

## boundaries/

Administrative boundary shapefiles are not stored in this repository — they
are large binary files better retrieved directly from source. See
`boundaries/README.md` for download links, exact file names, coordinate
reference systems, and the specific processing (reprojection, geometry
simplification, territory exclusions) applied to each before use.

## processed/

`dataset_5country_corrected_v2.csv` is the single frozen dataset all model
results in the paper are computed from. It combines consumption data
(with the France correction applied exactly once), satellite-derived
features (population, VIIRS radiance, climate, and several additional
features tested but not retained — see `docs/model_selection_log.md`),
for all 174 regions across the five countries.

**This file should not be regenerated silently.** Earlier stages of this
project lost time to a bug where the France correction was applied twice
during dataset reconstruction, producing incorrect results that went
undetected for several analysis runs. If the dataset needs to be rebuilt
from `consumption/` and satellite extractions, verify the rebuilt file
against these known values before using it for any analysis:

| Country | Expected per-capita (kWh) |
|---|---|
| US | 11,342 |
| France | 6,818 |
| UK | 4,126 |
| Italy | 5,012 |
| Turkey | 3,080 |

A rebuild that doesn't reproduce these five numbers exactly has a bug
somewhere in the pipeline.