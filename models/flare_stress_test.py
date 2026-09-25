"""
Texas / North Dakota Flare Stress Test
=========================================
Uses the ONE calibration country with real, verified ground-truth
consumption data AND real gas flaring: the US.

Train on France + UK + Italy (Turkey excluded as before), predict
US state shares, and check specifically whether flare-heavy states
(Texas, North Dakota, Oklahoma, New Mexico, Louisiana) are over- or
under-allocated relative to their ACTUAL known consumption share.

This directly tests each VIIRS treatment against ground truth,
rather than speculating about Nigeria with no reference point.

Usage:
  python3 flare_stress_test.py
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import HuberRegressor

OUTPUT_DIR = "model_outputs"
TRAIN_EXCL_US = ["France", "UK", "Italy"]  # Turkey stays excluded throughout, as decided

# Known flare-heavy US states (EIA/EPA gas flaring data) vs population-comparable
# non-flaring states, for direct comparison
FLARE_STATES = ["Texas", "North Dakota", "Oklahoma", "New Mexico", "Louisiana"]
COMPARISON_STATES = ["California", "New York", "Florida", "Illinois", "Ohio"]  # similar pop scale, low flare


def main():
    print("=" * 70)
    print("FLARE STRESS TEST — Texas/North Dakota vs Ground Truth")
    print("=" * 70)

    df = pd.read_csv(f"{OUTPUT_DIR}/dataset_5country_corrected_v2.csv")

    df["log_consumption"] = np.log(df["consumption_gwh"].clip(lower=1))
    df["log_population"] = np.log(df["population"].clip(lower=1))
    df["log_total_dd"] = np.log1p(df["total_dd"])
    df["log_viirs_sum_raw"] = np.log(df["viirs_sum_rad"].clip(lower=1))
    df["log_viirs_sum_settled"] = np.log(df["viirs_sum_settled"].clip(lower=1))
    df["log_viirs_mean_settled"] = np.log(df["viirs_mean_settled"].clip(lower=0.01))
    df["log_built_up_sum"] = np.log(df["built_up_sum"].clip(lower=1))

    p95 = df["viirs_sum_rad"].quantile(0.95)
    df["viirs_sum_raw_capped"] = df["viirs_sum_rad"].clip(upper=p95)
    df["log_viirs_sum_raw_capped"] = np.log(df["viirs_sum_raw_capped"].clip(lower=1))

    train = df[df.country.isin(TRAIN_EXCL_US)]
    us = df[df.country == "US"].copy()

    versions = {
        "V1: Raw VIIRS sum": ["log_population", "log_viirs_sum_raw", "log_total_dd"],
        "V2: Settlement-masked VIIRS sum": ["log_population", "log_viirs_sum_settled", "log_total_dd"],
        "V3: Settlement-masked VIIRS mean": ["log_population", "log_viirs_mean_settled", "log_total_dd"],
        "V4: Population only": ["log_population", "log_total_dd"],
        "V5: Raw VIIRS capped at p95": ["log_population", "log_viirs_sum_raw_capped", "log_total_dd"],
        "V6: built_up_sum": ["log_population", "log_built_up_sum", "log_total_dd"],
    }

    # Actual shares (ground truth)
    us["actual_share_pct"] = (us["consumption_gwh"] / us["consumption_gwh"].sum()) * 100

    results = {}

    for label, features in versions.items():
        train_clean = train.dropna(subset=features + ["log_consumption"])
        model = HuberRegressor(epsilon=1.35, max_iter=1000)
        model.fit(train_clean[features].values, train_clean["log_consumption"].values)

        us_clean = us.dropna(subset=features).copy()
        pred_log = model.predict(us_clean[features].values)
        pred_relative = np.exp(pred_log)
        us_clean["predicted_share_pct"] = (pred_relative / pred_relative.sum()) * 100
        us_clean["error_pp"] = us_clean["predicted_share_pct"] - us_clean["actual_share_pct"]

        results[label] = us_clean.set_index("region_name")[["actual_share_pct", "predicted_share_pct", "error_pp"]]

    # ── Print comparison table for flare states ──
    print(f"\n{'=' * 70}")
    print("FLARE-HEAVY STATES — Predicted vs Actual Share (percentage points error)")
    print("Positive error = model OVER-allocates (flare inflation)")
    print(f"{'=' * 70}")

    for state in FLARE_STATES:
        print(f"\n  {state}:")
        actual = None
        for label in versions:
            if state in results[label].index:
                row = results[label].loc[state]
                actual = row["actual_share_pct"]
                print(f"    {label:<40} actual={row['actual_share_pct']:>6.2f}%  pred={row['predicted_share_pct']:>6.2f}%  error={row['error_pp']:>+6.2f}pp")

    print(f"\n{'=' * 70}")
    print("COMPARISON STATES (similar population, low flare) — sanity check")
    print("These should NOT show large errors if the fix is working correctly")
    print(f"{'=' * 70}")

    for state in COMPARISON_STATES:
        print(f"\n  {state}:")
        for label in versions:
            if state in results[label].index:
                row = results[label].loc[state]
                print(f"    {label:<40} actual={row['actual_share_pct']:>6.2f}%  pred={row['predicted_share_pct']:>6.2f}%  error={row['error_pp']:>+6.2f}pp")

    # ── Summary: mean absolute error on flare states vs comparison states ──
    print(f"\n{'=' * 70}")
    print("SUMMARY — Mean |error| on flare states vs comparison states")
    print("A good flare-fix should show LOW error on flare states")
    print("WITHOUT increasing error on comparison states")
    print(f"{'=' * 70}")

    print(f"\n  {'Version':<40} {'Flare MAE':>12} {'Comparison MAE':>16} {'Overall US MAE':>16}")
    print(f"  {'-'*84}")

    for label in versions:
        r = results[label]
        flare_errs = [abs(r.loc[s, "error_pp"]) for s in FLARE_STATES if s in r.index]
        comp_errs = [abs(r.loc[s, "error_pp"]) for s in COMPARISON_STATES if s in r.index]
        overall_errs = r["error_pp"].abs().values

        print(f"  {label:<40} {np.mean(flare_errs):>11.2f}pp {np.mean(comp_errs):>15.2f}pp {np.mean(overall_errs):>15.2f}pp")

    print(f"\nDone!")


if __name__ == "__main__":
    main()