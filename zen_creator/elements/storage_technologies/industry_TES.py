from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.mayer2024 import Mayer2024Dataset
from zen_creator.elements.storage_technologies.storage_technology import (
    StorageTechnology,
)
from zen_creator.utils.attribute import Attribute


class IndustryTESWater0100(StorageTechnology):

    name: str = "industry_TES_water_0_100"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_lifetime(self) -> Attribute:
        return Mayer2024Dataset().get_lifetime(element=self)

    def _set_efficiency_charge(self) -> Attribute:
        return Mayer2024Dataset().get_efficiency_charge(element=self)

    def _set_efficiency_discharge(self) -> Attribute:
        return Mayer2024Dataset().get_efficiency_discharge(element=self)

    def _set_capex_specific_storage_energy(self) -> Attribute:
        return Mayer2024Dataset().get_capex_specific_storage_energy(element=self)

    def _set_opex_specific_fixed_energy(self) -> Attribute:
        return Mayer2024Dataset().get_opex_specific_fixed_energy(element=self)


class IndustryTESWater100150(StorageTechnology):

    name: str = "industry_TES_water_100_150"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_lifetime(self) -> Attribute:
        return Mayer2024Dataset().get_lifetime(element=self)

    def _set_efficiency_charge(self) -> Attribute:
        return Mayer2024Dataset().get_efficiency_charge(element=self)

    def _set_efficiency_discharge(self) -> Attribute:
        return Mayer2024Dataset().get_efficiency_discharge(element=self)

    def _set_capex_specific_storage_energy(self) -> Attribute:
        return Mayer2024Dataset().get_capex_specific_storage_energy(element=self)

    def _set_opex_specific_fixed_energy(self) -> Attribute:
        return Mayer2024Dataset().get_opex_specific_fixed_energy(element=self)


class IndustryTESSteam100150(StorageTechnology):

    name: str = "industry_TES_steam_100_150"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_lifetime(self) -> Attribute:
        return Mayer2024Dataset().get_lifetime(element=self)

    def _set_efficiency_charge(self) -> Attribute:
        return Mayer2024Dataset().get_efficiency_charge(element=self)

    def _set_efficiency_discharge(self) -> Attribute:
        return Mayer2024Dataset().get_efficiency_discharge(element=self)

    def _set_capex_specific_storage_energy(self) -> Attribute:
        return Mayer2024Dataset().get_capex_specific_storage_energy(element=self)

    def _set_opex_specific_fixed_energy(self) -> Attribute:
        return Mayer2024Dataset().get_opex_specific_fixed_energy(element=self)


class IndustryTESSteam150200(StorageTechnology):

    name: str = "industry_TES_steam_150_200"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_lifetime(self) -> Attribute:
        return Mayer2024Dataset().get_lifetime(element=self)

    def _set_efficiency_charge(self) -> Attribute:
        return Mayer2024Dataset().get_efficiency_charge(element=self)

    def _set_efficiency_discharge(self) -> Attribute:
        return Mayer2024Dataset().get_efficiency_discharge(element=self)

    def _set_capex_specific_storage_energy(self) -> Attribute:
        return Mayer2024Dataset().get_capex_specific_storage_energy(element=self)

    def _set_opex_specific_fixed_energy(self) -> Attribute:
        return Mayer2024Dataset().get_opex_specific_fixed_energy(element=self)
