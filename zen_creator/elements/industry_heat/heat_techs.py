"""Industry heat supply technology Element subclasses.

Structure (v3.0+):
- 3 heat pump variants: HP 0_100 (highest COP), HP 100_150, HP 150_200
- 3 boilers producing heat_industry_150_200 only
- 2 temperature conversion techs:
    heat_industry_150_200 → heat_industry_100_150
    heat_industry_100_150 → heat_industry_0_100

HP capacity is split by demand-weighted 3-level temperature share.
Boiler capacity is NOT split — full capacity goes to the 150_200 level.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

import numpy as np

from zen_creator.elements.conversion_technologies.conversion_technology import (
    ConversionTechnology,
)
from zen_creator.utils.attribute import Attribute

from zen_creator.elements.industry_heat._apply import apply_attrs_dict
from zen_creator.elements.industry_heat._params import (
    CAPACITY_YEAR,
    FEC_YEAR,
    HEAT_CARRIER_NAMES,
    heat_capacity_split,
    heat_tech_base_data,
)
from zen_creator.elements.industry_heat.production_techs import _index_capacity_df
from zen_creator.industry_heat_eu.capacity_and_demand import (
    biomass_boiler_capacity_existing_df,
    electrode_boiler_capacity_existing_df,
    heat_pump_capacity_existing_df,
    natural_gas_boiler_capacity_existing_df,
)


# COP bonus per temperature level (lower temp → higher COP).
# Placeholder values — adapt later.
HP_COP_BONUS = {
    "0_100": 0.02,
    "100_150": 0.01,
    "150_200": 0.0,
}


def _build_heat_variant_dict(base_tech_name: str, temp_level: str) -> dict:
    """Build attributes dict for one temperature-level variant."""
    data = copy.deepcopy(heat_tech_base_data(base_tech_name))
    carrier = HEAT_CARRIER_NAMES[temp_level]
    data["reference_carrier"]["default_value"] = [carrier]
    data["output_carrier"]["default_value"] = [carrier]
    return data


def _make_split_capacity(tech, base_df, temp_level: str) -> Attribute:
    split = heat_capacity_split()
    attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=tech)
    df = base_df.copy()
    df["capacity_existing"] = df["capacity_existing"] * split[temp_level]
    attr.df = _index_capacity_df(df)
    return attr


def _make_full_capacity(tech, base_df) -> Attribute:
    attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=tech)
    attr.df = _index_capacity_df(base_df)
    return attr


def _hp_conversion_factor(tech, temp_level: str) -> Attribute:
    """HP variant with COP adjusted by temperature level."""
    data = _build_heat_variant_dict("heat_pump_industry", temp_level)
    bonus = HP_COP_BONUS[temp_level]
    for entry in data["conversion_factor"]:
        carrier = next(iter(entry))
        cf_base = entry[carrier]["default_value"]
        cop_base = 1.0 / cf_base
        cop_adjusted = cop_base + bonus
        entry[carrier]["default_value"] = round(1.0 / cop_adjusted, 12)
    return Attribute("conversion_factor", default_value=data["conversion_factor"], element=tech)


# ---------------------------------------------------------------------------
# Heat pumps — one per temperature level
# ---------------------------------------------------------------------------

class HeatPumpIndustry0100(ConversionTechnology):
    name = "heat_pump_industry_0_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_heat_variant_dict("heat_pump_industry", "0_100"))

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return _hp_conversion_factor(self, "0_100")

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        return _make_split_capacity(self, heat_pump_capacity_existing_df(), "0_100")


class HeatPumpIndustry100150(ConversionTechnology):
    name = "heat_pump_industry_100_150"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_heat_variant_dict("heat_pump_industry", "100_150"))

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return _hp_conversion_factor(self, "100_150")

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        return _make_split_capacity(self, heat_pump_capacity_existing_df(), "100_150")


class HeatPumpIndustry150200(ConversionTechnology):
    name = "heat_pump_industry_150_200"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_heat_variant_dict("heat_pump_industry", "150_200"))

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return _hp_conversion_factor(self, "150_200")

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        return _make_split_capacity(self, heat_pump_capacity_existing_df(), "150_200")


# ---------------------------------------------------------------------------
# Boilers — produce heat_industry_150_200 only
# ---------------------------------------------------------------------------

class BiomassBoilerIndustry(ConversionTechnology):
    name = "biomass_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_heat_variant_dict("biomass_boiler_industry", "150_200"))

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["biomass"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_heat_variant_dict("biomass_boiler_industry", "150_200")
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        return _make_full_capacity(self, biomass_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR))


class ElectrodeBoilerIndustry(ConversionTechnology):
    name = "electrode_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_heat_variant_dict("electrode_boiler_industry", "150_200"))

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_heat_variant_dict("electrode_boiler_industry", "150_200")
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        return _make_full_capacity(self, electrode_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR))


class NaturalGasBoilerIndustry(ConversionTechnology):
    name = "natural_gas_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_heat_variant_dict("natural_gas_boiler_industry", "150_200"))

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["natural_gas"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_heat_variant_dict("natural_gas_boiler_industry", "150_200")
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        return _make_full_capacity(self, natural_gas_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR))


# ---------------------------------------------------------------------------
# Temperature conversion: cascading downgrade
#   heat_industry_150_200 → heat_industry_100_150
#   heat_industry_100_150 → heat_industry_0_100
# ---------------------------------------------------------------------------

class HeatIndustryTempConversion150to100(ConversionTechnology):
    """Converts heat_industry_150_200 to heat_industry_100_150."""
    name = "heat_industry_temp_conversion_150_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        factors = [{"heat_industry_150_200": {"default_value": 1.0, "unit": "GW/GW"}}]
        return Attribute("conversion_factor", default_value=factors, element=self)

    def _set_lifetime(self) -> Attribute:
        return Attribute("lifetime", default_value=30, unit="1", element=self)


class HeatIndustryTempConversion100to0(ConversionTechnology):
    """Converts heat_industry_100_150 to heat_industry_0_100."""
    name = "heat_industry_temp_conversion_100_0"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        factors = [{"heat_industry_100_150": {"default_value": 1.0, "unit": "GW/GW"}}]
        return Attribute("conversion_factor", default_value=factors, element=self)

    def _set_lifetime(self) -> Attribute:
        return Attribute("lifetime", default_value=30, unit="1", element=self)
