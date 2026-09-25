"""
Final Model — Locked R3 Specification
=========================================
The specification reported in the paper (Sections 4.1, 5.5):

  log(consumption) ~ log(population) + log(viirs_sum_raw)

Trained on US, France, UK, Italy (93 regions). Validated independently
on Turkey (never included in training).

Usage (run from repo root):
  python3 models/final_model.py
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import HuberRegressor
from sklearn.metrics import r2_score
from scipy.stats import spearmanr
import pickle
import os

DATA_PATH = "data/processed/dataset_5country_corrected_v2.csv"
OUTPUT_DIR = "models"
RESULTS_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

TRAIN_COUNTRIES = ["US", "France", "UK", "Italy"]
VALIDATE_COUNTRY = "Turkey"

FEATURES = ["log_population", "log_viirs_sum"]
TARGET = "log_consumption"


def add_features(df):
    df = df.copy()
    df["log_consumption"] = np.log(df["consumption_gwh"].clip(lower=1))
    df["log_population"] = np.log(df["population"].clip(lower=1))
    df["log_viirs_sum"] = np.log(df["viirs_sum_rad"].clip(lower=1))
    return df


def main():
    df = pd.read_csv(DATA_PATH)
    df = add_features(df)
    df = df.dropna(subset=FEATURES + [TARGET])

    train = df[df.country.isin(TRAIN_COUNTRIES)]

    model = HuberRegressor(epsilon=1.35, max_iter=1000)
    model.fit(train[FEATURES].values, train[TARGET].values)

    print("Final model (R3): log(consumption) ~ log(population) + log(viirs_sum_raw)")
    print(f"Trained on: {TRAIN_COUNTRIES} ({len(train)} regions)")
    for f, c in zip(FEATURES, model.coef_):
        print(f"  {f:20s} {c:+.4f}")
    print(f"  {'intercept':20s} {model.intercept_:+.4f}")

    with open(f"{OUTPUT_DIR}/final_model.pkl", "wb") as f:
        pickle.dump({"model": model, "features": FEATURES, "target": TARGET}, f)

    # Independent validation on Turkey
    val = df[df.country == VALIDATE_COUNTRY].copy()
    pred = np.exp(model.predict(val[FEATURES].values))
    actual = val["consumption_gwh"].values
    a_s, p_s = actual / actual.sum(), pred / pred.sum()
    r2 = r2_score(a_s, p_s)
    rho, _ = spearmanr(actual, pred)

    print(f"\nIndependent validation (Turkey):")
    print(f"  Share R² = {r2:+.3f}  (paper reports +0.887)")
    print(f"  Spearman ρ = {rho:+.3f}  (paper reports +0.838)")

    # Save predictions
    val["predicted_gwh"] = pred
    val["actual_gwh"] = actual
    val["predicted_share"] = p_s
    val["actual_share"] = a_s
    val[["country", "region_name", "actual_gwh", "predicted_gwh",
         "actual_share", "predicted_share"]].to_csv(
        f"{RESULTS_DIR}/final_model_predictions.csv", index=False
    )

    # Save report
    with open(f"{RESULTS_DIR}/final_model_report.txt", "w") as f:
        f.write("FINAL MODEL (R3)\n")
        f.write("log(consumption) ~ log(population) + log(viirs_sum_raw)\n\n")
        f.write(f"Trained on: {TRAIN_COUNTRIES} ({len(train)} regions)\n\n")
        f.write("Coefficients:\n")
        for feat, c in zip(FEATURES, model.coef_):
            f.write(f"  {feat:20s} {c:+.4f}\n")
        f.write(f"  {'intercept':20s} {model.intercept_:+.4f}\n\n")
        f.write(f"Independent validation (Turkey):\n")
        f.write(f"  Share R² = {r2:+.3f}\n")
        f.write(f"  Spearman ρ = {rho:+.3f}\n")

    print(f"\nSaved to:")
    print(f"  {OUTPUT_DIR}/final_model.pkl")
    print(f"  {RESULTS_DIR}/final_model_predictions.csv")
    print(f"  {RESULTS_DIR}/final_model_report.txt")


if __name__ == "__main__":
    main()