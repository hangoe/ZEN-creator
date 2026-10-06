"""IndustryLowTempHeat sector — 0-100/100-150 band industry heat pumps.

Split out from industry_heat so that a "single temperature level" model
variant can be generated: one that keeps every industry_heat carrier,
production technology, boiler, and temperature-downgrade cascade technology,
but supplies low/mid-band heat only via the cascade from the highest band
rather than via dedicated heat pumps at those bands.

Requires industry_heat to be added to the model first so that the
heat/electricity carrier objects are registered before these heat pumps are
built. Omitted only in the single_temp scenario.
"""

from zen_creator.sectors import Sector

from zen_creator.datasets.datasets._industry_heat_utils import INDUSTRY_HEAT_SECTORS
from zen_creator.elements.conversion_technologies.industry_heat_supply import (
    HEAT_PUMP_CLASSES_BY_SECTOR,
    HeatPumpIndustry0100WasteHeat,
    HeatPumpIndustry0100Water,
    HeatPumpIndustry100150WasteHeat,
    HeatPumpIndustry100150Water,
)


class IndustryLowTempHeat(Sector):
    name = "industry_low_temp_heat"

    def __init__(self):
        super().__init__()
        self.elements = [
            HeatPumpIndustry0100WasteHeat, HeatPumpIndustry0100Water,
            HeatPumpIndustry100150WasteHeat, HeatPumpIndustry100150Water,
        ]


class IndustryLowTempHeatPerSector(Sector):
    """Per-sector variant (V11) of industry_low_temp_heat: the same four heat pumps,
    once per sector, on that sector's heat carriers. Requires industry_heat_per_sector."""

    name = "industry_low_temp_heat_per_sector"

    def __init__(self):
        super().__init__()
        self.elements = [
            hp
            for sector in INDUSTRY_HEAT_SECTORS
            for key, hp in HEAT_PUMP_CLASSES_BY_SECTOR[sector].items()
            if not key.startswith("150_200")
        ]
