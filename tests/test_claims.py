"""
Verification layer: every number claimed on a CV or in a memo is asserted here.

The point is falsifiability. Each test below corresponds to a specific published
claim, reads the actual generated output, and fails if the number moves. If these
pass on a clean clone, the claims are true of the code as shipped.

Run with pytest:      python -m pytest tests/ -v
Or standalone:        python tests/test_claims.py

Claim -> test mapping is documented in VERIFY.md.
"""
import hashlib
import json
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
P1 = ROOT / "project-1-megapack-cost" / "output"
P2 = ROOT / "project-2-queue-survival" / "output"
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"


def near(actual, expected, tol, label=""):
    """Assert actual is within +/- tol of expected, with a readable failure."""
    assert abs(actual - expected) <= tol, (
        "{}: expected {} +/- {}, got {}".format(label or "value", expected, tol, actual))


# ===========================================================================
# DATA INTEGRITY - are we analysing the file we think we are?
# ===========================================================================
EXPECTED_HASHES = {
    "LBNL_Ix_Queue_Data_File_thru2025.xlsx":
        "794582d3281c6a305e9615fcfec3fae9dc85be2165216d33760b677e976a08b6",
    "megapack_pricing_grid_2026-09-19.json":
        "bd7f59c354a1c08d01fb3329ae6d806ea1f1bddfb3b9c3d3ca0daa8cd9364bac",
}


def test_raw_data_unmodified():
    """Source files match the SHA-256 recorded at capture time."""
    for name, expected in EXPECTED_HASHES.items():
        path = RAW / name
        assert path.exists(), "missing raw input: {}".format(name)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, (
            "{} has changed since capture.\n  expected {}\n  got      {}\n"
            "If you re-downloaded from source, the upstream file was revised - "
            "results may legitimately differ.".format(name, expected, actual))


# ===========================================================================
# PROJECT 1 - Megapack price decomposition
# ===========================================================================
def test_p1_energy_rate():
    """CLAIM: energy capacity prices at $218.18/kWh on small orders."""
    d = pd.read_csv(P1 / "price_decomposition.csv").iloc[0]
    near(d["energy_usd_per_kwh"], 218.18, 0.05, "energy rate")


def test_p1_power_rate():
    """CLAIM: power conversion prices at $84.38/kW on small orders."""
    d = pd.read_csv(P1 / "price_decomposition.csv").iloc[0]
    near(d["power_usd_per_kw"], 84.38, 0.05, "power rate")


def test_p1_fixed_charge():
    """CLAIM: a $24,373 fixed order charge, identical across configurations."""
    d = pd.read_csv(P1 / "price_decomposition.csv").iloc[0]
    near(d["fixed_usd"], 24373, 5, "fixed charge")


def test_p1_fit_quality():
    """CLAIM: R-squared 1.000000, worst residual under 0.001%, overdetermined."""
    d = pd.read_csv(P1 / "price_decomposition.csv")
    for _, row in d.iterrows():
        assert row["r2"] > 0.9999999, "R2 {} below claim".format(row["r2"])
        assert row["worst_resid_pct"] < 0.001, (
            "worst residual {}% exceeds 0.001%".format(row["worst_resid_pct"]))
        assert row["n_obs"] > 3, "fit must be overdetermined, got n={}".format(row["n_obs"])


def test_p1_total_observations():
    """CLAIM: fitted across 18 observations against 3 unknowns."""
    d = pd.read_csv(P1 / "price_decomposition.csv")
    assert int(d["n_obs"].sum()) == 18, "expected 18 fitted points, got {}".format(
        int(d["n_obs"].sum()))


def test_p1_energy_share():
    """CLAIM: 91% of a 4-hour Megapack's price is energy capacity."""
    d = pd.read_csv(P1 / "price_decomposition.csv").iloc[0]
    e = d["energy_usd_per_kwh"] * 3.92 * 1000
    p = d["power_usd_per_kw"] * 0.98 * 1000
    near(e / (e + p) * 100, 91.2, 0.3, "energy share")


def test_p1_landed_costs():
    """CLAIM: imported cells land at $80/kWh, domestic at $42/kWh - 47% cheaper."""
    b = pd.read_csv(P1 / "base_case.csv")
    row = b[b["line"] == "LANDED COST"].iloc[0]
    near(row["import_usd_per_kwh"], 80.04, 0.05, "import landed")
    near(row["localise_usd_per_kwh"], 42.41, 0.05, "domestic landed")
    saving = (1 - row["localise_usd_per_kwh"] / row["import_usd_per_kwh"]) * 100
    near(saving, 47.0, 1.0, "saving %")


def test_p1_breakeven_uplift():
    """CLAIM: a US plant could cost 1.93x Chinese cost and still win."""
    b = pd.read_csv(P1 / "breakeven_uplift.csv")
    row = b[b["tariff_pct"] == 28.4].iloc[0]
    near(row["breakeven_us_uplift_multiple"], 1.93, 0.02, "breakeven uplift")


def test_p1_feoc_dominates_tariff():
    """CLAIM: FEOC exposure is 3.6x the tariff burden."""
    f = pd.read_csv(P1 / "feoc_value_at_risk.csv").iloc[0]
    near(f["itc_at_risk_usd_per_kwh"], 61.24, 0.1, "ITC at risk")
    near(f["tariff_burden_usd_per_kwh"], 17.04, 0.05, "tariff burden")
    near(f["ratio"], 3.59, 0.05, "FEOC/tariff ratio")


def test_p1_monte_carlo_robustness():
    """CLAIM: domestic cheaper in 100% of 20,000 draws, p5 advantage > $22/kWh."""
    m = pd.read_csv(P1 / "monte_carlo_summary.csv").iloc[0]
    assert m["n_sim"] == 20000, "expected 20,000 draws"
    near(m["prob_localise_cheaper_pct"], 100.0, 0.5, "P(domestic cheaper)")
    assert m["p5"] > 22.0, "p5 advantage {} below claim".format(m["p5"])


def test_p1_45x_phase_down_flips_2033():
    """CLAIM: the cost case turns negative in 2033 when 45X expires."""
    p = pd.read_csv(P1 / "phase_down_sensitivity.csv")
    pre = p[p["production_year"] <= 2032]
    post = p[p["production_year"] == 2033].iloc[0]
    assert (pre["localise_advantage_usd_per_kwh"] > 0).all(), "should be positive pre-2033"
    assert post["localise_advantage_usd_per_kwh"] < 0, "should be negative in 2033"


def test_p1_freight_gradient():
    """CLAIM: state pricing correlates 0.971 with distance from Lathrop."""
    g = pd.read_csv(P1 / "state_premium.csv")
    corr = g["premium_pct"].corr(g["km_from_lathrop"])
    near(corr, 0.971, 0.01, "freight correlation")


def test_p1_no_expediting_premium():
    """CLAIM: all four 2027 delivery quarters price identically."""
    raw = json.loads((RAW / "megapack_pricing_grid_2026-09-19.json").read_text())
    prices = set(raw["by_delivery_quarter"]["prices"].values())
    assert len(prices) == 1, "expected one price across quarters, got {}".format(prices)


# --- Idiot index -----------------------------------------------------------
def test_p1_lithium_stoichiometry_crosscheck():
    """The assumed cathode mass must independently reproduce the published
    0.47 kg lithium carbonate per kWh. This validates the mass budget rather
    than restating it - the two figures come from different places."""
    b = pd.read_csv(P1 / "raw_material_basket.csv").set_index("material")
    lce = b.loc["Lithium carbonate", "kg_per_kwh"]
    near(lce, 0.47, 0.015, "implied lithium carbonate per kWh")


def test_p1_raw_material_floor():
    """CLAIM: raw materials in an LFP cell are worth about $30/kWh."""
    idx = pd.read_csv(P1 / "idiot_index.csv")
    near(idx.iloc[0]["usd_per_kwh"], 30.19, 0.5, "raw material floor")


def test_p1_copper_exceeds_lithium():
    """CLAIM: copper is a larger raw input than lithium, and together they are
    62% of the basket."""
    b = pd.read_csv(P1 / "raw_material_basket.csv").set_index("material")
    cu = b.loc["Copper", "usd_per_kwh"]
    li = b.loc["Lithium carbonate", "usd_per_kwh"]
    assert cu > li, "copper ({}) should exceed lithium ({})".format(cu, li)
    near(b.loc["Copper", "share_pct"] + b.loc["Lithium carbonate", "share_pct"],
         62.0, 1.5, "combined copper+lithium share")


def test_p1_idiot_indices():
    """CLAIM: cell index 1.99x, system index 7.23x - the markup is downstream
    of the cell, not inside it."""
    idx = pd.read_csv(P1 / "idiot_index.csv")
    near(idx.iloc[1]["idiot_index"], 1.99, 0.05, "cell idiot index")
    near(idx.iloc[2]["idiot_index"], 7.23, 0.10, "system idiot index")
    assert idx.iloc[2]["idiot_index"] > 3 * idx.iloc[1]["idiot_index"], (
        "system index should be several times the cell index")


def test_p1_cell_stays_near_material_floor():
    """CLAIM: even at $80/kg lithium the cell index only falls to ~1.0x, so a
    lithium spike compresses margin rather than revealing manufacturing slack."""
    s = pd.read_csv(P1 / "idiot_index_lithium_sensitivity.csv")
    worst = s[s["lithium_carbonate_usd_per_kg"] == 80.0].iloc[0]
    assert worst["cell_idiot_index"] < 1.1, (
        "cell index at $80/kg lithium is {}, expected near 1.0".format(
            worst["cell_idiot_index"]))
    assert s["cell_idiot_index"].is_monotonic_decreasing, (
        "index must fall as lithium price rises")


# ===========================================================================
# PROJECT 2 - Interconnection queue survival
# ===========================================================================
def test_p2_sample_size():
    """CLAIM: 20,087 requests analysed in reliably-reporting regions."""
    df = pd.read_parquet(PROC / "survival_dataset.parquet")
    assert int(df["region_reliable"].sum()) == 20087, (
        "expected 20,087 reliable-region rows, got {}".format(int(df["region_reliable"].sum())))


def test_p2_completion_rates():
    """CLAIM: 11.2% built within 5 years, 20.0% within 10, 72% withdrawn."""
    s = pd.read_csv(P2 / "cif_summary.csv").set_index("horizon_years")
    near(s.loc[5, "pct_built"], 11.25, 0.15, "5-year completion")
    near(s.loc[10, "pct_built"], 20.03, 0.15, "10-year completion")
    near(s.loc[10, "pct_withdrawn"], 72.29, 0.20, "10-year withdrawal")


def test_p2_confidence_intervals_bracket_estimates():
    """Bootstrap CIs must actually contain their point estimates."""
    s = pd.read_csv(P2 / "cif_summary.csv")
    for _, r in s.iterrows():
        assert r["pct_built_ci_lo"] <= r["pct_built"] <= r["pct_built_ci_hi"], (
            "CI does not bracket estimate at {} years".format(r["horizon_years"]))


def test_p2_naive_overstatement():
    """CLAIM: treating withdrawal as censoring overstates completion 2.9x at 10 years."""
    s = pd.read_csv(P2 / "cif_summary.csv").set_index("horizon_years")
    near(s.loc[10, "naive_overstatement_x"], 2.90, 0.05, "naive overstatement")
    near(s.loc[10, "pct_built_naive_km"], 58.04, 0.5, "naive 10-year estimate")


def test_p2_outcomes_sum_to_one():
    """Competing-risks sanity: built + withdrawn + waiting must equal 100%."""
    s = pd.read_csv(P2 / "cif_summary.csv")
    total = s["pct_built"] + s["pct_withdrawn"] + s["pct_still_waiting"]
    assert (abs(total - 100.0) < 0.01).all(), "CIFs do not sum to 100%: {}".format(total.tolist())


def test_p2_regional_gap():
    """CLAIM: ERCOT builds 20.7% within 5 years against CAISO's 3.7%."""
    r = pd.read_csv(P2 / "cif_by_region.csv").set_index("region")
    near(r.loc["ERCOT", "built_5yr_pct"], 20.73, 0.2, "ERCOT completion")
    near(r.loc["CAISO", "built_5yr_pct"], 3.66, 0.2, "CAISO completion")
    ratio = r.loc["ERCOT", "built_5yr_pct"] / r.loc["CAISO", "built_5yr_pct"]
    near(ratio, 5.6, 0.3, "ERCOT/CAISO ratio")


def test_p2_declining_completion():
    """CLAIM: completion fell from 24.6% to 6.8% across request eras."""
    e = pd.read_csv(P2 / "cif_by_era.csv")
    near(e.iloc[0]["built_5yr_pct"], 24.61, 0.2, "earliest era")
    near(e.iloc[-1]["built_5yr_pct"], 6.84, 0.2, "latest era")
    assert e["built_5yr_pct"].is_monotonic_decreasing, "era trend should decline monotonically"


def test_p2_scenario_spread():
    """CLAIM: identical battery project - 22.6% in ERCOT vs 2.7% in CAISO."""
    s = pd.read_csv(P2 / "scenario_battery_by_region.csv").set_index("region")
    near(s.loc["ERCOT", "predicted_built_7yr_pct"], 22.6, 0.5, "ERCOT scenario")
    near(s.loc["CAISO", "predicted_built_7yr_pct"], 2.7, 0.5, "CAISO scenario")


def test_p2_iso_ne_reporting_gap():
    """CLAIM: ISO-NE reports zero COD dates, so its 0% completion is an artifact."""
    q = pd.read_csv(PROC / "region_reporting_quality.csv").set_index("region")
    assert q.loc["ISO-NE", "cod_reporting_pct"] == 0.0, "ISO-NE should report no COD dates"
    assert q.loc["ISO-NE", "operational_projects"] > 200, "and still have many operational projects"
    assert not bool(q.loc["ISO-NE", "reliable"]), "ISO-NE must be excluded as unreliable"


def test_p2_excluded_regions():
    """CLAIM: four regions excluded for under-reporting; five retained."""
    q = pd.read_csv(PROC / "region_reporting_quality.csv")
    assert int((~q["reliable"]).sum()) == 4, "expected 4 excluded regions"
    assert int(q["reliable"].sum()) == 5, "expected 5 retained regions"


# ===========================================================================
# Standalone runner - works without pytest installed
# ===========================================================================
def _main():
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    passed, failed = [], []
    for name, fn in tests:
        try:
            fn()
            passed.append(name)
            print("  PASS  {:<42} {}".format(name, (fn.__doc__ or "").strip().split("\n")[0]))
        except AssertionError as e:
            failed.append((name, str(e)))
            print("  FAIL  {:<42} {}".format(name, e))
    print()
    print("{} passed, {} failed, {} total".format(len(passed), len(failed), len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    print("=" * 100)
    print("CLAIM VERIFICATION")
    print("=" * 100)
    sys.exit(_main())
