"""Industry heat supply technology Element subclasses.

Structure:
- 2 heat pump variants: HP 0_100 (slightly higher COP) and HP 100_200
- 3 boilers producing heat_industry_100_200 only
- 1 temperature conversion tech: heat_industry_100_200 → heat_industry_0_100

This allows the optimizer to supply low-temp heat either via HP 0_100
(preferred due to higher COP) or via boiler + temp_conversion.

Boiler capacity is NOT split — full capacity goes to the 100_200 variant.
HP capacity IS split by demand-weighted temperature share (~29.5% / 70.5%).
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

# COP bump for HP 0_100 relative to HP 100_200 (placeholder — adapt later)
HP_0_100_COP_BONUS = 0.01


def _build_heat_variant_dict(base_tech_name: str, suffix: str) -> dict:
    """Build the attributes dict for one temperature-level variant.

    Reads base tech from Excel, then swaps reference_carrier and
    output_carrier to the target heat carrier.
    """
    data = copy.deepcopy(heat_tech_base_data(base_tech_name))
    carrier = HEAT_CARRIERS[suffix]
    data["reference_carrier"]["default_value"] = [carrier]
    data["output_carrier"]["default_value"] = [carrier]
    return data


def _make_split_capacity(tech, base_df, temp_suffix: str) -> Attribute:
    """Split the base capacity by the demand-weighted temperature share."""
    attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=tech)
    split = heat_capacity_split()
    df = base_df.copy()
    df["capacity_existing"] = df["capacity_existing"] * split[temp_suffix]
    attr.df = _index_capacity_df(df)
    return attr


def _make_full_capacity(tech, base_df) -> Attribute:
    """Use full capacity (no split)."""
    attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=tech)
    attr.df = _index_capacity_df(base_df)
    return attr


# ---------------------------------------------------------------------------
# Heat pump — two variants with different COPs
# ---------------------------------------------------------------------------

def _hp_0_100_conversion_factor(tech) -> Attribute:
    """HP 0_100 gets a slightly higher COP (lower cf) than the base."""
    data = _build_heat_variant_dict("heat_pump_industry", "0_100")
    for entry in data["conversion_factor"]:
        carrier = next(iter(entry))
        cf_base = entry[carrier]["default_value"]
        cop_base = 1.0 / cf_base
        cop_adjusted = cop_base + HP_0_100_COP_BONUS
        entry[carrier]["default_value"] = round(1.0 / cop_adjusted, 12)
    return Attribute("conversion_factor", default_value=data["conversion_factor"], element=tech)


class HeatPumpIndustry0100(ConversionTechnology):
    name = "heat_pump_industry_0_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        _init_data = _build_heat_variant_dict("heat_pump_industry", "0_100")
        apply_attrs_dict(self, _init_data)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return _hp_0_100_conversion_factor(self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        df = heat_pump_capacity_existing_df()
        return _make_split_capacity(self, df, "0_100")


class HeatPumpIndustry100200(ConversionTechnology):
    name = "heat_pump_industry_100_200"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_heat_variant_dict("heat_pump_industry", "100_200"))

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
# Boilers — 100_200 only (low-temp heat via temp_conversion instead)
# ---------------------------------------------------------------------------

class BiomassBoilerIndustry(ConversionTechnology):
    name = "biomass_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_heat_variant_dict("biomass_boiler_industry", "100_200"))

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
        return _make_full_capacity(self, df)


class ElectrodeBoilerIndustry(ConversionTechnology):
    name = "electrode_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_heat_variant_dict("electrode_boiler_industry", "100_200"))

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
        return _make_full_capacity(self, df)


class NaturalGasBoilerIndustry(ConversionTechnology):
    name = "natural_gas_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_heat_variant_dict("natural_gas_boiler_industry", "100_200"))

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
        return _make_full_capacity(self, df)


# ---------------------------------------------------------------------------
# Temperature conversion: heat_industry_100_200 → heat_industry_0_100
# ---------------------------------------------------------------------------

class HeatIndustryTempConversion(ConversionTechnology):
    """Converts heat_industry_100_200 to heat_industry_0_100.

    Near-lossless conversion (cf = 1.0 for input per unit output).
    Allows boilers to indirectly supply low-temp heat.
    No capex, no existing capacity — purely a modeling bridge.
    """
    name = "heat_industry_temp_conversion"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["heat_industry_100_200"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        # 1.0 = lossless; adapt later
        factors = [
            {"heat_industry_100_200": {"default_value": 1.0, "unit": "GW/GW"}},
        ]
        return Attribute("conversion_factor", default_value=factors, element=self)

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", default_value=30, unit="1", element=self)
        return attr
