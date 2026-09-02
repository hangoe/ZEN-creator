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


def _production_methods(sector: str):
    """Return a dict of _set_* methods shared by every production technology,
    all delegated to ProcessParametrizationDataset with `sector` as the
    lookup key. `_set_capacity_existing` is NOT included here -- each sector
    sources its existing capacity from a different dataset (see the four
    classes below), so it stays a deliberate per-class override."""

    class _Mixin:
        def _set_reference_carrier(self) -> Attribute:
            return Attribute("reference_carrier", default_value=[sector], element=self)

        def _set_input_carrier(self) -> Attribute:
            return ProcessParametrizationDataset().get_input_carrier(self, sector)

        def _set_output_carrier(self) -> Attribute:
            return Attribute("output_carrier", default_value=[sector], element=self)

        def _set_conversion_factor(self) -> Attribute:
            return ProcessParametrizationDataset().get_conversion_factor(self, sector)

        def _set_lifetime(self) -> Attribute:
            return ProcessParametrizationDataset().get_lifetime(self, sector)

        def _set_capex_specific_conversion(self) -> Attribute:
            return ProcessParametrizationDataset().get_capex_specific_conversion(self, sector)

        def _set_opex_specific_fixed(self) -> Attribute:
            return ProcessParametrizationDataset().get_opex_specific_fixed(self, sector)

        def _set_opex_specific_variable(self) -> Attribute:
            return ProcessParametrizationDataset().get_opex_specific_variable(self, sector)

        def _set_carbon_intensity_technology(self) -> Attribute:
            return ProcessParametrizationDataset().get_carbon_intensity_technology(self, sector)

        def _set_max_diffusion_rate(self) -> Attribute:
            return ProcessParametrizationDataset().get_max_diffusion_rate(self, sector)

    return _Mixin


class GlassProduction(_production_methods("glass"), ConversionTechnology):
    """Glass production technology; existing capacity from JRC-IDEES-2023."""

    name = "glass_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_capacity_existing(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_capacity_existing(self, "glass", FEC_YEAR, CAPACITY_YEAR)


class CeramicProduction(_production_methods("ceramic"), ConversionTechnology):
    """Ceramic production technology; existing capacity derived from
    JRC-IDEES-2023 thermal FEC / Rehfeldt2017 specific energy (see
    get_ceramic_capacity_from_fec)."""

    name = "ceramic_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_capacity_existing(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_ceramic_capacity_from_fec(self, FEC_YEAR, CAPACITY_YEAR)


class PaperProduction(_production_methods("paper"), ConversionTechnology):
    """Paper production technology; existing capacity from JRC-IDEES-2023."""

    name = "paper_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_capacity_existing(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_capacity_existing(self, "paper", FEC_YEAR, CAPACITY_YEAR)


class FoodProduction(_production_methods("food"), ConversionTechnology):
    """Food production technology; existing capacity from FAOSTAT."""

    name = "food_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_capacity_existing(self) -> Attribute:
        return FaostatFoodDataset().get_food_capacity_existing(self, FEC_YEAR, CAPACITY_YEAR)
