"""Dataset extending Mannhardt (2026)'s carbon emission budget to new sectors.

Mannhardt (2026), Appendix A.2 ("Emissions and carbon budget", printed pp. 124-127)
derives the Chapters 5/6 carbon budget (the `carbon_emissions_budget` hardcoded in the
Crystal Ball base dataset, 23.152036605496253 Gt) as:

    B_countries = IPCC AR6 remaining global budget (2020) x per-capita share of the
                  28 modeled countries (EU-27 minus Malta/Cyprus, plus CH/NO/UK)
    old_budget  = B_countries x f_old,  where f_old = (2021 direct CO2 emissions of
                  the 11 sectors she modeled, 28 countries) / (total 2021 direct CO2
                  emissions of the 28 countries)

`old_budget` is known exactly; `B_countries` and `f_old` individually are not (they
are only published rounded to 1 decimal place). Crediting extra sectors therefore
does not require recovering them:

    new_budget = B_countries x (f_old + df) = old_budget x (1 + df/f_old)
               = old_budget x (1 + E_new_sectors / E_old_sectors)

where E_old_sectors / E_new_sectors are 2022 direct CO2 emissions (EEA/UNFCCC CRF
data, 28 countries minus UK - see below) for Mannhardt's 11 sectors and for the
sectors newly credited, respectively. See `input_data/ASSUMPTIONS.md` ("Carbon
emissions budget") for the full writeup, including the double-counting finding for
glass/ceramics and the three compared variants.

Data source: `input_data/Mannhardt2026/sector_emissions_2022.csv`, a small derived
extract of `input_data/Mannhardt2026/UNFCCC_v30.csv` (EEA national GHG inventory,
CRF-coded, EU-27 + CH + NO; UK is not covered by this EEA extract and is omitted from
both E_old_sectors and E_new_sectors) produced by
`input_data/Mannhardt2026/extract_sector_emissions.py`. 2022 is used as the reference
year (closest available year to Mannhardt's 2021 vintage).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from zen_creator.elements.element import Element

from zen_creator.datasets.datasets._industry_heat_utils import INPUT_DATA
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

_MANNHARDT_DIR = INPUT_DATA / "Mannhardt2026"
_SECTOR_EMISSIONS_CSV = _MANNHARDT_DIR / "sector_emissions_2022.csv"

# Which variant is currently applied when writing a new carbon_emissions_budget.
# "A" = zero increment (paper+food only), "B" = naive full-add (chosen, see
# ASSUMPTIONS.md), "C" = process-only for glass/ceramics. Change here to switch.
DEFAULT_VARIANT = "B"


class Mannhardt2026CarbonBudgetDataset(Dataset[pd.DataFrame]):

    name = "mannhardt_2026_carbon_budget"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Emissions and carbon budget (Appendix A.2)",
            author=["Mannhardt, J."],
            publication="PhD dissertation, ETH Zurich",
            publication_year=2026,
        )

    def _set_path(self) -> Path | None:
        return _SECTOR_EMISSIONS_CSV

    def _set_data(self) -> pd.DataFrame:
        return pd.read_csv(self.path)

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(
            description=description,
            metadata={
                "mannhardt_2026": self.metadata,
                "eea_unfccc_2022": MetaData(
                    name="eea_unfccc_2022",
                    title="UNFCCC Common Reporting Format GHG inventory data",
                    author=["European Environment Agency"],
                    publication="EEA GHG data viewer (UNFCCC_v30 export, 2022 data)",
                    publication_year=2026,
                ),
            },
        )

    def get_old_sector_emissions(self) -> float:
        """2022 direct CO2 emissions [kt] of Mannhardt's 11 modeled sectors, 28 countries."""
        return self.data.loc[self.data["bucket"] == "old", "emissions_kt_co2_28countries"].sum()

    def get_new_sector_emissions(self, variant: str = DEFAULT_VARIANT) -> float:
        """2022 direct CO2 emissions [kt] credited to the new sectors under `variant`.

        variant: "A" (paper+food only), "B" (+ glass/ceramic process and the shared
            1.A.2.f combustion bucket, chosen), or "C" (+ glass/ceramic process only).
        """
        new_rows = self.data[self.data["bucket"] == "new"]
        included = new_rows["variant_tags"].str.split(",").apply(lambda tags: variant in tags)
        return new_rows.loc[included, "emissions_kt_co2_28countries"].sum()

    def get_carbon_emissions_budget(
        self, element: Element, old_budget: Attribute, variant: str = DEFAULT_VARIANT
    ) -> Attribute:
        """Extend `old_budget` to credit the new sectors, per the formula above."""
        e_old = self.get_old_sector_emissions()
        e_new = self.get_new_sector_emissions(variant)
        # new_budget = old_budget * (1 + E_new_sectors / E_old_sectors)
        new_value = old_budget.default_value * (1 + e_new / e_old)

        attr = Attribute("carbon_emissions_budget", element=element)
        attr.set_data(
            default_value=new_value,
            unit=old_budget.unit,
            source=self._source_info(
                f"Extended Mannhardt (2026) Appendix A.2 carbon budget "
                f"({old_budget.default_value:.6f} Gt) to credit glass/ceramic/paper/"
                f"food sectors using variant '{variant}' "
                f"(E_old={e_old:.3f} kt, E_new={e_new:.3f} kt, 2022, 28 countries "
                "minus UK). See ASSUMPTIONS.md 'Carbon emissions budget' for the "
                "three compared variants and the double-counting caveat for "
                "glass/ceramics."
            ),
        )
        return attr
