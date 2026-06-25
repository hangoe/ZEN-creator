"""Industry production technology Element subclasses."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.faostat_food import FaostatFoodDataset
from zen_creator.datasets.datasets.jrc_idees_industry import JrcIdeesIndustryDataset
from zen_creator.datasets.datasets.process_parametrization import (
    CAPACITY_YEAR,
    FEC_YEAR,
    ProcessParametrizationDataset,
)
from zen_creator.elements.conversion_technologies.conversion_technology import (
    ConversionTechnology,
)
from zen_creator.utils.attribute import Attribute


class GlassProduction(ConversionTechnology):
    name = "glass_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["glass"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return ProcessParametrizationDataset().get_input_carrier(self, "glass")

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["glass"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return ProcessParametrizationDataset().get_conversion_factor(self, "glass")

    def _set_lifetime(self) -> Attribute:
        return ProcessParametrizationDataset().get_lifetime(self, "glass")

    def _set_capex_specific_conversion(self) -> Attribute:
        return ProcessParametrizationDataset().get_capex_specific_conversion(self, "glass")

    def _set_opex_specific_fixed(self) -> Attribute:
        return ProcessParametrizationDataset().get_opex_specific_fixed(self, "glass")

    def _set_opex_specific_variable(self) -> Attribute:
        return ProcessParametrizationDataset().get_opex_specific_variable(self, "glass")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return ProcessParametrizationDataset().get_carbon_intensity_technology(self, "glass")

    def _set_max_diffusion_rate(self) -> Attribute:
        return ProcessParametrizationDataset().get_max_diffusion_rate(self, "glass")

    def _set_capacity_existing(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_capacity_existing(self, "glass", FEC_YEAR, CAPACITY_YEAR)


class CeramicProduction(ConversionTechnology):
    name = "ceramic_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["ceramic"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return ProcessParametrizationDataset().get_input_carrier(self, "ceramic")

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["ceramic"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return ProcessParametrizationDataset().get_conversion_factor(self, "ceramic")

    def _set_lifetime(self) -> Attribute:
        return ProcessParametrizationDataset().get_lifetime(self, "ceramic")

    def _set_capex_specific_conversion(self) -> Attribute:
        return ProcessParametrizationDataset().get_capex_specific_conversion(self, "ceramic")

    def _set_opex_specific_fixed(self) -> Attribute:
        return ProcessParametrizationDataset().get_opex_specific_fixed(self, "ceramic")

    def _set_opex_specific_variable(self) -> Attribute:
        return ProcessParametrizationDataset().get_opex_specific_variable(self, "ceramic")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return ProcessParametrizationDataset().get_carbon_intensity_technology(self, "ceramic")

    def _set_max_diffusion_rate(self) -> Attribute:
        return ProcessParametrizationDataset().get_max_diffusion_rate(self, "ceramic")

    def _set_capacity_existing(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_capacity_existing(self, "ceramic", FEC_YEAR, CAPACITY_YEAR)


class PaperProduction(ConversionTechnology):
    name = "paper_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["paper"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return ProcessParametrizationDataset().get_input_carrier(self, "paper")

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["paper"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return ProcessParametrizationDataset().get_conversion_factor(self, "paper")

    def _set_lifetime(self) -> Attribute:
        return ProcessParametrizationDataset().get_lifetime(self, "paper")

    def _set_capex_specific_conversion(self) -> Attribute:
        return ProcessParametrizationDataset().get_capex_specific_conversion(self, "paper")

    def _set_opex_specific_fixed(self) -> Attribute:
        return ProcessParametrizationDataset().get_opex_specific_fixed(self, "paper")

    def _set_opex_specific_variable(self) -> Attribute:
        return ProcessParametrizationDataset().get_opex_specific_variable(self, "paper")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return ProcessParametrizationDataset().get_carbon_intensity_technology(self, "paper")

    def _set_max_diffusion_rate(self) -> Attribute:
        return ProcessParametrizationDataset().get_max_diffusion_rate(self, "paper")

    def _set_capacity_existing(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_capacity_existing(self, "paper", FEC_YEAR, CAPACITY_YEAR)


class FoodProduction(ConversionTechnology):
    name = "food_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["food"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return ProcessParametrizationDataset().get_input_carrier(self, "food")

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["food"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return ProcessParametrizationDataset().get_conversion_factor(self, "food")

    def _set_lifetime(self) -> Attribute:
        return ProcessParametrizationDataset().get_lifetime(self, "food")

    def _set_capex_specific_conversion(self) -> Attribute:
        return ProcessParametrizationDataset().get_capex_specific_conversion(self, "food")

    def _set_opex_specific_fixed(self) -> Attribute:
        return ProcessParametrizationDataset().get_opex_specific_fixed(self, "food")

    def _set_opex_specific_variable(self) -> Attribute:
        return ProcessParametrizationDataset().get_opex_specific_variable(self, "food")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return ProcessParametrizationDataset().get_carbon_intensity_technology(self, "food")

    def _set_max_diffusion_rate(self) -> Attribute:
        return ProcessParametrizationDataset().get_max_diffusion_rate(self, "food")

    def _set_capacity_existing(self) -> Attribute:
        return FaostatFoodDataset().get_food_capacity_existing(self, FEC_YEAR, CAPACITY_YEAR)
