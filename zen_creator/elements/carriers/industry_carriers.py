"""Industry heat carrier Element subclasses.

Product carriers: Glass, Ceramic, Paper, Food
Energy carriers: HeatIndustry0100, HeatIndustry100150, HeatIndustry150200
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets._industry_heat_utils import (
    HEAT_CARRIER_NAMES,
    INDUSTRY_HEAT_SECTORS,
    KILN_FUEL_SECTORS,
    heat_carrier_name,
    kiln_fuel_carrier_name,
)
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
    """Glass product carrier; demand set equal to capacity_existing (JRC-IDEES-2023)."""

    name = "glass"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_demand(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_demand_as_capacity_existing(self, "glass", FEC_YEAR)


_add_carrier_setters(Glass, "glass")


class Ceramic(Carrier):
    """Ceramic product carrier; demand set equal to capacity_existing
    (JRC-IDEES-2023 thermal FEC / Rehfeldt2017 specific energy)."""

    name = "ceramic"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_demand(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_ceramic_demand_as_capacity_existing(self, FEC_YEAR)


_add_carrier_setters(Ceramic, "ceramic")


class Paper(Carrier):
    """Paper product carrier; demand set equal to capacity_existing (JRC-IDEES-2023)."""

    name = "paper"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_demand(self) -> Attribute:
        return JrcIdeesIndustryDataset().get_demand_as_capacity_existing(self, "paper", FEC_YEAR)


_add_carrier_setters(Paper, "paper")


class Food(Carrier):
    """Food product carrier; demand set equal to capacity_existing (FAOSTAT)."""

    name = "food"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")

    def _set_demand(self) -> Attribute:
        return FaostatFoodDataset().get_food_demand_as_capacity_existing(self, FEC_YEAR)


_add_carrier_setters(Food, "food")


class HeatIndustry0100(Carrier):
    """Energy carrier for industrial process heat in the 0-100C band."""

    name = "heat_industry_0_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


_add_carrier_setters(HeatIndustry0100, "heat_industry_0_100")


class HeatIndustry100150(Carrier):
    """Energy carrier for industrial process heat in the 100-150C band."""

    name = "heat_industry_100_150"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


_add_carrier_setters(HeatIndustry100150, "heat_industry_100_150")


class HeatIndustry150200(Carrier):
    """Energy carrier for industrial process heat in the 150-200C band --
    the level every boiler produces and the top of the temperature cascade."""

    name = "heat_industry_150_200"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


_add_carrier_setters(HeatIndustry150200, "heat_industry_150_200")


class FuelToKiln(Carrier):
    """Shared kiln-fuel carrier that ceramic_production/glass_production draw
    on instead of a direct natural_gas input, switchable to hydrogen/
    electricity via *_to_kilnfuel technologies (see industry_heat_supply.py)."""

    name = "fuel_to_kiln"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


_add_carrier_setters(FuelToKiln, "fuel_to_kiln")


# -- Per-sector heat carriers (V11) --------------------------------------------
# One copy of every heat carrier (and the kiln-fuel carrier) per sector, named
# `<base name>_<sector>`; used by the per-sector industry heat structure so heat can
# never flow between sectors (added by the *_per_sector sectors, e.g. industry_heat_per_sector).

def _make_energy_carrier_class(carrier_name: str, class_name: str, doc: str) -> type[Carrier]:
    def __init__(self, model: Model) -> None:
        Carrier.__init__(self, model=model, power_unit="GW")

    cls = type(
        class_name,
        (Carrier,),
        {"__module__": __name__, "__qualname__": class_name, "__doc__": doc, "__init__": __init__, "name": carrier_name},
    )
    return _add_carrier_setters(cls, carrier_name)


HEAT_CARRIER_CLASSES_BY_SECTOR: dict[str, dict[str, type[Carrier]]] = {}
FUEL_TO_KILN_CARRIER_CLASSES_BY_SECTOR: dict[str, type[Carrier]] = {}

for _sector in INDUSTRY_HEAT_SECTORS:
    HEAT_CARRIER_CLASSES_BY_SECTOR[_sector] = {}
    for _level in HEAT_CARRIER_NAMES:
        _cls = _make_energy_carrier_class(
            heat_carrier_name(_level, _sector),
            f"HeatIndustry{_level.replace('_', '')}{_sector.capitalize()}",
            f"Energy carrier for {_sector} process heat in the {_level.replace('_', '-')}C band "
            "(per-sector copy of the pooled industry heat carrier).",
        )
        HEAT_CARRIER_CLASSES_BY_SECTOR[_sector][_level] = _cls
        globals()[_cls.__name__] = _cls

for _sector in KILN_FUEL_SECTORS:
    _cls = _make_energy_carrier_class(
        kiln_fuel_carrier_name(_sector),
        f"FuelToKiln{_sector.capitalize()}",
        f"Kiln-fuel carrier of the {_sector} sector (per-sector copy of fuel_to_kiln).",
    )
    FUEL_TO_KILN_CARRIER_CLASSES_BY_SECTOR[_sector] = _cls
    globals()[_cls.__name__] = _cls
del _sector, _level, _cls
