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
    BiomassBoilerIndustry0100,
    BiomassBoilerIndustry100200,
    ElectrodeBoilerIndustry0100,
    ElectrodeBoilerIndustry100200,
    HeatPumpIndustry0100,
    HeatPumpIndustry100200,
    NaturalGasBoilerIndustry0100,
    NaturalGasBoilerIndustry100200,
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
            Glass,
            Ceramic,
            Paper,
            Food,
            HeatIndustry0100,
            HeatIndustry100200,
            GlassProduction,
            CeramicProduction,
            PaperProduction,
            FoodProduction,
            BiomassBoilerIndustry0100,
            BiomassBoilerIndustry100200,
            ElectrodeBoilerIndustry0100,
            ElectrodeBoilerIndustry100200,
            HeatPumpIndustry0100,
            HeatPumpIndustry100200,
            NaturalGasBoilerIndustry0100,
            NaturalGasBoilerIndustry100200,
        ]
