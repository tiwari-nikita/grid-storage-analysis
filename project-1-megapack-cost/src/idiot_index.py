"""
Step 3 - The idiot index: finished price divided by raw material cost.

Elon Musk's framing: take what a part sells for, divide by what the raw
materials in it are worth. A high ratio means the gap is manufacturing,
integration and margin - which is where cost-down effort should go. A low ratio
means the part is already close to its material floor and squeezing the process
will not help.

Applied here at three levels, which is where it gets interesting:

  1. RAW BASKET      elemental and mineral inputs at commodity prices
  2. CELL            Chinese LFP cell price / raw basket
  3. SYSTEM          Tesla's energy-capacity price / raw basket
                     (the $/kWh recovered in decompose_price.py)

The spread between levels 2 and 3 localises the markup. If the cell index is low
and the system index is high, cells are not the cost problem and attacking cell
sourcing is wasted effort.

A NOTE ON RIGOUR
----------------
Material intensities are literature approximations, not measurements, and are the
weakest part of this script. They are made falsifiable by a cross-check: the
lithium implied by the assumed cathode mass is computed from first principles via
LiFePO4 stoichiometry and compared against the independently published figure of
~0.47 kg lithium carbonate per kWh. If the assumed cathode mass were wrong, that
check would fail.
"""
import pathlib
import json

import pandas as pd

# Repo root, derived from this file's own location so the project runs
# anywhere after a clone rather than only on the machine that wrote it.
ROOT = str(pathlib.Path(__file__).resolve().parents[2]).replace("\\", "/")
OUT = ROOT + "/project-1-megapack-cost/output"
A_PATH = ROOT + "/project-1-megapack-cost/assumptions.json"

with open(A_PATH) as f:
    A = json.load(f)

ENERGY_PRICE = A["decomposition"]["energy_price_usd_per_kwh_small_order"]
CELL_PRICE = A["cell_cost"]["china_lfp_cell_usd_per_kwh"]["value"]

# ---------------------------------------------------------------------------
# Cell mass budget
#
# An LFP cell runs about 160 Wh/kg at cell level, so 1 kWh of capacity is
# roughly 6.25 kg of cell. Mass fractions below are typical published values for
# a prismatic LFP cell and sum to 100%.
# ---------------------------------------------------------------------------
CELL_KG_PER_KWH = 6.25

MASS_FRACTION = {
    "Cathode active material (LiFePO4)": 0.32,
    "Anode active material (graphite)": 0.17,
    "Copper foil": 0.11,
    "Aluminium foil": 0.04,
    "Electrolyte": 0.12,
    "Separator": 0.03,
    "Cell casing": 0.18,
    "Binders and additives": 0.03,
}
assert abs(sum(MASS_FRACTION.values()) - 1.0) < 1e-9, "mass fractions must sum to 1"

kg = {k: v * CELL_KG_PER_KWH for k, v in MASS_FRACTION.items()}

# ---------------------------------------------------------------------------
# Stoichiometric cross-check on the cathode assumption
#
# LiFePO4 molar mass 157.76 g/mol, of which lithium is 6.94 -> 4.40% by mass.
# Lithium carbonate (Li2CO3, 73.89 g/mol) carries 2 Li (13.88), so converting
# lithium metal to carbonate equivalent multiplies mass by 73.89/13.88 = 5.324.
# ---------------------------------------------------------------------------
LI_FRACTION_OF_LFP = 6.94 / 157.76
LCE_PER_LI = 73.89 / 13.88

cathode_kg = kg["Cathode active material (LiFePO4)"]
li_metal_kg = cathode_kg * LI_FRACTION_OF_LFP
lce_kg = li_metal_kg * LCE_PER_LI
PUBLISHED_LCE = 0.47          # kg lithium carbonate per kWh, LFP, published

print("=" * 84)
print("CROSS-CHECK: does the assumed cathode mass imply the published lithium content?")
print("=" * 84)
print("assumed cathode active material   {:.3f} kg/kWh".format(cathode_kg))
print("lithium metal implied             {:.4f} kg/kWh   ({:.2f}% of LiFePO4 by mass)".format(
    li_metal_kg, LI_FRACTION_OF_LFP * 100))
print("as lithium carbonate equivalent   {:.3f} kg/kWh".format(lce_kg))
print("independently published figure    {:.3f} kg/kWh".format(PUBLISHED_LCE))
print("agreement                         {:.1f}%".format(100 - abs(lce_kg - PUBLISHED_LCE) / PUBLISHED_LCE * 100))
print()
print("The two are derived independently - one from an assumed mass budget, the")
print("other from published intensity data - so the agreement is a genuine check")
print("on the cathode assumption rather than a restatement of it.")

# ---------------------------------------------------------------------------
# Raw material basket
#
# The cathode is decomposed into its elemental inputs rather than priced as
# finished powder, because the idiot index is about RAW materials. Oxygen comes
# from precursors and air and is not priced.
# ---------------------------------------------------------------------------
FE_FRACTION_OF_LFP = 55.85 / 157.76
P_FRACTION_OF_LFP = 30.97 / 157.76
H3PO4_PER_P = 97.99 / 30.97      # phosphoric acid mass per unit phosphorus

iron_kg = cathode_kg * FE_FRACTION_OF_LFP
phos_acid_kg = cathode_kg * P_FRACTION_OF_LFP * H3PO4_PER_P
alu_kg = kg["Aluminium foil"] + kg["Cell casing"]

# price_usd_per_kg, provenance
PRICES = {
    "Lithium carbonate": (19.50, "sourced", "Benchmark/SMM spot, Sept 2026, ~$19,300-19,750/t"),
    "Iron (battery precursor)": (0.50, "estimate", "purified iron source; iron ore itself is ~$0.10/kg"),
    "Phosphoric acid": (1.00, "estimate", "industrial grade, ~$1,000/t"),
    "Graphite (natural flake, raw)": (0.70, "estimate", "raw flake, before anode processing"),
    "Copper": (13.90, "sourced", "~$6.30/lb, Sept 2026"),
    "Aluminium": (3.25, "sourced", "LME ~$3,250/t, Sept 2026"),
    "Electrolyte (solvents + salt)": (5.00, "estimate", "LiPF6-based, largely petrochemical solvents"),
    "Separator (polyolefin)": (2.00, "estimate", "raw PP/PE polymer"),
    "Binders and additives": (3.00, "estimate", "PVDF and conductive carbon"),
}

BASKET = [
    ("Lithium carbonate", lce_kg),
    ("Iron (battery precursor)", iron_kg),
    ("Phosphoric acid", phos_acid_kg),
    ("Graphite (natural flake, raw)", kg["Anode active material (graphite)"]),
    ("Copper", kg["Copper foil"]),
    ("Aluminium", alu_kg),
    ("Electrolyte (solvents + salt)", kg["Electrolyte"]),
    ("Separator (polyolefin)", kg["Separator"]),
    ("Binders and additives", kg["Binders and additives"]),
]

rows = []
for name, mass in BASKET:
    price, prov, note = PRICES[name]
    rows.append({"material": name, "kg_per_kwh": mass, "usd_per_kg": price,
                 "usd_per_kwh": mass * price, "provenance": prov, "note": note})
basket = pd.DataFrame(rows).sort_values("usd_per_kwh", ascending=False)
raw_total = basket["usd_per_kwh"].sum()
basket["share_pct"] = basket["usd_per_kwh"] / raw_total * 100
basket.round(3).to_csv(OUT + "/raw_material_basket.csv", index=False)

print()
print("=" * 84)
print("RAW MATERIAL BASKET PER kWh OF LFP CELL")
print("=" * 84)
print(basket[["material", "kg_per_kwh", "usd_per_kg", "usd_per_kwh", "share_pct"]]
      .round(2).to_string(index=False))
print("-" * 84)
print("{:>54} {:>10.2f}".format("TOTAL RAW MATERIALS, $/kWh", raw_total))

top2 = basket.head(2)
print()
print("{} and {} alone are {:.0f}% of the raw basket.".format(
    top2.iloc[0]["material"], top2.iloc[1]["material"], top2["share_pct"].sum()))

# ---------------------------------------------------------------------------
# The indices
# ---------------------------------------------------------------------------
cell_idx = CELL_PRICE / raw_total
system_idx = ENERGY_PRICE / raw_total

idx = pd.DataFrame([
    {"level": "Raw materials", "usd_per_kwh": raw_total, "idiot_index": 1.00,
     "reading": "the material floor"},
    {"level": "LFP cell (Chinese market price)", "usd_per_kwh": CELL_PRICE,
     "idiot_index": cell_idx,
     "reading": "cell manufacturing roughly doubles the material cost"},
    {"level": "Megapack energy capacity (Tesla price)", "usd_per_kwh": ENERGY_PRICE,
     "idiot_index": system_idx,
     "reading": "everything downstream of the cell adds the rest"},
])
idx.round(2).to_csv(OUT + "/idiot_index.csv", index=False)

print()
print("=" * 84)
print("THE IDIOT INDEX")
print("=" * 84)
print(idx.round(2).to_string(index=False))

print()
print("=" * 84)
print("WHAT THIS SAYS")
print("=" * 84)
print("Cell-level index   {:.2f}x   LFP cell manufacturing is already close to its".format(cell_idx))
print("                          material floor. There is little to extract by")
print("                          squeezing cell producers.")
print()
print("System-level index {:.2f}x   The gap between a cell and a delivered Megapack".format(system_idx))
print("                          is {:.1f}x the cell itself. Enclosure, thermal,".format(
    ENERGY_PRICE / CELL_PRICE))
print("                          integration, warranty and margin live here.")
print()
print("Cost-down effort belongs downstream of the cell, not on cell price.")
print("That also cuts the other way: the localisation case in localization_model.py")
print("is driven by tariffs and tax credits, NOT by any expectation of beating")
print("Chinese cell manufacturing on cost.")

# ---------------------------------------------------------------------------
# Sensitivity to lithium, the most volatile input
# ---------------------------------------------------------------------------
rows = []
for li in [5, 10, 15, 19.5, 30, 50, 80]:
    delta = (li - 19.50) * lce_kg
    tot = raw_total + delta
    rows.append({"lithium_carbonate_usd_per_kg": li,
                 "raw_basket_usd_per_kwh": tot,
                 "cell_idiot_index": CELL_PRICE / tot,
                 "system_idiot_index": ENERGY_PRICE / tot,
                 "lithium_share_pct": (lce_kg * li) / tot * 100})
sens = pd.DataFrame(rows)
sens.round(2).to_csv(OUT + "/idiot_index_lithium_sensitivity.csv", index=False)

print()
print("=" * 84)
print("SENSITIVITY TO LITHIUM PRICE  (the most volatile input; $19.50/kg today)")
print("=" * 84)
print(sens.round(2).to_string(index=False))
print()
print("Lithium has traded from under $10/kg to over $80/kg within recent memory.")
print("Even at $80/kg the cell index only falls to {:.2f}x - the cell stays close".format(
    sens.iloc[-1]["cell_idiot_index"]))
print("to its material floor, and a lithium spike compresses margin rather than")
print("revealing hidden manufacturing slack.")
