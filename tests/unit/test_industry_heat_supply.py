"""Unit tests for industry_heat_supply.py: heat pumps, boilers, the temperature
downgrade cascade, and kiln-fuel-switching technologies.

None of these 17 Element subclasses had any test coverage before this (see
cleanup plan, Phase 2 item 9).
"""

from __future__ import annotations

import pytest

from zen_creator.elements.conversion_technologies.industry_heat_supply import (
    BiomassBoilerIndustry,
    CoalBoilerIndustry,
    ElectricityToKilnfuel,
    ElectrodeBoilerIndustry,
    HeatIndustryTempConversion100,
    HeatIndustryTempConversion150,
    HeatPumpIndustry0100WasteHeat,
    HeatPumpIndustry0100Water,
    HeatPumpIndustry100150WasteHeat,
    HeatPumpIndustry100150Water,
    HeatPumpIndustry150200WasteHeat,
    HeatPumpIndustry150200Water,
    HydrogenToKilnfuel,
    NaturalGasBoilerIndustry,
    NaturalGasToKilnfuel,
    OilBoilerIndustry,
    WasteBoilerIndustry,
)
from zen_creator.model import Model

BOILER_CLASSES = [
    BiomassBoilerIndustry, ElectrodeBoilerIndustry, NaturalGasBoilerIndustry,
    OilBoilerIndustry, CoalBoilerIndustry, WasteBoilerIndustry,
]
HEAT_PUMP_CLASSES = [
    HeatPumpIndustry0100WasteHeat, HeatPumpIndustry0100Water,
    HeatPumpIndustry100150WasteHeat, HeatPumpIndustry100150Water,
    HeatPumpIndustry150200WasteHeat, HeatPumpIndustry150200Water,
]
CASCADE_CLASSES = [HeatIndustryTempConversion150, HeatIndustryTempConversion100]
KILN_FUEL_CLASSES = [NaturalGasToKilnfuel, HydrogenToKilnfuel, ElectricityToKilnfuel]
ALL_CLASSES = BOILER_CLASSES + HEAT_PUMP_CLASSES + CASCADE_CLASSES + KILN_FUEL_CLASSES


@pytest.mark.parametrize("technology_cls", ALL_CLASSES)
def test_build_succeeds_and_output_matches_reference_carrier(technology_cls, model: Model):
    """Every technology must build without error, and its reference_carrier must
    also be its (single) output_carrier -- the ZEN-garden convention this whole
    file relies on."""
    technology = technology_cls(model=model)
    technology.build()

    assert technology.reference_carrier.default_value == technology.output_carrier.default_value
    assert len(technology.reference_carrier.default_value) == 1
    assert technology.lifetime.default_value > 0


@pytest.mark.parametrize("technology_cls", BOILER_CLASSES)
def test_boiler_output_is_heat_industry_150_200(technology_cls, model: Model):
    """Every boiler produces only the highest temperature band -- see module docstring."""
    technology = technology_cls(model=model)
    technology.build()
    assert technology.output_carrier.default_value == ["heat_industry_150_200"]


@pytest.mark.parametrize("technology_cls", BOILER_CLASSES)
def test_boiler_conversion_factor_is_at_least_one(technology_cls, model: Model):
    """conversion_factor (GW fuel in per GW heat out) must be >= 1 for every boiler
    (net efficiency <= 100%)."""
    technology = technology_cls(model=model)
    technology.build()
    cf_entry = next(iter(technology.conversion_factor.default_value[0].values()))
    assert cf_entry["default_value"] >= 1.0


@pytest.mark.parametrize(
    "technology_cls,temp_level",
    [
        (HeatPumpIndustry0100WasteHeat, "0_100"), (HeatPumpIndustry0100Water, "0_100"),
        (HeatPumpIndustry100150WasteHeat, "100_150"), (HeatPumpIndustry100150Water, "100_150"),
        (HeatPumpIndustry150200WasteHeat, "150_200"), (HeatPumpIndustry150200Water, "150_200"),
    ],
)
def test_heat_pump_output_matches_its_temperature_band(technology_cls, temp_level, model: Model):
    technology = technology_cls(model=model)
    technology.build()
    assert technology.output_carrier.default_value == [f"heat_industry_{temp_level}"]
    assert technology.input_carrier.default_value == ["electricity"]


def test_waste_heat_heat_pumps_have_capacity_limit_water_variants_dont(model: Model):
    """Only the *_waste_heat variants are capacity-limited (bounded by available
    waste heat); the *_water variants are unconstrained -- see module comment
    'source = water at 15C ... unconstrained'."""
    waste_heat = HeatPumpIndustry150200WasteHeat(model=model)
    water = HeatPumpIndustry150200Water(model=model)
    assert "_set_capacity_limit" in waste_heat.__class__.__dict__
    assert "_set_capacity_limit" not in water.__class__.__dict__


@pytest.mark.parametrize("technology_cls", CASCADE_CLASSES)
def test_temperature_cascade_is_lossless_pass_through(technology_cls, model: Model):
    """The temperature downgrade cascade has conversion_factor == 1.0 (GW/GW) --
    it's a pure temperature relabeling, not an energy conversion."""
    technology = technology_cls(model=model)
    technology.build()
    cf_entry = next(iter(technology.conversion_factor.default_value[0].values()))
    assert cf_entry["default_value"] == pytest.approx(1.0)


def test_temperature_cascade_flows_from_high_to_low_temperature(model: Model):
    cascade_150 = HeatIndustryTempConversion150(model=model)
    cascade_150.build()
    assert cascade_150.input_carrier.default_value == ["heat_industry_150_200"]
    assert cascade_150.output_carrier.default_value == ["heat_industry_100_150"]

    cascade_100 = HeatIndustryTempConversion100(model=model)
    cascade_100.build()
    assert cascade_100.input_carrier.default_value == ["heat_industry_100_150"]
    assert cascade_100.output_carrier.default_value == ["heat_industry_0_100"]


@pytest.mark.parametrize(
    "technology_cls,fuel",
    [(NaturalGasToKilnfuel, "natural_gas"), (HydrogenToKilnfuel, "hydrogen"), (ElectricityToKilnfuel, "electricity")],
)
def test_kiln_fuel_switch_input_matches_its_fuel(technology_cls, fuel, model: Model):
    technology = technology_cls(model=model)
    technology.build()
    assert technology.input_carrier.default_value == [fuel]
    assert technology.output_carrier.default_value == ["fuel_to_kiln"]


def test_only_hydrogen_and_electricity_kilnfuel_have_max_diffusion_rate(model: Model):
    """natural_gas_to_kilnfuel (the incumbent) has no diffusion cap (falls back
    to ConversionTechnology's own unset default); the two switching
    alternatives are capped at 0.13 -- see module comment."""
    ng = NaturalGasToKilnfuel(model=model)
    h2 = HydrogenToKilnfuel(model=model)
    elec = ElectricityToKilnfuel(model=model)
    ng.build()
    h2.build()
    elec.build()
    assert ng.max_diffusion_rate.default_value != pytest.approx(0.13)
    assert h2.max_diffusion_rate.default_value == pytest.approx(0.13)
    assert elec.max_diffusion_rate.default_value == pytest.approx(0.13)


if __name__ == "__main__":
    pytest.main([__file__])
