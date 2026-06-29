"""Industry heat supply technology Element subclasses.

3 heat pump variants, 3 boilers, 2 temperature conversion techs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.eurostat_boiler import EurostatBoilerDataset
from zen_creator.datasets.datasets.heat_tech_parametrization import (
    HP_COP_WASTE_HEAT,
    HP_COP_WATER,
    HeatTechParametrizationDataset,
)
from zen_creator.datasets.datasets.process_parametrization import (
    CAPACITY_YEAR,
    FEC_YEAR,
    ProcessParametrizationDataset,
)
from zen_creator.elements.conversion_technologies.conversion_technology import (
    ConversionTechnology,
)
from zen_creator.utils.attribute import Attribute


def _hp_capacity(element, temp_level: str) -> Attribute:
    base_attr = EurostatBoilerDataset().get_heat_pump_capacity(element, CAPACITY_YEAR)
    split = ProcessParametrizationDataset().get_heat_capacity_split()
    if base_attr.df is not None:
        df = base_attr.df.copy()
        # divide by 2: existing capacity split equally between waste-heat and water variants
        df["capacity_existing"] = df["capacity_existing"] * split[temp_level] / 2
        base_attr.df = df
    return base_attr


def _hp_waste_heat_limit(element, temp_level: str) -> Attribute:
    return ProcessParametrizationDataset().get_waste_heat_capacity_limit(element, temp_level)


# -- Heat pumps ---------------------------------------------------------------
# Two variants per temperature level:
#   _waste_heat: source = waste heat at 50°C (Bever2024, Agora_IGE2023); capacity limited
#   _water:      source = water at 15°C (Agora_IGE2023); unconstrained

def _hp_methods(base_tech: str, temp_level: str, cop: float):
    """Return a dict of _set_* methods shared across all HP variants."""
    carrier = f"heat_industry_{temp_level}"

    class _Mixin:
        def _set_reference_carrier(self) -> Attribute:
            return Attribute("reference_carrier", default_value=[carrier], element=self)

        def _set_input_carrier(self) -> Attribute:
            return Attribute("input_carrier", default_value=["electricity"], element=self)

        def _set_output_carrier(self) -> Attribute:
            return Attribute("output_carrier", default_value=[carrier], element=self)

        def _set_conversion_factor(self) -> Attribute:
            return HeatTechParametrizationDataset().get_conversion_factor(self, base_tech, temp_level, cop_override=cop)

        def _set_lifetime(self) -> Attribute:
            return HeatTechParametrizationDataset().get_lifetime(self, base_tech)

        def _set_capex_specific_conversion(self) -> Attribute:
            return HeatTechParametrizationDataset().get_capex_specific_conversion(self, base_tech)

        def _set_opex_specific_fixed(self) -> Attribute:
            return HeatTechParametrizationDataset().get_opex_specific_fixed(self, base_tech)

        def _set_opex_specific_variable(self) -> Attribute:
            return HeatTechParametrizationDataset().get_opex_specific_variable(self, base_tech)

        def _set_carbon_intensity_technology(self) -> Attribute:
            return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, base_tech)

        def _set_max_diffusion_rate(self) -> Attribute:
            return HeatTechParametrizationDataset().get_max_diffusion_rate(self, base_tech)

        def _set_capacity_existing(self) -> Attribute:
            return _hp_capacity(self, temp_level)

    return _Mixin


# --- 0–100°C ---

class HeatPumpIndustry0100WasteHeat(_hp_methods("heat_pump_industry", "0_100", HP_COP_WASTE_HEAT["0_100"]), ConversionTechnology):
    name = "heat_pump_industry_0_100_waste_heat"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_capacity_addition_max(self) -> Attribute:
        return _hp_waste_heat_limit(self, "0_100")


class HeatPumpIndustry0100Water(_hp_methods("heat_pump_industry", "0_100", HP_COP_WATER["0_100"]), ConversionTechnology):
    name = "heat_pump_industry_0_100_water"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


# --- 100–150°C ---

class HeatPumpIndustry100150WasteHeat(_hp_methods("heat_pump_industry", "100_150", HP_COP_WASTE_HEAT["100_150"]), ConversionTechnology):
    name = "heat_pump_industry_100_150_waste_heat"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_capacity_addition_max(self) -> Attribute:
        return _hp_waste_heat_limit(self, "100_150")


class HeatPumpIndustry100150Water(_hp_methods("heat_pump_industry", "100_150", HP_COP_WATER["100_150"]), ConversionTechnology):
    name = "heat_pump_industry_100_150_water"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


# --- 150–200°C ---

class HeatPumpIndustry150200WasteHeat(_hp_methods("heat_pump_industry", "150_200", HP_COP_WASTE_HEAT["150_200"]), ConversionTechnology):
    name = "heat_pump_industry_150_200_waste_heat"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_capacity_addition_max(self) -> Attribute:
        return _hp_waste_heat_limit(self, "150_200")


class HeatPumpIndustry150200Water(_hp_methods("heat_pump_industry", "150_200", HP_COP_WATER["150_200"]), ConversionTechnology):
    name = "heat_pump_industry_150_200_water"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


# -- Boilers (produce heat_industry_150_200 only) ----------------------------

class BiomassBoilerIndustry(ConversionTechnology):
    name = "biomass_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["biomass"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return HeatTechParametrizationDataset().get_conversion_factor(self, "biomass_boiler_industry", "150_200")

    def _set_lifetime(self) -> Attribute:
        return HeatTechParametrizationDataset().get_lifetime(self, "biomass_boiler_industry")

    def _set_capex_specific_conversion(self) -> Attribute:
        return HeatTechParametrizationDataset().get_capex_specific_conversion(self, "biomass_boiler_industry")

    def _set_opex_specific_fixed(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_fixed(self, "biomass_boiler_industry")

    def _set_opex_specific_variable(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_variable(self, "biomass_boiler_industry")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, "biomass_boiler_industry")

    def _set_max_diffusion_rate(self) -> Attribute:
        return HeatTechParametrizationDataset().get_max_diffusion_rate(self, "biomass_boiler_industry")

    def _set_capacity_existing(self) -> Attribute:
        return EurostatBoilerDataset().get_biomass_boiler_capacity(self, FEC_YEAR, CAPACITY_YEAR)


class ElectrodeBoilerIndustry(ConversionTechnology):
    name = "electrode_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return HeatTechParametrizationDataset().get_conversion_factor(self, "electrode_boiler_industry", "150_200")

    def _set_lifetime(self) -> Attribute:
        return HeatTechParametrizationDataset().get_lifetime(self, "electrode_boiler_industry")

    def _set_capex_specific_conversion(self) -> Attribute:
        return HeatTechParametrizationDataset().get_capex_specific_conversion(self, "electrode_boiler_industry")

    def _set_opex_specific_fixed(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_fixed(self, "electrode_boiler_industry")

    def _set_opex_specific_variable(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_variable(self, "electrode_boiler_industry")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, "electrode_boiler_industry")

    def _set_max_diffusion_rate(self) -> Attribute:
        return HeatTechParametrizationDataset().get_max_diffusion_rate(self, "electrode_boiler_industry")

    def _set_capacity_existing(self) -> Attribute:
        return EurostatBoilerDataset().get_electrode_boiler_capacity(self, FEC_YEAR, CAPACITY_YEAR)


class NaturalGasBoilerIndustry(ConversionTechnology):
    name = "natural_gas_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["natural_gas"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return HeatTechParametrizationDataset().get_conversion_factor(self, "natural_gas_boiler_industry", "150_200")

    def _set_lifetime(self) -> Attribute:
        return HeatTechParametrizationDataset().get_lifetime(self, "natural_gas_boiler_industry")

    def _set_capex_specific_conversion(self) -> Attribute:
        return HeatTechParametrizationDataset().get_capex_specific_conversion(self, "natural_gas_boiler_industry")

    def _set_opex_specific_fixed(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_fixed(self, "natural_gas_boiler_industry")

    def _set_opex_specific_variable(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_variable(self, "natural_gas_boiler_industry")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, "natural_gas_boiler_industry")

    def _set_max_diffusion_rate(self) -> Attribute:
        return HeatTechParametrizationDataset().get_max_diffusion_rate(self, "natural_gas_boiler_industry")

    def _set_capacity_existing(self) -> Attribute:
        return EurostatBoilerDataset().get_natural_gas_boiler_capacity(self, FEC_YEAR, CAPACITY_YEAR)


# -- Temperature conversion cascade ------------------------------------------

class HeatIndustryTempConversion150(ConversionTechnology):
    name = "heat_industry_temp_conversion_150"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return Attribute("conversion_factor", default_value=[{"heat_industry_150_200": {"default_value": 1.0, "unit": "GW/GW"}}], element=self)

    def _set_lifetime(self) -> Attribute:
        return Attribute("lifetime", default_value=30, unit="1", element=self)


class HeatIndustryTempConversion100(ConversionTechnology):
    name = "heat_industry_temp_conversion_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return Attribute("conversion_factor", default_value=[{"heat_industry_100_150": {"default_value": 1.0, "unit": "GW/GW"}}], element=self)

    def _set_lifetime(self) -> Attribute:
        return Attribute("lifetime", default_value=30, unit="1", element=self)
