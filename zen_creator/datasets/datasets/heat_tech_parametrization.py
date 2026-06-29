"""Dataset for heat supply technology parametrization."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from zen_creator.elements.element import Element

from zen_creator.datasets.datasets._industry_heat_utils import (
    INPUT_DATA,
    build_tech_from_table,
)
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

_HEAT_XLSX = INPUT_DATA / "Parametrization" / "heat_tech_parametrization.xlsx"
_HEAT_SHEET = "heat_techs"

HEAT_CARRIER_NAMES = {
    "0_100": "heat_industry_0_100",
    "100_150": "heat_industry_100_150",
    "150_200": "heat_industry_150_200",
}

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


class HeatTechParametrizationDataset(Dataset[pd.DataFrame]):

    name = "heat_tech_parametrization"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self._tech_dicts: dict[str, dict] = {}

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Industry heat technology parametrization",
            author=["ZEN Creator"],
            publication="Internal parametrization workbook",
            publication_year=2024,
        )

    def _set_path(self) -> Path | None:
        return _HEAT_XLSX

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(description=description, metadata=self.metadata)

    def _get_tech_dict(self, base_tech: str) -> dict:
        if base_tech not in self._tech_dicts:
            self._tech_dicts[base_tech] = build_tech_from_table(_HEAT_XLSX, _HEAT_SHEET, base_tech)
        return self._tech_dicts[base_tech]

    def get_heat_tech_dict(self, base_tech: str, temp_level: str) -> dict:
        data = copy.deepcopy(self._get_tech_dict(base_tech))
        carrier = HEAT_CARRIER_NAMES[temp_level]
        data["reference_carrier"]["default_value"] = [carrier]
        data["output_carrier"]["default_value"] = [carrier]
        return data

    def _extract_numeric(self, data: dict, attr_name: str) -> tuple[float, str | None]:
        entry = data.get(attr_name, {})
        val = entry.get("default_value", 0)
        if val == "inf":
            val = np.inf
        return float(val), entry.get("unit")

    def get_conversion_factor(self, element: Element, base_tech: str, temp_level: str, cop_override: float | None = None) -> Attribute:
        data = self.get_heat_tech_dict(base_tech, temp_level)
        if cop_override is not None:
            for entry in data["conversion_factor"]:
                carrier = next(iter(entry))
                entry[carrier]["default_value"] = round(1.0 / cop_override, 12)
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=element)

    def get_lifetime(self, element: Element, base_tech: str) -> Attribute:
        data = self._get_tech_dict(base_tech)
        val, unit = self._extract_numeric(data, "lifetime")
        attr = Attribute("lifetime", element=element)
        attr.set_data(default_value=val, unit=unit, source=self._source_info(f"Lifetime for {base_tech} from heat_tech_parametrization.xlsx."))
        return attr

    def get_capex_specific_conversion(self, element: Element, base_tech: str) -> Attribute:
        data = self._get_tech_dict(base_tech)
        val, unit = self._extract_numeric(data, "capex_specific_conversion")
        attr = Attribute("capex_specific_conversion", element=element)
        attr.set_data(default_value=val, unit=unit, source=self._source_info(f"CAPEX for {base_tech}."))
        return attr

    def get_opex_specific_fixed(self, element: Element, base_tech: str) -> Attribute:
        data = self._get_tech_dict(base_tech)
        val, unit = self._extract_numeric(data, "opex_specific_fixed")
        attr = Attribute("opex_specific_fixed", element=element)
        attr.set_data(default_value=val, unit=unit, source=self._source_info(f"Fixed OPEX for {base_tech}."))
        return attr

    def get_opex_specific_variable(self, element: Element, base_tech: str) -> Attribute:
        data = self._get_tech_dict(base_tech)
        val, unit = self._extract_numeric(data, "opex_specific_variable")
        attr = Attribute("opex_specific_variable", element=element)
        attr.set_data(default_value=val, unit=unit, source=self._source_info(f"Variable OPEX for {base_tech}."))
        return attr

    def get_min_load(self, element: Element, base_tech: str) -> Attribute:
        data = self._get_tech_dict(base_tech)
        val, unit = self._extract_numeric(data, "min_load")
        attr = Attribute("min_load", element=element)
        attr.set_data(default_value=val, unit=unit, source=self._source_info(f"Min load for {base_tech}."))
        return attr

    def get_max_load(self, element: Element, base_tech: str) -> Attribute:
        data = self._get_tech_dict(base_tech)
        val, unit = self._extract_numeric(data, "max_load")
        attr = Attribute("max_load", element=element)
        attr.set_data(default_value=val, unit=unit, source=self._source_info(f"Max load for {base_tech}."))
        return attr

    def get_carbon_intensity_technology(self, element: Element, base_tech: str) -> Attribute:
        data = self._get_tech_dict(base_tech)
        val, unit = self._extract_numeric(data, "carbon_intensity_technology")
        attr = Attribute("carbon_intensity_technology", element=element)
        attr.set_data(default_value=val, unit=unit, source=self._source_info(f"Carbon intensity for {base_tech}."))
        return attr

    def get_max_diffusion_rate(self, element: Element, base_tech: str) -> Attribute:
        data = self._get_tech_dict(base_tech)
        val, unit = self._extract_numeric(data, "max_diffusion_rate")
        attr = Attribute("max_diffusion_rate", element=element)
        attr.set_data(default_value=val, unit=unit, source=self._source_info(f"Max diffusion rate for {base_tech}."))
        return attr
