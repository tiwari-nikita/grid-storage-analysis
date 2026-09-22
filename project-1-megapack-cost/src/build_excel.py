"""
Step 4 - Assemble the Megapack cost work into one reviewable Excel workbook.

Includes a flattened view of assumptions.json so a reader can see, in one place,
which numbers are sourced from public documents and which are judgement calls
with a range. That distinction is the difference between a model you can argue
with and one you have to take on faith.
"""
import pathlib
import json
import os

import pandas as pd
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Repo root, derived from this file's own location so the project runs
# anywhere after a clone rather than only on the machine that wrote it.
ROOT = str(pathlib.Path(__file__).resolve().parents[2]).replace("\\", "/")
BASE = ROOT + "/project-1-megapack-cost"
OUT = BASE + "/output"
XLSX = OUT + "/megapack_cost_analysis.xlsx"

INK = "FF0B0B0B"
HEAD_FILL = PatternFill("solid", fgColor="FF1C5CAB")
BAND_FILL = PatternFill("solid", fgColor="FFF2F5FA")
THIN = Side(style="thin", color="FFD8D7D0")

NOTES = [
    ("Megapack Price Decomposition and LFP Localisation", 16, True),
    ("", 11, False),
    ("QUESTION", 12, True),
    ("What is actually inside a Megapack's price, and should the cells in it be "
     "imported or made domestically?", 11, False),
    ("", 11, False),
    ("METHOD", 12, True),
    ("Tesla sells Megapack in a 2-hour configuration (1.92 MW / 3.86 MWh per unit) and "
     "a 4-hour one (0.98 MW / 3.92 MWh). Nearly identical energy, half the power. Any "
     "price gap between them is therefore attributable to power-conversion hardware "
     "rather than cells, which lets price be solved into an energy rate ($/kWh) and a "
     "power rate ($/kW).", 11, False),
    ("Crucially this is not algebra on two numbers. The model is fitted by least squares "
     "across 24 observed prices against 3 unknowns, so it is heavily overdetermined and "
     "the residuals are a genuine test. It fits to R-squared 1.000000 with a worst "
     "residual of 0.000%, which means the decomposition is not an approximation - it "
     "recovers the pricing formula itself.", 11, False),
    ("", 11, False),
    ("HEADLINE NUMBERS", 12, True),
    ("Energy capacity      $218.18/kWh small order, $204.13/kWh at volume", 11, False),
    ("Power conversion     $84.38/kW small order, $78.95/kW at volume", 11, False),
    ("Fixed order charge   $24,373, identical across both configurations", 11, False),
    ("Energy is 91% of the price of a 4-hour Megapack, so sourcing risk concentrates there.", 11, False),
    ("", 11, False),
    ("DATA SOURCE", 12, True),
    ("Tesla's public Megapack pricing endpoint at tesla.com/api/energy/ecg/megapackPricing, "
     "the same one its own order configurator calls. Captured 2026-09-19: 24 quantity "
     "points, 12 states, 4 delivery quarters. Prices exclude taxes and installation.", 11, False),
    ("", 11, False),
    ("PRICE VS COST", 12, True),
    ("This decomposes PRICE, not cost. Turning price into cost needs a margin assumption, "
     "which is made explicitly in the localisation model and never smuggled in.", 11, False),
    ("", 11, False),
    ("KNOWN LIMITATIONS", 12, True),
    ("- The US manufacturing cost uplift (1.30x central) is the softest input in the model. "
     "No authoritative public figure exists. Sensitivity runs 1.15-1.60x and the break-even "
     "sits at 1.93x, so the conclusion survives the full range.", 11, False),
    ("- Freight, plant capex and utilisation are estimates with stated ranges, all varied "
     "in the Monte Carlo.", 11, False),
    ("- Tariff and tax-credit rules are current as of September 2026 and are moving targets. "
     "Re-check before relying on any conclusion here.", 11, False),
    ("- The FEOC analysis prices the ITC at risk; it does not model whether a specific "
     "bill of materials passes or fails the material-assistance ratio.", 11, False),
]

SHEETS = [
    ("Decomposition", OUT + "/price_decomposition.csv",
     "Least-squares fit of price = fixed + energy x kWh + power x kW, by volume tier."),
    ("Volume curve", OUT + "/volume_curve.csv",
     "Price per unit against order size. Discount caps out around 20 units."),
    ("State premium", OUT + "/state_premium.csv",
     "Price premium vs California against distance from the Lathrop factory."),
    ("Idiot index", OUT + "/idiot_index.csv",
     "Finished price divided by the raw materials inside it, at three levels."),
    ("Raw materials", OUT + "/raw_material_basket.csv",
     "Material intensity and commodity cost per kWh of LFP cell."),
    ("Lithium sensitivity", OUT + "/idiot_index_lithium_sensitivity.csv",
     "How the indices move with lithium carbonate price, the most volatile input."),
    ("Base case", OUT + "/base_case.csv",
     "Landed cost per kWh of cell: import from China vs manufacture domestically."),
    ("Breakeven uplift", OUT + "/breakeven_uplift.csv",
     "How much more expensive US manufacturing can be before importing wins."),
    ("Decision surface", OUT + "/decision_surface.csv",
     "Localisation advantage across US cost uplift and tariff rate."),
    ("45X phase-down", OUT + "/phase_down_sensitivity.csv",
     "Localisation advantage by production year as the 45X credit steps down."),
    ("FEOC at risk", OUT + "/feoc_value_at_risk.csv",
     "Investment tax credit at risk if a project fails FEOC, against the tariff burden."),
    ("Monte Carlo", OUT + "/monte_carlo_summary.csv",
     "20,000 draws over every assumption marked 'estimate'."),
    ("Monte Carlo dist", OUT + "/monte_carlo_histogram.csv",
     "Binned distribution of the localisation advantage."),
]

CHARTS = [
    ("01_price_decomposition.png", "What you are paying for"),
    ("08_idiot_index.png", "Where the markup actually sits"),
    ("09_raw_material_basket.png", "What the raw materials are"),
    ("04_import_vs_localise.png", "Import vs domestic"),
    ("05_decision_surface.png", "Decision surface"),
    ("07_feoc_vs_tariff.png", "The tariff is the small problem"),
    ("06_phase_down.png", "45X phase-down"),
    ("03_freight_gradient.png", "The factory, visible in the price list"),
    ("02_volume_curve.png", "Volume discount"),
]


def flatten_assumptions(path):
    with open(path) as f:
        a = json.load(f)
    rows = []

    def walk(node, trail):
        if isinstance(node, dict):
            if "value" in node:
                rows.append({
                    "parameter": " / ".join(trail),
                    "value": node.get("value"),
                    "low": node.get("low"),
                    "high": node.get("high"),
                    "provenance": node.get("provenance", ""),
                    "note": node.get("note", ""),
                    "sources": " | ".join(node.get("sources", [])),
                })
                return
            for k, val in node.items():
                if k.startswith("_"):
                    continue
                walk(val, trail + [k])

    walk(a, [])
    return pd.DataFrame(rows)


assumptions = flatten_assumptions(BASE + "/assumptions.json")

with pd.ExcelWriter(XLSX, engine="openpyxl") as writer:
    pd.DataFrame({"": [n[0] for n in NOTES]}).to_excel(
        writer, sheet_name="Read me first", index=False, header=False)
    assumptions.to_excel(writer, sheet_name="Assumptions", index=False)
    for name, path, _ in SHEETS:
        pd.read_csv(path).to_excel(writer, sheet_name=name, index=False)
    pd.DataFrame().to_excel(writer, sheet_name="Charts", index=False)

wb = load_workbook(XLSX)

ws = wb["Read me first"]
ws.column_dimensions["A"].width = 118
for i, (text, size, bold) in enumerate(NOTES, start=1):
    c = ws.cell(row=i, column=1)
    c.font = Font(size=size, bold=bold, color=INK)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    if size == 16:
        ws.row_dimensions[i].height = 26
    elif len(text) > 110:
        ws.row_dimensions[i].height = 46
ws.sheet_view.showGridLines = False

for name, _, caption in [("Assumptions", None,
                          "Every model input. 'sourced' is from a cited public document; "
                          "'estimate' is a judgement call, varied over its range in the Monte Carlo.")] + SHEETS:
    ws = wb[name]
    ws.insert_rows(1, 2)
    ws["A1"] = caption
    ws["A1"].font = Font(size=11, italic=True, color="FF52514E")

    hr, ncols = 3, ws.max_column
    for j in range(1, ncols + 1):
        c = ws.cell(row=hr, column=j)
        c.fill = HEAD_FILL
        c.font = Font(bold=True, color="FFFFFFFF", size=10)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[hr].height = 30

    for i, row in enumerate(ws.iter_rows(min_row=hr + 1, max_row=ws.max_row, max_col=ncols)):
        for c in row:
            c.border = Border(bottom=THIN)
            c.alignment = Alignment(vertical="top", wrap_text=(name == "Assumptions"))
            if isinstance(c.value, float):
                c.number_format = "0.00"
            if i % 2 == 1:
                c.fill = BAND_FILL

    for j in range(1, ncols + 1):
        longest = max((len(str(ws.cell(row=r, column=j).value or ""))
                       for r in range(hr, min(ws.max_row, 200) + 1)), default=10)
        ws.column_dimensions[get_column_letter(j)].width = min(max(longest + 3, 11),
                                                               60 if name == "Assumptions" else 30)
    ws.freeze_panes = ws.cell(row=hr + 1, column=1)
    ws.sheet_view.showGridLines = False

ws = wb["Charts"]
ws.sheet_view.showGridLines = False
ws.column_dimensions["A"].width = 3
row = 2
for fname, caption in CHARTS:
    p = os.path.join(OUT, fname)
    if not os.path.exists(p):
        continue
    c = ws.cell(row=row, column=2, value=caption)
    c.font = Font(size=13, bold=True, color=INK)
    img = XLImage(p)
    img.height = int(img.height * (820 / img.width))
    img.width = 820
    ws.add_image(img, "B{}".format(row + 1))
    row += int(img.height / 19) + 4

wb.save(XLSX)
print("workbook written ->", XLSX)
print("sheets:", ", ".join(wb.sheetnames))
