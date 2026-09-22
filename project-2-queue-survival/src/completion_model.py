"""
Step 3 - What predicts whether a project gets built?

TARGET
------
"Built within 7 years of the interconnection request", restricted to projects
that requested in 2018 or earlier. That restriction matters: a 2023 project has
not had 7 years to succeed, so including it would label a perfectly healthy
project as a failure. Every row in this model has had a full 7-year window.

y = 1  ->  reached commercial operation within 7 years
y = 0  ->  withdrawn, or still waiting, or took longer than 7 years

TWO MODELS, DELIBERATELY
------------------------
Model A uses only what is knowable the day the request is filed: technology,
region, size, service type, and the year. This is the one that can actually
forecast.

Model B adds whether the project ever signed an interconnection agreement. That
is far more predictive - and useless for forecasting, because it happens years
after the request. It is included to size how much of the outcome is determined
by clearing that one milestone, not to pretend it is a feature.

Reporting odds ratios rather than raw coefficients: an odds ratio of 2.0 means
the feature doubles the odds of being built, relative to the baseline category.
"""
import pathlib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Repo root, derived from this file's own location so the project runs
# anywhere after a clone rather than only on the machine that wrote it.
ROOT = str(pathlib.Path(__file__).resolve().parents[2]).replace("\\", "/")
SRC = ROOT + "/data/processed/survival_dataset.parquet"
OUTDIR = ROOT + "/project-2-queue-survival/output"

HORIZON_YEARS = 7
MAX_COHORT = 2018          # so every row has a full 7-year observation window
SEED = 42

df = pd.read_parquet(SRC)
df = df[df["region_reliable"]].copy()
df = df[df["cohort"] <= MAX_COHORT].copy()

df["built_7yr"] = ((df["event"] == 1) & (df["duration_years"] <= HORIZON_YEARS)).astype(int)
df["log_mw"] = np.log10(df["mw_1"])

# The categorical columns arrive as pandas nullable strings with real NAs in
# them (service type is often blank in the source queues). scikit-learn's
# encoder needs uniformly typed input, and "we don't know the service type" is
# genuinely informative here, so it becomes its own category rather than a drop.
for c in ["tech", "region", "service"]:
    df[c] = df[c].astype(object).where(df[c].notna(), "Unknown").astype(str)

print("=" * 88)
print("MODEL SCOPE")
print("=" * 88)
print("cohorts {}-{}, reliable regions only".format(int(df["cohort"].min()), MAX_COHORT))
print("rows                {:,}".format(len(df)))
print("built within 7 yrs  {:,}  ({:.1f}%)".format(
    int(df["built_7yr"].sum()), df["built_7yr"].mean() * 100))

CAT = ["tech", "region", "service"]
NUM = ["log_mw", "cohort"]


def fit(features, label):
    X = df[features]
    y = df["built_7yr"]
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=SEED, stratify=y)

    cats = [c for c in features if c in CAT]
    nums = [c for c in features if c in NUM or c == "has_ia"]

    pre = ColumnTransformer([
        ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), cats),
        ("num", StandardScaler(), nums),
    ])
    pipe = Pipeline([("pre", pre),
                     ("lr", LogisticRegression(max_iter=2000, C=1.0))])
    pipe.fit(X_tr, y_tr)

    p_te = pipe.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_te, p_te)
    brier = brier_score_loss(y_te, p_te)

    names = pipe.named_steps["pre"].get_feature_names_out()
    coefs = pipe.named_steps["lr"].coef_[0]
    odds = pd.DataFrame({
        "feature": [n.split("__", 1)[1] for n in names],
        "coef": coefs,
        "odds_ratio": np.exp(coefs),
    }).sort_values("odds_ratio", ascending=False)

    print()
    print("=" * 88)
    print(label)
    print("=" * 88)
    print("test AUC   {:.3f}   (0.5 = coin flip, 1.0 = perfect)".format(auc))
    print("Brier      {:.4f}   (lower is better; calibration + accuracy)".format(brier))
    print()
    print(odds.round(3).to_string(index=False))
    return pipe, odds, auc, brier, (X_te, y_te, p_te)


# ---------------------------------------------------------------------------
# Model A - knowable at request time
# ---------------------------------------------------------------------------
feat_a = CAT + NUM
pipe_a, odds_a, auc_a, brier_a, test_a = fit(
    feat_a, "MODEL A - using only what is known when the request is filed")
odds_a.round(4).to_csv(OUTDIR + "/model_a_odds_ratios.csv", index=False)

# ---------------------------------------------------------------------------
# Model B - adds the interconnection-agreement milestone
# ---------------------------------------------------------------------------
df["has_ia"] = df["has_ia"].astype(int)
feat_b = CAT + NUM + ["has_ia"]
pipe_b, odds_b, auc_b, brier_b, test_b = fit(
    feat_b, "MODEL B - adds 'signed an interconnection agreement' (NOT a forecast feature)")
odds_b.round(4).to_csv(OUTDIR + "/model_b_odds_ratios.csv", index=False)

print()
print("=" * 88)
print("WHAT THE COMPARISON SAYS")
print("=" * 88)
print("Model A AUC (request-time only)  {:.3f}".format(auc_a))
print("Model B AUC (with IA milestone)  {:.3f}".format(auc_b))
print("lift from knowing IA status      {:+.3f}".format(auc_b - auc_a))
print()
print("Read: project characteristics known at filing carry real but limited")
print("signal. Clearing the interconnection agreement is the milestone that")
print("actually separates projects that get built from ones that do not.")

# ---------------------------------------------------------------------------
# Calibration of Model A - are the predicted probabilities honest?
# ---------------------------------------------------------------------------
X_te, y_te, p_te = test_a
cal = pd.DataFrame({"p": p_te, "y": y_te.to_numpy()})
cal["bin"] = pd.qcut(cal["p"], 10, labels=False, duplicates="drop")
cal_tbl = (cal.groupby("bin")
             .agg(n=("y", "size"), predicted=("p", "mean"), actual=("y", "mean"))
             .reset_index())
cal_tbl[["predicted", "actual"]] = (cal_tbl[["predicted", "actual"]] * 100).round(1)
cal_tbl.to_csv(OUTDIR + "/model_a_calibration.csv", index=False)

print()
print("=" * 88)
print("MODEL A CALIBRATION  (decile of predicted probability, held-out set)")
print("=" * 88)
print(cal_tbl.to_string(index=False))
print()
print("If predicted and actual track each other down the table, the model's")
print("probabilities can be taken at face value rather than just its ranking.")

# ---------------------------------------------------------------------------
# Worked example: score a hypothetical storage project in each market
# ---------------------------------------------------------------------------
scen = pd.DataFrame([
    {"tech": "Battery", "region": r, "service": "ERIS",
     "log_mw": np.log10(200), "cohort": 2018}
    for r in sorted(df["region"].unique())
])
scen["predicted_built_7yr_pct"] = (pipe_a.predict_proba(scen[feat_a])[:, 1] * 100).round(1)
scen[["region", "predicted_built_7yr_pct"]].to_csv(
    OUTDIR + "/scenario_battery_by_region.csv", index=False)

print()
print("=" * 88)
print("WORKED EXAMPLE - identical 200 MW battery project, filed 2018, by market")
print("=" * 88)
print(scen[["region", "predicted_built_7yr_pct"]]
      .sort_values("predicted_built_7yr_pct", ascending=False).to_string(index=False))
