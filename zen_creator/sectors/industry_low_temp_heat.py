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

from zen_creator.elements.conversion_technologies.industry_heat_supply import (
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
