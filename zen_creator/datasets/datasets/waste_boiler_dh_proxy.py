"""Cost/efficiency proxy for waste_boiler_industry.

No Danish Energy Agency sheet exists for an industrial waste boiler (unlike
coal — see dea_industrial_heat.py, "6.3 Boiler, coal"). In its absence, this
reuses the Crystal Ball base model's own waste_boiler_DH technology as a
district-heating proxy — the same kind of approximation already accepted for
the Eurostat-derived fuel-mix shares themselves (see ASSUMPTIONS.md, "Boiler
(industry) capacity").

Values are a frozen snapshot of waste_boiler_DH's attributes.json from the
Crystal Ball base model (read 2026-08-05); zen_creator has no live read access
to that external base model's technology definitions during sector-dataset
construction (only `Model.from_existing()` in my_scripts/my_model.py loads it,
after all zen_creator datasets have already been built), so these are
hardcoded here rather than read at build time.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from zen_creator.elements.element import Element

from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

# waste_boiler_DH/attributes.json, Crystal Ball base model (outputs/Crystal_Ball_ind_heat_v7_4)
_LIFETIME_YEARS = 30.0
_CAPEX_EUR_PER_KW = 1429.99928353338
_OPEX_FIXED_EUR_PER_KW_Y = 49.81066190544665
_OPEX_VARIABLE_EUR_PER_MWH = 4.687676211701609
_CONVERSION_FACTOR_GW_PER_GW = 1.068231106926384  # waste input per unit district_heat output


class WasteBoilerDhProxyDataset(Dataset[pd.DataFrame]):

    name = "waste_boiler_dh_proxy"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Crystal Ball waste_boiler_DH technology (district-heating proxy)",
            author=["Crystal Ball base model"],
            publication="Crystal Ball base model, waste_boiler_DH technology definition",
            publication_year=2026,
        )

    def _set_path(self) -> Path | None:
        return None

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(description=description, metadata=self.metadata)

    def get_lifetime(self, element: Element) -> Attribute:
        attr = Attribute("lifetime", element=element)
        attr.set_data(
            default_value=_LIFETIME_YEARS, unit="1",
            source=self._source_info("Technical lifetime for waste_boiler_industry, proxied from Crystal Ball's waste_boiler_DH."),
        )
        return attr

    def get_capex_specific_conversion(self, element: Element) -> Attribute:
        attr = Attribute("capex_specific_conversion", element=element)
        attr.set_data(
            default_value=_CAPEX_EUR_PER_KW, unit="Euro/kW",
            source=self._source_info("Capex for waste_boiler_industry, proxied from Crystal Ball's waste_boiler_DH."),
        )
        return attr

    def get_opex_specific_fixed(self, element: Element) -> Attribute:
        attr = Attribute("opex_specific_fixed", element=element)
        attr.set_data(
            default_value=_OPEX_FIXED_EUR_PER_KW_Y, unit="Euro/kW",
            source=self._source_info("Fixed O&M for waste_boiler_industry, proxied from Crystal Ball's waste_boiler_DH."),
        )
        return attr

    def get_opex_specific_variable(self, element: Element) -> Attribute:
        attr = Attribute("opex_specific_variable", element=element)
        attr.set_data(
            default_value=_OPEX_VARIABLE_EUR_PER_MWH, unit="Euro/MWh",
            source=self._source_info("Variable O&M for waste_boiler_industry, proxied from Crystal Ball's waste_boiler_DH."),
        )
        return attr

    def get_conversion_factor(self, element: Element) -> Attribute:
        attr = Attribute("conversion_factor", element=element)
        attr.set_data(
            default_value=[{"waste": {"default_value": round(_CONVERSION_FACTOR_GW_PER_GW, 12), "unit": "GW/GW"}}],
            source=self._source_info("Waste input conversion factor for waste_boiler_industry, proxied from Crystal Ball's waste_boiler_DH."),
        )
        return attr
