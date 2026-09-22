"""
Step 4 - Charts.

Palette and mark rules follow a validated colourblind-safe categorical set.
Conventions held throughout:
  * one y-axis per chart, never two
  * hue identifies an entity and never changes when the series count changes
  * grid is a recessive hairline; spines are removed except the baseline
  * value labels sit in ink colours, never in the series colour
  * every group estimate carries its sample size, so a thin estimate looks thin
"""
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# Repo root, derived from this file's own location so the project runs
# anywhere after a clone rather than only on the machine that wrote it.
ROOT = str(pathlib.Path(__file__).resolve().parents[2]).replace("\\", "/")
OUT = ROOT + "/project-2-queue-survival/output"

# --- validated categorical slots (light mode) -------------------------------
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
# --- chrome -----------------------------------------------------------------
SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE = "#e1e0d9", "#c3c2b7"
WAITING = "#d8d7d0"          # neutral for the "neither yet" band

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans"],
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK2,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "font.size": 10,
})


def style(ax, xgrid=False):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.grid(axis="x" if xgrid else "y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def titles(ax, title, subtitle=None):
    """Title above subtitle above the plot, in axes-fraction space so they
    never collide with the data or with each other."""
    ax.set_title(title, loc="left", pad=32 if subtitle else 14)
    if subtitle:
        ax.text(0, 1.03, subtitle, transform=ax.transAxes, color=MUTED,
                fontsize=9, va="bottom", ha="left")


def save(fig, name):
    fig.savefig("{}/{}".format(OUT, name), dpi=150, bbox_inches="tight",
                facecolor=SURFACE)
    plt.close(fig)
    print("wrote", name)


# ===========================================================================
# 1. What happens to a project - composition over time
# ===========================================================================
cur = pd.read_csv(OUT + "/cif_curves_overall.csv")
cur = cur[cur["years"] <= 12]
built, withdrawn = cur["cif_built"] * 100, cur["cif_withdrawn"] * 100
waiting = 100 - built - withdrawn

fig, ax = plt.subplots(figsize=(9, 5.2))
ax.stackplot(cur["years"], built, withdrawn, waiting,
             colors=[BLUE, ORANGE, WAITING],
             edgecolor=SURFACE, linewidth=0.8)
style(ax)
ax.set_xlim(0, 12)
ax.set_ylim(0, 100)
ax.set_xlabel("Years since interconnection request")
ax.set_ylabel("Share of projects (%)")
titles(ax, "Most projects that ask to connect to the grid are never built",
       "20,087 generation and storage requests, 1997-2025, regions reporting operation dates")

# Direct labels inside the bands - identity without relying on colour
ax.text(9.6, built.iloc[-1] / 2, "Built", color="white", fontweight="bold",
        fontsize=11, ha="left", va="center")
ax.text(9.6, built.iloc[-1] + withdrawn.iloc[-1] / 2, "Withdrawn", color="white",
        fontweight="bold", fontsize=11, ha="left", va="center")
ax.text(9.6, 100 - waiting.iloc[-1] / 2, "Still waiting", color=INK2,
        fontweight="bold", fontsize=11, ha="left", va="center")
save(fig, "01_outcome_composition.png")


# ===========================================================================
# 2. The methodological point - naive vs competing risks
# ===========================================================================
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.plot(cur["years"], cur["naive_km_built"] * 100, color=ORANGE, linewidth=2,
        label="Naive Kaplan-Meier (treats withdrawal as censoring)")
ax.plot(cur["years"], built, color=BLUE, linewidth=2,
        label="Competing-risks estimate (correct)")
style(ax)
ax.set_xlim(0, 12)
ax.set_ylim(0, 72)
ax.set_xlabel("Years since interconnection request")
ax.set_ylabel("Estimated probability of being built (%)")
titles(ax, "Treating withdrawals as censoring overstates completion by ~2.9x at ten years",
       "A withdrawn project cannot later be built. Censoring assumes it still might.")

y_naive = cur["naive_km_built"].iloc[-1] * 100
y_true = built.iloc[-1]
ax.annotate("", xy=(11.5, y_naive), xytext=(11.5, y_true),
            arrowprops=dict(arrowstyle="<->", color=INK2, linewidth=1.3))
ax.text(11.25, (y_naive + y_true) / 2, "the error", color=INK2, fontsize=10,
        rotation=90, ha="right", va="center", fontweight="bold")
ax.legend(frameon=False, loc="upper left", fontsize=9.5, labelcolor=INK2)
save(fig, "02_naive_vs_competing_risks.png")


# ===========================================================================
# 3. Completion by technology
# ===========================================================================
tech = pd.read_csv(OUT + "/cif_by_tech.csv").sort_values("built_5yr_pct")
labels = ["{}\n(n={:,}, {:,} tracked 5yr)".format(r.tech, int(r.n), int(r.n_observed_5yr))
          for r in tech.itertuples()]

fig, ax = plt.subplots(figsize=(9, 5.6))
ax.barh(range(len(tech)), tech["built_5yr_pct"], color=BLUE, height=0.62, zorder=3)
style(ax, xgrid=True)
ax.set_yticks(range(len(tech)))
ax.set_yticklabels(labels, fontsize=9, color=INK2)
ax.set_xlabel("Probability of being built within 5 years (%)")
ax.set_xlim(0, 50)
titles(ax, "The technologies the energy transition depends on fare worst",
       "Batteries entered the queue mostly after 2019, so their 5-year estimate rests on a small early sample")
for i, v in enumerate(tech["built_5yr_pct"]):
    ax.text(v + 0.7, i, "{:.1f}%".format(v), va="center", color=INK, fontsize=10,
            fontweight="bold")
save(fig, "03_completion_by_tech.png")


# ===========================================================================
# 4. Completion by region
# ===========================================================================
reg = pd.read_csv(OUT + "/cif_by_region.csv").sort_values("built_5yr_pct")
fig, ax = plt.subplots(figsize=(9, 4.4))
ax.barh(reg["region"], reg["built_5yr_pct"], color=BLUE, height=0.6, zorder=3)
style(ax, xgrid=True)
ax.set_xlabel("Probability of being built within 5 years (%)")
ax.set_xlim(0, 25)
titles(ax, "Same queue, different markets: ERCOT builds 5.6x more often than CAISO",
       "Only regions that report commercial operation dates. ISO-NE, NYISO, Southeast and West excluded.")
for i, v in enumerate(reg["built_5yr_pct"]):
    ax.text(v + 0.35, i, "{:.1f}%".format(v), va="center", color=INK, fontsize=10,
            fontweight="bold")
ax.tick_params(axis="y", labelcolor=INK2)
save(fig, "04_completion_by_region.png")


# ===========================================================================
# 5. Deterioration over time
# ===========================================================================
era = pd.read_csv(OUT + "/cif_by_era.csv")
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.bar(era["era"], era["built_5yr_pct"], color=BLUE, width=0.55, zorder=3)
style(ax)
ax.set_ylabel("Built within 5 years of request (%)")
ax.set_xlabel("Year the project entered the queue")
ax.set_ylim(0, 30)
titles(ax, "A project filed recently is a quarter as likely to get built as one filed in 2005",
       "Every era measured at the same 5-year horizon, so the comparison is like-for-like")
for i, r in enumerate(era.itertuples()):
    ax.text(i, r.built_5yr_pct + 0.6, "{:.1f}%".format(r.built_5yr_pct), ha="center",
            color=INK, fontsize=11, fontweight="bold")
    ax.text(i, 0.8, "n={:,}".format(int(r.n)), ha="center", color="white", fontsize=9)
ax.tick_params(axis="x", labelcolor=INK2)
save(fig, "05_era_trend.png")


# ===========================================================================
# 6. Worked example - identical project, five markets
# ===========================================================================
scen = pd.read_csv(OUT + "/scenario_battery_by_region.csv").sort_values(
    "predicted_built_7yr_pct")
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.barh(scen["region"], scen["predicted_built_7yr_pct"], color=AQUA, height=0.6, zorder=3)
style(ax, xgrid=True)
ax.set_xlabel("Model-predicted probability of being built within 7 years (%)")
ax.set_xlim(0, 27)
titles(ax, "Identical 200 MW battery project, filed the same year, five markets",
       "Logistic model using only what is knowable at filing. Held-out AUC 0.744.")
for i, v in enumerate(scen["predicted_built_7yr_pct"]):
    ax.text(v + 0.4, i, "{:.1f}%".format(v), va="center", color=INK, fontsize=10,
            fontweight="bold")
ax.tick_params(axis="y", labelcolor=INK2)
save(fig, "06_scenario_by_region.png")

print("\nall charts written to", OUT)
