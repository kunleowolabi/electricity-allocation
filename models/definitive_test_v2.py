"""
Definitive Allocation Test V2 — Corrected Dataset
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import HuberRegressor
from sklearn.metrics import r2_score
from scipy.stats import spearmanr
import warnings

warnings.filterwarnings('ignore')

OUTPUT_DIR = "model_outputs"
TRAIN = ["US", "France", "UK", "Italy"]
ALL5 = TRAIN + ["Turkey"]


def add_features(df):
    df = df.copy()
    df["log_consumption"] = np.log(df["consumption_gwh"].clip(lower=1))
    df["log_viirs_sum"] = np.log(df["viirs_sum_rad"].clip(lower=1))
    df["log_viirs_sum_settled"] = np.log(df["viirs_sum_settled"].clip(lower=1))
    df["log_viirs_mean_settled"] = np.log(df["viirs_mean_settled"].clip(lower=0.01))
    df["log_built_sum"] = np.log(df["built_up_sum"].clip(lower=1))
    df["log_built_mean"] = np.log(df["built_up_mean"].clip(lower=0.01))
    df["log_population"] = np.log(df["population"].clip(lower=1))
    df["log_total_dd"] = np.log1p(df["total_dd"])
    df["lit_logit"] = np.log(df["lit_area_fraction"].clip(0.001, 0.999) / (1 - df["lit_area_fraction"].clip(0.001, 0.999)))
    return df


def test_regression(df, label, features, target="log_consumption"):
    r2s = []
    rhos = []
    for holdout in ALL5:
        train_countries = [c for c in TRAIN if c != holdout] if holdout in TRAIN else TRAIN
        train = df[df.country.isin(train_countries)].dropna(subset=features + [target])
        test = df[df.country == holdout].dropna(subset=features + [target])
        if len(test) < 2 or len(train) < 5:
            r2s.append(np.nan)
            rhos.append(np.nan)
            continue
        reg = HuberRegressor(epsilon=1.35, max_iter=1000)
        reg.fit(train[features].values, train[target].values)
        pred_gwh = np.exp(reg.predict(test[features].values))
        actual = test["consumption_gwh"].values
        a_s = actual / actual.sum()
        p_s = pred_gwh / pred_gwh.sum()
        r2s.append(r2_score(a_s, p_s))
        rho, _ = spearmanr(actual, pred_gwh)
        rhos.append(rho)

    valid_r2 = [r for r in r2s if not np.isnan(r)]
    valid_rho = [r for r in rhos if not np.isnan(r)]

    print(f"  {label:<55}", end="")
    for r2 in r2s:
        if np.isnan(r2):
            print(f" {'N/A':>7}", end="")
        else:
            print(f" {r2:>+7.3f}", end="")
    print(f" {np.mean(valid_r2):>+7.3f} {min(valid_r2):>+7.3f} {min(valid_rho):>+7.3f}")


def main():
    print("=" * 70)
    print("DEFINITIVE ALLOCATION TEST V2 — CORRECTED DATASET")
    print("=" * 70)

    df = pd.read_csv(f"{OUTPUT_DIR}/dataset_5country_corrected_v2.csv")
    df = add_features(df)

    print(f"\nDataset: {len(df)} rows")
    for c in ALL5:
        sub = df[df.country == c]
        ppc = (sub.consumption_gwh.sum()*1e6)/sub.population.sum()
        print(f"  {c:10s} {len(sub)} regions  {ppc:,.0f} kWh/capita")

    # PART A: DIRECT PROPORTIONAL
    print(f"\n{'=' * 70}")
    print("PART A: DIRECT PROPORTIONAL (no regression)")
    print(f"{'=' * 70}")

    alloc_features = [
        ("population", "population"),
        ("viirs_sum_settled", "viirs_sum_settled"),
        ("built_sum", "built_up_sum"),
        ("viirs_mean x pop", None),
        ("built_mean x pop", None),
        ("lit_frac x pop", None),
    ]

    print(f"\n  {'Feature':<55}", end="")
    for c in ALL5:
        print(f" {c:>7}", end="")
    print(f" {'MEAN':>7} {'MIN':>7}")
    print(f"  {'-' * 105}")

    for label, col in alloc_features:
        r2s = []
        for c in ALL5:
            sub = df[df.country == c].dropna(subset=["consumption_gwh"])
            actual_share = sub["consumption_gwh"].values / sub["consumption_gwh"].sum()
            if col is not None:
                vals = sub[col].values.clip(min=0)
            elif label == "viirs_mean x pop":
                vals = (sub["viirs_mean_settled"].fillna(0) * sub["population"]).values.clip(min=0)
            elif label == "built_mean x pop":
                vals = (sub["built_up_mean"] * sub["population"]).values.clip(min=0)
            elif label == "lit_frac x pop":
                vals = (sub["lit_area_fraction"] * sub["population"]).values.clip(min=0)
            pred_share = vals / vals.sum() if vals.sum() > 0 else np.ones(len(vals)) / len(vals)
            r2s.append(r2_score(actual_share, pred_share))

        print(f"  {label:<55}", end="")
        for r2 in r2s:
            print(f" {r2:>+7.3f}", end="")
        print(f" {np.mean(r2s):>+7.3f} {min(r2s):>+7.3f}")

    # PART B: REGRESSION LOCO — direct consumption only
    print(f"\n{'=' * 70}")
    print("PART B: REGRESSION LOCO — Share R2 (direct consumption models only)")
    print(f"{'=' * 70}")

    header = f"\n  {'Model':<55}"
    for c in ALL5:
        header += f" {c:>7}"
    header += f" {'MEAN':>7} {'MIN':>7} {'MINrho':>7}"
    print(header)
    print(f"  {'-' * 115}")

    models = [
        # Baselines
        ("R1:  pop", ["log_population"]),
        ("R2:  pop + dd", ["log_population", "log_total_dd"]),

        # Pop + single satellite (sum)
        ("R3:  pop + viirs_sum_raw", ["log_viirs_sum", "log_population"]),
        ("R4:  pop + viirs_sum_settled", ["log_viirs_sum_settled", "log_population"]),
        ("R5:  pop + built_sum", ["log_built_sum", "log_population"]),

        # Pop + dd + single satellite (sum)
        ("R6:  pop + dd + viirs_sum_raw", ["log_viirs_sum", "log_population", "log_total_dd"]),
        ("R7:  pop + dd + viirs_sum_settled", ["log_viirs_sum_settled", "log_population", "log_total_dd"]),
        ("R8:  pop + dd + built_sum", ["log_built_sum", "log_population", "log_total_dd"]),

        # Pop + dd + single satellite (mean/intensity)
        ("R9:  pop + dd + viirs_mean_settled", ["log_viirs_mean_settled", "log_population", "log_total_dd"]),
        ("R10: pop + dd + built_mean", ["log_built_mean", "log_population", "log_total_dd"]),

        # Pop + dd + lit_area_fraction
        ("R11: pop + dd + lit_frac", ["log_population", "log_total_dd", "lit_area_fraction"]),
        ("R12: pop + dd + lit_logit", ["log_population", "log_total_dd", "lit_logit"]),

        # Pop + dd + smod
        ("R13: pop + dd + smod_urban", ["log_population", "log_total_dd", "smod_urban_pct"]),

        # Pop + dd + two satellite features
        ("R14: pop + dd + viirs_mean + built_mean", ["log_viirs_mean_settled", "log_built_mean", "log_population", "log_total_dd"]),
        ("R15: pop + dd + viirs_mean + lit_frac", ["log_viirs_mean_settled", "log_population", "log_total_dd", "lit_area_fraction"]),
        ("R16: pop + dd + built_mean + lit_frac", ["log_built_mean", "log_population", "log_total_dd", "lit_area_fraction"]),
        ("R17: pop + dd + viirs_mean + smod", ["log_viirs_mean_settled", "log_population", "log_total_dd", "smod_urban_pct"]),

        # Merged sum features
        ("R18: pop + dd + viirs_sum_set + built_sum", ["log_viirs_sum_settled", "log_built_sum", "log_population", "log_total_dd"]),

        # No-population models (satellite only)
        ("R19: viirs_sum_settled only", ["log_viirs_sum_settled"]),
        ("R20: built_sum only", ["log_built_sum"]),
        ("R21: viirs_sum_settled + dd", ["log_viirs_sum_settled", "log_total_dd"]),
        ("R22: built_sum + dd", ["log_built_sum", "log_total_dd"]),
    ]

    for label, features in models:
        test_regression(df, label, features)

    print(f"\nDone!")


if __name__ == "__main__":
    main()