"""IndustryHeat sector — groups all industry heat carriers and technologies."""

from zen_creator.sectors import Sector

from zen_creator.elements.carriers.industry_carriers import (
    Ceramic,
    Food,
    Glass,
    HeatIndustry0100,
    HeatIndustry100150,
    HeatIndustry150200,
    Paper,
)
from zen_creator.elements.conversion_technologies.industry_production import (
    CeramicProduction,
    FoodProduction,
    GlassProduction,
    PaperProduction,
)
from zen_creator.elements.conversion_technologies.industry_heat_supply import (
    BiomassBoilerIndustry,
    ElectrodeBoilerIndustry,
    HeatIndustryTempConversion100to0,
    HeatIndustryTempConversion150to100,
    HeatPumpIndustry0100,
    HeatPumpIndustry100150,
    HeatPumpIndustry150200,
    NaturalGasBoilerIndustry,
)


class IndustryHeat(Sector):
    name = "industry_heat"

    def __init__(self):
        super().__init__()
        self.elements = [
            # carriers
            Glass, Ceramic, Paper, Food,
            HeatIndustry0100, HeatIndustry100150, HeatIndustry150200,
            # production technologies
            GlassProduction, CeramicProduction, PaperProduction, FoodProduction,
            # heat pumps (one per temperature level)
            HeatPumpIndustry0100, HeatPumpIndustry100150, HeatPumpIndustry150200,
            # boilers (150-200 only)
            BiomassBoilerIndustry, ElectrodeBoilerIndustry, NaturalGasBoilerIndustry,
            # temperature downgrade cascade
            HeatIndustryTempConversion150to100,
            HeatIndustryTempConversion100to0,
        ]
