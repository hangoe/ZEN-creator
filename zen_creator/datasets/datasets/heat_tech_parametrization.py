"""Dataset for heat supply technology parametrization."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from zen_creator.elements.element import Element

from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

# COP = 0.5 × COP_Carnot, T_hot = midpoint of supply temperature range
# Source i: waste heat at T_cold = 50°C (Bever2024, Agora_IGE2023)
HP_COP_WASTE_HEAT = {
    "0_100":   round(0.5 * 348.15 / (348.15 - 323.15), 4),  # T_hot=75°C  → 6.963
    "100_150": round(0.5 * 398.15 / (398.15 - 323.15), 4),  # T_hot=125°C → 2.654
    "150_200": round(0.5 * 448.15 / (448.15 - 323.15), 4),  # T_hot=175°C → 1.793
}
# Source ii: water (rivers, groundwater, seawater) at T_cold = 15°C (Agora_IGE2023)
HP_COP_WATER = {
    "0_100":   round(0.5 * 348.15 / (348.15 - 288.15), 4),  # T_hot=75°C  → 2.901
    "100_150": round(0.5 * 398.15 / (398.15 - 288.15), 4),  # T_hot=125°C → 1.810
    "150_200": round(0.5 * 448.15 / (448.15 - 288.15), 4),  # T_hot=175°C → 1.400
}

# Input carrier per heat tech (reference/output carrier is always heat_low_temp_industry).
HEAT_TECH_INPUT_CARRIER: dict[str, str] = {
    "heat_pump_industry": "electricity",
    "electrode_boiler_industry": "electricity",
    "natural_gas_boiler_industry": "natural_gas",
    "biomass_boiler_industry": "biomass",
    "oil_boiler_industry": "oil",
    "coal_boiler_industry": "hard_coal",
    "waste_boiler_industry": "waste",
}

# conversion_factor (input_carrier per unit heat output), "similar to existing techs" in
# Crystal Ball (source: Crystal_Ball, per former heat_tech_parametrization.xlsx).
# heat_pump_industry's value here is only a placeholder -- get_conversion_factor always
# overrides it per-node/temperature-level via cop_override at every call site.
HEAT_TECH_CONVERSION_FACTOR: dict[str, float] = {
    "heat_pump_industry": 0.3305785123966942,
    "electrode_boiler_industry": 1,
    "natural_gas_boiler_industry": 1.005025125628141,
    "biomass_boiler_industry": 1.197604790419162,
    "oil_boiler_industry": 1.005025125628141,
    "coal_boiler_industry": 1.005025125628141,
    "waste_boiler_industry": 1.005025125628141,
}

# carbon_intensity_technology is 0 for every heat tech: combustion CO2 is carried on the
# fuel carrier (natural_gas/biomass/etc.), not on the conversion tech.
CARBON_INTENSITY_TECHNOLOGY = 0
MAX_DIFFUSION_RATE = 0.29


class HeatTechParametrizationDataset(Dataset[pd.DataFrame]):

    name = "heat_tech_parametrization"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Industry heat technology parametrization",
            author=["ZEN Creator"],
            publication="Internal parametrization workbook",
            publication_year=2024,
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(description=description, metadata=self.metadata)

    def get_conversion_factor(self, element: Element, base_tech: str, temp_level: str, cop_override: float | None = None) -> Attribute:
        input_carrier = HEAT_TECH_INPUT_CARRIER[base_tech]
        value = HEAT_TECH_CONVERSION_FACTOR[base_tech] if cop_override is None else round(1.0 / cop_override, 12)
        conversion_factor = [{input_carrier: {"default_value": value, "unit": "GW/GW"}}]
        return Attribute("conversion_factor", default_value=conversion_factor, element=element)

    def get_carbon_intensity_technology(self, element: Element, base_tech: str) -> Attribute:
        attr = Attribute("carbon_intensity_technology", element=element)
        attr.set_data(
            default_value=CARBON_INTENSITY_TECHNOLOGY,
            unit="kilotons/GWh",
            source=self._source_info(f"Carbon intensity for {base_tech} (combustion CO2 carried on fuel carrier)."),
        )
        return attr

    def get_max_diffusion_rate(self, element: Element, base_tech: str) -> Attribute:
        attr = Attribute("max_diffusion_rate", element=element)
        attr.set_data(
            default_value=MAX_DIFFUSION_RATE,
            unit="1",
            source=self._source_info(f"Max diffusion rate for {base_tech}."),
        )
        return attr
