"""IndustryDSM sectors — demand-side management for industrial products.

Groups the demand-side-management technologies, separate from the thermal
energy storage technologies in industry_tes. This allows TES and DSM to be
added to a model independently of one another, and extends to carriers from
any industrial sector (not only those in industry_heat).

Requires industry_heat to be added to the model first so that the
glass/ceramic/paper/food carrier objects are registered before the DSM
elements are built.

Two sectors are defined, `industry_dsm_optimistic` and
`industry_dsm_pessimistic`, parametrizing every DSM technology with the
optimistic or pessimistic demand-shiftability category respectively (see
`zen_creator/elements/storage_technologies/industry_DSM.py` and
`input_data/DSM_parametrization/DSM_literature_review.md`).
"""

from zen_creator.sectors import Sector

from zen_creator.elements.storage_technologies.industry_DSM import (
    AmmoniaDSMOptimistic,
    AmmoniaDSMPessimistic,
    CeramicDSMOptimistic,
    CeramicDSMPessimistic,
    ClinkerDSMOptimistic,
    ClinkerDSMPessimistic,
    FoodDSMOptimistic,
    FoodDSMPessimistic,
    GlassDSMOptimistic,
    GlassDSMPessimistic,
    MethanolDSMOptimistic,
    MethanolDSMPessimistic,
    OlefinDSMOptimistic,
    OlefinDSMPessimistic,
    PaperDSMOptimistic,
    PaperDSMPessimistic,
    PrimarysteelDSMOptimistic,
    PrimarysteelDSMPessimistic,
    SecondarysteelDSMOptimistic,
    SecondarysteelDSMPessimistic,
)


class IndustryDSMOptimistic(Sector):
    name = "industry_dsm_optimistic"

    def __init__(self):
        super().__init__()
        self.elements = [
            # demand-side management — industry_heat products
            GlassDSMOptimistic,
            CeramicDSMOptimistic,
            PaperDSMOptimistic,
            FoodDSMOptimistic,
            # demand-side management — other industrial products (existing Crystal Ball carriers)
            AmmoniaDSMOptimistic,
            ClinkerDSMOptimistic,
            MethanolDSMOptimistic,
            PrimarysteelDSMOptimistic,
            SecondarysteelDSMOptimistic,
            OlefinDSMOptimistic,
        ]


class IndustryDSMPessimistic(Sector):
    name = "industry_dsm_pessimistic"

    def __init__(self):
        super().__init__()
        self.elements = [
            # demand-side management — industry_heat products
            GlassDSMPessimistic,
            CeramicDSMPessimistic,
            PaperDSMPessimistic,
            FoodDSMPessimistic,
            # demand-side management — other industrial products (existing Crystal Ball carriers)
            AmmoniaDSMPessimistic,
            ClinkerDSMPessimistic,
            MethanolDSMPessimistic,
            PrimarysteelDSMPessimistic,
            SecondarysteelDSMPessimistic,
            OlefinDSMPessimistic,
        ]
