"""Unit tests for industry thermal energy storage (TES) technologies.

industry_TES.py had zero test coverage before this (see cleanup plan, Phase 2
item 6) -- unlike its sibling industry_DSM.py, which is exercised (partially)
by test_industry_dsm.py.
"""

from __future__ import annotations

import pytest

from zen_creator.elements.storage_technologies.industry_TES import (
    IndustryTESSteam150200,
    IndustryTESWater0100,
    IndustryTESWater100150,
)
from zen_creator.model import Model

TES_CLASSES = [IndustryTESWater0100, IndustryTESWater100150, IndustryTESSteam150200]


@pytest.mark.parametrize("technology_cls", TES_CLASSES)
def test_build_succeeds_and_sets_core_attributes(technology_cls, model: Model):
    technology = technology_cls(model=model)
    technology.build()

    assert technology.lifetime.default_value > 0
    assert technology.capex_specific_storage_energy.default_value > 0
    assert 0.0 < technology.efficiency_charge.default_value <= 1.0
    assert 0.0 < technology.efficiency_discharge.default_value <= 1.0
    assert 0.0 < technology.self_discharge.default_value <= 1.0


@pytest.mark.parametrize(
    "technology_cls,expected_carrier",
    [
        (IndustryTESWater0100, "heat_industry_0_100"),
        (IndustryTESWater100150, "heat_industry_100_150"),
        (IndustryTESSteam150200, "heat_industry_150_200"),
    ],
)
def test_reference_carrier_matches_temperature_band(technology_cls, expected_carrier, model: Model):
    technology = technology_cls(model=model)
    technology.build()
    assert technology.reference_carrier.default_value == [expected_carrier]


def test_efficiency_is_lossless_v7_convention(model: Model):
    """v7.0 onward: charge/discharge efficiency is 1.0 -- all losses are
    represented via self_discharge instead (see module docstring)."""
    for technology_cls in TES_CLASSES:
        technology = technology_cls(model=model)
        technology.build()
        assert technology.efficiency_charge.default_value == pytest.approx(1.0)
        assert technology.efficiency_discharge.default_value == pytest.approx(1.0)


def test_water_tanks_allow_longer_duration_than_steam_accumulator(model: Model):
    """Water tanks (intraday buffer) must have a wider energy-to-power ratio
    range than the steam accumulator (inherently short-duration) -- see
    _TES_E2P_SOURCE."""
    water = IndustryTESWater0100(model=model)
    water.build()
    steam = IndustryTESSteam150200(model=model)
    steam.build()

    assert water.energy_to_power_ratio_min.default_value >= steam.energy_to_power_ratio_min.default_value
    assert water.energy_to_power_ratio_max.default_value > steam.energy_to_power_ratio_max.default_value
    assert water.energy_to_power_ratio_min.default_value < water.energy_to_power_ratio_max.default_value
    assert steam.energy_to_power_ratio_min.default_value < steam.energy_to_power_ratio_max.default_value


if __name__ == "__main__":
    pytest.main([__file__])
