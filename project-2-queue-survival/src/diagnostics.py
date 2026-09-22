"""
Step 2b - Interrogate two suspicious results before they go anywhere near a memo.

  (1) ISO-NE shows a 0% completion probability. Is New England genuinely
      building nothing, or does it simply not report operational dates?
  (2) Battery and Solar+Battery show very low completion. Is that real, or are
      those technologies just too young for a 5-year horizon to mean much?

If either turns out to be a reporting artifact, the finding has to be withdrawn
or heavily caveated. That check is the difference between analysis and noise.
"""
import pathlib
import pandas as pd

# Repo root, derived from this file's own location so the project runs
# anywhere after a clone rather than only on the machine that wrote it.
ROOT = str(pathlib.Path(__file__).resolve().parents[2]).replace("\\", "/")
RAW = ROOT + "/data/processed/queue_raw.parquet"
SURV = ROOT + "/data/processed/survival_dataset.parquet"

raw = pd.read_parquet(RAW)
raw = raw[raw["project_type"] == "Generation"]
surv = pd.read_parquet(SURV)

print("=" * 86)
print("CHECK 1 - Do all regions actually report commercial operation dates?")
print("=" * 86)
op = raw[raw["q_status"].str.lower() == "operational"]
chk = (op.groupby("region")
         .agg(operational_projects=("q_id", "size"),
              with_on_date=("on_date", lambda s: int(s.notna().sum())))
         .reset_index())
chk["pct_reported"] = (chk["with_on_date"] / chk["operational_projects"] * 100).round(1)
chk = chk.sort_values("pct_reported")
print(chk.to_string(index=False))

print()
print("Interpretation: a region with many operational projects but near-zero")
print("on_date coverage cannot produce a completion curve. Its 0% is a")
print("REPORTING ARTIFACT, not a finding.")

print()
print("=" * 86)
print("CHECK 2 - Is each technology old enough for a 5-year horizon to mean anything?")
print("=" * 86)
rows = []
for tech, sub in surv.groupby("tech", observed=True):
    # A project only informs the 5-year estimate if it was observed for 5 years
    # (i.e. it had an outcome by then) or is still being tracked past year 5.
    mature = sub[sub["duration_years"] >= 5]
    rows.append({
        "tech": tech,
        "n": len(sub),
        "median_cohort": int(sub["cohort"].median()),
        "pct_cohort_2019plus": round((sub["cohort"] >= 2019).mean() * 100, 1),
        "n_observed_5yr": len(mature),
        "pct_observed_5yr": round(len(mature) / len(sub) * 100, 1),
    })
mat = pd.DataFrame(rows).sort_values("pct_observed_5yr")
print(mat.to_string(index=False))

print()
print("Interpretation: a technology where very few projects have been tracked")
print("for 5 years has a 5-year estimate resting on a thin, early, and possibly")
print("unrepresentative subset. Report it with the sample size attached.")

print()
print("=" * 86)
print("CHECK 3 - Same maturity question, by region")
print("=" * 86)
rows = []
for reg, sub in surv.groupby("region", observed=True):
    mature = sub[sub["duration_years"] >= 5]
    built = sub[sub["event"] == 1]
    rows.append({
        "region": reg,
        "n": len(sub),
        "n_built_in_data": len(built),
        "n_observed_5yr": len(mature),
        "median_cohort": int(sub["cohort"].median()),
    })
print(pd.DataFrame(rows).sort_values("n_built_in_data").to_string(index=False))
