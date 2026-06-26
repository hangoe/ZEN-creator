"""Industry heat carrier Element subclasses.

Product carriers: Glass, Ceramic, Paper, Food
Energy carriers: HeatIndustry0100, HeatIndustry100150, HeatIndustry150200
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.faostat_food import FaostatFoodDataset
from zen_creator.datasets.datasets.industry_carrier_data import IndustryCarrierDataset
from zen_creator.datasets.datasets.jrc_idees_industry import JrcIdeesIndustryDataset
from zen_creator.datasets.datasets.process_parametrization import FEC_YEAR
from zen_creator.elements.carriers.carrier import Carrier
from zen_creator.utils.attribute import Attribute

_CARRIER_ATTRS = (
    "price_shed_demand", "max_shed_demand",
    "availability_import", "availability_export",
    "availability_import_yearly", "availability_export_yearly",
    "price_export", "price_import",
    "carbon_intensity_carrier_import", "carbon_intensity_carrier_export",
)


def _make_carrier_setter(attr_name: str, carrier_name: str):
    def _setter(self) -> Attribute:
        return IndustryCarrierDataset().get_carrier_attr(self, carrier_name, attr_name)
    _setter.__name__ = f"_set_{attr_name}"
    return _setter


def _add_carrier_setters(cls, carrier_name: str):
    for attr_name in _CARRIER_ATTRS:
        setattr(cls, f"_set_{attr_name}", _make_carrier_setter(attr_name, carrier_name))
    return cls


class Glass(Carrier):
    name = "glass"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_demand(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_demand_as_capacity_existing(self, "glass", FEC_YEAR)


_add_carrier_setters(Glass, "glass")


class Ceramic(Carrier):
    name = "ceramic"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_demand(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_demand_as_capacity_existing(self, "ceramic", FEC_YEAR)


_add_carrier_setters(Ceramic, "ceramic")


class Paper(Carrier):
    name = "paper"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_demand(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_demand_as_capacity_existing(self, "paper", FEC_YEAR)


_add_carrier_setters(Paper, "paper")


class Food(Carrier):
    name = "food"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_demand(self) -> Attribute:
        return FaostatFoodDataset().get_food_demand_as_capacity_existing(self, FEC_YEAR)


_add_carrier_setters(Food, "food")


class HeatIndustry0100(Carrier):
    name = "heat_industry_0_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


_add_carrier_setters(HeatIndustry0100, "heat_industry_0_100")


class HeatIndustry100150(Carrier):
    name = "heat_industry_100_150"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


_add_carrier_setters(HeatIndustry100150, "heat_industry_100_150")


class HeatIndustry150200(Carrier):
    name = "heat_industry_150_200"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


_add_carrier_setters(HeatIndustry150200, "heat_industry_150_200")
