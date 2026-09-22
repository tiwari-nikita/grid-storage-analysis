"""
Step 3 - Charts for the Megapack cost decomposition and localisation decision.

Same conventions as the queue project: one axis per chart, hue tied to entity,
recessive grid, labels in ink rather than series colour. The decision surface is
the one place a diverging ramp is correct - the quantity has a sign, and the
zero crossing is the whole point - so it uses blue/red with a neutral midpoint
rather than a rainbow.
"""
import pathlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

# Repo root, derived from this file's own location so the project runs
# anywhere after a clone rather than only on the machine that wrote it.
ROOT = str(pathlib.Path(__file__).resolve().parents[2]).replace("\\", "/")
OUT = ROOT + "/project-1-megapack-cost/output"

BLUE, ORANGE, AQUA, RED = "#2a78d6", "#eb6834", "#1baf7a", "#e34948"
SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE = "#e1e0d9", "#c3c2b7"
NEUTRAL = "#d8d7d0"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": BASELINE, "axes.labelcolor": INK2,
    "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.titlesize": 13, "axes.titleweight": "bold", "font.size": 10,
})

DIVERGING = LinearSegmentedColormap.from_list("bwr_brand", [RED, "#f0efec", BLUE])


def style(ax, xgrid=False):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.grid(axis="x" if xgrid else "y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def titles(ax, title, subtitle=None):
    ax.set_title(title, loc="left", pad=32 if subtitle else 14)
    if subtitle:
        ax.text(0, 1.03, subtitle, transform=ax.transAxes, color=MUTED,
                fontsize=9, va="bottom", ha="left")


def save(fig, name):
    fig.savefig("{}/{}".format(OUT, name), dpi=150, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print("wrote", name)


with open(ROOT + "/project-1-megapack-cost/assumptions.json") as f:
    A = json.load(f)
dec = pd.read_csv(OUT + "/price_decomposition.csv")

# ===========================================================================
# 1. What you are actually paying for
# ===========================================================================
small = dec.iloc[0]
e_unit = small["energy_usd_per_kwh"] * 3.92 * 1000
p_unit = small["power_usd_per_kw"] * 0.98 * 1000
tot = e_unit + p_unit

fig, ax = plt.subplots(figsize=(9, 3.4))
ax.barh([0], [e_unit], color=BLUE, height=0.5, zorder=3)
ax.barh([0], [p_unit], left=[e_unit], color=ORANGE, height=0.5, zorder=3,
        edgecolor=SURFACE, linewidth=2)
style(ax, xgrid=True)
ax.set_yticks([])
ax.set_xlim(0, tot * 1.04)
ax.set_xlabel("Price of one 4-hour Megapack (3.92 MWh / 0.98 MW), USD")
titles(ax, "91% of a Megapack's price is energy capacity, not power electronics",
       "Solved from 18 public price points. R-squared 1.000000 - this is Tesla's own pricing formula, recovered.")
ax.text(e_unit / 2, 0, "Energy capacity\n${:,.0f}  ({:.0f}%)\n${:.2f}/kWh".format(
    e_unit, e_unit / tot * 100, small["energy_usd_per_kwh"]),
    ha="center", va="center", color="white", fontweight="bold", fontsize=11)
ax.annotate("Power conversion\n${:,.0f}  ({:.0f}%)\n${:.2f}/kW".format(
    p_unit, p_unit / tot * 100, small["power_usd_per_kw"]),
    xy=(e_unit + p_unit / 2, 0.28), xytext=(e_unit + p_unit / 2, 0.62),
    ha="center", color=INK, fontsize=9.5, fontweight="bold",
    arrowprops=dict(arrowstyle="-", color=INK2, linewidth=1))
save(fig, "01_price_decomposition.png")

# ===========================================================================
# 2. Volume curve
# ===========================================================================
vol = pd.read_csv(OUT + "/volume_curve.csv")
fig, ax = plt.subplots(figsize=(8.5, 4.6))
ax.plot(vol["count"], vol["2hXL"] / 1000, marker="o", markersize=6, linewidth=2,
        color=BLUE, label="2-hour config")
ax.plot(vol["count"], vol["4hXL"] / 1000, marker="o", markersize=6, linewidth=2,
        color=ORANGE, label="4-hour config")
style(ax)
ax.set_xlabel("Megapacks ordered")
ax.set_ylabel("Price per unit (USD thousands)")
titles(ax, "Volume discount is real but caps out at about 20 units",
       "Roughly 9% off the single-unit price, flat thereafter")
ax.legend(frameon=False, labelcolor=INK2, fontsize=9.5)
save(fig, "02_volume_curve.png")

# ===========================================================================
# 3. Freight gradient
# ===========================================================================
geo = pd.read_csv(OUT + "/state_premium.csv")
corr = geo["premium_pct"].corr(geo["km_from_lathrop"])
fig, ax = plt.subplots(figsize=(8.5, 5))
ax.scatter(geo["km_from_lathrop"], geo["premium_pct"], s=70, color=BLUE,
           zorder=3, edgecolor=SURFACE, linewidth=1.5)
m, b = np.polyfit(geo["km_from_lathrop"], geo["premium_pct"], 1)
xs = np.linspace(0, geo["km_from_lathrop"].max() * 1.05, 10)
ax.plot(xs, m * xs + b, color=MUTED, linewidth=1.3, linestyle="--", zorder=2)
for r in geo.itertuples():
    ax.annotate(r.state, (r.km_from_lathrop, r.premium_pct),
                textcoords="offset points", xytext=(7, -3),
                fontsize=9.5, color=INK2, fontweight="bold")
style(ax)
ax.set_xlabel("Straight-line distance from Lathrop, CA (km)")
ax.set_ylabel("Price premium vs California (%)")
titles(ax, "You can see the factory in the price list",
       "Correlation {:.3f}. Hawaii and Puerto Rico sit above the line - ocean freight.".format(corr))
save(fig, "03_freight_gradient.png")

# ===========================================================================
# 4. Import vs localise
# ===========================================================================
base = pd.read_csv(OUT + "/base_case.csv")
imp = base[base["line"] == "LANDED COST"]["import_usd_per_kwh"].iloc[0]
loc = base[base["line"] == "LANDED COST"]["localise_usd_per_kwh"].iloc[0]
body = base[base["line"] != "LANDED COST"]

fig, ax = plt.subplots(figsize=(9.5, 5.6))
colors = {"Chinese LFP cell price": BLUE, "Tariff": ORANGE, "Ocean freight": MUTED,
          "US manufacturing cost": BLUE, "Plant capex, amortised": AQUA,
          "Section 45X credit": RED}
# Short forms so a label always fits inside its segment
SHORT = {"Chinese LFP cell price": "Chinese cell", "Tariff": "Tariff",
         "Ocean freight": "Freight", "US manufacturing cost": "US mfg cost",
         "Plant capex, amortised": "Plant capex", "Section 45X credit": "45X credit"}
W = 0.38

bot_i = bot_l = 0.0
for r in body.itertuples():
    key = r.line.split(" (")[0]
    col, lab = colors.get(key, MUTED), SHORT.get(key, key)
    vi = 0 if pd.isna(r.import_usd_per_kwh) else r.import_usd_per_kwh
    vl = 0 if pd.isna(r.localise_usd_per_kwh) else r.localise_usd_per_kwh
    if vi:
        ax.bar(0, vi, bottom=bot_i, color=col, width=W, edgecolor=SURFACE,
               linewidth=2, zorder=3)
        if vi >= 8:
            ax.text(0, bot_i + vi / 2, "{}\n${:.0f}".format(lab, vi), ha="center",
                    va="center", color="white", fontsize=9.5, fontweight="bold")
        else:   # too thin to label inside - leader line out to the LEFT, so it
                # cannot collide with the net marker sitting on the right
            ax.annotate("{}  ${:.0f}".format(lab, vi), xy=(-W / 2, bot_i + vi / 2),
                        xytext=(-0.48, bot_i + vi / 2), fontsize=9, color=INK2,
                        va="center", ha="right",
                        arrowprops=dict(arrowstyle="-", color=BASELINE, linewidth=1))
        bot_i += vi
    if vl > 0:
        ax.bar(1, vl, bottom=bot_l, color=col, width=W, edgecolor=SURFACE,
               linewidth=2, zorder=3)
        if vl >= 8:
            ax.text(1, bot_l + vl / 2, "{}\n${:.0f}".format(lab, vl), ha="center",
                    va="center", color="white", fontsize=9.5, fontweight="bold")
        bot_l += vl
    elif vl < 0:
        ax.bar(1, vl, bottom=0, color=col, width=W, edgecolor=SURFACE,
               linewidth=2, zorder=3)
        ax.text(1, vl / 2, "{}\n${:.0f}".format(lab, vl), ha="center", va="center",
                color="white", fontsize=9.5, fontweight="bold")

style(ax)
ax.axhline(0, color=INK2, linewidth=1.2, zorder=4)
ax.set_xticks([0, 1])
ax.set_xticklabels(["Import from China", "Make in the US"], fontsize=11.5, color=INK2)
ax.set_ylabel("Landed cost, USD per kWh of cell")
ax.set_xlim(-0.95, 1.65)
ax.set_ylim(-52, 100)
titles(ax, "After tariffs and 45X, domestic LFP lands 47% cheaper",
       "Central assumptions. Every input is in assumptions.json with its range and provenance.")

# Net totals marked just OUTSIDE each column, so the rule never crosses a
# segment label. Horizontal position makes the association unambiguous.
for x, net in [(0, imp), (1, loc)]:
    ax.hlines(net, x + 0.23, x + 0.40, color=INK, linewidth=2.5, zorder=6)
    ax.text(x + 0.43, net, "NET\n${:.0f}".format(net), ha="left", va="center",
            fontsize=12, fontweight="bold", color=INK, linespacing=1.2)
save(fig, "04_import_vs_localise.png")

# ===========================================================================
# 5. Decision surface
# ===========================================================================
surf = pd.read_csv(OUT + "/decision_surface.csv")
piv = surf.pivot(index="us_cost_uplift", columns="tariff_pct",
                 values="localise_advantage_usd_per_kwh")
fig, ax = plt.subplots(figsize=(9, 5.6))
lim = float(np.abs(piv.values).max())
mesh = ax.pcolormesh(piv.columns, piv.index, piv.values, cmap=DIVERGING,
                     norm=TwoSlopeNorm(vcenter=0, vmin=-lim, vmax=lim), shading="auto")
cs = ax.contour(piv.columns, piv.index, piv.values, levels=[0], colors=[INK], linewidths=2)
ax.clabel(cs, fmt={0: "break-even"}, fontsize=10)
ax.scatter([28.4], [1.30], s=140, marker="*", color=INK, zorder=5,
           edgecolor="white", linewidth=1.2)
ax.annotate("today: 28.4% tariff,\n1.30x assumed uplift", xy=(28.4, 1.30),
            xytext=(36, 1.55), fontsize=9.5, color=INK, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=INK2, linewidth=1.2))
ax.set_xlabel("Combined tariff on Chinese cells (%)")
ax.set_ylabel("US manufacturing cost, as a multiple of Chinese cost")
titles(ax, "Domestic LFP wins across almost the entire plausible space",
       "Blue = domestic cheaper. A US plant would have to cost 1.93x Chinese cost at today's tariff before importing wins.")
cb = fig.colorbar(mesh, ax=ax, pad=0.02)
cb.set_label("Localisation advantage, $/kWh", color=INK2)
cb.outline.set_edgecolor(BASELINE)
save(fig, "05_decision_surface.png")

# ===========================================================================
# 6. 45X phase-down
# ===========================================================================
ph = pd.read_csv(OUT + "/phase_down_sensitivity.csv")
cols = [BLUE if a > 0 else RED for a in ph["localise_advantage_usd_per_kwh"]]
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.bar(ph["production_year"], ph["localise_advantage_usd_per_kwh"], color=cols,
       width=0.6, zorder=3)
style(ax)
ax.axhline(0, color=INK2, linewidth=1.2)
ax.set_xlabel("Production year")
ax.set_ylabel("Localisation advantage, $/kWh")
titles(ax, "The cost case depends on 45X, and 45X expires",
       "Domestic manufacture stops paying for itself on cost alone in 2033. FEOC eligibility does not expire with it.")
for r in ph.itertuples():
    off = 1.4 if r.localise_advantage_usd_per_kwh > 0 else -2.8
    ax.text(r.production_year, r.localise_advantage_usd_per_kwh + off,
            "${:.0f}".format(r.localise_advantage_usd_per_kwh), ha="center",
            fontsize=9.5, fontweight="bold", color=INK)
ax.tick_params(axis="x", labelcolor=INK2)
save(fig, "06_phase_down.png")

# ===========================================================================
# 7. FEOC vs tariff
# ===========================================================================
f = pd.read_csv(OUT + "/feoc_value_at_risk.csv").iloc[0]
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(["Tariff on the cell\n(Section 301 + general)", "Investment tax credit\nlost if FEOC fails"],
        [f["tariff_burden_usd_per_kwh"], f["itc_at_risk_usd_per_kwh"]],
        color=[ORANGE, RED], height=0.55, zorder=3)
style(ax, xgrid=True)
ax.set_xlabel("USD per kWh at risk")
ax.set_xlim(0, f["itc_at_risk_usd_per_kwh"] * 1.22)
titles(ax, "The tariff is the small problem",
       "Failing the FEOC material-assistance test costs {:.1f}x what the tariff does - and it lands on the customer.".format(f["ratio"]))
for i, val in enumerate([f["tariff_burden_usd_per_kwh"], f["itc_at_risk_usd_per_kwh"]]):
    ax.text(val + 1.5, i, "${:.2f}".format(val), va="center", fontsize=11,
            fontweight="bold", color=INK)
ax.tick_params(axis="y", labelcolor=INK2)
save(fig, "07_feoc_vs_tariff.png")

# ===========================================================================
# 8. The idiot index - where the markup actually sits
# ===========================================================================
idx = pd.read_csv(OUT + "/idiot_index.csv")
floor = idx.iloc[0]["usd_per_kwh"]

fig, ax = plt.subplots(figsize=(9, 5.4))
labels = ["Raw materials\nin an LFP cell", "LFP cell\n(Chinese market price)",
          "Megapack energy capacity\n(Tesla price)"]
bars = ax.bar(range(3), idx["usd_per_kwh"], color=[MUTED, BLUE, ORANGE],
              width=0.5, zorder=3)
ax.axhline(floor, color=INK2, linewidth=1.3, linestyle="--", zorder=4)
ax.text(0.42, floor + 5, "material floor  ${:.0f}/kWh".format(floor), ha="left",
        fontsize=9, color=INK2, fontweight="bold")
style(ax)
ax.set_xticks(range(3))
ax.set_xticklabels(labels, fontsize=10, color=INK2)
ax.set_ylabel("USD per kWh")
ax.set_ylim(0, 250)
titles(ax, "Cell manufacturing is efficient. Everything after it is not.",
       "Idiot index = finished price divided by the raw materials inside it.")
for i, r in enumerate(idx.itertuples()):
    ax.text(i, r.usd_per_kwh + 8, "${:.0f}".format(r.usd_per_kwh), ha="center",
            fontsize=12, fontweight="bold", color=INK)
    ax.text(i, r.usd_per_kwh / 2, "{:.2f}x".format(r.idiot_index), ha="center",
            va="center", fontsize=17, fontweight="bold",
            color="white" if i else INK2)
save(fig, "08_idiot_index.png")

# ===========================================================================
# 9. What the raw materials actually are
# ===========================================================================
bk = pd.read_csv(OUT + "/raw_material_basket.csv").sort_values("usd_per_kwh")
fig, ax = plt.subplots(figsize=(9, 5))
cols = [ORANGE if m in ("Copper", "Lithium carbonate") else BLUE for m in bk["material"]]
ax.barh(bk["material"], bk["usd_per_kwh"], color=cols, height=0.62, zorder=3)
style(ax, xgrid=True)
ax.set_xlabel("USD per kWh of cell")
ax.set_xlim(0, 11.6)
titles(ax, "Copper is a bigger input than lithium",
       "Together they are 62% of the raw material cost of an LFP cell. Lithium gets the headlines.")
for i, r in enumerate(bk.itertuples()):
    ax.text(r.usd_per_kwh + 0.15, i, "${:.2f}".format(r.usd_per_kwh), va="center",
            fontsize=9.5, fontweight="bold", color=INK)
ax.tick_params(axis="y", labelcolor=INK2, labelsize=9)
save(fig, "09_raw_material_basket.png")

print("\nall charts written to", OUT)
