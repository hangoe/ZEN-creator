"""Unit tests for DeaIndustrialHeatDataset (dea_industrial_heat.py).

Covers the interpolation/constant-detection helpers shared with post_comb_cc.py,
and the boiler efficiency -> conversion_factor inversion -- none of which had
direct test coverage (see cleanup plan, Phase 2 item 3).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from zen_creator.datasets.datasets.dea_industrial_heat import (
    BOILER_TECHS,
    MODEL_FIRST_YEAR,
    MODEL_LAST_YEAR,
    DeaIndustrialHeatDataset,
    _interpolate_to_model_years,
    _is_constant,
)


def test_interpolate_to_model_years_holds_flat_before_first_known_year():
    series = _interpolate_to_model_years({2030: 10.0, 2040: 20.0})
    assert series.loc[MODEL_FIRST_YEAR] == pytest.approx(10.0)
    assert series.loc[2025] == pytest.approx(10.0)


def test_interpolate_to_model_years_holds_flat_after_last_known_year():
    series = _interpolate_to_model_years({2030: 10.0, 2040: 20.0})
    assert series.loc[MODEL_LAST_YEAR] == pytest.approx(20.0)
    assert series.loc[2045] == pytest.approx(20.0)


def test_interpolate_to_model_years_interpolates_linearly_between_known_years():
    series = _interpolate_to_model_years({2030: 10.0, 2040: 20.0})
    assert series.loc[2035] == pytest.approx(15.0)
    assert series.index.min() == MODEL_FIRST_YEAR
    assert series.index.max() == MODEL_LAST_YEAR


def test_is_constant_true_for_flat_series():
    series = pd.Series([5.0] * 10)
    assert _is_constant(series) is True


def test_is_constant_false_for_varying_series():
    series = pd.Series(np.linspace(1.0, 2.0, 10))
    assert _is_constant(series) is False


@pytest.fixture(scope="module")
def dataset() -> DeaIndustrialHeatDataset:
    return DeaIndustrialHeatDataset()


@pytest.mark.parametrize("tech,carrier", [
    ("natural_gas_boiler_industry", "natural_gas"),
    ("biomass_boiler_industry", "biomass"),
    ("coal_boiler_industry", "hard_coal"),
])
def test_boiler_conversion_factor_is_inverse_efficiency(dataset, model, tech, carrier):
    """conversion_factor (GW input per GW output) must be >= 1 (efficiency <= 100%),
    and its reciprocal must be a plausible net efficiency (0, 1]."""
    from zen_creator.elements.conversion_technologies.industry_heat_supply import (
        NaturalGasBoilerIndustry,
    )

    element = NaturalGasBoilerIndustry(model=model)
    attr = dataset.get_conversion_factor(element, tech, carrier)
    cf = attr.default_value[0][carrier]["default_value"]
    assert cf >= 1.0
    efficiency = 1.0 / cf
    assert 0.0 < efficiency <= 1.0


def test_conversion_factor_raises_for_non_boiler_tech(dataset, model):
    from zen_creator.elements.conversion_technologies.industry_heat_supply import (
        HeatPumpIndustry150200Water,
    )

    element = HeatPumpIndustry150200Water(model=model)
    with pytest.raises(ValueError):
        dataset.get_conversion_factor(element, "heat_pump_industry_100_200", "electricity")


def test_capex_and_opex_fixed_are_positive_with_expected_units(dataset, model):
    from zen_creator.elements.conversion_technologies.industry_heat_supply import (
        NaturalGasBoilerIndustry,
    )

    element = NaturalGasBoilerIndustry(model=model)
    capex = dataset.get_capex_specific_conversion(element, "natural_gas_boiler_industry")
    opex_fixed = dataset.get_opex_specific_fixed(element, "natural_gas_boiler_industry")

    assert capex.unit == "Euro/kW"
    assert capex.default_value > 0
    assert opex_fixed.unit == "Euro/kW"
    assert opex_fixed.default_value > 0


def test_lifetime_matches_2025_dea_value(dataset, model):
    from zen_creator.elements.conversion_technologies.industry_heat_supply import (
        NaturalGasBoilerIndustry,
    )

    element = NaturalGasBoilerIndustry(model=model)
    attr = dataset.get_lifetime(element, "natural_gas_boiler_industry")
    assert attr.default_value > 0
    assert attr.unit == "1"


def test_all_boiler_techs_are_covered_by_dea_sheet_map(dataset):
    """DEA_SHEET_FOR_TECH must define a sheet for every tech in BOILER_TECHS,
    since get_conversion_factor requires it."""
    from zen_creator.datasets.datasets.dea_industrial_heat import DEA_SHEET_FOR_TECH

    for tech in BOILER_TECHS:
        assert tech in DEA_SHEET_FOR_TECH


if __name__ == "__main__":
    pytest.main([__file__])
