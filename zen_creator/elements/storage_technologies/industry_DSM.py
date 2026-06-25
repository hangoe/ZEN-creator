"""Industry demand-side management (DSM) storage technologies.

Each product carrier (glass, ceramic, paper, food) gets a DSM storage that
allows the optimizer to shift production in time. The storages are modeled
as perfect (no losses, efficiency=1.0) with a minimal energy capex of
0.01 EUR/MWh to prevent unconstrained builds.
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
        "Perfect storage with minimal capex (0.01 EUR/(tonproduct/hour*h)) "
        "to allow production time-shifting without unconstrained builds."
    ),
    metadata=_DSM_METADATA,
)

_DSM_LIFETIME = 50


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
        attr.set_data(
            default_value=0.01,
            unit="Euro/(tonproduct/hour*h)",
            source=_DSM_SOURCE,
        )
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
        attr.set_data(
            default_value=0.01,
            unit="Euro/(tonproduct/hour*h)",
            source=_DSM_SOURCE,
        )
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
        attr.set_data(
            default_value=0.01,
            unit="Euro/(tonproduct/hour*h)",
            source=_DSM_SOURCE,
        )
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
        attr.set_data(
            default_value=0.01,
            unit="Euro/(tonproduct/hour*h)",
            source=_DSM_SOURCE,
        )
        return attr
