"""Industry demand-side management (DSM) storage technologies.

Product carriers get a DSM storage that allows the optimizer to shift production
in time. The storages are modeled as perfect (no losses, efficiency=1.0) with an
energy capex of 1.0 EUR/(tonproduct/hour*h) to prevent economically unjustified
over-building while still allowing cost-effective flexibility.

Covered carriers:
  - glass, ceramic, paper, food  (industry_heat sector products)
  - ammonia, clinker, methanol, primary_steel, secondary_steel, olefin
    (existing Crystal Ball carriers; no zen_creator carrier class needed)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.elements.storage_technologies.storage_technology import (
    StorageTechnology,
)
from zen_creator.utils.attribute import Attribute

_DSM_METADATA = MetaData(
    name="industry_DSM",
    title="Industry demand-side management assumption",
    author=["ZEN Creator"],
    publication="Internal assumption",
    publication_year=2024,
)

_DSM_SOURCE = SourceInformation(
    description=(
        "Perfect storage with energy capex of 1.0 EUR/(tonproduct/hour*h) "
        "to allow production time-shifting without economically unjustified builds."
    ),
    metadata=_DSM_METADATA,
)

_DSM_LIFETIME = 50

_DSM_E2P_SOURCE = SourceInformation(
    description=(
        "Maximum energy-to-power ratio (inventory horizon) per product type. "
        "Glass/ceramic/paper/chemicals/metals: ≤1 week (168 h), based on typical "
        "industrial inventory turnover and Mayer et al. (2024) tsc parameter. "
        "Food: ≤2 days (48 h) due to perishability constraints."
    ),
    metadata=_DSM_METADATA,
)

_CAPEX = 1.0
_E2P_MAX_WEEK = 168.0
_E2P_MAX_FOOD = 48.0


class GlassDSM(StorageTechnology):

    name: str = "glass_DSM"

    def __init__(self, model: Model, power_unit: str = "tonproduct/hour"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["glass"], element=self)

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", element=self)
        attr.set_data(default_value=_DSM_LIFETIME, unit="1", source=_DSM_SOURCE)
        return attr

    def _set_capex_specific_storage_energy(self) -> Attribute:
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=_CAPEX, unit="Euro/(tonproduct/hour*h)", source=_DSM_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=_E2P_MAX_WEEK, unit="h", source=_DSM_E2P_SOURCE)
        return attr


class CeramicDSM(StorageTechnology):

    name: str = "ceramic_DSM"

    def __init__(self, model: Model, power_unit: str = "tonproduct/hour"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["ceramic"], element=self)

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", element=self)
        attr.set_data(default_value=_DSM_LIFETIME, unit="1", source=_DSM_SOURCE)
        return attr

    def _set_capex_specific_storage_energy(self) -> Attribute:
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=_CAPEX, unit="Euro/(tonproduct/hour*h)", source=_DSM_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=_E2P_MAX_WEEK, unit="h", source=_DSM_E2P_SOURCE)
        return attr


class PaperDSM(StorageTechnology):

    name: str = "paper_DSM"

    def __init__(self, model: Model, power_unit: str = "tonproduct/hour"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["paper"], element=self)

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", element=self)
        attr.set_data(default_value=_DSM_LIFETIME, unit="1", source=_DSM_SOURCE)
        return attr

    def _set_capex_specific_storage_energy(self) -> Attribute:
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=_CAPEX, unit="Euro/(tonproduct/hour*h)", source=_DSM_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=_E2P_MAX_WEEK, unit="h", source=_DSM_E2P_SOURCE)
        return attr


class FoodDSM(StorageTechnology):

    name: str = "food_DSM"

    def __init__(self, model: Model, power_unit: str = "tonproduct/hour"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["food"], element=self)

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", element=self)
        attr.set_data(default_value=_DSM_LIFETIME, unit="1", source=_DSM_SOURCE)
        return attr

    def _set_capex_specific_storage_energy(self) -> Attribute:
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=_CAPEX, unit="Euro/(tonproduct/hour*h)", source=_DSM_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=_E2P_MAX_FOOD, unit="h", source=_DSM_E2P_SOURCE)
        return attr


# ---------------------------------------------------------------------------
# New DSM techs for existing Crystal Ball carriers (no carrier class needed)
# ---------------------------------------------------------------------------

class AmmoniaDSM(StorageTechnology):

    name: str = "ammonia_DSM"

    def __init__(self, model: Model, power_unit: str = "GW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["ammonia"], element=self)

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", element=self)
        attr.set_data(default_value=_DSM_LIFETIME, unit="1", source=_DSM_SOURCE)
        return attr

    def _set_capex_specific_storage_energy(self) -> Attribute:
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=_CAPEX, unit="Euro/(GW*h)", source=_DSM_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=_E2P_MAX_WEEK, unit="h", source=_DSM_E2P_SOURCE)
        return attr


class ClinkerDSM(StorageTechnology):

    name: str = "clinker_DSM"

    def __init__(self, model: Model, power_unit: str = "tonproduct/hour"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["clinker"], element=self)

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", element=self)
        attr.set_data(default_value=_DSM_LIFETIME, unit="1", source=_DSM_SOURCE)
        return attr

    def _set_capex_specific_storage_energy(self) -> Attribute:
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=_CAPEX, unit="Euro/(tonproduct/hour*h)", source=_DSM_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=_E2P_MAX_WEEK, unit="h", source=_DSM_E2P_SOURCE)
        return attr


class MethanolDSM(StorageTechnology):

    name: str = "methanol_DSM"

    def __init__(self, model: Model, power_unit: str = "GW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["methanol"], element=self)

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", element=self)
        attr.set_data(default_value=_DSM_LIFETIME, unit="1", source=_DSM_SOURCE)
        return attr

    def _set_capex_specific_storage_energy(self) -> Attribute:
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=_CAPEX, unit="Euro/(GW*h)", source=_DSM_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=_E2P_MAX_WEEK, unit="h", source=_DSM_E2P_SOURCE)
        return attr


class PrimarysteelDSM(StorageTechnology):

    name: str = "primary_steel_DSM"

    def __init__(self, model: Model, power_unit: str = "tonproduct/hour"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["primary_steel"], element=self)

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", element=self)
        attr.set_data(default_value=_DSM_LIFETIME, unit="1", source=_DSM_SOURCE)
        return attr

    def _set_capex_specific_storage_energy(self) -> Attribute:
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=_CAPEX, unit="Euro/(tonproduct/hour*h)", source=_DSM_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=_E2P_MAX_WEEK, unit="h", source=_DSM_E2P_SOURCE)
        return attr


class SecondarysteelDSM(StorageTechnology):

    name: str = "secondary_steel_DSM"

    def __init__(self, model: Model, power_unit: str = "tonproduct/hour"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["secondary_steel"], element=self)

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", element=self)
        attr.set_data(default_value=_DSM_LIFETIME, unit="1", source=_DSM_SOURCE)
        return attr

    def _set_capex_specific_storage_energy(self) -> Attribute:
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=_CAPEX, unit="Euro/(tonproduct/hour*h)", source=_DSM_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=_E2P_MAX_WEEK, unit="h", source=_DSM_E2P_SOURCE)
        return attr


class OlefinDSM(StorageTechnology):

    name: str = "olefin_DSM"

    def __init__(self, model: Model, power_unit: str = "tonproduct/hour"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=["olefin"], element=self)

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", element=self)
        attr.set_data(default_value=_DSM_LIFETIME, unit="1", source=_DSM_SOURCE)
        return attr

    def _set_capex_specific_storage_energy(self) -> Attribute:
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(default_value=_CAPEX, unit="Euro/(tonproduct/hour*h)", source=_DSM_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=_E2P_MAX_WEEK, unit="h", source=_DSM_E2P_SOURCE)
        return attr
