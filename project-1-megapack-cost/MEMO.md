# What's actually inside a Megapack's price — and where its sourcing risk sits

**Analysis memo · September 2026**
**Source:** Tesla's public Megapack pricing API, captured 19 September 2026 — 24 quantity points, 12 states, 4 delivery quarters

---

## Bottom line

Tesla's published Megapack prices decompose exactly into **$218.18 per kWh of energy capacity, $84.38 per kW of power conversion, and a $24,373 fixed order charge.** Not approximately — the model fits 18 overdetermined observations at R² = 1.000000 with a worst residual under 0.001%.

That matters because it locates the risk. **91% of a 4-hour Megapack's price rides on energy capacity** — the LFP cells — which is precisely the part exposed to Chinese supply, Section 301 tariffs and FEOC eligibility rules. Power electronics are less than a tenth of the price and a rounding error in the sourcing decision.

On that decision: domestic LFP cells land at **$42/kWh against $80/kWh imported**, 47% cheaper, and the conclusion holds across every plausible assumption I can construct.

## How the decomposition works

Tesla sells the same hardware in two configurations — a 2-hour unit at 1.92 MW / 3.86 MWh, and a 4-hour unit at 0.98 MW / 3.92 MWh. Nearly identical energy, half the power. Any price difference between them is therefore attributable to power-conversion hardware rather than cells, which is enough to solve price into separate energy and power rates.

Two equations and two unknowns would fit perfectly by construction and prove nothing, so the model is fitted by least squares across all 24 observed prices against 3 unknowns. The perfect fit across that many degrees of freedom is the finding: this isn't a curve fit, it recovers the pricing formula itself.

Three things fall out that Tesla doesn't publish:

**Volume discounts cap early.** Per-unit price falls about 9% from one unit to twenty, then goes flat. Both the energy and power rates drop by exactly 6.4% between tiers — the discount is applied uniformly, not negotiated per component.

**You can see the factory in the price list.** State pricing correlates **0.971** with straight-line distance from Lathrop, California. Hawaii and Puerto Rico sit above the line, which is ocean freight. California and Nevada are the floor.

**There is no expediting premium.** All four 2027 delivery quarters price identically. Schedule is not a commercial lever at the order stage — you cannot pay for an earlier slot.

## Where the markup actually sits

Applying the idiot index — finished price divided by the raw materials inside it — at three levels:

| Level | $/kWh | Index |
|---|---|---|
| Raw materials in an LFP cell | $30.19 | 1.00× |
| LFP cell, Chinese market price | $60.00 | **1.99×** |
| Megapack energy capacity, Tesla price | $218.18 | **7.23×** |

**Cell manufacturing roughly doubles material cost and stops there.** At 1.99× it is already close to its material floor — there is very little to extract by squeezing cell producers, and any plan premised on beating Chinese cell manufacturing on cost is starting from a bad assumption.

The system index of 7.23× is where the room is. Everything downstream of the cell — enclosure, thermal management, integration, controls, warranty and margin — accounts for 3.6× the cell itself. **That is where cost-down effort belongs.**

This also disciplines the sourcing conclusion below: localisation wins on tariffs and tax credits, *not* on any expectation of out-manufacturing China.

**A finding worth flagging separately: copper is a bigger raw input than lithium.** At $9.56/kWh against lithium's $9.13, copper is the single largest line in the basket, and the two together are 62% of raw material cost. Lithium gets the headlines and the price volatility; copper quietly costs more.

*Method note:* the material intensities are literature approximations, which would normally make this the weakest section. They're made falsifiable by a stoichiometric cross-check — the lithium implied by the assumed cathode mass, computed from LiFePO4 molar composition, comes to 0.468 kg LCE/kWh against an independently published 0.47. **99.7% agreement between two figures derived from different places**, which is a real check on the mass budget rather than a restatement of it.

Lithium is the most volatile input, so it gets its own sensitivity: even at $80/kg — roughly four times today's price and within recent historical range — the cell index only falls to 1.03×. A lithium spike compresses margin; it does not reveal hidden manufacturing slack.

## The sourcing decision

| Per kWh of cell | Import from China | Make in the US |
|---|---|---|
| Cell cost | $60.00 | $78.00 *(1.30× uplift)* |
| Tariff (301 at 25% + 3.4% general) | $17.04 | — |
| Ocean freight | $3.00 | — |
| Plant capex, amortised | — | $9.41 |
| Section 45X credit | — | −$45.00 |
| **Landed** | **$80.04** | **$42.41** |

The 45X credit — $35/kWh for cells plus $10/kWh for modules — is simply enormous relative to an LFP cell that costs roughly $60. It dominates everything else in the calculation.

**How wrong can the soft assumption be?** US manufacturing cost uplift is the weakest input; no authoritative public figure exists. At today's 28.4% combined tariff, a US plant could cost **1.93× what a Chinese producer spends** and still land cheaper. The central assumption is 1.30×. Across 20,000 Monte Carlo draws over every estimated input, domestic manufacture is cheaper in **100%** of cases, with a 5th-percentile advantage still above $22/kWh.

Cell price turns out not to be the swing variable at all — domestic wins at every plausible cell price, even at a zero tariff.

## The part that actually decides it

The tariff is the small problem.

| | Per kWh |
|---|---|
| Tariff burden on an imported cell | $17.04 |
| **Investment tax credit at risk if the project fails FEOC** | **$61.24** |

Storage projects beginning construction in 2026 or later must meet a Material Assistance Cost Ratio — a minimum share of material value from non-prohibited sources — to claim the 48E investment tax credit. The threshold is 60% for 2026 and ratchets up roughly 5 points a year thereafter.

Failing it doesn't compress a margin. It removes the entire 30% ITC, **3.6× the tariff burden**, and it lands on the customer rather than on the manufacturer. That makes FEOC compliance a commercial feature of the product, not a procurement detail — a cliff, not a gradient.

On a 20-unit, 78 MWh order: the cost difference between sourcing paths is about **$2.95M**, while the ITC at risk is **$4.80M** against a $17.6M list price.

## What would break this conclusion

The cost case rests on 45X, and 45X expires. As the credit steps down — 75% in 2030, 50% in 2031, 25% in 2032, zero thereafter — the domestic advantage erodes and **turns negative in 2033**. Any localisation investment needs to earn its return inside that window on cost grounds alone.

FEOC eligibility, however, does not expire with 45X. After 2032 the case for domestic cells stops being about cost and becomes entirely about keeping customers' projects creditworthy.

## So what

1. **Treat FEOC compliance as a product feature and price it.** It is worth 3.6× the tariff to the customer and is the strongest differentiator available against imported competition.
2. **Localise cells on the tax-credit window, not on the tariff.** Tariffs are volatile and reversible; 45X has a known schedule, and the investment case should be underwritten to 2032.
3. **Aim cost-down downstream of the cell.** At 1.99× materials the cell is near its floor; the 7.23× system index says the room is in enclosure, thermal, integration and margin. Squeezing cell suppliers is the wrong fight.
4. **Watch copper, not just lithium.** It is the largest single raw input and attracts none of the hedging attention lithium does.
5. **Don't over-engineer power electronics sourcing.** At under 9% of price it cannot move the answer — analytical effort belongs on the energy side.
6. **Stop treating order size as a negotiating lever past twenty units.** The discount curve is flat beyond that, and there's no expediting premium to trade against either.

## Limitations

The US cost uplift, freight, plant capex and utilisation are estimates with stated ranges rather than sourced figures; all are varied in the Monte Carlo and each is tagged in `assumptions.json`. Tariff and tax-credit rules are current as of September 2026 and are moving targets. The FEOC analysis prices the credit at risk — it does not model whether a specific bill of materials passes the material-assistance ratio. And the decomposition is of *price*, not cost; converting one to the other requires a margin assumption stated explicitly rather than assumed quietly.

## Sources

- [BloombergNEF battery price survey](https://about.bnef.com/insights/clean-transport/lithium-ion-battery-pack-prices-fall-to-108-per-kilowatt-hour-despite-rising-metal-prices-bloombergnef/) — LFP cell pricing
- [Benchmark Minerals: US battery imports after Section 301 rose to 25%](https://source.benchmarkminerals.com/article/us-battery-imports-fall-to-five-year-low-after-section-301-tariffs-raised-to-25-)
- [Fluence: impact of US tariffs on energy storage](https://blog.fluenceenergy.com/impact-us-tariffs-energy-storage-industry)
- [Congressional Research Service: Section 45X credit](https://www.congress.gov/crs-product/IF12809)
- [Morgan Lewis: FEOC rules and storage tax credit eligibility](https://www.morganlewis.com/pubs/2026/03/how-feoc-rules-are-reshaping-energy-storage-tax-credit-eligibility)
- [Foley Hoag: prohibited foreign entity rules and battery storage](https://foleyhoag.com/news-and-insights/blogs/energy-and-climate-counsel/2026/july/the-prohibited-foreign-entity-(or-feoc)-rules-and-battery-storage/)
