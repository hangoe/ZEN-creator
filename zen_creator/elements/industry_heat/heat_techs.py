"""Industry heat supply technology Element subclasses.

8 technologies: 4 base techs × 2 temperature levels (_0_100 and _100_200).
Each variant has a single output carrier matching its temperature level.

Attributes are set from the exact same build_tech_from_table function that
compute_params.py uses, with output carrier swapped per variant.
Capacity is split by demand-weighted temperature share (~29.5% / 70.5%).
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.elements.conversion_technologies.conversion_technology import (
    ConversionTechnology,
)
from zen_creator.utils.attribute import Attribute

from zen_creator.elements.industry_heat._apply import apply_attrs_dict
from zen_creator.elements.industry_heat._params import (
    CAPACITY_YEAR,
    FEC_YEAR,
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


HEAT_CARRIERS = {"0_100": "heat_industry_0_100", "100_200": "heat_industry_100_200"}


def _build_heat_variant_dict(base_tech_name: str, suffix: str) -> dict:
    """Build the attributes dict for one temperature-level variant.

    Matches compute_params.py logic: read base tech from Excel, then swap
    reference_carrier and output_carrier to the target heat carrier.
    """
    data = copy.deepcopy(heat_tech_base_data(base_tech_name))
    carrier = HEAT_CARRIERS[suffix]
    data["reference_carrier"]["default_value"] = [carrier]
    data["output_carrier"]["default_value"] = [carrier]
    return data


def _make_split_capacity(tech, base_df, temp_suffix: str) -> Attribute:
    split = heat_capacity_split()
    attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=tech)
    df = base_df.copy()
    df["capacity_existing"] = df["capacity_existing"] * split[temp_suffix]
    attr.df = _index_capacity_df(df)
    return attr


def _init_heat_variant(tech: ConversionTechnology, base_tech_name: str, suffix: str) -> None:
    data = _build_heat_variant_dict(base_tech_name, suffix)
    apply_attrs_dict(tech, data)


# ---------------------------------------------------------------------------
# Biomass boiler
# ---------------------------------------------------------------------------

class BiomassBoilerIndustry0100(ConversionTechnology):
    name = "biomass_boiler_industry_0_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        _init_heat_variant(self, "biomass_boiler_industry", "0_100")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["biomass"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_heat_variant_dict("biomass_boiler_industry", "0_100")
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        df = biomass_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR)
        return _make_split_capacity(self, df, "0_100")


class BiomassBoilerIndustry100200(ConversionTechnology):
    name = "biomass_boiler_industry_100_200"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        _init_heat_variant(self, "biomass_boiler_industry", "100_200")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_100_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["biomass"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_100_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_heat_variant_dict("biomass_boiler_industry", "100_200")
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        df = biomass_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR)
        return _make_split_capacity(self, df, "100_200")


# ---------------------------------------------------------------------------
# Electrode boiler
# ---------------------------------------------------------------------------

class ElectrodeBoilerIndustry0100(ConversionTechnology):
    name = "electrode_boiler_industry_0_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        _init_heat_variant(self, "electrode_boiler_industry", "0_100")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_heat_variant_dict("electrode_boiler_industry", "0_100")
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        df = electrode_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR)
        return _make_split_capacity(self, df, "0_100")


class ElectrodeBoilerIndustry100200(ConversionTechnology):
    name = "electrode_boiler_industry_100_200"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        _init_heat_variant(self, "electrode_boiler_industry", "100_200")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_100_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_100_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_heat_variant_dict("electrode_boiler_industry", "100_200")
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        df = electrode_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR)
        return _make_split_capacity(self, df, "100_200")


# ---------------------------------------------------------------------------
# Heat pump
# ---------------------------------------------------------------------------

class HeatPumpIndustry0100(ConversionTechnology):
    name = "heat_pump_industry_0_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        _init_heat_variant(self, "heat_pump_industry", "0_100")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_heat_variant_dict("heat_pump_industry", "0_100")
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        df = heat_pump_capacity_existing_df()
        return _make_split_capacity(self, df, "0_100")


class HeatPumpIndustry100200(ConversionTechnology):
    name = "heat_pump_industry_100_200"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        _init_heat_variant(self, "heat_pump_industry", "100_200")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_100_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_100_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_heat_variant_dict("heat_pump_industry", "100_200")
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        df = heat_pump_capacity_existing_df()
        return _make_split_capacity(self, df, "100_200")


# ---------------------------------------------------------------------------
# Natural gas boiler
# ---------------------------------------------------------------------------

class NaturalGasBoilerIndustry0100(ConversionTechnology):
    name = "natural_gas_boiler_industry_0_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        _init_heat_variant(self, "natural_gas_boiler_industry", "0_100")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["natural_gas"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_heat_variant_dict("natural_gas_boiler_industry", "0_100")
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        df = natural_gas_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR)
        return _make_split_capacity(self, df, "0_100")


class NaturalGasBoilerIndustry100200(ConversionTechnology):
    name = "natural_gas_boiler_industry_100_200"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        _init_heat_variant(self, "natural_gas_boiler_industry", "100_200")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_100_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["natural_gas"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_100_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_heat_variant_dict("natural_gas_boiler_industry", "100_200")
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        df = natural_gas_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR)
        return _make_split_capacity(self, df, "100_200")
