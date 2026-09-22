# Two analyses of the grid-storage supply chain

Both built on real public data, September 2026.

```bash
python verify.py
```

Rebuilds every result from hash-pinned source data and asserts all 24 published
figures. Takes about a minute. See [VERIFY.md](VERIFY.md) for the claim-by-claim
ledger.

The energy-storage business has two hard constraints that have nothing to do with
manufacturing capacity: **what a battery actually costs once policy is priced in**,
and **whether the project it's destined for ever gets built**. One project here
takes each.

---

## 1. [Megapack Price Decomposition & LFP Localisation](project-1-megapack-cost/)

*What's inside a Megapack's price, and should its cells be imported or made domestically?*

Tesla sells the same hardware as a 2-hour and a 4-hour unit — nearly identical
energy, half the power. That difference is enough to solve its published prices
into separate energy and power rates.

**Result:** $218.18/kWh of energy capacity, $84.38/kW of power conversion, $24,373
fixed. Fitted across 18 overdetermined observations at **R² = 1.000000** — this
recovers the pricing formula, it doesn't approximate it.

91% of the price is energy capacity, which is exactly the part exposed to Chinese
LFP supply, Section 301 tariffs and FEOC eligibility. Domestic cells land 47%
cheaper, and failing FEOC costs the customer **3.6× what the tariff does**.

Tracing it back to the raw materials locates the markup: an LFP cell's material
floor is $30/kWh, cell manufacturing runs at **1.99× materials**, and the delivered
system at **7.23×**. Cell production is already efficient — the room is downstream
of the cell. Copper, incidentally, is a larger raw input than lithium.

Incidental findings: state pricing correlates 0.971 with distance from the Lathrop
factory, volume discounts cap out at twenty units, and there is no expediting
premium to buy.

![Where the markup sits in a Megapack](project-1-megapack-cost/output/08_idiot_index.png)

→ [Memo](project-1-megapack-cost/MEMO.md) · [Method](project-1-megapack-cost/README.md) · [Workbook](project-1-megapack-cost/output/megapack_cost_analysis.xlsx)

## 2. [Interconnection Queue Survival Analysis](project-2-queue-survival/)

*Of the projects that ask to connect to the US grid, how many are ever built?*

Competing-risks survival analysis of 20,087 interconnection requests, 1997–2025,
from Lawrence Berkeley National Laboratory's *Queued Up* dataset.

**Result:** 11.2% are built within five years, 20.0% within ten, and 72% are
withdrawn. Completion has fallen from 24.6% to 6.8% across request eras. An
identical 200 MW battery project has a 22.6% chance of being built in ERCOT and
2.7% in CAISO.

The analysis catches two errors that would each have produced a confident wrong
answer: treating withdrawal as censoring (inflates completion 2.9×), and pooling
regions that don't report operation dates (ISO-NE reports zero, and would look like
it builds nothing).

![What happens to a project after it requests interconnection](project-2-queue-survival/output/01_outcome_composition.png)

![Naive Kaplan-Meier versus the competing-risks estimate](project-2-queue-survival/output/02_naive_vs_competing_risks.png)

→ [Memo](project-2-queue-survival/MEMO.md) · [Method](project-2-queue-survival/README.md) · [Workbook](project-2-queue-survival/output/interconnection_queue_analysis.xlsx)

---

## Common approach

- **Every claim is executable.** Each published figure has a test that fails if it
  changes. Raw inputs are pinned by SHA-256, so the pipeline can't silently analyse a
  different file. [VERIFY.md](VERIFY.md) maps claim → script → test → source.
- **Real public data only.** Tesla's own pricing API; LBNL's queue dataset (CC BY 4.0).
  No synthetic numbers anywhere.
- **Interrogate results before trusting them.** Both projects found a headline finding
  that turned out to be an artifact, and both document the check that caught it.
- **Estimators written from scratch** where the method is the point — Kaplan-Meier and
  Aalen-Johansen are about forty lines of readable numpy rather than a library call.
- **Assumptions tagged and ranged.** Every judgement call is marked as one, given a
  range, and varied in sensitivity analysis.
- **Limitations stated up front**, in the memo and the workbook's first sheet, not
  buried in a footnote.

## Repo layout

```
verify.py           one command: rebuild everything, assert every claim
VERIFY.md           claim -> script -> test -> source ledger
tests/              24 executable assertions, one per published figure
data/raw/           source data as captured, hash-pinned, with provenance notes
data/processed/     cached intermediates and audit trails (regenerated)
project-1-.../      src/ · output/ · README.md · MEMO.md · assumptions.json
project-2-.../      src/ · output/ · README.md · MEMO.md
```

Each project's `README.md` lists its scripts in run order. Both run end to end from
raw data with `pandas`, `numpy`, `matplotlib`, `openpyxl`, `scikit-learn` and `pyarrow`
on Python 3.10+.
