# Why 4 out of 5 grid projects never get built — and what that means for a storage order book

**Analysis memo · September 2026**
**Source:** LBNL *Queued Up* 2026 Edition (data through year-end 2025), CC BY 4.0 · 20,087 generation and storage interconnection requests, 1997–2025

---

## Bottom line

A project that requests grid interconnection has an **11.2% chance of being built within five years** and a **20.0% chance within ten**. Roughly **72% are withdrawn**. The constraint on deploying storage in the United States is not manufacturing capacity — it is the queue.

More usefully: that probability is not uniform. An identical 200 MW battery project has a **22.6% chance of reaching operation in ERCOT and a 2.7% chance in CAISO**. Any pipeline forecast that treats those two orders as equivalent is wrong by a factor of eight.

## What the data shows

**Completion is low and falling.** Measured at a fixed five-year horizon so eras compare like-for-like, completion has fallen from 24.6% for 1997–2009 filings to 6.8% for 2019–2020 filings. Withdrawals happen fast — median 1.6 years — while completions take a median 3.6 years.

**The technologies the transition depends on do worst.** Within five years: Gas 28.0%, Wind 14.2%, Solar 5.6%, Battery 3.5%, Solar+Battery 1.2%. Part of this is age — batteries entered the queue mostly after 2019, so their estimate rests on a few hundred mature projects — but the ordering is consistent and holds at seven years too.

**Market matters more than technology.** ERCOT completes 20.7% within five years against CAISO's 3.7%, a 5.6x gap between two large, well-documented markets. A logistic model using only what is knowable the day a request is filed reaches **AUC 0.744** on held-out data, and market is its strongest single signal. Larger projects fare *worse*: each tenfold increase in nameplate capacity cuts the odds of completion by about 39%.

**One milestone separates survivors from casualties.** Adding "has a signed interconnection agreement" lifts model AUC from 0.744 to 0.824, with an odds ratio of 3.1. It is useless as a forecasting input — it happens years after filing — but it is the cleanest available gate for pipeline confidence.

## Why the method matters

Most published queue analysis treats withdrawn projects as *censored* — statistical language for "we stopped watching, it might still happen." A withdrawn project cannot later be built. Treating withdrawal as censoring is the standard error in this literature, and here it inflates the ten-year completion estimate from the correct **20.0% to 58.0%** — a **2.9x overstatement**. This analysis uses Aalen-Johansen cumulative incidence, which models being built and being withdrawn as competing outcomes.

A second trap: four regions barely report commercial operation dates. ISO-NE reports **zero** across 227 operational projects. Pooling them would have produced a confident, false finding that New England builds nothing. They are excluded and the exclusion is documented.

## So what

1. **Weight the order pipeline by market-specific completion probability**, not by nameplate MW. A megawatt of signed ERCOT demand and a megawatt of signed CAISO demand are not the same forecast input.
2. **Treat interconnection agreement execution as the recognition gate** for production planning confidence. Before that milestone, a project is closer to a lead than an order.
3. **Expect long conversion in CAISO, PJM and MISO** and plan build-slot allocation accordingly — the constraint there is queue throughput, not customer demand.
4. **Long-lead equipment is the lever worth pulling.** Since withdrawal happens at a median 1.6 years, well before most hardware decisions, the commercial risk is concentrated early — which argues for staged commitments rather than firm allocation at order.

## Limitations

Roughly 30% of operational and 35% of withdrawn projects lack an outcome date and are excluded from duration estimates; dropped rows resemble kept rows on size and cohort year, so the bias looks mild but is not zero. Battery estimates will move as those cohorts mature. The model is associational — it ranks and forecasts, it does not establish that filing in ERCOT *causes* success.

## Reproducing this

`src/` runs end to end in six scripts, from the raw LBNL workbook to this memo's numbers. Survival estimators are implemented from first principles rather than imported, so each step is inspectable. Full results, method notes and charts are in `output/interconnection_queue_analysis.xlsx`.
