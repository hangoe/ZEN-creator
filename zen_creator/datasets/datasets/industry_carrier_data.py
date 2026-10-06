"""Dataset for industry carrier attributes (product carriers glass/ceramic/paper/food,
energy carriers heat_industry_*/fuel_to_kiln). All carriers use the plain
PRODUCT_CARRIER_TEMPLATE/ENERGY_CARRIER_TEMPLATE defaults from _industry_heat_utils.py --
no carrier-specific overrides exist."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from zen_creator.elements.element import Element

from zen_creator.datasets.datasets._industry_heat_utils import (
    ENERGY_CARRIER_TEMPLATE,
    PRODUCT_CARRIER_TEMPLATE,
)
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

_PRODUCT_CARRIERS = {"glass", "ceramic", "paper", "food"}


class IndustryCarrierDataset(Dataset[pd.DataFrame]):

    name = "industry_carrier_data"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self._carrier_dicts: dict[str, dict] = {}

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Industry carrier parametrization",
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

    def get_carrier_dict(self, carrier_name: str) -> dict:
        if carrier_name in self._carrier_dicts:
            return self._carrier_dicts[carrier_name]
        if carrier_name in _PRODUCT_CARRIERS:
            data = copy.deepcopy(PRODUCT_CARRIER_TEMPLATE)
        else:
            data = copy.deepcopy(ENERGY_CARRIER_TEMPLATE)
        self._carrier_dicts[carrier_name] = data
        return data

    def get_carrier_attr(self, element: Element, carrier_name: str, attr_name: str) -> Attribute:
        data = self.get_carrier_dict(carrier_name)
        if attr_name not in data:
            return getattr(element, f"_{attr_name}")
        entry = data[attr_name]
        val = entry.get("default_value", 0)
        unit = entry.get("unit")
        if val == "inf":
            val = np.inf
        attr = Attribute(attr_name, element=element)
        attr.set_data(
            default_value=float(val) if isinstance(val, (int, float, np.integer, np.floating)) else val,
            unit=unit,
            source=self._source_info(f"{attr_name} for carrier {carrier_name} (template default)."),
        )
        return attr
