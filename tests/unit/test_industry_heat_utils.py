"""Unit tests for the pure/data-processing functions in _industry_heat_utils.py.

These functions back the unit conversions, weighted averages, temperature-band
allocation, and GDP-deflator extrapolation used throughout
process_parametrization.py and the DEA/JRC-derived datasets, but had no direct
test coverage (see cleanup plan, Phase 2 item 1).
"""

from __future__ import annotations

import pytest

from zen_creator.datasets.datasets._industry_heat_utils import (
    MODEL_NODES,
    REHFELDT2017_CERAMIC,
    REHFELDT2017_GLASS,
    GJ_per_t_to_conversion_factor,
    SectorParams,
    activity_weights,
    boiler_capacity_existing_df_for_fuel,
    compute_sector_params,
    gdp_deflator_ratio,
    total_industry_heat_demand_gw,
    weighted_average,
    weighted_avg_temp_dist,
)


def test_GJ_per_t_to_conversion_factor():
    """1 GJ/t == 1/3600 GW per tonproduct/hour (GJ/h -> GW)."""
    assert GJ_per_t_to_conversion_factor(3600.0) == pytest.approx(1.0)
    assert GJ_per_t_to_conversion_factor(0.0) == pytest.approx(0.0)


def test_activity_weights_sum_to_one():
    """activity_weights() must return normalized shares regardless of input scale."""
    data = {"a": {"activity_Mt": 3.0}, "b": {"activity_Mt": 1.0}}
    weights = activity_weights(data)
    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights["a"] == pytest.approx(0.75)
    assert weights["b"] == pytest.approx(0.25)


def test_activity_weights_on_real_rehfeldt_data():
    """Real REHFELDT2017_CERAMIC sub-process weights must still sum to 1."""
    weights = activity_weights(REHFELDT2017_CERAMIC)
    assert sum(weights.values()) == pytest.approx(1.0)
    assert all(w >= 0 for w in weights.values())


def test_weighted_average_is_linear_interpolation():
    data = {"a": {"x": 10.0}, "b": {"x": 20.0}}
    weights = {"a": 0.25, "b": 0.75}
    assert weighted_average(data, weights, "x") == pytest.approx(17.5)


def test_weighted_avg_temp_dist_sums_to_one_on_real_data():
    """weighted_avg_temp_dist asserts internally that shares sum to 1 -- confirm
    this holds for real Rehfeldt2017 glass data, not just a synthetic case."""
    weights = activity_weights(REHFELDT2017_GLASS)
    dist = weighted_avg_temp_dist(REHFELDT2017_GLASS, weights)
    assert sum(dist.values()) == pytest.approx(1.0, abs=1e-6)


def test_weighted_avg_temp_dist_rejects_shares_not_summing_to_one():
    temp_dist = {"<100": 0.5, "100-200": 0.3, "200-500": 0.1, "500-1000": 0.05, ">1000": 0.05}
    # deliberately mis-scaled so shares no longer sum to 1
    bad_data = {"a": {"temp_dist": {k: v * 2 for k, v in temp_dist.items()}}}
    with pytest.raises(AssertionError):
        weighted_avg_temp_dist(bad_data, {"a": 1.0})


class TestSectorParams:
    def test_derived_properties_are_internally_consistent(self):
        params = SectorParams(
            fuel_GJ_t=10.0, lt_GJ_t_0_100=2.0, lt_GJ_t_100_200=1.0, elec_GJ_t=0.5, temp_dist={}
        )
        assert params.lt_GJ_t == pytest.approx(3.0)
        assert params.cf_fuel == pytest.approx(10.0 / 3600.0)
        assert params.cf_lt == pytest.approx(3.0 / 3600.0)
        assert params.cf_lt_0_100 == pytest.approx(2.0 / 3600.0)
        assert params.cf_lt_100_200 == pytest.approx(1.0 / 3600.0)
        assert params.cf_elec == pytest.approx(0.5 / 3600.0)


def test_compute_sector_params_splits_energy_by_temperature_band():
    """compute_sector_params must split each sector's total fuel energy into
    fuel_GJ_t (>200C) and the two low-temp bands using weighted_avg_temp_dist's
    <100 / 100-200 shares, with the three summing back to the un-split total."""
    weights = activity_weights(REHFELDT2017_CERAMIC)
    params = compute_sector_params(REHFELDT2017_CERAMIC, REHFELDT2017_CERAMIC, weights)
    total_fuel = weighted_average(REHFELDT2017_CERAMIC, weights, "fuels_GJ_t")
    assert params.fuel_GJ_t + params.lt_GJ_t_0_100 + params.lt_GJ_t_100_200 == pytest.approx(total_fuel)
    assert params.elec_GJ_t == pytest.approx(weighted_average(REHFELDT2017_CERAMIC, weights, "elec_GJ_t"))


def test_gdp_deflator_ratio_identity():
    """Deflating a year to itself must be a no-op."""
    assert gdp_deflator_ratio(2019, 2019) == pytest.approx(1.0)


def test_gdp_deflator_ratio_is_positive_and_invertible():
    ratio = gdp_deflator_ratio(2014, 2019)
    inverse = gdp_deflator_ratio(2019, 2014)
    assert ratio > 0
    assert ratio * inverse == pytest.approx(1.0, rel=1e-9)


class TestBoilerCapacityExistingDf:
    """Characterization tests pinning current boiler-capacity output for DE/CH/FR,
    2022, via the collapsed boiler_capacity_existing_df_for_fuel() (formerly six
    near-identical per-fuel functions -- see cleanup plan, Phase 4 #2)."""

    YEAR = 2022
    EXPECTED = {
        "biomass": {"DE": 0.6765566226582983, "CH": 0.020361830780288498, "FR": 1.290812218046706},
        "natural_gas": {"DE": 3.430639602983748, "CH": 0.18313142998636875, "FR": 1.4065042444684315},
        "electrode": {"DE": 0.0, "CH": 0.0, "FR": 0.00029606507170217846},
        "oil": {"DE": 0.17836476763675735, "CH": 0.05899735790193387, "FR": 0.1922256910614203},
        "coal": {"DE": 1.68980548948439, "CH": 0.007847922901697635, "FR": 0.08359126140863248},
        "waste": {"DE": 1.3529042858190456, "CH": 0.019567244462516013, "FR": 0.8095823461274697},
    }
    FUEL_KEYS = sorted(EXPECTED)

    @pytest.mark.parametrize("fuel", FUEL_KEYS)
    def test_capacity_matches_pinned_values(self, fuel):
        df = boiler_capacity_existing_df_for_fuel(fuel, self.YEAR)
        for node, expected in self.EXPECTED[fuel].items():
            actual = df.loc[df["node"] == node, "capacity_existing"].values[0]
            assert actual == pytest.approx(expected, rel=1e-9)

    def test_all_nodes_present_and_non_negative(self):
        for fuel in self.FUEL_KEYS:
            df = boiler_capacity_existing_df_for_fuel(fuel, self.YEAR)
            assert set(df["node"]) == set(MODEL_NODES)
            assert (df["capacity_existing"] >= 0).all()

    def test_fuel_capacities_sum_to_total_industry_heat_demand(self):
        """Per node, the six fuel-specific capacities must sum back to
        total_industry_heat_demand_gw() -- the fuel shares partition the total."""
        total = total_industry_heat_demand_gw(self.YEAR)
        dfs = {
            fuel: boiler_capacity_existing_df_for_fuel(fuel, self.YEAR).set_index("node")["capacity_existing"]
            for fuel in self.FUEL_KEYS
        }
        for node in MODEL_NODES:
            summed = sum(dfs[fuel][node] for fuel in self.FUEL_KEYS)
            assert summed == pytest.approx(total[node], rel=1e-9)


if __name__ == "__main__":
    pytest.main([__file__])
