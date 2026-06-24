"""IndustryHeat sector — groups all industry heat carriers and technologies."""

from zen_creator.sectors import Sector

from zen_creator.elements.industry_heat.carriers import (
    Ceramic,
    Food,
    Glass,
    HeatIndustry0100,
    HeatIndustry100200,
    Paper,
)
from zen_creator.elements.industry_heat.heat_techs import (
    BiomassBoilerIndustry,
    ElectrodeBoilerIndustry,
    HeatIndustryTempConversion,
    HeatPumpIndustry0100,
    HeatPumpIndustry100200,
    NaturalGasBoilerIndustry,
)
from zen_creator.elements.industry_heat.production_techs import (
    CeramicProduction,
    FoodProduction,
    GlassProduction,
    PaperProduction,
)


class IndustryHeat(Sector):
    name = "industry_heat"

    def __init__(self):
        super().__init__()
        self.elements = [
            # carriers
            Glass,
            Ceramic,
            Paper,
            Food,
            HeatIndustry0100,
            HeatIndustry100200,
            # production technologies
            GlassProduction,
            CeramicProduction,
            PaperProduction,
            FoodProduction,
            # heat supply: heat pumps (separate per temp level)
            HeatPumpIndustry0100,
            HeatPumpIndustry100200,
            # heat supply: boilers (100-200 only)
            BiomassBoilerIndustry,
            ElectrodeBoilerIndustry,
            NaturalGasBoilerIndustry,
            # temperature downgrade: 100-200 → 0-100
            HeatIndustryTempConversion,
        ]
