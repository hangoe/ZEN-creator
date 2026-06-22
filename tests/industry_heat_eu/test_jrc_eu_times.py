import pytest

from zen_creator.industry_heat_eu.data.jrc_eu_times import (
    GLASS_AIDRES_TO_JRC,
    HOURS_PER_YEAR,
    PAPER_REHFELDT_TO_JRC,
    PARAM_BASE_YEAR,
    gdp_deflator_ratio,
    read_ind_process_params,
    sector_weighted_params,
)


# ── read_ind_process_params ───────────────────────────────────────────────────

def test_read_ind_process_params_flat_glass_invcost_and_fixom():
    p = read_ind_process_params("IGFFLATGL01")
    assert p["INVCOST"] == pytest.approx(150.0)
    assert p["FIXOM"]   == pytest.approx(10.0)
    assert p["VAROM"]   == pytest.approx(50.0)
    assert p["LIFE"]    == pytest.approx(25.0)


def test_read_ind_process_params_hollow_glass_has_higher_capex_than_flat():
    flat    = read_ind_process_params("IGFFLATGL01")
    hollow  = read_ind_process_params("IGHHOLLOW01")
    assert hollow["INVCOST"] > flat["INVCOST"]
    assert hollow["FIXOM"]   > flat["FIXOM"]
    assert hollow["LIFE"]    == pytest.approx(30.0)


def test_read_ind_process_params_paper_high_quality_has_highest_capex():
    high  = read_ind_process_params("IPPHIGQUA01")
    low   = read_ind_process_params("IPPLOWQUA01")
    chem  = read_ind_process_params("IPPPUPCHE01")
    assert high["INVCOST"] > chem["INVCOST"] > low["INVCOST"]


def test_read_ind_process_params_chemical_pulp_has_nonzero_varom():
    p = read_ind_process_params("IPPPUPCHE01")
    assert p["VAROM"] > 0


def test_read_ind_process_params_paper_high_quality_zero_varom():
    # JRC-EU-TIMES has no VAROM for paper/recycled machines.
    p = read_ind_process_params("IPPHIGQUA01")
    assert p["VAROM"] == pytest.approx(0.0)


def test_read_ind_process_params_unknown_tech_returns_all_zeros():
    p = read_ind_process_params("NONEXISTENT_TECH_XYZ")
    assert all(v == 0.0 for v in p.values())


def test_read_ind_process_params_returns_required_keys():
    p = read_ind_process_params("IGFFLATGL01")
    assert set(p) == {"INVCOST", "FIXOM", "VAROM", "LIFE", "EMISSIONS_INDCO2P"}


# ── gdp_deflator_ratio ────────────────────────────────────────────────────────

def test_gdp_deflator_ratio_same_year_is_one():
    assert gdp_deflator_ratio(2008, 2008) == pytest.approx(1.0)


def test_gdp_deflator_ratio_increases_over_time():
    # EU prices rose from 2006 to 2019.
    assert gdp_deflator_ratio(2006, 2019) > 1.0


def test_gdp_deflator_ratio_is_inverse_of_reverse():
    r = gdp_deflator_ratio(2006, 2019)
    assert gdp_deflator_ratio(2019, 2006) == pytest.approx(1.0 / r, rel=1e-6)


def test_gdp_deflator_ratio_2006_to_2019_approximately_correct():
    # From the GDPdeflator sheet and CAGR extrapolation beyond 2012.
    r = gdp_deflator_ratio(2006, 2019)
    assert 1.15 < r < 1.25


def test_gdp_deflator_ratio_extrapolates_beyond_2012():
    # 2019 is beyond the last observed year (2012); must not raise.
    r = gdp_deflator_ratio(PARAM_BASE_YEAR, 2019)
    assert r > 0


# ── sector_weighted_params ────────────────────────────────────────────────────

def test_sector_weighted_params_returns_required_keys():
    result = sector_weighted_params(
        {"flat": "IGFFLATGL01"}, {"flat": 1.0}, target_year=2019
    )
    assert set(result) == {
        "capex_specific_conversion",
        "opex_specific_fixed",
        "opex_specific_variable",
        "carbon_intensity_technology",
        "lifetime",
    }


def test_sector_weighted_params_unit_conversion_capex():
    # capex [EUR/(t/h)] = INVCOST [EUR/(t/yr)] × deflator × 8760
    deflator = gdp_deflator_ratio(PARAM_BASE_YEAR, 2019)
    flat_invcost = read_ind_process_params("IGFFLATGL01")["INVCOST"]
    result = sector_weighted_params({"flat": "IGFFLATGL01"}, {"flat": 1.0}, target_year=2019)
    assert result["capex_specific_conversion"] == pytest.approx(
        flat_invcost * deflator * HOURS_PER_YEAR, rel=1e-6
    )


def test_sector_weighted_params_unit_conversion_opex_variable():
    # opex_variable [EUR/t] = VAROM [EUR/t] × deflator (no ×8760)
    deflator = gdp_deflator_ratio(PARAM_BASE_YEAR, 2019)
    chem_varom = read_ind_process_params("IPPPUPCHE01")["VAROM"]
    result = sector_weighted_params({"chem": "IPPPUPCHE01"}, {"chem": 1.0}, target_year=2019)
    assert result["opex_specific_variable"] == pytest.approx(chem_varom * deflator, rel=1e-6)


def test_sector_weighted_params_weights_are_applied():
    # Weighted result should lie between the two individual results.
    r_flat   = sector_weighted_params({"x": "IGFFLATGL01"}, {"x": 1.0}, 2019)
    r_hollow = sector_weighted_params({"x": "IGHHOLLOW01"}, {"x": 1.0}, 2019)
    r_mixed  = sector_weighted_params(
        {"flat": "IGFFLATGL01", "hollow": "IGHHOLLOW01"},
        {"flat": 0.5, "hollow": 0.5},
        target_year=2019,
    )
    # Weighted average must fall strictly between the two endpoints.
    assert r_flat["capex_specific_conversion"] < r_mixed["capex_specific_conversion"] < r_hollow["capex_specific_conversion"]


def test_sector_weighted_params_lifetime_is_rounded_integer():
    result = sector_weighted_params(GLASS_AIDRES_TO_JRC, {"container": 0.6, "flat": 0.3, "fibre": 0.1}, 2019)
    assert result["lifetime"] == round(result["lifetime"])


def test_sector_weighted_params_glass_regression():
    # Regression against values written to process_parametrization.xlsx.
    # lifetime: 0.6×30 + 0.3×25 + 0.1×25 = 28 yr
    weights = {"container": 0.6, "flat": 0.3, "fibre": 0.1}
    result = sector_weighted_params(GLASS_AIDRES_TO_JRC, weights, target_year=2019)
    assert result["capex_specific_conversion"] == pytest.approx(2_183_366, rel=1e-3)
    assert result["opex_specific_fixed"]       == pytest.approx(166_352,   rel=1e-3)
    assert result["opex_specific_variable"]    == pytest.approx(59.34,     rel=1e-3)
    assert result["lifetime"]                  == 28


def test_sector_weighted_params_paper_regression():
    # Regression against values previously written to process_parametrization.xlsx.
    # lifetime: all three IPP processes have LIFE=25 yr → 25 yr
    from zen_creator.industry_heat_eu.data.rehfeldt2017 import REHFELDT2017_PAPER
    from zen_creator.industry_heat_eu.process_params import activity_weights
    weights = activity_weights(REHFELDT2017_PAPER)
    result = sector_weighted_params(PAPER_REHFELDT_TO_JRC, weights, target_year=2019)
    assert result["capex_specific_conversion"] == pytest.approx(19_995_772, rel=1e-3)
    assert result["opex_specific_fixed"]       == pytest.approx(950_445,    rel=1e-3)
    assert result["opex_specific_variable"]    == pytest.approx(4.99,       rel=1e-3)
    assert result["lifetime"]                  == 25
