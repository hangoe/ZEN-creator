"""Dataset for industry heat pump / boiler cost & efficiency parametrization,
sourced from the Danish Energy Agency "Technology Data for Industrial Process
Heat" catalogue (input_data/DanishEnergyAgency/).
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from zen_creator.elements.element import Element

from zen_creator.datasets.datasets._industry_heat_utils import INPUT_DATA
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

_DEA_XLSX = INPUT_DATA / "DanishEnergyAgency" / "technology_data_for_industrial_process_heat.xlsx"
_DEA_SHEET = "alldata_flat"

# Which DEA technology sheet backs each model tech. Both heat pump tiers below
# 150°C output use "2.a High temp. hp Up to 125C"/"2.b .. Up to 150" as a cost
# proxy; the 150-200°C band reuses 2.b since DEA has no higher tier. See
# ASSUMPTIONS.md ("New in sector v7.0").
DEA_SHEET_FOR_TECH = {
    "heat_pump_industry_0_100": "2.a High temp. hp Up to 125C",
    "heat_pump_industry_100_200": "2.b High temp. hp Up to 150",
    "electrode_boiler_industry": "5.1a Electric boiler steam",
    "natural_gas_boiler_industry": "6.1 Boiler, gas and oil",
    "oil_boiler_industry": "6.1 Boiler, gas and oil",
    "biomass_boiler_industry": "6.2 Boiler, biomass",
}

BOILER_TECHS = {
    "electrode_boiler_industry", "natural_gas_boiler_industry",
    "oil_boiler_industry", "biomass_boiler_industry",
}

# DEA's `par` label text isn't consistent across sheets (extra whitespace,
# "from last update in 2019" suffixes) — map explicitly per sheet.
_CAPEX_LABEL = {
    "2.a High temp. hp Up to 125C": "Nominal investment (*total) [MEUR/MW]",
    "2.b High temp. hp Up to 150": "Nominal investment (*total) [MEUR/MW]",
    "5.1a Electric boiler steam": "Nominal investment [M€/MW]",
    "6.1 Boiler, gas and oil": "Nominal investment (*total) [MEUR/MW]",
    "6.2 Boiler, biomass": "Nominal investment (*total) [MEUR/MW]",
}
_OPEX_FIXED_LABEL = {
    "2.a High temp. hp Up to 125C": "Fixed O&M  [EUR/MW_y]",
    "2.b High temp. hp Up to 150": "Fixed O&M  [EUR/MW_y], from last update in 2019",
    "5.1a Electric boiler steam": "Fixed O&M [€/MJ/s/year]",
    "6.1 Boiler, gas and oil": "Fixed O&M  [EUR/MW_y]",
    "6.2 Boiler, biomass": "Fixed O&M  [EUR/MW_y]",
}
_OPEX_VARIABLE_LABEL = {
    "2.a High temp. hp Up to 125C": "Variable O&M [EUR/MWh]",
    "2.b High temp. hp Up to 150": "Variable O&M [EUR/MWh], from last update in 2019",
    "5.1a Electric boiler steam": "Variable O&M [€/MWh]",
    "6.1 Boiler, gas and oil": "Variable O&M [EUR/MWh]",
    "6.2 Boiler, biomass": "Variable O&M [EUR/MWh]",
}
_LIFETIME_LABEL = "Technical lifetime [years]"
_EFFICIENCY_LABEL = "Total efficiency, net [%], nominel load"

# capex/opex_fixed source units are all "M€/MW"-like or "EUR/MW_y"-like across
# the sheets used here (MJ/s == MW), so a single conversion factor applies.
_CAPEX_MEUR_PER_MW_TO_EUR_PER_KW = 1000.0
_OPEX_FIXED_EUR_PER_MW_Y_TO_EUR_PER_KW_Y = 1 / 1000.0

MODEL_FIRST_YEAR = 2022
MODEL_LAST_YEAR = 2050


@functools.lru_cache(maxsize=1)
def _load_alldata_flat() -> pd.DataFrame:
    return pd.read_excel(_DEA_XLSX, sheet_name=_DEA_SHEET)


def _year_values(sheet: str, label: str) -> dict[int, float]:
    """DEA {year: value} pairs for a given sheet/par label, central estimate."""
    df = _load_alldata_flat()
    rows = df[(df["ws"] == sheet) & (df["par"] == label) & (df["est"] == "ctrl")]
    if rows.empty:
        raise ValueError(f"No DEA data found for sheet={sheet!r}, par={label!r}")
    return dict(zip(rows["year"], rows["val"]))


def _interpolate_to_model_years(year_values: dict[int, float]) -> pd.Series:
    """Interpolate DEA's sparse sample years onto every calendar year in the
    model horizon, holding flat before the first and after the last DEA year.
    """
    known_years = sorted(year_values)
    known_vals = [year_values[y] for y in known_years]
    model_years = list(range(MODEL_FIRST_YEAR, MODEL_LAST_YEAR + 1))
    interpolated = np.interp(model_years, known_years, known_vals)
    return pd.Series(interpolated, index=pd.Index(model_years, name="year"))


class DeaIndustrialHeatDataset(Dataset[pd.DataFrame]):

    name = "dea_industrial_heat"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Technology Data for Industrial Process Heat",
            author=["Danish Energy Agency"],
            publication="Technology Data for Industrial Process Heat",
            publication_year=2026,
        )

    def _set_path(self) -> Path | None:
        return _DEA_XLSX

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(description=description, metadata=self.metadata)

    def get_lifetime(self, element: Element, tech: str) -> Attribute:
        sheet = DEA_SHEET_FOR_TECH[tech]
        val = _year_values(sheet, _LIFETIME_LABEL)[2025]
        attr = Attribute("lifetime", element=element)
        attr.set_data(default_value=val, unit="1", source=self._source_info(f"Technical lifetime for {tech} from DEA sheet {sheet!r}."))
        return attr

    def get_capex_specific_conversion(self, element: Element, tech: str) -> Attribute:
        sheet = DEA_SHEET_FOR_TECH[tech]
        year_values = {y: v * _CAPEX_MEUR_PER_MW_TO_EUR_PER_KW for y, v in _year_values(sheet, _CAPEX_LABEL[sheet]).items()}
        series = _interpolate_to_model_years(year_values)
        attr = Attribute("capex_specific_conversion", element=element)
        attr.set_data(
            default_value=float(series.loc[MODEL_FIRST_YEAR]), unit="Euro/kW",
            df=series.to_frame("capex_specific_conversion"),
            source=self._source_info(f"Nominal investment for {tech} from DEA sheet {sheet!r}, interpolated over {MODEL_FIRST_YEAR}-{MODEL_LAST_YEAR}."),
        )
        return attr

    def get_opex_specific_fixed(self, element: Element, tech: str) -> Attribute:
        sheet = DEA_SHEET_FOR_TECH[tech]
        year_values = {y: v * _OPEX_FIXED_EUR_PER_MW_Y_TO_EUR_PER_KW_Y for y, v in _year_values(sheet, _OPEX_FIXED_LABEL[sheet]).items()}
        series = _interpolate_to_model_years(year_values)
        attr = Attribute("opex_specific_fixed", element=element)
        attr.set_data(
            default_value=float(series.loc[MODEL_FIRST_YEAR]), unit="Euro/kW",
            df=series.to_frame("opex_specific_fixed"),
            source=self._source_info(f"Fixed O&M for {tech} from DEA sheet {sheet!r}, interpolated over {MODEL_FIRST_YEAR}-{MODEL_LAST_YEAR}."),
        )
        return attr

    def get_opex_specific_variable(self, element: Element, tech: str) -> Attribute:
        sheet = DEA_SHEET_FOR_TECH[tech]
        year_values = _year_values(sheet, _OPEX_VARIABLE_LABEL[sheet])
        series = _interpolate_to_model_years(year_values)
        attr = Attribute("opex_specific_variable", element=element)
        attr.set_data(
            default_value=float(series.loc[MODEL_FIRST_YEAR]), unit="Euro/MWh",
            df=series.to_frame("opex_specific_variable"),
            source=self._source_info(f"Variable O&M for {tech} from DEA sheet {sheet!r}, interpolated over {MODEL_FIRST_YEAR}-{MODEL_LAST_YEAR}."),
        )
        return attr

    def get_conversion_factor(self, element: Element, tech: str, input_carrier: str) -> Attribute:
        """Boiler efficiency only — heat pump COP stays on the Carnot formula."""
        if tech not in BOILER_TECHS:
            raise ValueError(f"DEA conversion_factor is only defined for boilers, got {tech!r}.")
        sheet = DEA_SHEET_FOR_TECH[tech]
        efficiency = _year_values(sheet, _EFFICIENCY_LABEL)[2025]
        conversion_factor = round(1.0 / efficiency, 12)
        attr = Attribute("conversion_factor", element=element)
        attr.set_data(
            default_value=[{input_carrier: {"default_value": conversion_factor, "unit": "GW/GW"}}],
            source=self._source_info(f"Net efficiency for {tech} from DEA sheet {sheet!r} ({efficiency:.0%})."),
        )
        return attr
