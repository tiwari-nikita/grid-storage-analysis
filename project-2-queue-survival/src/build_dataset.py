"""
Step 1 - Turn the raw LBNL queue extract into an analysis-ready survival dataset.

Design decisions that matter, all of them reversible at the top of this file:

  * A project's clock starts at its interconnection request (q_date).
  * Three mutually exclusive outcomes can end that clock:
        1 = reached commercial operation (COD)
        2 = withdrawn from the queue
        0 = neither yet, i.e. still waiting at the data cutoff (censored)
  * Withdrawal is a COMPETING RISK, not censoring. A withdrawn project cannot
    later reach COD, so it must not be treated as "we stopped watching".
    Getting this wrong is the single most common error in queue analysis and it
    inflates estimated completion rates substantially. See survival.py.
  * Only "Generation" requests are kept. Upgrades, surplus interconnection and
    replacements are a different animal and would pollute the denominator.
  * Regions that do not report commercial operation dates are flagged, not
    trusted. See section 3b - this one is easy to miss and produces confidently
    wrong conclusions about entire ISOs.
"""
import pathlib
import numpy as np
import pandas as pd

# Repo root, derived from this file's own location so the project runs
# anywhere after a clone rather than only on the machine that wrote it.
ROOT = str(pathlib.Path(__file__).resolve().parents[2]).replace("\\", "/")
CACHE = ROOT + "/data/processed/queue_raw.parquet"
OUT = ROOT + "/data/processed/survival_dataset.parquet"
AUDIT = ROOT + "/data/processed/missingness_audit.csv"
REPORT = ROOT + "/data/processed/region_reporting_quality.csv"

DATA_CUTOFF = pd.Timestamp("2025-12-31")   # LBNL 2026 Edition covers through 2025
MAX_YEARS = 25                              # sanity bound on any duration
MIN_REPORTING_PCT = 90.0                    # COD-date coverage needed to trust a region

df = pd.read_parquet(CACHE)
print("raw rows                              {:,}".format(len(df)))

# ----------------------------------------------------------------------------
# 1. Scope: new generation/storage requests only, with a known start date
# ----------------------------------------------------------------------------
df = df[df["project_type"] == "Generation"].copy()
print("after keeping project_type=Generation {:,}".format(len(df)))

df = df[df["q_date"].notna()].copy()
print("after requiring a request date        {:,}".format(len(df)))

df = df[df["q_date"] <= DATA_CUTOFF].copy()
print("after dropping post-cutoff requests   {:,}".format(len(df)))

# mw_1 carries some negative and zero values, which are data errors for a
# nameplate capacity field. Drop them rather than silently modelling nonsense.
bad_mw = (df["mw_1"].isna()) | (df["mw_1"] <= 0)
print("dropping non-positive/missing mw_1    {:,}".format(int(bad_mw.sum())))
df = df[~bad_mw].copy()

# ----------------------------------------------------------------------------
# 2. Outcome and duration
# ----------------------------------------------------------------------------
# "suspended" is treated as still-in-process rather than terminal: suspended
# projects can and do resume. Grouped with active for censoring purposes.
status = df["q_status"].str.lower()
df = df[status.isin(["operational", "withdrawn", "active", "suspended"])].copy()

status = df["q_status"].str.lower()
is_op = status.eq("operational")
is_wd = status.eq("withdrawn")
is_open = status.isin(["active", "suspended"])

df["event"] = np.select([is_op, is_wd, is_open], [1, 2, 0], default=-1)

# End date per outcome. Open projects are censored at the data cutoff.
df["end_date"] = pd.NaT
df.loc[is_op, "end_date"] = df.loc[is_op, "on_date"]
df.loc[is_wd, "end_date"] = df.loc[is_wd, "wd_date"]
df.loc[is_open, "end_date"] = DATA_CUTOFF

# ----------------------------------------------------------------------------
# 3. Missingness audit - BEFORE dropping anything, record who we are losing
# ----------------------------------------------------------------------------
df["date_missing"] = df["end_date"].isna()

(df.groupby(["q_status", "type_clean"], observed=True)
   .agg(n=("event", "size"),
        pct_missing_date=("date_missing", lambda s: round(s.mean() * 100, 1)),
        median_mw=("mw_1", "median"),
        median_q_year=("q_year", "median"))
   .reset_index()
   .sort_values("n", ascending=False)
   .to_csv(AUDIT, index=False))

print()
print("MISSING OUTCOME DATES - are the dropped rows different from the kept ones?")
for st in ["operational", "withdrawn"]:
    sub = df[df["q_status"].str.lower() == st]
    kept, lost = sub[~sub["date_missing"]], sub[sub["date_missing"]]
    if len(lost) == 0:
        continue
    print("  {:12s} kept {:>6,}  lost {:>6,} ({:.1f}%)".format(
        st, len(kept), len(lost), len(lost) / len(sub) * 100))
    print("               median MW   kept {:>7.1f} | lost {:>7.1f}".format(
        kept["mw_1"].median(), lost["mw_1"].median()))
    print("               median year kept {:>7.0f} | lost {:>7.0f}".format(
        kept["q_year"].median(), lost["q_year"].median()))

# ----------------------------------------------------------------------------
# 3b. Regional reporting quality  <-- the trap in this dataset
# ----------------------------------------------------------------------------
# Some ISOs never populate on_date at all. ISO-NE, for instance, has hundreds of
# projects marked operational and not one commercial operation date. A survival
# curve built on that region will show a 0% chance of ever being built, which is
# not a finding about New England - it is a finding about New England's data.
#
# Measure COD-date coverage per region so unreliable regions can be excluded
# explicitly rather than silently mistaken for non-builders.
op_only = df[df["q_status"].str.lower() == "operational"]
coverage = (op_only.groupby("region")
            .agg(operational_projects=("event", "size"),
                 with_cod_date=("end_date", lambda s: int(s.notna().sum())))
            .reset_index())
coverage["cod_reporting_pct"] = (
    coverage["with_cod_date"] / coverage["operational_projects"] * 100).round(1)
coverage["reliable"] = coverage["cod_reporting_pct"] >= MIN_REPORTING_PCT
coverage.sort_values("cod_reporting_pct").to_csv(REPORT, index=False)

print()
print("COD-DATE REPORTING COVERAGE BY REGION  (threshold {:.0f}%)".format(MIN_REPORTING_PCT))
print(coverage.sort_values("cod_reporting_pct").to_string(index=False))

rel_map = dict(zip(coverage["region"], coverage["cod_reporting_pct"]))
df["region_reporting_pct"] = df["region"].map(rel_map)
df["region_reliable"] = df["region_reporting_pct"] >= MIN_REPORTING_PCT
df["region_reliable"] = df["region_reliable"].fillna(False)

df = df[~df["date_missing"]].copy()
print()
print("rows with a usable duration           {:,}".format(len(df)))

# ----------------------------------------------------------------------------
# 4. Duration, with sanity bounds
# ----------------------------------------------------------------------------
df["duration_years"] = (df["end_date"] - df["q_date"]).dt.days / 365.25

bad_dur = (df["duration_years"] <= 0) | (df["duration_years"] > MAX_YEARS)
print("dropping impossible durations         {:,}".format(int(bad_dur.sum())))
df = df[~bad_dur].copy()

# ----------------------------------------------------------------------------
# 5. Features
# ----------------------------------------------------------------------------
TYPE_MAP = {
    "Solar": "Solar", "Wind": "Wind", "Battery": "Battery",
    "Solar+Battery": "Solar+Battery", "Gas": "Gas",
    "Offshore Wind": "Offshore Wind", "Nuclear": "Nuclear", "Coal": "Coal",
}
df["tech"] = df["type_clean"].map(TYPE_MAP).fillna("Other")

df["size_bucket"] = pd.cut(
    df["mw_1"], bins=[0, 20, 100, 250, 500, np.inf],
    labels=["<20 MW", "20-100 MW", "100-250 MW", "250-500 MW", "500+ MW"],
)

# Cohort = the year the project joined the queue. Essential: later cohorts have
# had less time to finish, which is exactly what the survival model corrects for.
df["cohort"] = df["q_year"].astype("Int64")

# Did this project ever get a signed interconnection agreement? Strong signal,
# but it happens AFTER the request, so it is not knowable at request time.
# completion_model.py builds one model with it and one without, deliberately.
df["has_ia"] = df["ia_date"].notna()

# How long was this project actually observed for? Needed to judge whether a
# 5-year estimate for a given group rests on real data or on a handful of rows.
df["observed_5yr"] = df["duration_years"] >= 5

KEEP = [
    "q_id", "entity", "region", "state", "tech", "type_clean",
    "mw_1", "size_bucket", "service", "cohort", "q_year",
    "q_date", "end_date", "duration_years", "event", "q_status", "has_ia",
    "region_reporting_pct", "region_reliable", "observed_5yr",
]
out = df[KEEP].copy()
out.to_parquet(OUT, index=False)

print()
print("=" * 78)
print("FINAL SURVIVAL DATASET")
print("=" * 78)
print("rows: {:,}    ->  {}".format(len(out), OUT))
print()
lbl = {0: "0 censored (still waiting)", 1: "1 reached COD", 2: "2 withdrawn"}
for k, v in out["event"].value_counts().sort_index().items():
    print("  {:<28} {:>7,}  ({:>4.1f}%)".format(lbl[k], v, v / len(out) * 100))

print()
print("reliable-region subset (used for completion estimates): {:,} rows".format(
    int(out["region_reliable"].sum())))
print("excluded as under-reporting:                            {:,} rows".format(
    int((~out["region_reliable"]).sum())))
print()
print("median duration by outcome (years):")
print(out.groupby("event")["duration_years"].median().round(2).to_string())
print()
print("cohort span: {} - {}".format(int(out["cohort"].min()), int(out["cohort"].max())))
