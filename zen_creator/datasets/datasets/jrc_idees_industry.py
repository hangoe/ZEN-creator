"""Dataset for industry capacity and demand from JRC-IDEES-2023."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from zen_creator.elements.element import Element

from zen_creator.datasets.datasets._industry_heat_utils import (
    INPUT_DATA,
    OPERATING_HOURS,
    SECTOR_LIFETIMES,
    capacity_existing_df,
    ceramic_demand_from_fec_df,
    industry_demand_df,
)
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

_IDEES_DIR = INPUT_DATA / "JRC-IDEES-2023"
_BAT_PAPER_CSV = INPUT_DATA / "JRC-BAT" / "JRC_BAT_Paper2014_Table1_2.csv"


class JrcIdeesIndustryDataset(Dataset[pd.DataFrame]):

    name = "jrc_idees_industry"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="JRC-IDEES-2023 Industry dataset",
            author=["European Commission, Joint Research Centre"],
            publication="JRC-IDEES-2023",
            publication_year=2023,
        )

    def _set_path(self) -> Path | None:
        if _IDEES_DIR.exists():
            return _IDEES_DIR
        return None

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(description=description, metadata=self.metadata)

    def get_capacity_existing(self, element: Element, sector: str, year: int, year_construction: int) -> Attribute:
        lifetime = SECTOR_LIFETIMES[sector]
        df = capacity_existing_df(sector, year, lifetime=lifetime, year_construction=year_construction)
        if sector == "paper":
            bat = pd.read_csv(_BAT_PAPER_CSV)
            bat_nodes = {"Switzerland": "CH", "Norway": "NO", "United Kingdom": "UK"}
            bat = bat[bat["country"].isin(bat_nodes)]
            for _, row in bat.iterrows():
                node = bat_nodes[row["country"]]
                total_cap = row["consumption_1000t_2008"] * 1000 / 8000
                df.loc[df["node"] == node, "capacity_existing"] = total_cap / lifetime
        attr = Attribute("capacity_existing", default_value=0.0, unit="tonproduct/hour", element=element)
        attr.set_data(
            df=df.set_index(["node", "year_construction"]),
            source=self._source_info(f"Capacity existing for {sector} from JRC-IDEES-2023."),
        )
        return attr

    def get_demand_as_capacity_existing(self, element: Element, sector: str, year: int) -> Attribute:
        """Return demand equal to capacity_existing values (v4.2+ assumption)."""
        df = capacity_existing_df(sector, year)
        demand_df = df[["node", "capacity_existing"]].rename(columns={"capacity_existing": "demand"})
        if sector == "paper":
            bat = pd.read_csv(_BAT_PAPER_CSV)
            bat_nodes = {"Switzerland": "CH", "Norway": "NO", "United Kingdom": "UK"}
            bat = bat[bat["country"].isin(bat_nodes)]
            for _, row in bat.iterrows():
                node = bat_nodes[row["country"]]
                demand_df.loc[demand_df["node"] == node, "demand"] = row["consumption_1000t_2008"] * 1000 / OPERATING_HOURS
        attr = Attribute("demand", default_value=0.0, unit="tonproduct/hour", element=element)
        attr.set_data(
            df=demand_df.set_index("node")["demand"],
            source=self._source_info(f"Demand for {sector} set equal to capacity_existing (v4.2 assumption)."),
        )
        return attr

    def get_demand(self, element: Element, sector: str, year: int) -> Attribute:
        df = industry_demand_df(sector, year)
        if sector == "paper":
            bat = pd.read_csv(_BAT_PAPER_CSV)
            bat_nodes = {"Switzerland": "CH", "Norway": "NO", "United Kingdom": "UK"}
            bat = bat[bat["country"].isin(bat_nodes)]
            for _, row in bat.iterrows():
                node = bat_nodes[row["country"]]
                df.loc[df["node"] == node, "demand"] = row["consumption_1000t_2008"] * 1000 / 8760
        attr = Attribute("demand", default_value=0.0, unit="tonproduct/hour", element=element)
        attr.set_data(
            df=df.set_index("node")["demand"],
            source=self._source_info(f"Demand for {sector} from JRC-IDEES-2023 physical output."),
        )
        return attr

    def get_ceramic_demand_as_capacity_existing(self, element: Element, year: int) -> Attribute:
        """Ceramic demand set equal to capacity_existing (FEC-derived production volume)."""
        df = ceramic_demand_from_fec_df(year)
        demand_series = df.set_index("node")["kt_yr"] * 1000 / OPERATING_HOURS
        attr = Attribute("demand", default_value=0.0, unit="tonproduct/hour", element=element)
        attr.set_data(
            df=demand_series,
            source=self._source_info(
                "Ceramic demand from JRC-IDEES-2023 NMM_fec thermal FEC "
                "(kiln/furnace rows) ÷ Rehfeldt-2017 weighted specific energy, "
                "set equal to capacity_existing."
            ),
        )
        return attr

    def get_ceramic_capacity_from_fec(self, element: Element, year: int, year_construction: int) -> Attribute:
        """Ceramic capacity_existing from JRC-IDEES thermal FEC ÷ Rehfeldt weighted specific energy (v4.3)."""
        df = ceramic_demand_from_fec_df(year)
        lifetime = SECTOR_LIFETIMES["ceramic"]
        cap_per_yr = df.set_index("node")["kt_yr"] * 1000 / OPERATING_HOURS / lifetime
        rows = [
            {"node": node, "year_construction": yc, "capacity_existing": cap}
            for node, cap in cap_per_yr.items()
            for yc in range(year_construction - lifetime + 1, year_construction + 1)
        ]
        result_df = pd.DataFrame(rows)
        attr = Attribute("capacity_existing", default_value=0.0, unit="tonproduct/hour", element=element)
        attr.set_data(
            df=result_df.set_index(["node", "year_construction"])["capacity_existing"],
            source=self._source_info(
                "Ceramic capacity_existing from JRC-IDEES-2023 NMM_fec thermal FEC "
                "(kiln/furnace rows) ÷ Rehfeldt-2017 weighted specific energy; "
                "capacity set equal to FEC-derived production volume (v4.3)."
            ),
        )
        return attr
