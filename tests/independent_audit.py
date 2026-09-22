"""
Independent audit. Imports NOTHING from the project's src/ - recomputes the key
findings from raw data by DIFFERENT methods than the project uses, then checks
them against external ground truth. If the project code had a bug, re-running
its own tests would not catch it. This can.

Run:  python tests/independent_audit.py   (or via verify.py, which runs it last)

Sections A-D and F read only the raw files in data/raw/. Section E reads the
processed survival dataset, so run the pipeline first - verify.py does that.
"""
import hashlib
import json
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
results = []


def check(name, ok, detail):
    results.append((name, ok))
    print("  {}  {}".format("PASS" if ok else "FAIL", name))
    print("        {}".format(detail))


print("=" * 88)
print("A. SOURCE INTEGRITY")
print("=" * 88)
for fname, expected in [
    ("LBNL_Ix_Queue_Data_File_thru2025.xlsx",
     "794582d3281c6a305e9615fcfec3fae9dc85be2165216d33760b677e976a08b6"),
    ("megapack_pricing_grid_2026-09-19.json",
     "bd7f59c354a1c08d01fb3329ae6d806ea1f1bddfb3b9c3d3ca0daa8cd9364bac"),
]:
    h = hashlib.sha256((RAW / fname).read_bytes()).hexdigest()
    check(fname, h == expected, "sha256 {}...".format(h[:16]))

# ---------------------------------------------------------------------------
print()
print("=" * 88)
print("B. PRICE DECOMPOSITION - different method (exact differencing + Cramer's rule,")
print("   not least squares)")
print("=" * 88)
g = json.loads((RAW / "megapack_pricing_grid_2026-09-19.json").read_text())
qc, spec = g["quantity_curve"], g["unit_specs"]
counts = qc["counts"]
p2 = dict(zip(counts, qc["price_2hXL"]))
p4 = dict(zip(counts, qc["price_4hXL"]))

# Marginal price of one extra unit, from the endpoints of the linear tier only
m2 = (p2[5] - p2[1]) / 4
m4 = (p4[5] - p4[1]) / 4

# m = a*kWh_per_unit + b*kW_per_unit, solved by Cramer's rule
E2, P2 = spec["2hXL"]["energy_mwh_per_unit"] * 1000, spec["2hXL"]["power_mw_per_unit"] * 1000
E4, P4 = spec["4hXL"]["energy_mwh_per_unit"] * 1000, spec["4hXL"]["power_mw_per_unit"] * 1000
det = E2 * P4 - P2 * E4
a = (m2 * P4 - P2 * m4) / det
b = (E2 * m4 - m2 * E4) / det
fixed = p2[1] - m2

check("energy rate $218.18/kWh", abs(a - 218.18) < 0.05, "independently: ${:.4f}/kWh".format(a))
check("power rate $84.38/kW", abs(b - 84.38) < 0.05, "independently: ${:.4f}/kW".format(b))
check("fixed charge $24,373", abs(fixed - 24373) < 5, "independently: ${:,.0f}".format(fixed))

# The real test: do those three numbers, derived from only four prices,
# reproduce the other prices in the tier that were never used to derive them?
held_out = []
for n in [2, 3, 4]:
    for table, E, P in [(p2, E2, P2), (p4, E4, P4)]:
        pred = fixed + n * (a * E + b * P)
        held_out.append(abs(pred - table[n]) / table[n] * 100)
check("predicts 6 held-out prices it never saw", max(held_out) < 0.01,
      "worst out-of-sample error {:.5f}%".format(max(held_out)))

# ---------------------------------------------------------------------------
print()
print("=" * 88)
print("C. QUEUE DATA - reproduce LBNL's OWN published headline from the raw workbook")
print("   LBNL states: of capacity requesting 2000-2020, 13% operational, 75% withdrawn,")
print("   10% still active, by end-2025")
print("=" * 88)
df = pd.read_excel(RAW / "LBNL_Ix_Queue_Data_File_thru2025.xlsx",
                   sheet_name="03. Complete Queue Data", header=1)
df["status"] = df["q_status"].astype(str).str.lower()
cap = df[["mw_1", "mw_2", "mw_3"]].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
df["cap"] = cap.clip(lower=0)
coh = df[(df["q_year"] >= 2000) & (df["q_year"] <= 2020)]
share = coh.groupby("status")["cap"].sum() / coh["cap"].sum() * 100
op, wd, ac = share.get("operational", 0), share.get("withdrawn", 0), share.get("active", 0)
check("operational ~13% (LBNL published)", abs(op - 13) < 2, "raw data: {:.1f}%".format(op))
check("withdrawn ~75% (LBNL published)", abs(wd - 75) < 2, "raw data: {:.1f}%".format(wd))
check("active ~10% (LBNL published)", abs(ac - 10) < 2, "raw data: {:.1f}%".format(ac))

# ---------------------------------------------------------------------------
print()
print("=" * 88)
print("D. ISO-NE REPORTING GAP - straight from the raw workbook")
print("=" * 88)
ne = df[(df["region"] == "ISO-NE") & (df["status"] == "operational")]
on = pd.to_datetime(ne["on_date"], errors="coerce").notna().sum()
check("ISO-NE reports zero COD dates", on == 0 and len(ne) > 200,
      "{} operational projects, {} with a COD date".format(len(ne), on))

# ---------------------------------------------------------------------------
print()
print("=" * 88)
print("E. COMPETING RISKS - recomputed with a textbook loop, not the vectorised version")
print("=" * 88)
s = pd.read_parquet(ROOT / "data" / "processed" / "survival_dataset.parquet")
s = s[s["region_reliable"]]
t_all = np.sort(s["duration_years"].unique())
at_risk_n = len(s)
surv, cif, km = 1.0, 0.0, 1.0
ev = s.groupby("duration_years")["event"].apply(list).to_dict()
for t in t_all:
    if t > 10:
        break
    evs = ev[t]
    d1, d2 = evs.count(1), evs.count(2)
    cif += surv * d1 / at_risk_n
    km *= (1 - d1 / at_risk_n)
    surv *= (1 - (d1 + d2) / at_risk_n)
    at_risk_n -= len(evs)
check("10-yr completion 20.0% (competing risks)", abs(cif * 100 - 20.03) < 0.2,
      "loop: {:.2f}%".format(cif * 100))
check("10-yr naive KM 58.0%", abs((1 - km) * 100 - 58.04) < 0.5,
      "loop: {:.2f}%".format((1 - km) * 100))

# ---------------------------------------------------------------------------
print()
print("=" * 88)
print("F. STOICHIOMETRY - from standard atomic masses, not the script's constants")
print("=" * 88)
Li, Fe, P, O, C = 6.941, 55.845, 30.974, 15.999, 12.011
lfp = Li + Fe + P + 4 * O
li2co3 = 2 * Li + C + 3 * O
lce = 2.00 * (Li / lfp) * (li2co3 / (2 * Li))
check("2.00 kg LiFePO4 implies ~0.47 kg LCE", abs(lce - 0.47) < 0.015,
      "from atomic masses: {:.4f} kg/kWh".format(lce))

print()
print("=" * 88)
n_pass = sum(1 for _, ok in results if ok)
print("INDEPENDENT AUDIT: {} of {} checks pass".format(n_pass, len(results)))
print("=" * 88)
sys.exit(0 if n_pass == len(results) else 1)
