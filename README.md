# Cross-Country Satellite-Based Allocation of Subnational Electricity Consumption

A method for allocating a country's total electricity consumption across its
states, provinces, or regions using globally available satellite data
(population and VIIRS nighttime light radiance), for countries that lack
a published subnational consumption breakdown.

This repository contains the data, extraction pipeline, models, and paper
for the working study *Cross-Country Satellite-Based Allocation of
Subnational Electricity Consumption: A Five-Country Calibration Study*.

## What this is

Given a country's total electricity consumption, from any source, this
model predicts what share of that total each subnational region accounts
for. It does not estimate national-level consumption; it answers the
question that comes after a national figure exists: where, specifically,
is that consumption concentrated?

The model is trained on four countries with verified, publicly available
subnational consumption data (United States, France, United Kingdom,
Italy) and validated independently on a fifth (Turkey), held out entirely
from model development.

**Final specification:**
log(consumption) ~ log(population) + log(viirs_sum_raw)


Huber robust regression (epsilon = 1.35). Predicts each region's share
of national consumption with minimum share R² of 0.885 across all five
holdout countries, outperforming simple population-proportional
allocation in three of five cases. See the paper for full results,
including a comparison against population alone and a stress test for
gas-flare contamination in the nighttime-light signal.

## Repository structure
├── data/
│ ├── consumption/ Raw subnational consumption data, as downloaded, 5 countries
│ ├── boundaries/ Download instructions for administrative boundary shapefiles
│ └── processed/ The frozen, verified dataset all results are computed from
│
├── extraction/ Scripts to extract satellite features via Google Earth Engine
│
├── models/ Model testing, selection, and the final locked specification
│
├── outputs/ Model coefficients, predictions, and validation results
│
├── paper/ The manuscript, figures, and bibliography
│
└── docs/ Full model selection log and project handover notes


## Reproducing the results

1. **Get the data.** Consumption files are in `data/consumption/`. Boundary
   shapefiles are not stored in this repo — see `data/boundaries/README.md`
   for download links.

2. **Extract satellite features** (requires a Google Earth Engine account
   and project):
```bash
   export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")
   python3 extraction/gee_extract_features.py --country US --boundary <path> --id-col <col> --name-col <col>
```
   Repeat per country. See the script's docstring for exact arguments used
   for each of the five countries.

3. **Merge into the analysis dataset:**
```bash
   python3 extraction/merge_datasets.py
```
   The output should exactly reproduce `data/processed/dataset_5country_corrected_v2.csv`.
   Verify against the known per-capita values listed in `data/README.md`
   before trusting a rebuilt file.

4. **Run model selection and validation:**
```bash
   python3 models/definitive_test_v2.py     # all tested variants, share R² by country
   python3 models/flare_stress_test.py      # gas-flare robustness check
   python3 models/final_model.py            # locks the final R3 specification
   python3 models/generate_figures.py       # regenerates the paper's figures
```

All scripts assume they are run from the repository root.

## Key findings

- Of 26 candidate model variants tested, only raw VIIRS radiance sum
  consistently improved on population-proportional allocation under
  genuine cross-country holdout validation.
- Several features that perform well in within-country studies
  (settlement-masked VIIRS, GHSL urban classification, built-up surface
  area, climate degree-days) did not survive cross-country testing. Full
  detail in `docs/model_selection_log.md`.
- No reliable pre-screening rule was found to determine, in advance,
  whether a new country would be better served by the satellite-augmented
  model or by population alone. This is reported as an open limitation,
  not resolved by this work.
- A dedicated stress test on US gas-flaring states found no evidence that
  raw VIIRS systematically over-allocates consumption to flare-heavy
  regions.

See `paper/CROSS-COUNTRY_SATELLITE-BASED_ALLOCATION.docx` for the full
manuscript, including methodology, complete results, limitations, and
discussion.

## Data sources

| Country | Consumption source | Years used |
|---|---|---|
| United States | EIA Open Data API | 2019 |
| France | RTE éCO2mix | 2019 |
| United Kingdom | DESNZ | 2019 |
| Italy | Terna Download Centre | 2019 |
| Turkey | TUIK | 2019 |

Satellite features: NOAA VIIRS DNB Annual Composite V2.1, JRC GHS-POP
R2023A, ERA5-Land monthly reanalysis, all extracted via Google Earth
Engine.

## Status

This is a working paper. It has not undergone peer review. Results and
conclusions are subject to revision. See `docs/handover_document.md` for
the current state of related, unpublished work (a companion study on
national-level demand estimation) that this method is designed to feed
into but does not itself address.

## License

MIT License. See `LICENSE` for full terms. Data sourced from third-party
providers (EIA, RTE, DESNZ, Terna, TUIK, NOAA, JRC, ECMWF) retains
whatever license terms those providers apply; see `data/boundaries/README.md`
and each source's own usage terms before redistributing raw data files.

## Citation

If you use this method or code, please cite:

Ayokunle Owolabi (2026). Cross-Country Satellite-Based Allocation of
Subnational Electricity Consumption: A Five-Country Calibration Study.
Working paper.
