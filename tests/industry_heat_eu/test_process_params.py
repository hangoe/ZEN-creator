import pytest

from zen_creator.industry_heat_eu.process_params import (
    GJ_per_t_to_conversion_factor,
    activity_weights,
    compute_sector_params,
    low_temp_fraction,
    weighted_average,
    weighted_avg_temp_dist,
)

DATA = {
    "a": {
        "fuels_GJ_t": 10.0,
        "elec_GJ_t": 2.0,
        "activity_Mt": 3.0,
        "temp_dist": {"<100": 0.5, "100-200": 0.5, "200-500": 0.0, "500-1000": 0.0, ">1000": 0.0},
    },
    "b": {
        "fuels_GJ_t": 2.0,
        "elec_GJ_t": 1.0,
        "activity_Mt": 1.0,
        "temp_dist": {"<100": 0.0, "100-200": 0.0, "200-500": 0.0, "500-1000": 0.0, ">1000": 1.0},
    },
}


def test_activity_weights_normalises_to_one():
    weights = activity_weights(DATA)
    assert weights == {"a": 0.75, "b": 0.25}
    assert sum(weights.values()) == pytest.approx(1.0)


def test_weighted_average():
    weights = {"a": 0.75, "b": 0.25}
    assert weighted_average(DATA, weights, "fuels_GJ_t") == pytest.approx(0.75 * 10.0 + 0.25 * 2.0)


def test_weighted_avg_temp_dist_sums_to_one():
    weights = {"a": 0.75, "b": 0.25}
    temp_dist = weighted_avg_temp_dist(DATA, weights)
    assert temp_dist["<100"] == pytest.approx(0.75 * 0.5)
    assert temp_dist[">1000"] == pytest.approx(0.25 * 1.0)
    assert sum(temp_dist.values()) == pytest.approx(1.0)


def test_low_temp_fraction():
    assert low_temp_fraction({"<100": 0.2, "100-200": 0.3, "200-500": 0.5, "500-1000": 0.0, ">1000": 0.0}) == pytest.approx(0.5)


def test_GJ_per_t_to_conversion_factor():
    assert GJ_per_t_to_conversion_factor(3600.0) == pytest.approx(1.0)


def test_compute_sector_params_splits_fuel_by_temperature():
    # DATA: "a" has <100=0.5, 100-200=0.5; "b" has >1000=1.0; weights 0.75/0.25
    # weighted temp_dist: <100=0.375, 100-200=0.375, >1000=0.25
    weights = {"a": 0.75, "b": 0.25}
    params = compute_sector_params(DATA, DATA, weights)

    fuel_total = weighted_average(DATA, weights, "fuels_GJ_t")
    assert params.lt_GJ_t_0_100   == pytest.approx(fuel_total * 0.375)
    assert params.lt_GJ_t_100_200 == pytest.approx(fuel_total * 0.375)
    assert params.fuel_GJ_t + params.lt_GJ_t == pytest.approx(fuel_total)
    assert params.lt_frac == pytest.approx(0.75)
    assert params.elec_GJ_t == pytest.approx(weighted_average(DATA, weights, "elec_GJ_t"))


def test_compute_sector_params_supports_separate_energy_and_temp_data():
    energy_data = {"a": {"fuels_GJ_t": 5.0, "elec_GJ_t": 1.0}}
    temp_data = {"a": {"temp_dist": {"<100": 1.0, "100-200": 0.0, "200-500": 0.0, "500-1000": 0.0, ">1000": 0.0}}}
    weights = {"a": 1.0}

    params = compute_sector_params(energy_data, temp_data, weights, fuel_key="fuels_GJ_t")
    assert params.lt_GJ_t_0_100   == pytest.approx(5.0)
    assert params.lt_GJ_t_100_200 == pytest.approx(0.0)
    assert params.fuel_GJ_t == pytest.approx(0.0)


def test_compute_sector_params_conversion_factors():
    weights = {"a": 1.0, "b": 0.0}
    data = {
        "a": {
            "fuels_GJ_t": 3600.0,
            "elec_GJ_t": 3600.0,
            "temp_dist": {"<100": 0.0, "100-200": 0.0, "200-500": 1.0, "500-1000": 0.0, ">1000": 0.0},
        },
        "b": DATA["b"],
    }
    params = compute_sector_params(data, data, weights)
    assert params.cf_fuel        == pytest.approx(1.0)
    assert params.cf_elec        == pytest.approx(1.0)
    assert params.cf_lt_0_100    == pytest.approx(0.0)
    assert params.cf_lt_100_200  == pytest.approx(0.0)
