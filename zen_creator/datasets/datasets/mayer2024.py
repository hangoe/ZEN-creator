from pathlib import Path

import pandas as pd

from zen_creator.elements.element import Element
from zen_creator.utils.attribute import Attribute

from .dataset import Dataset
from .metadata import MetaData, SourceInformation

_INPUT_DATA = Path(__file__).resolve().parents[3] / "input_data"

TECH_NAME_MAP = {
    "industry_TES_water_0_100": "water tank",
    "industry_TES_water_100_150": "water tank",
    "industry_TES_steam_150_200": "steam accumulator",
}


class Mayer2024Dataset(Dataset[pd.DataFrame]):

    name = "mayer2024"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Review of thermal energy storage technologies for"
                " industrial process heat"
            ),
            author=["Mayer, M.J."],
            publication="Renewable and Sustainable Energy Reviews",
            publication_year=2024,
        )

    def _set_path(self) -> Path | None:
        if self.source_path is not None:
            p = Path(self.source_path) / "Mayer2024" / "Mayer2024_Table3.csv"
            if p.exists():
                return p
        return _INPUT_DATA / "Mayer2024" / "Mayer2024_Table3.csv"

    def _set_data(self) -> pd.DataFrame:
        return pd.read_csv(self.path, index_col="technology")

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(description=description, metadata=self.metadata)

    # attr_name -> (CSV column, description noun)
    _COST_ATTRS: dict[str, tuple[str, str]] = {
        "capex_specific_storage_energy": ("invest_cost_EUR_kWh", "Investment cost"),
        "opex_specific_fixed_energy": ("fixed_OaM_cost_EUR_kWh", "Fixed O&M cost"),
    }

    def _get_cost_attr(self, element: Element, attr_name: str) -> Attribute:
        csv_name = TECH_NAME_MAP[element.name]
        column, noun = self._COST_ATTRS[attr_name]
        cost_eur_mwh = float(self.data.at[csv_name, column]) * 1000.0
        attr = Attribute(attr_name, element=element)
        attr.set_data(
            default_value=cost_eur_mwh,
            unit="Euro/MWh",
            source=self._source_info(f"{noun} from Mayer2024 Table 3, converted from EUR/kWh to EUR/MWh."),
        )
        return attr

    def get_capex_specific_storage_energy(self, element: Element) -> Attribute:
        return self._get_cost_attr(element, "capex_specific_storage_energy")

    def get_opex_specific_fixed_energy(self, element: Element) -> Attribute:
        return self._get_cost_attr(element, "opex_specific_fixed_energy")

    def get_lifetime(self, element: Element) -> Attribute:
        csv_name = TECH_NAME_MAP[element.name]
        lifetime = float(self.data.at[csv_name, "lifetime_years"])
        attr = Attribute("lifetime", element=element)
        attr.set_data(
            default_value=lifetime,
            unit="1",
            source=self._source_info("Lifetime from Mayer2024 Table 3."),
        )
        return attr
