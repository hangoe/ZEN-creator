"""End-to-end test: build a full model with all four industry sectors together,
against the crystal_ball fixture (the same base every other end-to-end test in
this directory uses).

Before this, nothing in the test suite ever built a Model with any industry
sector at all -- so cross-sector composition issues (registration order,
shared carriers between industry_heat/industry_low_temp_heat/industry_tes/
industry_dsm_optimistic, the custom energy system) went unchecked (see cleanup
plan, Phase 2 item 11). This mirrors my_scripts/my_model.py's main-scenario
sector combination exactly, just against the small local fixture instead of
the external Crystal Ball model directory.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import zen_creator.elements.energy_systems.crystal_ball_industry as crystal_ball_industry
from zen_creator.model import Model
from zen_creator.utils.default_config import Config

# import sectors (triggers auto-registration via __init_subclass__ into
# Sector._sector_registry, which -- unlike Element._registry -- is NOT reset
# by this directory's autouse reset_element_registry fixture)
from zen_creator.sectors.industry_dsm import IndustryDSMOptimistic  # noqa: F401
from zen_creator.sectors.industry_heat import IndustryHeat  # noqa: F401
from zen_creator.sectors.industry_low_temp_heat import IndustryLowTempHeat  # noqa: F401
from zen_creator.sectors.industry_tes import IndustryTES  # noqa: F401

MAIN_SECTORS = ["industry_heat", "industry_low_temp_heat", "industry_tes", "industry_dsm_optimistic"]


def _build_industry_model(tmp_path: Path) -> Model:
    # reset_element_registry (conftest.py) clears Registry._registry before this
    # test runs, which also wipes CrystalBallIndustryEnergySystem's registration
    # under "crystal_ball_industry_energy_system" -- reload to re-trigger
    # __init_subclass__ and restore it, the same pattern test_from_existing_with_config
    # uses for existing_model_elements.
    importlib.reload(crystal_ball_industry)

    existing_model_path = Path(".//tests//end_to_end//fixtures//crystal_ball")
    config = Config.load_from_existing_model(existing_model_path)
    config.elements.insert.energy_system = "crystal_ball_industry_energy_system"

    model = Model.from_existing(existing_model_path=existing_model_path, config=config)
    for sector_name in MAIN_SECTORS:
        model.add_sector_by_name(sector_name)

    model.build()
    model.name = "test_industry_model"
    model.output_folder = tmp_path
    return model


def test_full_industry_model_builds_and_writes(tmp_path: Path):
    model = _build_industry_model(tmp_path)

    # the custom energy system was actually used, and its carbon budget was
    # extended beyond the base fixture's value (see carbon_budget_allocation.py)
    assert model.energy_system.__class__.__name__ == "CrystalBallIndustryEnergySystem"
    assert model.energy_system.carbon_emissions_budget.default_value > 23.152036605496253

    # every carrier/technology from all four sectors is present, alongside the
    # base fixture's own elements (e.g. photovoltaics, natural_gas)
    for expected in ("glass", "ceramic", "paper", "food", "fuel_to_kiln"):
        assert expected in model.elements
    for expected in ("glass_production", "biomass_boiler_industry", "natural_gas_to_kilnfuel"):
        assert expected in model.elements
    for expected in ("industry_TES_water_0_100", "industry_TES_steam_150_200"):
        assert expected in model.elements
    for expected in ("glass_DSM", "ammonia_DSM"):
        assert expected in model.elements
    assert "photovoltaics" in model.elements  # base fixture element, untouched

    model.write()
    written = model.output_folder / model.name
    assert (written / "system.json").exists()
    assert (written / "set_carriers" / "glass" / "attributes.json").exists()
    assert (written / "set_technologies" / "set_conversion_technologies" / "glass_production" / "attributes.json").exists()
    assert (written / "set_technologies" / "set_storage_technologies" / "industry_TES_water_0_100" / "attributes.json").exists()


def test_single_temp_scenario_omits_low_temp_heat_pumps(tmp_path: Path):
    """The single_temp scenario variant (my_scripts/my_model.py) drops
    industry_low_temp_heat -- confirm that composition also works, and that
    the 0-100/100-150 heat pumps are then genuinely absent."""
    importlib.reload(crystal_ball_industry)
    existing_model_path = Path(".//tests//end_to_end//fixtures//crystal_ball")
    config = Config.load_from_existing_model(existing_model_path)
    config.elements.insert.energy_system = "crystal_ball_industry_energy_system"

    model = Model.from_existing(existing_model_path=existing_model_path, config=config)
    for sector_name in ("industry_heat", "industry_tes", "industry_dsm_optimistic"):
        model.add_sector_by_name(sector_name)
    model.build()

    assert "heat_pump_industry_0_100_water" not in model.elements
    assert "heat_pump_industry_150_200_water" in model.elements


if __name__ == "__main__":
    pytest.main([__file__])
