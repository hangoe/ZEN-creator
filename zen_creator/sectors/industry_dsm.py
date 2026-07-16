"""IndustryDSM sector — demand-side management for industrial products.

Groups the demand-side-management technologies, separate from the thermal
energy storage technologies in industry_tes. This allows TES and DSM to be
added to a model independently of one another, and extends to carriers from
any industrial sector (not only those in industry_heat).

Requires industry_heat to be added to the model first so that the
glass/ceramic/paper/food carrier objects are registered before the DSM
elements are built.
"""

from zen_creator.sectors import Sector

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


class IndustryDSM(Sector):
    name = "industry_dsm"

    def __init__(self):
        super().__init__()
        self.elements = [
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
