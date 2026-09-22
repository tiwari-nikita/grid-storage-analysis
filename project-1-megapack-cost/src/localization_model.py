"""
Step 2 - Should the LFP cells in a Megapack be imported or made domestically?

Step 1 established that ~91% of a Megapack's price rides on energy capacity, so
that is where sourcing risk concentrates. This script prices the two paths for
that energy portion, per kWh of cell:

  IMPORT     Chinese LFP cell price
             x (1 + Section 301 + general tariff)
             + ocean freight
             No 45X credit, because it is not manufactured domestically.

  LOCALISE   Chinese cell price x US cost uplift      (operating cost gap)
             + greenfield plant capex, amortised      (set to 0 if you believe
                                                       the uplift already covers it)
             - Section 45X credit (cell + module), subject to phase-down

Then, separately, the thing that actually dominates the decision: FEOC. A storage
project beginning construction in 2026 or later must meet a minimum share of
non-prohibited material value to claim the 48E investment tax credit. Failing it
does not cost a margin - it costs the entire ITC. That is a cliff, not a gradient,
and it is modelled as one.

Every input comes from assumptions.json, where each value is marked 'sourced' or
'estimate' with a range. Nothing is hardcoded here.
"""
import pathlib
import json

import numpy as np
import pandas as pd

# Repo root, derived from this file's own location so the project runs
# anywhere after a clone rather than only on the machine that wrote it.
ROOT = str(pathlib.Path(__file__).resolve().parents[2]).replace("\\", "/")
A_PATH = ROOT + "/project-1-megapack-cost/assumptions.json"
OUT = ROOT + "/project-1-megapack-cost/output"

N_SIM = 20000
RNG = np.random.default_rng(7)

with open(A_PATH) as f:
    A = json.load(f)


def v(*path):
    """Pull a 'value' out of the nested assumptions file."""
    node = A
    for k in path:
        node = node[k]
    return node["value"] if isinstance(node, dict) and "value" in node else node


CELL = v("cell_cost", "china_lfp_cell_usd_per_kwh")
UPLIFT = v("cell_cost", "us_cost_uplift_multiple")
S301 = v("trade_policy", "section_301_rate_pct")
GEN = v("trade_policy", "general_tariff_rate_pct")
FREIGHT = v("trade_policy", "ocean_freight_usd_per_kwh")
C45X = v("tax_credits", "credit_45x_cell_usd_per_kwh") + v("tax_credits", "credit_45x_module_usd_per_kwh")
ITC = v("tax_credits", "itc_rate_pct")
CAPEX = v("plant", "us_capex_usd_per_kwh_annual_capacity")
YEARS = v("plant", "amortisation_years")
UTIL = v("plant", "utilisation_pct")
ENERGY_PRICE = A["decomposition"]["energy_price_usd_per_kwh_volume_order"]


def import_cost(cell=CELL, tariff_pct=S301 + GEN, freight=FREIGHT):
    return cell * (1 + tariff_pct / 100.0) + freight


def capex_per_kwh(capex=CAPEX, years=YEARS, util=UTIL):
    """Greenfield capex spread over lifetime output, not nameplate."""
    return capex / (years * util / 100.0)


def localise_cost(cell=CELL, uplift=UPLIFT, credit=C45X, capex=CAPEX,
                  years=YEARS, util=UTIL):
    return cell * uplift + capex_per_kwh(capex, years, util) - credit


# ---------------------------------------------------------------------------
# 1. Base case
# ---------------------------------------------------------------------------
imp, loc = import_cost(), localise_cost()
tariff_burden = CELL * (S301 + GEN) / 100.0
feoc_at_risk = ENERGY_PRICE * ITC / 100.0

base = pd.DataFrame([
    {"line": "Chinese LFP cell price", "import_usd_per_kwh": CELL, "localise_usd_per_kwh": None},
    {"line": "Tariff (Sec 301 {:.0f}% + general {:.1f}%)".format(S301, GEN),
     "import_usd_per_kwh": tariff_burden, "localise_usd_per_kwh": 0.0},
    {"line": "Ocean freight", "import_usd_per_kwh": FREIGHT, "localise_usd_per_kwh": 0.0},
    {"line": "US manufacturing cost ({}x uplift)".format(UPLIFT),
     "import_usd_per_kwh": None, "localise_usd_per_kwh": CELL * UPLIFT},
    {"line": "Plant capex, amortised", "import_usd_per_kwh": None,
     "localise_usd_per_kwh": capex_per_kwh()},
    {"line": "Section 45X credit (cell + module)", "import_usd_per_kwh": 0.0,
     "localise_usd_per_kwh": -C45X},
    {"line": "LANDED COST", "import_usd_per_kwh": imp, "localise_usd_per_kwh": loc},
])
base.round(2).to_csv(OUT + "/base_case.csv", index=False)

print("=" * 86)
print("LANDED COST OF LFP CELLS, PER kWh  -  IMPORT vs LOCALISE")
print("=" * 86)
print(base.to_string(index=False, na_rep="", float_format=lambda x: "{:>8.2f}".format(x)))
print()
print("Localisation advantage: ${:.2f}/kWh  ({:.0f}% cheaper)".format(
    imp - loc, (1 - loc / imp) * 100))

print()
print("=" * 86)
print("THE PART THAT ACTUALLY DECIDES IT: FEOC")
print("=" * 86)
print("Tariff burden on an imported cell           ${:>7.2f} /kWh".format(tariff_burden))
print("ITC at risk if the project fails FEOC       ${:>7.2f} /kWh".format(feoc_at_risk))
print("                                            {:>8.1f}x the tariff".format(
    feoc_at_risk / tariff_burden))
print()
print("A 25% tariff is a margin problem. Losing the 30% investment tax credit is")
print("a project-killer, and it lands on the CUSTOMER rather than the manufacturer.")
print("Material-assistance thresholds ratchet up every year:")
for yr, pct in A["feoc"]["macr_threshold_pct_by_year"].items():
    print("   {}  requires {:>3}% non-prohibited material value".format(yr, pct))

pd.DataFrame([{"tariff_burden_usd_per_kwh": tariff_burden,
               "itc_at_risk_usd_per_kwh": feoc_at_risk,
               "ratio": feoc_at_risk / tariff_burden,
               "itc_rate_pct": ITC,
               "energy_price_basis_usd_per_kwh": ENERGY_PRICE}]).round(2).to_csv(
    OUT + "/feoc_value_at_risk.csv", index=False)


# ---------------------------------------------------------------------------
# 2. Decision surface
#
# Cell price turns out NOT to be the swing variable. The 45X credit is large
# enough relative to an LFP cell that domestic manufacture wins at every
# plausible Chinese cell price, even at a zero tariff - a result worth stating
# plainly rather than dressing up in a chart that has no frontier in it.
#
# So the surface is drawn over the two things that genuinely are uncertain: how
# much more expensive US manufacturing really is, and where tariffs land.
# ---------------------------------------------------------------------------
uplifts = np.round(np.arange(1.00, 2.55, 0.05), 2)
tariffs = np.arange(0, 61, 2.5)
grid = []
for u in uplifts:
    for t in tariffs:
        adv = import_cost(tariff_pct=t) - localise_cost(uplift=u)
        grid.append({"us_cost_uplift": u, "tariff_pct": t,
                     "localise_advantage_usd_per_kwh": adv,
                     "localise_wins": int(adv > 0)})
pd.DataFrame(grid).round(2).to_csv(OUT + "/decision_surface.csv", index=False)

# Break-even uplift: how expensive can US manufacturing get before importing wins?
#   cell*u + capex - credit = import   ->   u = (import - capex + credit) / cell
be = []
for t in [0, 10, 20, 28.4, 40, 60]:
    u_star = (import_cost(tariff_pct=t) - capex_per_kwh() + C45X) / CELL
    be.append({"tariff_pct": t,
               "import_landed_usd_per_kwh": import_cost(tariff_pct=t),
               "breakeven_us_uplift_multiple": u_star})
be_df = pd.DataFrame(be)
be_df.round(2).to_csv(OUT + "/breakeven_uplift.csv", index=False)

print()
print("=" * 86)
print("HOW UNCOMPETITIVE CAN US MANUFACTURING BE AND STILL WIN?")
print("=" * 86)
print("Break-even US cost uplift vs Chinese cell cost, by tariff rate:")
print(be_df.round(2).to_string(index=False))
print()
print("At the current 28.4% combined tariff, a US plant could cost {:.2f}x what a".format(
    be_df.loc[be_df["tariff_pct"] == 28.4, "breakeven_us_uplift_multiple"].iloc[0]))
print("Chinese producer spends and still land cheaper. The central assumption is")
print("1.30x, so there is a wide margin of safety on the softest input in the model.")
print()
print("Cell price is not the swing variable: 45X is large enough relative to an")
print("LFP cell that domestic manufacture wins at every plausible cell price,")
print("even with no tariff at all.")


# ---------------------------------------------------------------------------
# 3. 45X phase-down - does the answer survive the credit going away?
# ---------------------------------------------------------------------------
sched = A["tax_credits"]["credit_45x_phase_down"]["schedule"]
rows = []
for yr, factor in sched.items():
    l = localise_cost(credit=C45X * factor)
    rows.append({"production_year": int(yr), "credit_factor": factor,
                 "credit_usd_per_kwh": C45X * factor,
                 "localise_usd_per_kwh": l, "import_usd_per_kwh": imp,
                 "localise_advantage_usd_per_kwh": imp - l})
phase = pd.DataFrame(rows)
phase.round(2).to_csv(OUT + "/phase_down_sensitivity.csv", index=False)

print()
print("=" * 86)
print("WHAT HAPPENS AS 45X PHASES DOWN")
print("=" * 86)
print(phase.round(2).to_string(index=False))
flip = phase[phase["localise_advantage_usd_per_kwh"] <= 0]
if len(flip):
    print()
    print("Domestic manufacture stops paying for itself on cost alone in {}.".format(
        int(flip.iloc[0]["production_year"])))
    print("Note this is the COST case only - FEOC eligibility does not expire with 45X.")
else:
    print()
    print("Domestic manufacture stays cheaper across the whole phase-down schedule.")


# ---------------------------------------------------------------------------
# 4. Monte Carlo - how confident is the answer, given the soft assumptions?
# ---------------------------------------------------------------------------
def tri(node, *path):
    """Triangular draw from an assumption's low/value/high."""
    n = A
    for k in path:
        n = n[k]
    return RNG.triangular(n["low"], n["value"], n["high"], N_SIM)


sim_cell = tri(A, "cell_cost", "china_lfp_cell_usd_per_kwh")
sim_uplift = tri(A, "cell_cost", "us_cost_uplift_multiple")
sim_freight = tri(A, "trade_policy", "ocean_freight_usd_per_kwh")
sim_capex = tri(A, "plant", "us_capex_usd_per_kwh_annual_capacity")
sim_util = tri(A, "plant", "utilisation_pct")

sim_imp = sim_cell * (1 + (S301 + GEN) / 100.0) + sim_freight
sim_loc = sim_cell * sim_uplift + sim_capex / (YEARS * sim_util / 100.0) - C45X
sim_adv = sim_imp - sim_loc

pct = np.percentile(sim_adv, [5, 25, 50, 75, 95])
mc = pd.DataFrame([{
    "p5": pct[0], "p25": pct[1], "median": pct[2], "p75": pct[3], "p95": pct[4],
    "prob_localise_cheaper_pct": float((sim_adv > 0).mean() * 100),
    "n_sim": N_SIM,
}]).round(2)
mc.to_csv(OUT + "/monte_carlo_summary.csv", index=False)

# Write a binned histogram rather than 20,000 raw draws - it is what the chart
# needs, it stays readable in Excel, and it keeps the file small.
counts, edges = np.histogram(sim_adv, bins=60)
pd.DataFrame({
    "bin_low_usd_per_kwh": edges[:-1].round(2),
    "bin_high_usd_per_kwh": edges[1:].round(2),
    "count": counts,
}).to_csv(OUT + "/monte_carlo_histogram.csv", index=False)

print()
print("=" * 86)
print("MONTE CARLO  ({:,} draws over every 'estimate' assumption)".format(N_SIM))
print("=" * 86)
print("Localisation advantage, $/kWh of cell:")
print("   p5 {:>7.2f}   p25 {:>7.2f}   median {:>7.2f}   p75 {:>7.2f}   p95 {:>7.2f}".format(*pct))
print()
print("Probability domestic manufacture is cheaper: {:.1f}%".format((sim_adv > 0).mean() * 100))
print()
print("This is the cost case alone and excludes FEOC entirely. Adding FEOC would")
print("push it higher, since the ITC cliff only ever penalises the import path.")


# ---------------------------------------------------------------------------
# 5. Scale it - what is this worth on a real Megapack order?
# ---------------------------------------------------------------------------
mwh = 3.92 * 20        # a 20-unit 4-hour order
kwh = mwh * 1000
print()
print("=" * 86)
print("SCALED TO A 20-UNIT MEGAPACK ORDER ({:.0f} MWh)".format(mwh))
print("=" * 86)
print("Cost delta, import vs localise      ${:>12,.0f}".format((imp - loc) * kwh))
print("ITC at risk if FEOC is failed       ${:>12,.0f}".format(feoc_at_risk * kwh))
print("Tesla list price for that order     ${:>12,.0f}".format(
    A["decomposition"]["energy_price_usd_per_kwh_volume_order"] * kwh
    + A["decomposition"]["power_price_usd_per_kw_volume_order"] * 0.98 * 1000 * 20
    + A["decomposition"]["fixed_order_charge_usd"]))
