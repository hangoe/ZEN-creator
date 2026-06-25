"""Industry heat supply technology Element subclasses.

3 heat pump variants, 3 boilers, 2 temperature conversion techs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.eurostat_boiler import EurostatBoilerDataset
from zen_creator.datasets.datasets.heat_tech_parametrization import (
    HP_COP_BONUS,
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
        df["capacity_existing"] = df["capacity_existing"] * split[temp_level]
        base_attr.df = df
    return base_attr


# -- Heat pumps ---------------------------------------------------------------

class HeatPumpIndustry0100(ConversionTechnology):
    name = "heat_pump_industry_0_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return HeatTechParametrizationDataset().get_conversion_factor(self, "heat_pump_industry", "0_100", cop_bonus=HP_COP_BONUS["0_100"])

    def _set_lifetime(self) -> Attribute:
        return HeatTechParametrizationDataset().get_lifetime(self, "heat_pump_industry")

    def _set_capex_specific_conversion(self) -> Attribute:
        return HeatTechParametrizationDataset().get_capex_specific_conversion(self, "heat_pump_industry")

    def _set_opex_specific_fixed(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_fixed(self, "heat_pump_industry")

    def _set_opex_specific_variable(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_variable(self, "heat_pump_industry")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, "heat_pump_industry")

    def _set_max_diffusion_rate(self) -> Attribute:
        return HeatTechParametrizationDataset().get_max_diffusion_rate(self, "heat_pump_industry")

    def _set_capacity_existing(self) -> Attribute:
        return _hp_capacity(self, "0_100")


class HeatPumpIndustry100150(ConversionTechnology):
    name = "heat_pump_industry_100_150"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return HeatTechParametrizationDataset().get_conversion_factor(self, "heat_pump_industry", "100_150", cop_bonus=HP_COP_BONUS["100_150"])

    def _set_lifetime(self) -> Attribute:
        return HeatTechParametrizationDataset().get_lifetime(self, "heat_pump_industry")

    def _set_capex_specific_conversion(self) -> Attribute:
        return HeatTechParametrizationDataset().get_capex_specific_conversion(self, "heat_pump_industry")

    def _set_opex_specific_fixed(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_fixed(self, "heat_pump_industry")

    def _set_opex_specific_variable(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_variable(self, "heat_pump_industry")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, "heat_pump_industry")

    def _set_max_diffusion_rate(self) -> Attribute:
        return HeatTechParametrizationDataset().get_max_diffusion_rate(self, "heat_pump_industry")

    def _set_capacity_existing(self) -> Attribute:
        return _hp_capacity(self, "100_150")


class HeatPumpIndustry150200(ConversionTechnology):
    name = "heat_pump_industry_150_200"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return HeatTechParametrizationDataset().get_conversion_factor(self, "heat_pump_industry", "150_200", cop_bonus=HP_COP_BONUS["150_200"])

    def _set_lifetime(self) -> Attribute:
        return HeatTechParametrizationDataset().get_lifetime(self, "heat_pump_industry")

    def _set_capex_specific_conversion(self) -> Attribute:
        return HeatTechParametrizationDataset().get_capex_specific_conversion(self, "heat_pump_industry")

    def _set_opex_specific_fixed(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_fixed(self, "heat_pump_industry")

    def _set_opex_specific_variable(self) -> Attribute:
        return HeatTechParametrizationDataset().get_opex_specific_variable(self, "heat_pump_industry")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, "heat_pump_industry")

    def _set_max_diffusion_rate(self) -> Attribute:
        return HeatTechParametrizationDataset().get_max_diffusion_rate(self, "heat_pump_industry")

    def _set_capacity_existing(self) -> Attribute:
        return _hp_capacity(self, "150_200")


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

class HeatIndustryTempConversion150to100(ConversionTechnology):
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
        return Attribute("conversion_factor", default_value=[{"heat_industry_150_200": {"default_value": 1.0, "unit": "GW/GW"}}], element=self)

    def _set_lifetime(self) -> Attribute:
        return Attribute("lifetime", default_value=30, unit="1", element=self)


class HeatIndustryTempConversion100to0(ConversionTechnology):
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
        return Attribute("conversion_factor", default_value=[{"heat_industry_100_150": {"default_value": 1.0, "unit": "GW/GW"}}], element=self)

    def _set_lifetime(self) -> Attribute:
        return Attribute("lifetime", default_value=30, unit="1", element=self)
