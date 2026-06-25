from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.mayer2024 import Mayer2024Dataset
from zen_creator.elements.storage_technologies.storage_technology import (
    StorageTechnology,
)
from zen_creator.utils.attribute import Attribute


class IndustryTESWater(StorageTechnology):

    name: str = "industry_TES_water"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(
            name="reference_carrier",
            default_value=["heat_industry_0_100"],
            element=self,
        )

    def _set_lifetime(self) -> Attribute:
        return Mayer2024Dataset(self.model.config.source_path).get_lifetime(
            element=self
        )

    def _set_efficiency_charge(self) -> Attribute:
        return Mayer2024Dataset(self.model.config.source_path).get_efficiency_charge(
            element=self
        )

    def _set_efficiency_discharge(self) -> Attribute:
        return Mayer2024Dataset(self.model.config.source_path).get_efficiency_discharge(
            element=self
        )

    def _set_capex_specific_storage_energy(self) -> Attribute:
        return Mayer2024Dataset(
            self.model.config.source_path
        ).get_capex_specific_storage_energy(element=self)

    def _set_opex_specific_fixed_energy(self) -> Attribute:
        return Mayer2024Dataset(
            self.model.config.source_path
        ).get_opex_specific_fixed_energy(element=self)


class IndustryTESSteam(StorageTechnology):

    name: str = "industry_TES_steam"

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(
            name="reference_carrier",
            default_value=["heat_industry_100_150"],
            element=self,
        )

    def _set_lifetime(self) -> Attribute:
        return Mayer2024Dataset(self.model.config.source_path).get_lifetime(
            element=self
        )

    def _set_efficiency_charge(self) -> Attribute:
        return Mayer2024Dataset(self.model.config.source_path).get_efficiency_charge(
            element=self
        )

    def _set_efficiency_discharge(self) -> Attribute:
        return Mayer2024Dataset(self.model.config.source_path).get_efficiency_discharge(
            element=self
        )

    def _set_capex_specific_storage_energy(self) -> Attribute:
        return Mayer2024Dataset(
            self.model.config.source_path
        ).get_capex_specific_storage_energy(element=self)

    def _set_opex_specific_fixed_energy(self) -> Attribute:
        return Mayer2024Dataset(
            self.model.config.source_path
        ).get_opex_specific_fixed_energy(element=self)
