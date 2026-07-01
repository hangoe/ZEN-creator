"""IndustryFlexibility sector — thermal and demand-side storage for industry.

Groups all flexibility technologies (TES and DSM) in one place, separate from
the heat-supply and production technologies in industry_heat. This allows the
sector to be added independently and extended to cover carriers from any
industrial sector (not only those in industry_heat).

Requires industry_heat to be added to the model first so that the
glass/ceramic/paper/food carrier objects are registered before the DSM
elements are built.
"""

from zen_creator.sectors import Sector

from zen_creator.elements.storage_technologies.industry_TES import (
    IndustryTESSteam100150,
    IndustryTESSteam150200,
    IndustryTESWater0100,
    IndustryTESWater100150,
)
from zen_creator.elements.storage_technologies.industry_DSM import (
    AmmoniaDSM,
    CeramicDSM,
    ClinkerDSM,
    FoodDSM,
    GlassDSM,
    MethanolDSM,
    OlefinDSM,
    PaperDSM,
    PrimarysteelDSM,
    SecondarysteelDSM,
)


class IndustryFlexibility(Sector):
    name = "industry_flexibility"

    def __init__(self):
        super().__init__()
        self.elements = [
            # thermal energy storage
            IndustryTESWater0100,
            IndustryTESWater100150,
            IndustryTESSteam100150,
            IndustryTESSteam150200,
            # demand-side management — industry_heat products
            GlassDSM,
            CeramicDSM,
            PaperDSM,
            FoodDSM,
            # demand-side management — other industrial products (existing Crystal Ball carriers)
            AmmoniaDSM,
            ClinkerDSM,
            MethanolDSM,
            PrimarysteelDSM,
            SecondarysteelDSM,
            OlefinDSM,
        ]
