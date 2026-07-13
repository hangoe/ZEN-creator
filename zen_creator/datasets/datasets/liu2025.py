import math
from pathlib import Path

import pandas as pd

from zen_creator.elements.element import Element
from zen_creator.utils.attribute import Attribute

from .dataset import Dataset
from .metadata import MetaData, SourceInformation

_INPUT_DATA = Path(__file__).resolve().parents[3] / "input_data"

# Liu2025 reports costs in USD; the model is EUR-denominated and the paper gives no
# EUR figures, so a fixed illustrative rate is used (internal assumption, not from
# the paper) and applied flat across all projection years.
_USD_TO_EUR = 0.92

# 1 GWh = 1e6 kWh
_KWH_TO_GWH = 1.0e6


class Liu2025Dataset(Dataset[pd.DataFrame]):

    name = "liu2025"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title=(
                "Techno-economic analysis of using ammonia as an energy carrier"
                " for renewable energy conversion and storage"
            ),
            author=["Liu, Y."],
            publication="International Journal of Hydrogen Energy",
            publication_year=2025,
            doi="10.1016/j.ijhydene.2025.150784",
        )

    def _set_path(self) -> Path | None:
        if self.source_path is not None:
            p = Path(self.source_path) / "Liu2025" / "Liu2025_ammonia_storage.csv"
            if p.exists():
                return p
        return _INPUT_DATA / "Liu2025" / "Liu2025_ammonia_storage.csv"

    def _set_data(self) -> pd.DataFrame:
        return pd.read_csv(self.path, index_col="year")

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(description=description, metadata=self.metadata)

    def _capex_eur_per_gwh(self) -> pd.Series:
        return self.data["capex_usd_per_kwh"] * _USD_TO_EUR * _KWH_TO_GWH

    def get_capex_specific_storage_energy(self, element: Element) -> Attribute:
        capex = self._capex_eur_per_gwh()
        df = capex.rename("capex_specific_storage_energy").to_frame()
        attr = Attribute("capex_specific_storage_energy", element=element)
        attr.set_data(
            default_value=float(capex.iloc[0]),
            unit="Euro/GWh",
            df=df,
            source=self._source_info(
                "Investment cost from Liu2025 Table S2/S3 (ammonia storage tank),"
                f" converted from USD/kWh to EUR/GWh (USD->EUR rate={_USD_TO_EUR},"
                " internal assumption; x1e6 for kWh->GWh)."
            ),
        )
        return attr

    def get_opex_specific_fixed_energy(self, element: Element) -> Attribute:
        capex = self._capex_eur_per_gwh()
        opex = capex * (self.data["opex_pct_of_capex"] / 100.0)
        df = opex.rename("opex_specific_fixed_energy").to_frame()
        attr = Attribute("opex_specific_fixed_energy", element=element)
        attr.set_data(
            default_value=float(opex.iloc[0]),
            unit="Euro/GWh",
            df=df,
            source=self._source_info(
                "Fixed O&M cost = 2% of CAPEX per year, from Liu2025 Table S2/S3."
                " Computed as opex_pct_of_capex x capex_specific_storage_energy"
                " for each year."
            ),
        )
        return attr

    def _round_trip_efficiency(self) -> float:
        loss_pct = float(self.data["energy_loss_pct"].iloc[0])
        return 1.0 - loss_pct / 100.0

    def get_efficiency_charge(self, element: Element) -> Attribute:
        attr = Attribute("efficiency_charge", element=element)
        attr.set_data(
            default_value=math.sqrt(self._round_trip_efficiency()),
            unit="1",
            source=self._source_info(
                "Charge efficiency = sqrt(round-trip efficiency). Round-trip"
                " efficiency = 1 - energy loss (4%, flat 2023-2050) from Liu2025"
                " Table S3. Note: the source text describes the 4% loss as"
                " covering the combined transport+storage process, while the"
                " tables list it separately per stage; treated here as a"
                " storage-only round-trip loss."
            ),
        )
        return attr

    def get_efficiency_discharge(self, element: Element) -> Attribute:
        attr = Attribute("efficiency_discharge", element=element)
        attr.set_data(
            default_value=math.sqrt(self._round_trip_efficiency()),
            unit="1",
            source=self._source_info(
                "Discharge efficiency = sqrt(round-trip efficiency). See"
                " get_efficiency_charge for the round-trip efficiency source"
                " and the storage-vs-transport loss ambiguity."
            ),
        )
        return attr

    def get_lifetime(self, element: Element) -> Attribute:
        lifetime = float(self.data["lifetime_years"].iloc[0])
        attr = Attribute("lifetime", element=element)
        attr.set_data(
            default_value=lifetime,
            unit="1",
            source=self._source_info(
                "Equipment lifetime from Liu2025 (30 years, assumed to coincide"
                " with the ammonia production facility's equipment lifespan)."
            ),
        )
        return attr
