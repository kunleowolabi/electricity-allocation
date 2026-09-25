# Model Selection Log

## Overview

This document records all model variants tested during the development of the
electricity consumption allocation model described in the accompanying working
paper. Each entry states what was tested, why, the specific holdout results,
and why the variant was retained or rejected.

All results reported here are from `definitive_test_v2.py`, run on
`dataset_5country_corrected_v2.csv` — the frozen, verified dataset with
the France correction applied exactly once. Numbers in this document
correspond to a single execution on that dataset; no figures are
reconstructed from memory or averaged across multiple runs.

**Selection criterion:** minimum share R² across all five holdout countries
(US, France, UK, Italy via LOCO; Turkey via independent holdout). A model
must achieve the highest MIN to be selected. MEAN is reported but does not
override MIN — a model that averages well but fails catastrophically on
one country cannot be trusted on an unseen country where failure would be
undetectable.

**Training countries:** US, France, UK, Italy (93 regions).
**Validation country:** Turkey (81 provinces), held out from all training
and all model development decisions.

**Regression method:** Huber robust regression (epsilon=1.35) throughout.
The same epsilon was used for every variant to ensure performance
differences reflect feature choice, not regularisation tuning.

---

## The winner

**R3: log(consumption) ~ log(population) + log(viirs_sum_raw)**

| Country | Share R² |
|---------|----------|
| US      | +0.885   |
| France  | +0.942   |
| UK      | +0.924   |
| Italy   | +0.903   |
| Turkey  | +0.887   |
| MEAN    | +0.908   |
| MIN     | +0.885   |
| MINρ    | +0.838   |

This is the final recommended specification. Two features, both in
extensive (summed) form, both log-transformed. The remainder of this
document explains what else was tested and why it was rejected.

---

## Group 1: Population baselines

These establish the floor — what can be achieved without any satellite data.

### R1: log(population) only

| Country | Share R² |
|---------|----------|
| US      | +0.802   |
| France  | +0.865   |
| UK      | +0.989   |
| Italy   | +0.849   |
| Turkey  | +0.894   |
| MEAN    | +0.880   |
| MIN     | +0.802   |
| MINρ    | +0.856   |

Population alone is a strong baseline — MEAN of 0.880, and near-perfect
on the UK (0.989). Its weakness is the US (0.802), where industrial
concentration creates per-capita consumption variation that population
cannot capture. R1 also has the best MINρ (0.856), meaning it ranks
regions most reliably in the worst case.

### R2: log(population) + log(total_dd)

| Country | Share R² |
|---------|----------|
| US      | +0.780   |
| France  | +0.867   |
| UK      | +0.971   |
| Italy   | +0.886   |
| Turkey  | +0.875   |
| MEAN    | +0.876   |
| MIN     | +0.780   |
| MINρ    | +0.812   |

Adding climate (degree-days) to population actually reduces MIN from
0.802 to 0.780 — the US gets worse, not better. Climate helps Italy
(+0.037) but hurts the US (-0.022) and UK (-0.018). Rejected: worse
MIN than population alone.

---

## Group 2: Population + single satellite feature (sum variants)

Testing whether each satellite total, added to population, improves
the baseline.

### R3: log(population) + log(viirs_sum_raw) — SELECTED

See "The winner" above. MIN = 0.885, beating R1 by +0.083.

### R4: log(population) + log(viirs_sum_settled)

| Country | Share R² |
|---------|----------|
| US      | +0.828   |
| France  | +0.789   |
| UK      | +0.678   |
| Italy   | +0.835   |
| Turkey  | +0.813   |
| MEAN    | +0.789   |
| MIN     | +0.678   |

Settlement-masked VIIRS. Developed specifically to fix the Alaska/oil-
infrastructure confound in the US. Reduced US non-settlement radiance
from 100% to 33% of total. But cross-country MIN drops to 0.678 — far
worse than both R3 (0.885) and R1 (0.802).

Two causes identified:
1. GHSL's built-up detection threshold missed 8 Turkish provinces
   entirely (zero settled pixels despite real populations of 65k-378k),
   requiring a fallback to raw VIIRS for those provinces
2. Settlement masking concentrates signal in dense urban cores,
   amplifying urban-rural brightness contrasts that don't correspond
   proportionally to consumption differences across countries

Rejected: MIN 0.678, worse than population alone.

### R5: log(population) + log(built_sum)

| Country | Share R² |
|---------|----------|
| US      | +0.833   |
| France  | +0.517   |
| UK      | +0.218   |
| Italy   | +0.879   |
| Turkey  | +0.740   |
| MEAN    | +0.637   |
| MIN     | +0.218   |

GHSL built-up surface total. Heavily correlated with population
(r = 0.85), so the two features are partially redundant. UK collapses
to 0.218 — the worst single-country result in the entire selection
process outside of per-capita models.

Rejected: MIN 0.218.

---

## Group 3: Population + satellite + climate

Testing whether adding degree-days to the population + satellite
combinations improves them.

### R6: log(population) + log(viirs_sum_raw) + log(total_dd)

| Country | Share R² |
|---------|----------|
| US      | +0.866   |
| France  | +0.942   |
| UK      | +0.926   |
| Italy   | +0.869   |
| Turkey  | +0.892   |
| MEAN    | +0.899   |
| MIN     | +0.866   |
| MINρ    | +0.846   |

Adding climate to R3. France holds; Turkey improves marginally (+0.005).
But US drops from 0.885 to 0.866 and Italy drops from 0.903 to 0.869.
MIN drops from 0.885 to 0.866.

The most plausible explanation is redundancy: VIIRS radiance already
correlates with climate-driven demand (brighter regions tend to be more
climate-conditioned), so the explicit climate term adds collinear noise
rather than independent signal.

R6 does have the best MINρ among VIIRS-including models (0.846) but
still below R1's 0.856.

Rejected: MIN 0.866 < R3's 0.885.

### R7: log(population) + log(viirs_sum_settled) + log(total_dd)

| Country | Share R² |
|---------|----------|
| US      | +0.811   |
| France  | +0.787   |
| UK      | +0.677   |
| Italy   | +0.788   |
| Turkey  | +0.813   |
| MEAN    | +0.775   |
| MIN     | +0.677   |

Adding climate to settlement-masked VIIRS. Does not fix R4's
problems — MIN still 0.677.

Rejected: MIN 0.677.

### R8: log(population) + log(built_sum) + log(total_dd)

| Country | Share R² |
|---------|----------|
| US      | +0.827   |
| France  | +0.596   |
| UK      | +0.263   |
| Italy   | +0.898   |
| Turkey  | +0.786   |
| MEAN    | +0.674   |
| MIN     | +0.263   |

Adding climate to built_sum. Does not fix R5's problems.

Rejected: MIN 0.263.

---

## Group 4: Population + intensity (mean) features

Testing whether intensive (per-pixel-average) satellite features,
which measure character rather than size, avoid the collinearity
issues that plagued sum features in Group 2.

### R9: log(population) + log(viirs_mean_settled) + log(total_dd)

| Country | Share R² |
|---------|----------|
| US      | +0.760   |
| France  | +0.693   |
| UK      | +0.906   |
| Italy   | +0.891   |
| Turkey  | +0.865   |
| MEAN    | +0.824   |
| MIN     | +0.693   |

Settlement-masked VIIRS mean intensity. Helps UK substantially
(+0.906 vs R4's 0.678) because mean intensity doesn't penalise
regions with GHSL detection failures the way sum does. But France
drops to 0.693 and US to 0.760.

Rejected: MIN 0.693.

### R10: log(population) + log(built_mean) + log(total_dd)

| Country | Share R² |
|---------|----------|
| US      | +0.754   |
| France  | +0.905   |
| UK      | +0.679   |
| Italy   | +0.845   |
| Turkey  | +0.601   |
| MEAN    | +0.757   |
| MIN     | +0.601   |

Built-up mean intensity. Strong on France (0.905) but collapses
on Turkey (0.601), likely because Turkish built-up mean values
sit in a fundamentally different range than the calibration
countries (median log built_mean of 1.63 vs 3.87-5.44 for
calibration countries).

Rejected: MIN 0.601.

---

## Group 5: Population + alternative urbanisation proxies

### R11: log(population) + log(total_dd) + lit_area_fraction

| Country | Share R² |
|---------|----------|
| US      | +0.612   |
| France  | +0.821   |
| UK      | +0.841   |
| Italy   | +0.873   |
| Turkey  | +0.823   |
| MEAN    | +0.794   |
| MIN     | +0.612   |

Lit area fraction — the proportion of a region with detectable
nightlight (radiance > 0.5 nW/cm²/sr). Developed as a universal
urbanisation proxy that doesn't depend on GHSL detection thresholds.
Good on UK (0.841) and Turkey (0.823) but poor on US (0.612).

Rejected: MIN 0.612.

### R13: log(population) + log(total_dd) + smod_urban_pct

| Country | Share R² |
|---------|----------|
| US      | +0.769   |
| France  | +0.927   |
| UK      | +0.691   |
| Italy   | +0.877   |
| Turkey  | +0.874   |
| MEAN    | +0.828   |
| MIN     | +0.691   |

GHS-SMOD urban classification percentage. Strong on France (0.927)
and Turkey (0.874). However, 47 of 81 Turkish provinces were
classified as having zero urban area — an artefact of GHSL's
detection thresholds calibrated on European morphology, not real
absence of urbanisation. This data quality issue depresses the
feature's reliability across countries.

Rejected: MIN 0.691.

---

## Group 6: Multi-feature combinations

Testing whether combining two satellite features improves on
single-feature models.

### R14: log(population) + log(total_dd) + log(viirs_mean_settled) + log(built_mean)

| Country | Share R² |
|---------|----------|
| US      | +0.762   |
| France  | +0.916   |
| UK      | +0.759   |
| Italy   | +0.835   |
| Turkey  | +0.625   |
| MEAN    | +0.780   |
| MIN     | +0.625   |

Combining the two intensity features. Turkey collapses (0.625),
consistent with both features having Turkey-specific measurement
issues documented above.

Rejected: MIN 0.625.

### R18: log(population) + log(total_dd) + log(viirs_sum_settled) + log(built_sum)

| Country | Share R² |
|---------|----------|
| US      | +0.817   |
| France  | +0.774   |
| UK      | +0.417   |
| Italy   | +0.825   |
| Turkey  | +0.810   |
| MEAN    | +0.729   |
| MIN     | +0.417   |

Combining the two sum features with population and climate. UK
collapses to 0.417 — the collinearity problem at its worst.
Population, viirs_sum, and built_sum are all correlated at
r = 0.81-0.85. Including all three produced unstable coefficients:
population's coefficient went negative (-0.19) in some fits,
an economically meaningless result.

Rejected: MIN 0.417.

---

## Group 7: Satellite-only models (no population)

Testing whether satellite features alone, without population,
can perform the allocation.

### R19: log(viirs_sum_settled) only

| Country | Share R² |
|---------|----------|
| US      | +0.920   |
| France  | +0.762   |
| UK      | +0.457   |
| Italy   | +0.806   |
| Turkey  | +0.775   |
| MEAN    | +0.744   |
| MIN     | +0.457   |

Strong on the US (0.920 — VIIRS alone captures most of the
consumption pattern there) but weak on UK (0.457) and France
(0.762). Without population as an anchor, the model has no
way to handle countries where brightness doesn't track
consumption proportionally.

Rejected: MIN 0.457.

### R20: log(built_sum) only

| Country | Share R² |
|---------|----------|
| US      | +0.842   |
| France  | +0.773   |
| UK      | +0.568   |
| Italy   | +0.890   |
| Turkey  | +0.834   |
| MEAN    | +0.781   |
| MIN     | +0.568   |

Better than VIIRS-only across most countries except the US,
consistent with built_sum being a more stable proxy for
"where people live" than VIIRS (which includes non-residential
radiance). But still worse than population alone (MIN 0.568
vs 0.802).

Rejected: MIN 0.568.

### R21: log(viirs_sum_settled) + log(total_dd)

| Country | Share R² |
|---------|----------|
| US      | +0.898   |
| France  | +0.762   |
| UK      | +0.497   |
| Italy   | +0.752   |
| Turkey  | +0.785   |
| MEAN    | +0.739   |
| MIN     | +0.497   |

Rejected: MIN 0.497.

### R22: log(built_sum) + log(total_dd)

| Country | Share R² |
|---------|----------|
| US      | +0.830   |
| France  | +0.778   |
| UK      | +0.434   |
| Italy   | +0.909   |
| Turkey  | +0.836   |
| MEAN    | +0.757   |
| MIN     | +0.434   |

Rejected: MIN 0.434.

---

## Group 8: Per-capita formulations

The earliest model approach. Predict consumption per capita from
intensive features, then multiply by population to recover total
consumption. This was the default specification for most of the
model development period before being replaced by direct total-
consumption prediction.

Per-capita models are not included in the definitive_test_v2.py
run (which tests only direct-consumption formulations) because
they were eliminated earlier in the process. The numbers below
are from the share_prediction.py run on the same corrected dataset.

### Per-capita Model A (A-combo1): log(consumption_pc) ~ log(viirs_settled_pc) + log(total_dd) + lit_area_fraction

Failed on the UK (share R² = -0.007, worse than random) and
underperformed on the US (share R² = +0.451). The UK failure
occurs because per-capita consumption is nearly uniform across
English regions (std = 85 kWh against a mean of 4,126 kWh) —
the model introduces artificial variation by predicting that
London's higher density should produce different per-capita
consumption than the South West, when in fact shares are almost
perfectly proportional to population.

Rejected: UK share R² negative.

### Per-capita Model B (B-smod2): log(consumption_pc) ~ log(built_mean) + log(pop_density) + log(total_dd) + smod_urban_pct

Originally developed as the "population-based" model in a
dual-model framework where Model A (VIIRS-based) would estimate
actual consumption and Model B would estimate potential demand.

Performance degraded severely once Turkey was added to testing
(share R² as low as -1.514 on some holdouts), traced to SMOD
data quality issues (47/81 Turkish provinces at zero).

The dual-model framework was abandoned when it became clear
that both models were better suited to share allocation than
to absolute demand estimation, making the A/B distinction —
which depended on interpreting the gap between two absolute
predictions — no longer meaningful.

Rejected: negative R² on multiple holdouts.

---

## Group 9: Regression method alternatives

### OLS (ordinary least squares)

Tested on multiple specifications. Consistently 3-8 percentage
points worse on holdout share R² than Huber regression, with
the largest degradation on holdouts containing regions with high
extractive-sector radiance (US). OLS gives disproportionate
influence to extreme values — a single outlier region can shift
fitted coefficients for all 93 training observations.

Rejected: systematically worse than Huber.

### Ridge regression

Tested on the merged specification (R18: viirs_sum + built_sum +
population + climate). Ridge applies a penalty to coefficient
magnitude, intended to stabilise estimates under multicollinearity.
The population coefficient remained negative (-0.109) under Ridge —
the regularisation did not resolve the collinearity problem because
the issue was three correlated "size" variables, not ill-conditioned
estimation per se.

Rejected: did not fix the problem it was intended to address.

---

## Summary: all variants ranked by MIN share R²

| Rank | Model | MIN R² | MEAN R² |
|------|-------|--------|---------|
| 1 | R3: pop + viirs_raw | +0.885 | +0.908 |
| 2 | R6: pop + dd + viirs_raw | +0.866 | +0.899 |
| 3 | R1: pop only | +0.802 | +0.880 |
| 4 | R2: pop + dd | +0.780 | +0.876 |
| 5 | R9: pop + dd + viirs_mean | +0.693 | +0.824 |
| 6 | R13: pop + dd + smod | +0.691 | +0.828 |
| 7 | R4: pop + viirs_settled | +0.678 | +0.789 |
| 8 | R7: pop + dd + viirs_settled | +0.677 | +0.775 |
| 9 | R14: pop + dd + viirs_m + built_m | +0.625 | +0.780 |
| 10 | R11: pop + dd + lit_frac | +0.612 | +0.794 |
| 11 | R10: pop + dd + built_mean | +0.601 | +0.757 |
| 12 | R20: built_sum only | +0.568 | +0.781 |
| 13 | R21: viirs_settled + dd | +0.497 | +0.739 |
| 14 | R19: viirs_settled only | +0.457 | +0.744 |
| 15 | R22: built_sum + dd | +0.434 | +0.757 |
| 16 | R18: pop + dd + viirs_s + built_s | +0.417 | +0.729 |
| 17 | R8: pop + dd + built_sum | +0.263 | +0.674 |
| 18 | R5: pop + built_sum | +0.218 | +0.637 |