# Verification

Every number claimed anywhere in this repository — on a CV, in a memo, in a README —
is listed below with the script that produces it and the test that will fail if it
changes.

```bash
python verify.py
```

Checks dependencies, confirms raw inputs are byte-identical to capture, rebuilds
every result from scratch, and asserts all 29 claims. Takes about a minute.
Exit code 0 means every claim holds.

Run the claims alone with `python -m pytest tests/ -v` or `python tests/test_claims.py`.

---

## Why this exists

Anyone can put a number on a CV. The useful question is whether a stranger can check
it without taking your word for anything. This layer means they can: the raw inputs
are hash-pinned, the pipeline rebuilds from those inputs, and each claim is an
executable assertion rather than a sentence.

It also protects against the more likely failure — me changing an assumption six
months from now and forgetting that a number downstream was quoted somewhere.

## Data integrity

Raw inputs are pinned by SHA-256 and checked before anything else runs.

| File | SHA-256 | Size |
|---|---|---|
| `LBNL_Ix_Queue_Data_File_thru2025.xlsx` | `794582d3…76a08b6` | 15,571,236 B |
| `megapack_pricing_grid_2026-09-19.json` | `bd7f59c3…d9364bac` | 3,052 B |

If a hash mismatches, the test fails loudly rather than silently analysing a
different file. Note that LBNL revises *Queued Up* annually — a mismatch after
re-downloading means the upstream data was updated, and results may legitimately
differ.

## Project 1 — Megapack price decomposition

| Claim | Value | Produced by | Test |
|---|---|---|---|
| Energy capacity rate | $218.18 / kWh | `decompose_price.py` | `test_p1_energy_rate` |
| Power conversion rate | $84.38 / kW | `decompose_price.py` | `test_p1_power_rate` |
| Fixed order charge | $24,373 | `decompose_price.py` | `test_p1_fixed_charge` |
| Fit quality | R² = 1.000000, residual < 0.001% | `decompose_price.py` | `test_p1_fit_quality` |
| Overdetermination | 18 observations, 3 unknowns | `decompose_price.py` | `test_p1_total_observations` |
| Energy share of price | 91.2% | `decompose_price.py` | `test_p1_energy_share` |
| Freight gradient | r = 0.971 vs distance from Lathrop | `decompose_price.py` | `test_p1_freight_gradient` |
| No expediting premium | all 2027 quarters identical | raw capture | `test_p1_no_expediting_premium` |
| Raw material floor | $30.19 / kWh | `idiot_index.py` | `test_p1_raw_material_floor` |
| Stoichiometric cross-check | 0.468 vs 0.47 kg LCE/kWh published | `idiot_index.py` | `test_p1_lithium_stoichiometry_crosscheck` |
| Copper exceeds lithium | $9.56 vs $9.13; 62% combined | `idiot_index.py` | `test_p1_copper_exceeds_lithium` |
| Idiot index, cell / system | 1.99× / 7.23× | `idiot_index.py` | `test_p1_idiot_indices` |
| Lithium sensitivity | cell index ~1.0× even at $80/kg | `idiot_index.py` | `test_p1_cell_stays_near_material_floor` |
| Import landed cost | $80.04 / kWh | `localization_model.py` | `test_p1_landed_costs` |
| Domestic landed cost | $42.41 / kWh (47% cheaper) | `localization_model.py` | `test_p1_landed_costs` |
| Break-even US cost uplift | 1.93× at 28.4% tariff | `localization_model.py` | `test_p1_breakeven_uplift` |
| FEOC exposure vs tariff | $61.24 vs $17.04 = 3.6× | `localization_model.py` | `test_p1_feoc_dominates_tariff` |
| Monte Carlo robustness | domestic cheaper in 100% of 20,000 draws | `localization_model.py` | `test_p1_monte_carlo_robustness` |
| 45X phase-down | cost case turns negative in 2033 | `localization_model.py` | `test_p1_45x_phase_down_flips_2033` |

**Source:** Tesla's public pricing endpoint `tesla.com/api/energy/ecg/megapackPricing`,
captured 2026-09-19. Policy inputs are cited individually in `assumptions.json`.

## Project 2 — Interconnection queue survival

| Claim | Value | Produced by | Test |
|---|---|---|---|
| Sample size | 20,087 requests | `build_dataset.py` | `test_p2_sample_size` |
| Built within 5 years | 11.2% | `survival.py` | `test_p2_completion_rates` |
| Built within 10 years | 20.0% | `survival.py` | `test_p2_completion_rates` |
| Withdrawn by 10 years | 72.3% | `survival.py` | `test_p2_completion_rates` |
| Naive-KM overstatement | 2.90× at 10 years | `survival.py` | `test_p2_naive_overstatement` |
| ERCOT vs CAISO | 20.7% vs 3.7% at 5 years | `survival.py` | `test_p2_regional_gap` |
| Era decline | 24.6% → 6.8%, monotonic | `survival.py` | `test_p2_declining_completion` |
| Scenario spread | 22.6% ERCOT vs 2.7% CAISO | `completion_model.py` | `test_p2_scenario_spread` |
| ISO-NE reporting gap | 0 COD dates / 227 operational | `build_dataset.py` | `test_p2_iso_ne_reporting_gap` |
| Regions excluded | 4 excluded, 5 retained | `build_dataset.py` | `test_p2_excluded_regions` |

**Source:** Lawrence Berkeley National Laboratory, *Queued Up* 2026 Edition
(data through year-end 2025), CC BY 4.0, from <https://emp.lbl.gov/queues>.

## Independent cross-checks

Three tests assert nothing about published claims and everything about whether the
work is self-consistent. They would catch a silent bug that left every headline
number looking perfectly plausible:

- **`test_p1_lithium_stoichiometry_crosscheck`** — the weakest inputs in the idiot
  index are the assumed material intensities. The lithium content implied by the
  assumed cathode mass is computed from LiFePO4 molar composition and compared to
  an independently published figure of 0.47 kg LCE/kWh. It lands at 0.468. The two
  numbers come from different sources, so agreement is evidence the mass budget is
  right rather than a restatement of the assumption.

- **`test_p2_outcomes_sum_to_one`** — built + withdrawn + still-waiting must equal
  100% at every horizon. A competing-risks estimator that doesn't partition the
  sample is broken regardless of what the individual curves look like.
- **`test_p2_confidence_intervals_bracket_estimates`** — every bootstrap interval
  must contain its own point estimate.

## What this layer does not do

It verifies that the code produces the numbers claimed, and that it does so from
unmodified source data. It does **not** verify that the assumptions are correct.

The soft inputs in Project 1 — US manufacturing cost uplift, freight, plant capex,
utilisation — are judgement calls, tagged `estimate` in `assumptions.json` with
explicit ranges, and varied in sensitivity analysis. Tariff and tax-credit rules
were current as of September 2026 and will move. No test can tell you an assumption
is wrong; that is what the ranges and the Monte Carlo are for.
