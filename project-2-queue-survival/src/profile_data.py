"""
Step 0 - Profile the LBNL Queued Up dataset before modelling anything.

The point of this script is to find out what the data can and cannot support.
Specifically: how complete are the date fields, because the whole survival
analysis depends on knowing WHEN a project reached its outcome, not just THAT
it did.
"""
import pathlib
import pandas as pd

# Repo root, derived from this file's own location so the project runs
# anywhere after a clone rather than only on the machine that wrote it.
ROOT = str(pathlib.Path(__file__).resolve().parents[2]).replace("\\", "/")
RAW = ROOT + "/data/raw/LBNL_Ix_Queue_Data_File_thru2025.xlsx"
CACHE = ROOT + "/data/processed/queue_raw.parquet"
SHEET = "03. Complete Queue Data"

DATE_COLS = ["q_date", "prop_date", "on_date", "wd_date", "ia_date"]

# Row 0 of the sheet is a "RETURN TO CONTENTS" navigation link, so the real
# header sits on row 1.
df = pd.read_excel(RAW, sheet_name=SHEET, header=1)

# q_id mixes integers and strings ("Q007 - 061" vs 1234), which parquet rejects.
# Normalise every text column to pandas' nullable string dtype so the cache is
# round-trippable and NaN stays NaN rather than becoming the literal "nan".
for c in df.columns:
    if df[c].dtype == "object":
        df[c] = df[c].astype("string")
for c in DATE_COLS:
    df[c] = pd.to_datetime(df[c], errors="coerce")

df.to_parquet(CACHE, index=False)   # cache so we never re-parse 15MB of xlsx

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)

print(f"rows: {len(df):,}   cols: {len(df.columns)}")
print(f"cached -> {CACHE}\n")

print("=" * 90)
print("QUEUE STATUS")
print("=" * 90)
print(df["q_status"].value_counts(dropna=False).to_string())

print()
print("=" * 90)
print("DATE FIELD COMPLETENESS BY STATUS  (% of rows with a usable date)")
print("=" * 90)
cov = df.groupby("q_status")[DATE_COLS].apply(lambda g: g.notna().mean() * 100).round(1)
print(cov.to_string())

print()
print("=" * 90)
print("DATE RANGES")
print("=" * 90)
for c in DATE_COLS:
    s = df[c].dropna()
    if len(s):
        print(f"{c:10s}  {s.min().date()} -> {s.max().date()}   n={len(s):,}")

print()
print("=" * 90)
print("RESOURCE TYPE (top 12) and REGION")
print("=" * 90)
print(df["type_clean"].value_counts().head(12).to_string())
print()
print(df["region"].value_counts().to_string())

print()
print("=" * 90)
print("CAPACITY (mw_1)")
print("=" * 90)
print(df["mw_1"].describe(percentiles=[.1, .25, .5, .75, .9, .99]).round(1).to_string())
