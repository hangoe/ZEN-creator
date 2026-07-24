"""IndustryTES sector — thermal energy storage for industry.

Groups the industry_heat thermal-storage technologies, separate from the
demand-side-management technologies in industry_dsm. This allows TES and DSM
to be added to a model independently of one another.

Requires industry_heat to be added to the model first so that the
heat carrier objects are registered before the TES elements are built.
"""

from zen_creator.sectors import Sector

from zen_creator.elements.storage_technologies.industry_TES import (
    IndustryTESSteam150200,
    IndustryTESWater0100,
    IndustryTESWater100150,
)


class IndustryTES(Sector):
    name = "industry_tes"

    def __init__(self):
        super().__init__()
        self.elements = [
            IndustryTESWater0100,
            IndustryTESWater100150,
            IndustryTESSteam150200,
        ]
