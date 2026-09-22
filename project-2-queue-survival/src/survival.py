"""
Step 2 - Survival analysis of the interconnection queue, with competing risks.

THE METHODOLOGICAL POINT OF THIS PROJECT
----------------------------------------
A project leaves the queue one of two ways: it gets built (COD), or it is
withdrawn. Standard Kaplan-Meier handles ONE event and treats everything else as
censoring. Censoring means "still possible, we just stopped watching".

But a withdrawn project is not still possible. It is dead. Treating withdrawal
as censoring assumes those projects could still reach COD later, which
systematically OVERSTATES the probability of completion.

The correct tool is the Aalen-Johansen cumulative incidence function, which
estimates the probability of each outcome in the presence of the other. This
script computes both and reports the gap, because the size of that gap is the
finding.

Both estimators are implemented from scratch - roughly forty lines - rather than
imported, so every step is inspectable.

SCOPE: completion estimates use only regions that actually report commercial
operation dates (see build_dataset.py section 3b). Including the others would
report ISO-NE as building nothing, which is false.
"""
import pathlib
import numpy as np
import pandas as pd

# Repo root, derived from this file's own location so the project runs
# anywhere after a clone rather than only on the machine that wrote it.
ROOT = str(pathlib.Path(__file__).resolve().parents[2]).replace("\\", "/")
SRC = ROOT + "/data/processed/survival_dataset.parquet"
OUTDIR = ROOT + "/project-2-queue-survival/output"

HORIZONS = [2, 3, 5, 7, 10]     # years after interconnection request
N_BOOT = 300                     # bootstrap replicates for the headline CI
RNG = np.random.default_rng(42)


def estimate(durations, events):
    """
    Returns (t, cif_cod, cif_wd, naive_cod, at_risk).

    cif_cod / cif_wd : Aalen-Johansen cumulative incidence, competing risks.
    naive_cod        : 1 - Kaplan-Meier, i.e. what you get if you wrongly treat
                       withdrawal as censoring.

    event coding: 0 = censored, 1 = COD, 2 = withdrawn.
    """
    n = len(durations)
    t, idx = np.unique(durations, return_inverse=True)

    n_at_time = np.bincount(idx, minlength=len(t))
    d_cod = np.bincount(idx, weights=(events == 1).astype(float), minlength=len(t))
    d_wd = np.bincount(idx, weights=(events == 2).astype(float), minlength=len(t))

    # Number still at risk immediately before each distinct time
    at_risk = n - np.concatenate([[0], np.cumsum(n_at_time)[:-1]])
    at_risk = np.maximum(at_risk, 1)

    # Overall survival: still in the queue, neither built nor withdrawn
    overall_surv = np.cumprod(1.0 - (d_cod + d_wd) / at_risk)
    surv_prev = np.concatenate([[1.0], overall_surv[:-1]])

    # Aalen-Johansen: each increment weighted by the chance of still being in
    # the queue just before that moment.
    cif_cod = np.cumsum(surv_prev * d_cod / at_risk)
    cif_wd = np.cumsum(surv_prev * d_wd / at_risk)

    # Naive Kaplan-Meier for COD, treating withdrawals as censored
    naive_cod = 1.0 - np.cumprod(1.0 - d_cod / at_risk)

    return t, cif_cod, cif_wd, naive_cod, at_risk


def at_horizons(t, curve, horizons=HORIZONS):
    """Step-function lookup: value of `curve` at each horizon."""
    pos = np.searchsorted(t, horizons, side="right") - 1
    return np.array([curve[p] if p >= 0 else 0.0 for p in pos])


full = pd.read_parquet(SRC)
df = full[full["region_reliable"]].copy()   # headline scope

print("=" * 94)
print("SCOPE")
print("=" * 94)
print("all regions in dataset          {:,} projects".format(len(full)))
print("regions reporting COD dates     {:,} projects  <- used below".format(len(df)))
print("excluded as under-reporting     {:,} projects  ({})".format(
    len(full) - len(df),
    ", ".join(sorted(full.loc[~full["region_reliable"], "region"].unique()))))

dur = df["duration_years"].to_numpy(float)
ev = df["event"].to_numpy(int)

# ---------------------------------------------------------------------------
# Overall
# ---------------------------------------------------------------------------
t, cif_cod, cif_wd, naive, at_risk = estimate(dur, ev)

cod_h = at_horizons(t, cif_cod)
wd_h = at_horizons(t, cif_wd)
naive_h = at_horizons(t, naive)
still_h = 1.0 - cod_h - wd_h

boot = np.empty((N_BOOT, len(HORIZONS)))
n = len(dur)
for b in range(N_BOOT):
    s = RNG.integers(0, n, n)
    tb, cb, _, _, _ = estimate(dur[s], ev[s])
    boot[b] = at_horizons(tb, cb)
lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)

print()
print("=" * 94)
print("WHAT HAPPENS TO A PROJECT AFTER IT REQUESTS INTERCONNECTION")
print("n = {:,} generation and storage requests, 1997-2025".format(len(df)))
print("=" * 94)
print("{:>6} | {:>21} | {:>10} | {:>14} | {:>9} | {:>11}".format(
    "years", "built (95% CI)", "withdrawn", "still waiting", "naive KM", "overstated"))
print("-" * 94)
for i, h in enumerate(HORIZONS):
    ci = "[{:.1f}-{:.1f}]".format(lo[i] * 100, hi[i] * 100)
    over = naive_h[i] / cod_h[i] if cod_h[i] > 0 else np.nan
    print("{:>6} | {:>6.1f}% {:>14} | {:>9.1f}% | {:>13.1f}% | {:>8.1f}% | {:>10.2f}x".format(
        h, cod_h[i] * 100, ci, wd_h[i] * 100, still_h[i] * 100, naive_h[i] * 100, over))

pd.DataFrame({
    "horizon_years": HORIZONS,
    "pct_built": cod_h * 100,
    "pct_built_ci_lo": lo * 100,
    "pct_built_ci_hi": hi * 100,
    "pct_withdrawn": wd_h * 100,
    "pct_still_waiting": still_h * 100,
    "pct_built_naive_km": naive_h * 100,
    "naive_overstatement_x": naive_h / cod_h,
}).round(2).to_csv(OUTDIR + "/cif_summary.csv", index=False)

pd.DataFrame({
    "years": t, "cif_built": cif_cod, "cif_withdrawn": cif_wd,
    "naive_km_built": naive, "at_risk": at_risk,
}).to_csv(OUTDIR + "/cif_curves_overall.csv", index=False)


# ---------------------------------------------------------------------------
# By technology and by region
#
# n_observed_5yr is reported alongside every estimate. Batteries entered the
# queue overwhelmingly after 2019, so their 5-year number rests on a small and
# early subset. The estimate is not wrong, but it is thin, and hiding that
# would be misleading.
# ---------------------------------------------------------------------------
def by_group(col, min_n=150):
    rows, curves = [], []
    for g, sub in df.groupby(col, observed=True):
        if len(sub) < min_n:
            continue
        tg, cg, wg, _, _ = estimate(sub["duration_years"].to_numpy(float),
                                    sub["event"].to_numpy(int))
        rows.append({
            col: g,
            "n": len(sub),
            "n_observed_5yr": int(sub["observed_5yr"].sum()),
            "median_cohort": int(sub["cohort"].median()),
            "built_5yr_pct": at_horizons(tg, cg, [5])[0] * 100,
            "built_7yr_pct": at_horizons(tg, cg, [7])[0] * 100,
            "withdrawn_5yr_pct": at_horizons(tg, wg, [5])[0] * 100,
            "median_mw": sub["mw_1"].median(),
        })
        curves.append(pd.DataFrame({col: g, "years": tg, "cif_built": cg,
                                    "cif_withdrawn": wg}))
    return (pd.DataFrame(rows).sort_values("built_5yr_pct", ascending=False),
            pd.concat(curves, ignore_index=True))


tech_tbl, tech_curves = by_group("tech")
tech_tbl.round(2).to_csv(OUTDIR + "/cif_by_tech.csv", index=False)
tech_curves.to_csv(OUTDIR + "/cif_curves_by_tech.csv", index=False)

region_tbl, region_curves = by_group("region")
region_tbl.round(2).to_csv(OUTDIR + "/cif_by_region.csv", index=False)
region_curves.to_csv(OUTDIR + "/cif_curves_by_region.csv", index=False)

print()
print("=" * 94)
print("PROBABILITY OF BEING BUILT, BY TECHNOLOGY")
print("=" * 94)
print(tech_tbl.round(1).to_string(index=False))

print()
print("=" * 94)
print("PROBABILITY OF BEING BUILT, BY REGION  (reliable reporters only)")
print("=" * 94)
print(region_tbl.round(1).to_string(index=False))


# ---------------------------------------------------------------------------
# Has the queue got worse over time? Fixed 5-year horizon per era, so every
# cohort is judged on equal footing.
# ---------------------------------------------------------------------------
eras = [(1997, 2009), (2010, 2014), (2015, 2018), (2019, 2020)]
rows = []
for a, b in eras:
    sub = df[(df["cohort"] >= a) & (df["cohort"] <= b)]
    tg, cg, wg, _, _ = estimate(sub["duration_years"].to_numpy(float),
                                sub["event"].to_numpy(int))
    rows.append({"era": "{}-{}".format(a, b), "n": len(sub),
                 "built_5yr_pct": at_horizons(tg, cg, [5])[0] * 100,
                 "withdrawn_5yr_pct": at_horizons(tg, wg, [5])[0] * 100})
era_tbl = pd.DataFrame(rows)
era_tbl.round(2).to_csv(OUTDIR + "/cif_by_era.csv", index=False)

print()
print("=" * 94)
print("IS IT GETTING WORSE?  Outcomes 5 years after request, by request era")
print("(2021+ cohorts excluded: not yet 5 years old, nothing to compare)")
print("=" * 94)
print(era_tbl.round(1).to_string(index=False))


# ---------------------------------------------------------------------------
# Appendix: what the unfiltered data would have told us
# ---------------------------------------------------------------------------
ta, ca, _, _, _ = estimate(full["duration_years"].to_numpy(float),
                           full["event"].to_numpy(int))
print()
print("=" * 94)
print("APPENDIX - cost of skipping the reporting-quality check")
print("=" * 94)
print("5-year completion, reliable regions only : {:.1f}%".format(
    at_horizons(t, cif_cod, [5])[0] * 100))
print("5-year completion, all regions pooled    : {:.1f}%".format(
    at_horizons(ta, ca, [5])[0] * 100))
print("The second number is depressed by regions that report no COD dates at all.")
