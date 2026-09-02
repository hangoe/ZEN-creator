"""Unit tests for HeatTechParametrizationDataset (heat_tech_parametrization.py).

Covers the hand-computed Carnot-COP constants (HP_COP_WASTE_HEAT/HP_COP_WATER)
and the heat-pump conversion_factor override, plus the simple attribute getters
-- none of which had direct test coverage (see cleanup plan, Phase 2 item 4).
"""

from __future__ import annotations

import pytest

from zen_creator.datasets.datasets.heat_tech_parametrization import (
    HP_COP_WASTE_HEAT,
    HP_COP_WATER,
    HeatTechParametrizationDataset,
)


def _carnot_cop(t_hot_k: float, t_cold_k: float, carnot_efficiency: float = 0.5) -> float:
    """COP = carnot_efficiency x COP_Carnot = carnot_efficiency x T_hot / (T_hot - T_cold)."""
    return round(carnot_efficiency * t_hot_k / (t_hot_k - t_cold_k), 4)


@pytest.mark.parametrize("level,t_hot_c", [("0_100", 75), ("100_150", 125), ("150_200", 175)])
def test_hp_cop_waste_heat_matches_carnot_formula(level, t_hot_c):
    """Waste-heat source is 50 degC (323.15 K) -- see module docstring."""
    t_hot_k = t_hot_c + 273.15
    assert HP_COP_WASTE_HEAT[level] == pytest.approx(_carnot_cop(t_hot_k, 323.15))


@pytest.mark.parametrize("level,t_hot_c", [("0_100", 75), ("100_150", 125), ("150_200", 175)])
def test_hp_cop_water_matches_carnot_formula(level, t_hot_c):
    """Water source is 15 degC (288.15 K) -- see module docstring."""
    t_hot_k = t_hot_c + 273.15
    assert HP_COP_WATER[level] == pytest.approx(_carnot_cop(t_hot_k, 288.15))


def test_waste_heat_cop_exceeds_water_cop_at_every_level():
    """Waste heat (50 degC) is a warmer source than water (15 degC), so it must
    always yield a higher COP for the same target temperature."""
    for level in HP_COP_WASTE_HEAT:
        assert HP_COP_WASTE_HEAT[level] > HP_COP_WATER[level]


def test_cop_decreases_as_target_temperature_increases():
    """A larger temperature lift (T_hot - T_cold) must give a lower COP."""
    levels_in_order = ["0_100", "100_150", "150_200"]
    waste_cops = [HP_COP_WASTE_HEAT[level] for level in levels_in_order]
    water_cops = [HP_COP_WATER[level] for level in levels_in_order]
    assert waste_cops == sorted(waste_cops, reverse=True)
    assert water_cops == sorted(water_cops, reverse=True)


@pytest.fixture(scope="module")
def dataset() -> HeatTechParametrizationDataset:
    return HeatTechParametrizationDataset()


def test_get_conversion_factor_uses_cop_override(dataset, model):
    """cop_override must set conversion_factor's electricity entry to 1/COP."""
    from zen_creator.elements.conversion_technologies.industry_heat_supply import (
        HeatPumpIndustry0100WasteHeat,
    )

    element = HeatPumpIndustry0100WasteHeat(model=model)
    cop = HP_COP_WASTE_HEAT["0_100"]
    attr = dataset.get_conversion_factor(element, "heat_pump_industry", "0_100", cop_override=cop)
    entry = next(iter(attr.default_value[0].values()))
    assert entry["default_value"] == pytest.approx(1.0 / cop, rel=1e-9)


def test_simple_getters_return_positive_values_with_units(dataset, model):
    from zen_creator.elements.conversion_technologies.industry_heat_supply import (
        BiomassBoilerIndustry,
    )

    element = BiomassBoilerIndustry(model=model)
    lifetime = dataset.get_lifetime(element, "biomass_boiler_industry")
    max_load = dataset.get_max_load(element, "biomass_boiler_industry")
    min_load = dataset.get_min_load(element, "biomass_boiler_industry")

    assert lifetime.default_value > 0
    assert 0 <= min_load.default_value <= max_load.default_value


if __name__ == "__main__":
    pytest.main([__file__])
