"""Dataset for boiler and heat pump capacity from Eurostat."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from zen_creator.elements.element import Element

from zen_creator.datasets.datasets._industry_heat_utils import (
    INPUT_DATA,
    BOILER_LIFETIMES,
    biomass_boiler_capacity_existing_df,
    electrode_boiler_capacity_existing_df,
    heat_pump_capacity_existing_df,
    natural_gas_boiler_capacity_existing_df,
    oil_boiler_capacity_existing_df,
)
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

_EUROSTAT_FILE = INPUT_DATA / "Eurostat" / "Eurostat_EB_GWh.xlsx"


class EurostatBoilerDataset(Dataset[pd.DataFrame]):

    name = "eurostat_boiler"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Eurostat energy balance — gross heat production",
            author=["Eurostat"],
            publication="Eurostat Energy Balance",
            publication_year=2024,
        )

    def _set_path(self) -> Path | None:
        return _EUROSTAT_FILE

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(description=description, metadata=self.metadata)

    def get_biomass_boiler_capacity(self, element: Element, year: int, year_construction: int) -> Attribute:
        df = biomass_boiler_capacity_existing_df(year, lifetime=BOILER_LIFETIMES["biomass_boiler_industry"], year_construction=year_construction)
        attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=element)
        attr.set_data(df=df.set_index(["node", "year_construction"]), source=self._source_info("Biomass boiler capacity from Eurostat gross heat production."))
        return attr

    def get_natural_gas_boiler_capacity(self, element: Element, year: int, year_construction: int) -> Attribute:
        df = natural_gas_boiler_capacity_existing_df(year, lifetime=BOILER_LIFETIMES["natural_gas_boiler_industry"], year_construction=year_construction)
        attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=element)
        attr.set_data(df=df.set_index(["node", "year_construction"]), source=self._source_info("Natural gas boiler capacity from Eurostat gross heat production."))
        return attr

    def get_electrode_boiler_capacity(self, element: Element, year: int, year_construction: int) -> Attribute:
        df = electrode_boiler_capacity_existing_df(year, lifetime=BOILER_LIFETIMES["electrode_boiler_industry"], year_construction=year_construction)
        attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=element)
        attr.set_data(df=df.set_index(["node", "year_construction"]), source=self._source_info("Electrode boiler capacity from Eurostat gross heat production."))
        return attr

    def get_oil_boiler_capacity(self, element: Element, year: int, year_construction: int) -> Attribute:
        df = oil_boiler_capacity_existing_df(year, lifetime=BOILER_LIFETIMES["oil_boiler_industry"], year_construction=year_construction)
        attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=element)
        attr.set_data(df=df.set_index(["node", "year_construction"]), source=self._source_info("Oil boiler capacity from Eurostat gross heat production."))
        return attr

    def get_heat_pump_capacity(self, element: Element, year_construction: int) -> Attribute:
        df = heat_pump_capacity_existing_df()
        attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=element)
        attr.set_data(df=df.set_index(["node", "year_construction"]), source=self._source_info("Industrial heat pump capacity (zero — no deployed industrial HP capacity)."))
        return attr
