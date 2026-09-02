"""Dataset for food capacity and demand from FAOSTAT."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from zen_creator.elements.element import Element

from zen_creator.datasets.datasets._industry_heat_utils import (
    INPUT_DATA,
    SECTOR_LIFETIMES,
    food_capacity_existing_df,
)
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

_FAOSTAT_DIR = INPUT_DATA / "FAOSTAT"


class FaostatFoodDataset(Dataset[pd.DataFrame]):

    name = "faostat_food"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="FAOSTAT food production and feed data",
            author=["Food and Agriculture Organization of the United Nations"],
            publication="FAOSTAT",
            publication_year=2024,
        )

    def _set_path(self) -> Path | None:
        return _FAOSTAT_DIR

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(description=description, metadata=self.metadata)

    def get_food_capacity_existing(self, element: Element, year: int, year_construction: int) -> Attribute:
        df = food_capacity_existing_df(year, lifetime=SECTOR_LIFETIMES["food"], year_construction=year_construction)
        attr = Attribute("capacity_existing", default_value=0.0, unit="tonproduct/hour", element=element)
        attr.set_data(
            df=df.set_index(["node", "year_construction"]),
            source=self._source_info("Food production capacity from FAOSTAT."),
        )
        return attr

    def get_food_demand_as_capacity_existing(self, element: Element, year: int) -> Attribute:
        """Return food demand equal to capacity_existing values (v4.2+ assumption)."""
        df = food_capacity_existing_df(year)
        demand_df = df[["node", "capacity_existing"]].rename(columns={"capacity_existing": "demand"})
        attr = Attribute("demand", default_value=0.0, unit="tonproduct/hour", element=element)
        attr.set_data(
            df=demand_df.set_index("node")["demand"],
            source=self._source_info("Food demand set equal to capacity_existing (v4.2 assumption)."),
        )
        return attr
