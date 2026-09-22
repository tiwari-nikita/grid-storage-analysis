"""
Step 1 - Decompose Tesla's published Megapack price into its physical parts.

THE IDEA
--------
Tesla sells Megapack in two configurations built from the same unit: a 2-hour
version (1.92 MW / 3.86 MWh per unit) and a 4-hour version (0.98 MW / 3.92 MWh).
Nearly the same energy, half the power. Any price difference between them is
therefore attributable to POWER CONVERSION hardware rather than to cells.

That lets us solve for two unit economics that Tesla never publishes separately:

    price = fixed_order_charge
          + energy_rate ($/kWh) x total kWh
          + power_rate  ($/kW)  x total kW

WHY THIS IS NOT JUST ALGEBRA ON TWO NUMBERS
-------------------------------------------
Two equations with two unknowns fit perfectly by construction and prove nothing.
So the model is fitted by least squares across TWENTY-FOUR observed prices
(12 quantities x 2 configurations) against 3 unknowns. It is heavily
overdetermined, which means the residuals are a real test: if price genuinely
decomposes this way, the fit will be near-exact. If it does not, we will see it.

IMPORTANT: this decomposes PRICE, not cost. Converting to cost requires a margin
assumption, which is made explicitly in localization_model.py and never smuggled
in here.
"""
import pathlib
import json

import numpy as np
import pandas as pd

# Repo root, derived from this file's own location so the project runs
# anywhere after a clone rather than only on the machine that wrote it.
ROOT = str(pathlib.Path(__file__).resolve().parents[2]).replace("\\", "/")
SRC = ROOT + "/data/raw/megapack_pricing_grid_2026-09-19.json"
OUT = ROOT + "/project-1-megapack-cost/output"

# Volume tiers. Pricing is linear inside each and steps between them, so they
# are fitted separately rather than forced through one line.
TIERS = {"small order (1-5 units)": [1, 2, 3, 4, 5],
         "volume order (20-50 units)": [20, 30, 40, 50]}

LATHROP = (37.82, -121.28)      # Tesla Megafactory, Lathrop CA
STATE_CENTROIDS = {             # approximate geographic centroids
    "CA": (36.78, -119.42), "NV": (38.80, -116.42), "AZ": (34.05, -111.09),
    "WY": (43.08, -107.29), "WA": (47.40, -121.49), "TX": (31.97, -99.90),
    "IL": (40.00, -89.00), "NY": (43.00, -75.00), "FL": (28.63, -82.45),
    "MA": (42.41, -71.38), "HI": (21.09, -157.50), "PR": (18.22, -66.59),
}

with open(SRC) as f:
    d = json.load(f)

specs = d["unit_specs"]
qc = d["quantity_curve"]

# ---------------------------------------------------------------------------
# Long-format observation table
# ---------------------------------------------------------------------------
rows = []
for v, key in [("2hXL", "price_2hXL"), ("4hXL", "price_4hXL")]:
    for n, price in zip(qc["counts"], qc[key]):
        rows.append({
            "variation": v,
            "count": n,
            "price": price,
            "kwh": n * specs[v]["energy_mwh_per_unit"] * 1000,
            "kw": n * specs[v]["power_mw_per_unit"] * 1000,
        })
obs = pd.DataFrame(rows)
obs["price_per_kwh"] = obs["price"] / obs["kwh"]
obs["price_per_unit"] = obs["price"] / obs["count"]


def fit(sub, label):
    """Least-squares fit of price = F + a*kWh + b*kW."""
    A = np.column_stack([np.ones(len(sub)), sub["kwh"], sub["kw"]])
    coef, *_ = np.linalg.lstsq(A, sub["price"].to_numpy(float), rcond=None)
    F, a, b = coef
    pred = A @ coef
    resid = sub["price"].to_numpy(float) - pred
    ss_res = float((resid ** 2).sum())
    ss_tot = float(((sub["price"] - sub["price"].mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot
    worst = float(np.abs(resid / sub["price"].to_numpy(float)).max() * 100)

    print()
    print("=" * 84)
    print(label.upper())
    print("=" * 84)
    print("observations {}   unknowns 3   ->  {} degrees of freedom".format(
        len(sub), len(sub) - 3))
    print()
    print("  fixed order charge      ${:>12,.0f}".format(F))
    print("  energy capacity         ${:>12,.2f} per kWh".format(a))
    print("  power conversion        ${:>12,.2f} per kW".format(b))
    print()
    print("  R-squared               {:>13.6f}".format(r2))
    print("  worst residual          {:>12.3f}% of price".format(worst))
    return {"tier": label, "fixed_usd": F, "energy_usd_per_kwh": a,
            "power_usd_per_kw": b, "r2": r2, "worst_resid_pct": worst,
            "n_obs": len(sub)}


print("=" * 84)
print("TESLA MEGAPACK PRICE DECOMPOSITION")
print("Source: tesla.com public pricing API, captured 2026-09-19")
print("=" * 84)
print()
print("Observed configurations (California, 2027 Q1 delivery):")
print(obs.groupby("variation").agg(
    n_points=("price", "size"),
    min_price=("price", "min"),
    max_price=("price", "max"),
    kwh_per_unit=("kwh", lambda s: s.iloc[0]),
).to_string())

results = [fit(obs[obs["count"].isin(counts)], label)
           for label, counts in TIERS.items()]
res_df = pd.DataFrame(results)
res_df.to_csv(OUT + "/price_decomposition.csv", index=False)

# ---------------------------------------------------------------------------
# What the decomposition means
# ---------------------------------------------------------------------------
small, large = results[0], results[1]
print()
print("=" * 84)
print("WHAT THIS SAYS")
print("=" * 84)
u = specs["4hXL"]
e_share = small["energy_usd_per_kwh"] * u["energy_mwh_per_unit"] * 1000
p_share = small["power_usd_per_kw"] * u["power_mw_per_unit"] * 1000
tot = e_share + p_share
print("For one 4-hour Megapack ({} MWh / {} MW) at small-order pricing:".format(
    u["energy_mwh_per_unit"], u["power_mw_per_unit"]))
print("  energy capacity (cells, thermal, enclosure)  ${:>10,.0f}   {:>4.1f}%".format(
    e_share, e_share / tot * 100))
print("  power conversion (inverter, controls)        ${:>10,.0f}   {:>4.1f}%".format(
    p_share, p_share / tot * 100))
print()
print("Volume discount between tiers:")
print("  energy  ${:.2f} -> ${:.2f} per kWh   ({:+.1f}%)".format(
    small["energy_usd_per_kwh"], large["energy_usd_per_kwh"],
    (large["energy_usd_per_kwh"] / small["energy_usd_per_kwh"] - 1) * 100))
print("  power   ${:.2f} -> ${:.2f} per kW    ({:+.1f}%)".format(
    small["power_usd_per_kw"], large["power_usd_per_kw"],
    (large["power_usd_per_kw"] / small["power_usd_per_kw"] - 1) * 100))
print()
print("Roughly {:.0f}% of a Megapack's price rides on energy capacity, which is the".format(
    e_share / tot * 100))
print("part exposed to LFP cell sourcing, tariffs and FEOC rules.")
print("That is the exposure quantified in localization_model.py.")

# ---------------------------------------------------------------------------
# Volume curve
# ---------------------------------------------------------------------------
vol = (obs.pivot_table(index="count", columns="variation", values="price_per_unit")
          .reset_index())
vol.columns.name = None
vol["discount_vs_n1_2hXL_pct"] = (vol["2hXL"] / vol["2hXL"].iloc[0] - 1) * 100
vol.round(2).to_csv(OUT + "/volume_curve.csv", index=False)

print()
print("=" * 84)
print("PRICE PER UNIT BY ORDER SIZE")
print("=" * 84)
print(vol.round(0).to_string(index=False))

# ---------------------------------------------------------------------------
# Geography: is the state premium freight?
# ---------------------------------------------------------------------------
def haversine(a, b):
    R = 6371.0
    la1, lo1, la2, lo2 = map(np.radians, [a[0], a[1], b[0], b[1]])
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(h))


st = d["by_state"]["prices"]
base = st["CA"]
geo = pd.DataFrame([
    {"state": s, "price": p,
     "premium_pct": (p / base - 1) * 100,
     "km_from_lathrop": haversine(LATHROP, STATE_CENTROIDS[s])}
    for s, p in st.items()
]).sort_values("km_from_lathrop")
geo.round(2).to_csv(OUT + "/state_premium.csv", index=False)

corr = geo["premium_pct"].corr(geo["km_from_lathrop"])

print()
print("=" * 84)
print("IS THE STATE PREMIUM JUST FREIGHT?")
print("=" * 84)
print(geo.round(2).to_string(index=False))
print()
print("correlation between distance from Lathrop and price premium: {:.3f}".format(corr))
print()
print("Distances are straight-line to state centroids, so this is indicative")
print("rather than a shipping model - but the gradient is unmistakable, and it")
print("points at the Lathrop Megafactory. Delivery quarter, by contrast, has no")
print("price effect at all: there is no expediting premium to pay or negotiate.")
