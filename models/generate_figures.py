"""
Generate Paper Figures
=======================
Produces F1-F4 for the working paper, all from the verified
corrected dataset and the definitive test results.

Usage:
  python3 generate_figures.py
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import HuberRegressor
from sklearn.metrics import r2_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os

OUTPUT_DIR = "model_outputs"
FIG_DIR = "paper/figures"
os.makedirs(FIG_DIR, exist_ok=True)

TRAIN = ["US", "France", "UK", "Italy"]
ALL5 = TRAIN + ["Turkey"]
COLORS = {"US": "#1f77b4", "France": "#ff7f0e", "UK": "#2ca02c", "Italy": "#d62728", "Turkey": "#9467bd"}


def add_features(df):
    df = df.copy()
    df["log_consumption"] = np.log(df["consumption_gwh"].clip(lower=1))
    df["log_population"] = np.log(df["population"].clip(lower=1))
    df["log_viirs_sum"] = np.log(df["viirs_sum_rad"].clip(lower=1))
    return df


def get_predictions(df):
    """Run LOCO + Turkey holdout, return all predictions."""
    features = ["log_population", "log_viirs_sum"]
    target = "log_consumption"
    rows = []

    for holdout in ALL5:
        train_countries = [c for c in TRAIN if c != holdout] if holdout in TRAIN else TRAIN
        train = df[df.country.isin(train_countries)].dropna(subset=features + [target])
        test = df[df.country == holdout].dropna(subset=features + [target])

        if len(test) < 2:
            continue

        reg = HuberRegressor(epsilon=1.35, max_iter=1000)
        reg.fit(train[features].values, train[target].values)
        pred_gwh = np.exp(reg.predict(test[features].values))
        actual_gwh = test["consumption_gwh"].values

        actual_share = actual_gwh / actual_gwh.sum()
        pred_share = pred_gwh / pred_gwh.sum()

        # Also get R1 (population only) shares
        pop_share = test["population"].values / test["population"].values.sum()

        for i, (_, row) in enumerate(test.iterrows()):
            rows.append({
                "country": row["country"],
                "region": row["region_name"],
                "actual_gwh": actual_gwh[i],
                "pred_gwh": pred_gwh[i],
                "actual_share": actual_share[i],
                "pred_share": pred_share[i],
                "pop_share": pop_share[i],
                "share_error_r3": pred_share[i] - actual_share[i],
                "ape_r3": abs(pred_share[i] - actual_share[i]) / actual_share[i] * 100,
                "validation": "Independent" if holdout == "Turkey" else "LOCO",
            })

    return pd.DataFrame(rows)


def fig_f1(preds):
    """F1: Predicted vs actual shares, all 5 countries."""
    fig, ax = plt.subplots(figsize=(8, 7))

    for c in ALL5:
        sub = preds[preds.country == c]
        marker = "^" if c == "Turkey" else "o"
        ax.scatter(
            sub.actual_share * 100, sub.pred_share * 100,
            c=COLORS[c], label=c, alpha=0.7, s=45, marker=marker,
            edgecolors="white", linewidth=0.5,
        )

    max_val = max(preds.actual_share.max(), preds.pred_share.max()) * 100
    ax.plot([0, max_val * 1.05], [0, max_val * 1.05], "k--", alpha=0.25, linewidth=1)

    ax.set_xlabel("Actual share of national consumption (%)", fontsize=11)
    ax.set_ylabel("Predicted share (%)", fontsize=11)
    ax.legend(fontsize=10, framealpha=0.9)
    ax.set_xlim(0, max_val * 1.05)
    ax.set_ylim(0, max_val * 1.05)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.15)

    plt.tight_layout()
    plt.savefig(f"{FIG_DIR}/F1_predicted_vs_actual_shares.png", dpi=200)
    plt.close()
    print(f"  Saved F1")


def fig_f2(preds):
    """F2: Share error distribution by country (box plot)."""
    fig, ax = plt.subplots(figsize=(9, 5))

    data_by_country = []
    labels = []
    box_colors = []
    for c in ALL5:
        sub = preds[preds.country == c]
        data_by_country.append(sub.share_error_r3.values * 100)
        labels.append(f"{c}\n(n={len(sub)})")
        box_colors.append(COLORS[c])

    bp = ax.boxplot(
        data_by_country, tick_labels=labels, patch_artist=True,
        widths=0.6, showfliers=True,
        flierprops=dict(marker="o", markersize=4, alpha=0.5),
    )
    for patch, color in zip(bp["boxes"], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)

    ax.axhline(y=0, color="black", linestyle="--", alpha=0.3, linewidth=1)
    ax.set_ylabel("Share prediction error (percentage points)", fontsize=11)
    ax.grid(True, axis="y", alpha=0.15)

    plt.tight_layout()
    plt.savefig(f"{FIG_DIR}/F2_share_error_by_country.png", dpi=200)
    plt.close()
    print(f"  Saved F2")


def fig_f3(preds):
    """F3: MAPE by region-size tercile (bar chart)."""
    preds = preds.copy()
    preds["tercile"] = pd.qcut(preds["actual_share"], 3, labels=["Small\n(bottom third)", "Medium", "Large\n(top third)"])

    summary = preds.groupby("tercile", observed=True)["ape_r3"].agg(["mean", "median"]).reset_index()

    fig, ax = plt.subplots(figsize=(7, 5))

    x = range(len(summary))
    width = 0.35

    bars_mean = ax.bar(
        [i - width / 2 for i in x], summary["mean"], width,
        label="Mean APE", color="#1f77b4", alpha=0.7,
    )
    bars_median = ax.bar(
        [i + width / 2 for i in x], summary["median"], width,
        label="Median APE", color="#ff7f0e", alpha=0.7,
    )

    ax.set_xticks(list(x))
    ax.set_xticklabels(summary["tercile"], fontsize=11)
    ax.set_ylabel("Absolute percentage error on shares (%)", fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(True, axis="y", alpha=0.15)

    for bar in bars_mean:
        height = bar.get_height()
        ax.annotate(f"{height:.0f}%", xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
    for bar in bars_median:
        height = bar.get_height()
        ax.annotate(f"{height:.0f}%", xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(f"{FIG_DIR}/F3_mape_by_region_size.png", dpi=200)
    plt.close()
    print(f"  Saved F3")


def fig_f4(df):
    """F4: Feature selection summary — MIN R² for all tested variants."""

    features_list = [
        ("R1:  pop", ["log_population"]),
        ("R2:  pop + dd", ["log_population", "log_total_dd"]),
        ("R3:  pop + viirs_raw", ["log_population", "log_viirs_sum"]),
        ("R4:  pop + viirs_settled", ["log_population", "log_viirs_sum_settled"]),
        ("R5:  pop + built_sum", ["log_population", "log_built_sum"]),
        ("R6:  pop + dd + viirs_raw", ["log_population", "log_viirs_sum", "log_total_dd"]),
        ("R7:  pop + dd + viirs_settled", ["log_population", "log_viirs_sum_settled", "log_total_dd"]),
        ("R8:  pop + dd + built_sum", ["log_population", "log_built_sum", "log_total_dd"]),
        ("R9:  pop + dd + viirs_mean", ["log_population", "log_viirs_mean_settled", "log_total_dd"]),
        ("R10: pop + dd + built_mean", ["log_population", "log_built_mean", "log_total_dd"]),
        ("R11: pop + dd + lit_frac", ["log_population", "log_total_dd", "lit_area_fraction"]),
        ("R13: pop + dd + smod", ["log_population", "log_total_dd", "smod_urban_pct"]),
        ("R14: pop + dd + viirs_m + built_m", ["log_viirs_mean_settled", "log_built_mean", "log_population", "log_total_dd"]),
        ("R18: pop + dd + viirs_s + built_s", ["log_viirs_sum_settled", "log_built_sum", "log_population", "log_total_dd"]),
        ("R19: viirs_settled only", ["log_viirs_sum_settled"]),
        ("R20: built_sum only", ["log_built_sum"]),
    ]

    # Need additional log features
    df = df.copy()
    df["log_viirs_sum_settled"] = np.log(df["viirs_sum_settled"].clip(lower=1))
    df["log_viirs_mean_settled"] = np.log(df["viirs_mean_settled"].clip(lower=0.01))
    df["log_built_sum"] = np.log(df["built_up_sum"].clip(lower=1))
    df["log_built_mean"] = np.log(df["built_up_mean"].clip(lower=0.01))
    df["log_total_dd"] = np.log1p(df["total_dd"])

    results = []
    for label, features in features_list:
        min_r2 = 1.0
        for holdout in ALL5:
            train_countries = [c for c in TRAIN if c != holdout] if holdout in TRAIN else TRAIN
            train = df[df.country.isin(train_countries)].dropna(subset=features + ["log_consumption"])
            test = df[df.country == holdout].dropna(subset=features + ["log_consumption"])
            if len(test) < 2:
                continue
            reg = HuberRegressor(epsilon=1.35, max_iter=1000)
            reg.fit(train[features].values, train["log_consumption"].values)
            pred = np.exp(reg.predict(test[features].values))
            actual = test["consumption_gwh"].values
            a_s = actual / actual.sum()
            p_s = pred / pred.sum()
            r2 = r2_score(a_s, p_s)
            min_r2 = min(min_r2, r2)
        results.append({"model": label, "min_r2": min_r2})

    results_df = pd.DataFrame(results).sort_values("min_r2", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 7))

    y_pos = range(len(results_df))
    bars = ax.barh(
        y_pos, results_df["min_r2"],
        color=["#2ca02c" if "R3" in m else "#cccccc" for m in results_df["model"]],
        alpha=0.8, height=0.7,
    )

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(results_df["model"], fontsize=9)
    ax.set_xlabel("Minimum share R² across all 5 holdout countries", fontsize=11)
    ax.axvline(x=0, color="black", linewidth=0.8)
    ax.grid(True, axis="x", alpha=0.15)

    # Mark R1 baseline
    r1_min = results_df[results_df.model.str.startswith("R1:")]["min_r2"].values[0]
    ax.axvline(x=r1_min, color="#d62728", linestyle="--", alpha=0.6, linewidth=1.2)
    ax.annotate("R1 baseline", xy=(r1_min, len(results_df) - 1), fontsize=9, color="#d62728",
                xytext=(10, 0), textcoords="offset points", va="center")

    plt.tight_layout()
    plt.savefig(f"{FIG_DIR}/F4_feature_selection_min_r2.png", dpi=200)
    plt.close()
    print(f"  Saved F4")


def main():
    print("Generating paper figures...")
    print()

    df = pd.read_csv(f"{OUTPUT_DIR}/dataset_5country_corrected_v2.csv")
    df = add_features(df)

    # Get all predictions for F1-F3
    preds = get_predictions(df)

    fig_f1(preds)
    fig_f2(preds)
    fig_f3(preds)
    fig_f4(df)

    print(f"\nAll figures saved to {FIG_DIR}/")


if __name__ == "__main__":
    main()