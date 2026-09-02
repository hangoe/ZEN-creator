"""Unit tests for the industry Sector definitions (zen_creator/sectors/*.py).

Nothing previously checked that a Sector's `.elements` list is complete --
a silently dropped technology/carrier would go unnoticed by every other test
in this suite, since none of them build a full sector (see cleanup plan,
Phase 2 item 8).
"""

from __future__ import annotations

import pytest

from zen_creator.elements.element import Element
from zen_creator.sectors.industry_dsm import IndustryDSMOptimistic, IndustryDSMPessimistic
from zen_creator.sectors.industry_heat import IndustryHeat
from zen_creator.sectors.industry_low_temp_heat import IndustryLowTempHeat
from zen_creator.sectors.industry_tes import IndustryTES


@pytest.mark.parametrize(
    "sector_cls", [IndustryHeat, IndustryLowTempHeat, IndustryTES, IndustryDSMOptimistic, IndustryDSMPessimistic]
)
def test_elements_is_a_nonempty_list_of_element_subclasses(sector_cls):
    sector = sector_cls()
    assert isinstance(sector.elements, list)
    assert len(sector.elements) > 0
    for element_cls in sector.elements:
        assert issubclass(element_cls, Element)


def test_industry_heat_covers_all_150_200_technologies():
    """IndustryHeat groups the carriers, production techs, post-comb retrofits,
    150-200 heat pumps, boilers, the temperature cascade, and kiln-fuel-switching
    techs -- a dropped entry here silently removes a technology from every
    scenario, since all of them include industry_heat."""
    from zen_creator.elements.carriers.industry_carriers import (
        Ceramic, Food, FuelToKiln, Glass, HeatIndustry0100, HeatIndustry100150, HeatIndustry150200, Paper,
    )
    from zen_creator.elements.conversion_technologies.industry_ccs import CeramicPostComb, GlassPostComb
    from zen_creator.elements.conversion_technologies.industry_heat_supply import (
        BiomassBoilerIndustry, CoalBoilerIndustry, ElectricityToKilnfuel, ElectrodeBoilerIndustry,
        HeatIndustryTempConversion100, HeatIndustryTempConversion150, HeatPumpIndustry150200WasteHeat,
        HeatPumpIndustry150200Water, HydrogenToKilnfuel, NaturalGasBoilerIndustry, NaturalGasToKilnfuel,
        OilBoilerIndustry, WasteBoilerIndustry,
    )
    from zen_creator.elements.conversion_technologies.industry_production import (
        CeramicProduction, FoodProduction, GlassProduction, PaperProduction,
    )

    expected = {
        Glass, Ceramic, Paper, Food, HeatIndustry0100, HeatIndustry100150, HeatIndustry150200, FuelToKiln,
        GlassProduction, CeramicProduction, PaperProduction, FoodProduction,
        GlassPostComb, CeramicPostComb,
        HeatPumpIndustry150200WasteHeat, HeatPumpIndustry150200Water,
        BiomassBoilerIndustry, ElectrodeBoilerIndustry, NaturalGasBoilerIndustry, OilBoilerIndustry,
        CoalBoilerIndustry, WasteBoilerIndustry,
        HeatIndustryTempConversion150, HeatIndustryTempConversion100,
        NaturalGasToKilnfuel, HydrogenToKilnfuel, ElectricityToKilnfuel,
    }

    assert set(IndustryHeat().elements) == expected


def test_industry_low_temp_heat_covers_0_100_and_100_150_heat_pumps():
    from zen_creator.elements.conversion_technologies.industry_heat_supply import (
        HeatPumpIndustry0100WasteHeat, HeatPumpIndustry0100Water,
        HeatPumpIndustry100150WasteHeat, HeatPumpIndustry100150Water,
    )

    expected = {
        HeatPumpIndustry0100WasteHeat, HeatPumpIndustry0100Water,
        HeatPumpIndustry100150WasteHeat, HeatPumpIndustry100150Water,
    }
    assert set(IndustryLowTempHeat().elements) == expected


def test_industry_tes_covers_all_three_temperature_bands():
    from zen_creator.elements.storage_technologies.industry_TES import (
        IndustryTESSteam150200, IndustryTESWater0100, IndustryTESWater100150,
    )

    expected = {IndustryTESWater0100, IndustryTESWater100150, IndustryTESSteam150200}
    assert set(IndustryTES().elements) == expected


@pytest.mark.parametrize(
    "sector_cls,variant",
    [(IndustryDSMOptimistic, "Optimistic"), (IndustryDSMPessimistic, "Pessimistic")],
)
def test_industry_dsm_covers_all_ten_carriers(sector_cls, variant):
    """Both DSM sectors must cover the same 10 carriers (4 industry_heat products
    + 6 existing Crystal Ball carriers), each with the matching variant class."""
    import zen_creator.elements.storage_technologies.industry_DSM as dsm

    carriers = ["Glass", "Ceramic", "Paper", "Food", "Ammonia", "Clinker", "Methanol", "Primarysteel", "Secondarysteel", "Olefin"]
    expected = {getattr(dsm, f"{carrier}DSM{variant}") for carrier in carriers}
    assert set(sector_cls().elements) == expected


if __name__ == "__main__":
    pytest.main([__file__])
