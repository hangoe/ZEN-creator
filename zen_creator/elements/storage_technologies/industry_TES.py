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

_TES_EFFICIENCY_SOURCE = SourceInformation(
    description=(
        "efficiency_charge = efficiency_discharge = 1.0 (no charge/discharge losses) "
        "for all TES technologies, v7.0 onward — all standing/thermal losses are "
        "represented via self_discharge instead of splitting them across charge and "
        "discharge. Replaces the previous sqrt(round-trip efficiency) values derived "
        "from Mayer2024 Table 3."
    ),
    metadata=MetaData(
        name="industry_TES_efficiency",
        title="Industrial TES charge/discharge efficiency assumption",
        author=["ZEN Creator"],
        publication="Internal assumption",
        publication_year=2026,
    ),
)


class _IndustryTESTechnology:
    """Shared logic for industry thermal energy storage (TES) technologies,
    mixed in alongside `StorageTechnology` by every concrete class below
    (rather than subclassed directly) so it does not add an extra level to
    the MRO between the concrete class and `StorageTechnology` -- same
    reasoning as `_IndustryDSMTechnology` in industry_DSM.py.

    Subclasses set `_carrier_name` (the reference carrier) and the
    `_e2p_min`/`_e2p_max` energy-to-power ratio bounds; every other attribute
    (lifetime/capex/opex from Mayer2024, cost/efficiency assumptions) is
    identical across all three temperature bands.
    """

    _carrier_name: str
    _e2p_min: float
    _e2p_max: float

    def __init__(self, model: Model, power_unit: str = "MW"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=[self._carrier_name], element=self)

    def _set_lifetime(self) -> Attribute:
        return Mayer2024Dataset().get_lifetime(element=self)

    def _set_efficiency_charge(self) -> Attribute:
        attr = Attribute("efficiency_charge", element=self)
        attr.set_data(default_value=1.0, unit="1", source=_TES_EFFICIENCY_SOURCE)
        return attr

    def _set_efficiency_discharge(self) -> Attribute:
        attr = Attribute("efficiency_discharge", element=self)
        attr.set_data(default_value=1.0, unit="1", source=_TES_EFFICIENCY_SOURCE)
        return attr

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
        attr.set_data(default_value=self._e2p_min, unit="h", source=_TES_E2P_SOURCE)
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(default_value=self._e2p_max, unit="h", source=_TES_E2P_SOURCE)
        return attr


class IndustryTESWater0100(_IndustryTESTechnology, StorageTechnology):
    """Hot-water thermal storage tank for the 0-100C band (1-24h duration)."""

    name: str = "industry_TES_water_0_100"
    _carrier_name = "heat_industry_0_100"
    _e2p_min = 1.0
    _e2p_max = 24.0


class IndustryTESWater100150(_IndustryTESTechnology, StorageTechnology):
    """Hot-water thermal storage tank for the 100-150C band (1-24h duration)."""

    name: str = "industry_TES_water_100_150"
    _carrier_name = "heat_industry_100_150"
    _e2p_min = 1.0
    _e2p_max = 24.0


class IndustryTESSteam150200(_IndustryTESTechnology, StorageTechnology):
    """Steam accumulator for the 150-200C band (0.25-4h duration -- shorter
    than the water tanks, being an inherently short-duration pressure vessel)."""

    name: str = "industry_TES_steam_150_200"
    _carrier_name = "heat_industry_150_200"
    _e2p_min = 0.25
    _e2p_max = 4.0
