"""IndustryHeat sector — groups all industry heat carriers and technologies."""

from zen_creator.sectors import Sector

from zen_creator.datasets.datasets._industry_heat_utils import INDUSTRY_HEAT_SECTORS
from zen_creator.elements.carriers.industry_carriers import (
    FUEL_TO_KILN_CARRIER_CLASSES_BY_SECTOR,
    HEAT_CARRIER_CLASSES_BY_SECTOR,
    Ceramic,
    Food,
    FuelToKiln,
    Glass,
    HeatIndustry0100,
    HeatIndustry100150,
    HeatIndustry150200,
    Paper,
)
from zen_creator.elements.conversion_technologies.industry_ccs import (
    CeramicPostComb,
    GlassPostComb,
)
from zen_creator.elements.conversion_technologies.industry_production import (
    CeramicProduction,
    FoodProduction,
    GlassProduction,
    PaperProduction,
)
from zen_creator.elements.conversion_technologies.industry_heat_supply import (
    BOILER_CLASSES_BY_SECTOR,
    CASCADE_CLASSES_BY_SECTOR,
    HEAT_PUMP_CLASSES_BY_SECTOR,
    KILN_FUEL_CLASSES_BY_SECTOR,
    BiomassBoilerIndustry,
    CoalBoilerIndustry,
    ElectricityToKilnfuel,
    ElectrodeBoilerIndustry,
    HeatIndustryTempConversion100,
    HeatIndustryTempConversion150,
    HeatPumpIndustry150200WasteHeat,
    HeatPumpIndustry150200Water,
    HydrogenToKilnfuel,
    NaturalGasBoilerIndustry,
    NaturalGasToKilnfuel,
    OilBoilerIndustry,
    WasteBoilerIndustry,
)


class IndustryHeat(Sector):
    name = "industry_heat"

    def __init__(self):
        super().__init__()
        self.elements = [
            # carriers
            Glass, Ceramic, Paper, Food,
            HeatIndustry0100, HeatIndustry100150, HeatIndustry150200,
            FuelToKiln,
            # production technologies
            GlassProduction, CeramicProduction, PaperProduction, FoodProduction,
            # post-combustion CC retrofits (mirror cement's cement_post_comb;
            # see zen_creator/datasets/datasets/post_comb_cc.py, ASSUMPTIONS.md)
            GlassPostComb, CeramicPostComb,
            # heat pumps (highest temperature level only: waste heat 50°C and water 15°C;
            # the 0-100 and 100-150 level heat pumps live in industry_low_temp_heat)
            HeatPumpIndustry150200WasteHeat, HeatPumpIndustry150200Water,
            # boilers (150-200 only)
            BiomassBoilerIndustry, ElectrodeBoilerIndustry, NaturalGasBoilerIndustry, OilBoilerIndustry,
            CoalBoilerIndustry, WasteBoilerIndustry,
            # temperature downgrade cascade
            HeatIndustryTempConversion150,
            HeatIndustryTempConversion100,
            # kiln fuel switching (fuel_to_kiln): ceramic_production/glass_production's
            # direct high-temp natural_gas input is rerouted through fuel_to_kiln,
            # switchable to hydrogen/electricity (see ASSUMPTIONS.md)
            NaturalGasToKilnfuel, HydrogenToKilnfuel, ElectricityToKilnfuel,
        ]


class IndustryHeatPerSector(Sector):
    """Per-sector variant (V11) of industry_heat: the product carriers, production
    technologies and post-combustion CC are the same, but the heat carriers, the
    highest-band heat pumps, boilers, temperature cascade and kiln-fuel switching exist
    once per sector (`<name>_<sector>`), so no heat can be shared between sectors. Use
    with industry_low_temp_heat_per_sector / industry_tes_per_sector, not with the
    pooled sectors (see ASSUMPTIONS.md, "Per-sector industry heat (V11)")."""

    name = "industry_heat_per_sector"

    def __init__(self):
        super().__init__()
        elements = [Glass, Ceramic, Paper, Food]
        elements += [GlassProduction, CeramicProduction, PaperProduction, FoodProduction]
        elements += [GlassPostComb, CeramicPostComb]
        for sector in INDUSTRY_HEAT_SECTORS:
            elements += list(HEAT_CARRIER_CLASSES_BY_SECTOR[sector].values())
            if sector in FUEL_TO_KILN_CARRIER_CLASSES_BY_SECTOR:
                elements.append(FUEL_TO_KILN_CARRIER_CLASSES_BY_SECTOR[sector])
            # highest band only; the 0-100 / 100-150 heat pumps live in industry_low_temp_heat_per_sector
            hps = HEAT_PUMP_CLASSES_BY_SECTOR[sector]
            elements += [hps["150_200_waste_heat"], hps["150_200_water"]]
            elements += BOILER_CLASSES_BY_SECTOR[sector]
            elements += CASCADE_CLASSES_BY_SECTOR[sector]
            elements += KILN_FUEL_CLASSES_BY_SECTOR.get(sector, [])
        self.elements = elements
