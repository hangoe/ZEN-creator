from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.mayer2024 import Mayer2024Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.elements.storage_technologies.storage_technology import (
    StorageTechnology,
)
from zen_creator.utils.attribute import Attribute

_TES_E2P_SOURCE = SourceInformation(
    description=(
        "Energy-to-power ratio bounds from industrial TES practice. "
        "Water tanks: 1–24 h (intraday buffer; tank always has ≥1 h thermal mass). "
        "Steam accumulators: 0.25–4 h (pressure vessel, inherently short-duration)."
    ),
    metadata=MetaData(
        name="industry_TES_e2p",
        title="Industrial TES energy-to-power ratio",
        author=["ZEN Creator"],
        publication="Internal assumption based on Mayer et al. (2024) and industrial practice",
        publication_year=2024,
    ),
)


_TES_COST_SOURCE = SourceInformation(
    description=(
        "Water TES: capex overridden to 1000 EUR/MWh (Mayer2024 reports 0 — no literature "
        "value for cheap water tanks; 1000 EUR/MWh applied as a modeling friction cost). "
        "opex_specific_variable = 1 EUR/GWh (small friction to prevent spurious cycling). "
        "self_discharge = 0.95 (standing thermal loss per time step; Mayer2024 does not "
        "report self-discharge rates, so this internal assumption is used)."
    ),
    metadata=MetaData(
        name="industry_TES_costs",
        title="Industrial TES cost assumptions",
        author=["ZEN Creator"],
        publication="Internal assumption",
        publication_year=2024,
    ),
)


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
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=1000.0, unit="Euro/MWh", source=_TES_COST_SOURCE)
        return attr

    def _set_opex_specific_fixed_energy(self) -> Attribute:
        return Mayer2024Dataset().get_opex_specific_fixed_energy(element=self)

    def _set_opex_specific_variable(self) -> Attribute:
        attr = Attribute("opex_specific_variable", element=self)
        attr.set_data(default_value=1.0, unit="Euro/GWh", source=_TES_COST_SOURCE)
        return attr

    def _set_self_discharge(self) -> Attribute:
        attr = Attribute("self_discharge", element=self)
        attr.set_data(default_value=0.95, unit="1", source=_TES_COST_SOURCE)
        return attr

    def _set_energy_to_power_ratio_min(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_min", element=self)
        attr.set_data(default_value=1.0, unit="h", source=_TES_E2P_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=24.0, unit="h", source=_TES_E2P_SOURCE)
        return attr


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
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=1000.0, unit="Euro/MWh", source=_TES_COST_SOURCE)
        return attr

    def _set_opex_specific_fixed_energy(self) -> Attribute:
        return Mayer2024Dataset().get_opex_specific_fixed_energy(element=self)

    def _set_opex_specific_variable(self) -> Attribute:
        attr = Attribute("opex_specific_variable", element=self)
        attr.set_data(default_value=1.0, unit="Euro/GWh", source=_TES_COST_SOURCE)
        return attr

    def _set_self_discharge(self) -> Attribute:
        attr = Attribute("self_discharge", element=self)
        attr.set_data(default_value=0.95, unit="1", source=_TES_COST_SOURCE)
        return attr

    def _set_energy_to_power_ratio_min(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_min", element=self)
        attr.set_data(default_value=1.0, unit="h", source=_TES_E2P_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=24.0, unit="h", source=_TES_E2P_SOURCE)
        return attr


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

    def _set_opex_specific_variable(self) -> Attribute:
        attr = Attribute("opex_specific_variable", element=self)
        attr.set_data(default_value=1.0, unit="Euro/GWh", source=_TES_COST_SOURCE)
        return attr

    def _set_self_discharge(self) -> Attribute:
        attr = Attribute("self_discharge", element=self)
        attr.set_data(default_value=0.95, unit="1", source=_TES_COST_SOURCE)
        return attr

    def _set_energy_to_power_ratio_min(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_min", element=self)
        attr.set_data(default_value=0.25, unit="h", source=_TES_E2P_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=4.0, unit="h", source=_TES_E2P_SOURCE)
        return attr


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

    def _set_opex_specific_variable(self) -> Attribute:
        attr = Attribute("opex_specific_variable", element=self)
        attr.set_data(default_value=1.0, unit="Euro/GWh", source=_TES_COST_SOURCE)
        return attr

    def _set_self_discharge(self) -> Attribute:
        attr = Attribute("self_discharge", element=self)
        attr.set_data(default_value=0.95, unit="1", source=_TES_COST_SOURCE)
        return attr

    def _set_energy_to_power_ratio_min(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_min", element=self)
        attr.set_data(default_value=0.25, unit="h", source=_TES_E2P_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=4.0, unit="h", source=_TES_E2P_SOURCE)
        return attr
