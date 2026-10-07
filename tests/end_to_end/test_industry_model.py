"""End-to-end test: build a full model with all four industry sectors together,
against the crystal_ball fixture (the same base every other end-to-end test in
this directory uses).

Checks cross-sector composition (registration order, shared carriers between
industry_heat/industry_low_temp_heat/industry_tes/industry_dsm_optimistic, the
custom energy system). This mirrors my_scripts/my_model.py's main-scenario
sector combination exactly, just against the small local fixture instead of
the external Crystal Ball model directory.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import zen_creator.elements.energy_systems.zen_europe_industry as zen_europe_industry
from zen_creator.datasets.datasets._industry_heat_utils import INDUSTRY_HEAT_SECTORS
from zen_creator.model import Model
from zen_creator.utils.config import Config

# import sectors (triggers auto-registration via __init_subclass__ into
# Sector._sector_registry, which -- unlike Element._registry -- is NOT reset
# by this directory's autouse reset_element_registry fixture)
from zen_creator.sectors.industry_dsm import IndustryDSMOptimistic  # noqa: F401
from zen_creator.sectors.industry_heat import IndustryHeat, IndustryHeatPerSector  # noqa: F401
from zen_creator.sectors.industry_low_temp_heat import IndustryLowTempHeat, IndustryLowTempHeatPerSector  # noqa: F401
from zen_creator.sectors.industry_tes import IndustryTES, IndustryTESPerSector  # noqa: F401

MAIN_SECTORS = ["industry_heat", "industry_low_temp_heat", "industry_tes", "industry_dsm_optimistic"]
PER_SECTOR_MAIN_SECTORS = [
    "industry_heat_per_sector", "industry_low_temp_heat_per_sector", "industry_tes_per_sector",
    "industry_dsm_optimistic",
]


def _build_industry_model(tmp_path: Path, sectors: list[str] = MAIN_SECTORS) -> Model:
    # reset_element_registry (conftest.py) clears Registry._registry before this
    # test runs, which also wipes ZenEuropeIndustryEnergySystem's registration
    # under "zen_europe_industry_energy_system" -- reload to re-trigger
    # __init_subclass__ and restore it, the same pattern test_from_existing_with_config
    # uses for existing_model_elements.
    importlib.reload(zen_europe_industry)

    existing_model_path = Path(".//tests//end_to_end//fixtures//crystal_ball")
    config = Config.load_from_existing_model(existing_model_path)
    config.elements.insert.energy_system = "zen_europe_industry_energy_system"

    model = Model.from_existing(existing_model_path=existing_model_path, config=config)
    for sector_name in sectors:
        model.add_sector_by_name(sector_name)

    model.build()
    model.name = "test_industry_model"
    model.output_folder = tmp_path
    return model


def test_full_industry_model_builds_and_writes(tmp_path: Path):
    model = _build_industry_model(tmp_path)

    # the custom energy system was actually used, and its carbon budget was
    # extended beyond the base fixture's value (see carbon_budget_allocation.py)
    assert model.energy_system.__class__.__name__ == "ZenEuropeIndustryEnergySystem"
    assert model.energy_system.carbon_emissions_budget.default_value > 22.586810231692006

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
    assert (written / "system.yaml").exists()
    assert (written / "set_carriers" / "glass" / "attributes.yaml").exists()
    assert (written / "set_technologies" / "set_conversion_technologies" / "glass_production" / "attributes.yaml").exists()
    assert (written / "set_technologies" / "set_storage_technologies" / "industry_TES_water_0_100" / "attributes.yaml").exists()


def test_single_temp_scenario_omits_low_temp_heat_pumps(tmp_path: Path):
    """The single_temp scenario variant (my_scripts/my_model.py) drops
    industry_low_temp_heat -- confirm that composition also works, and that
    the 0-100/100-150 heat pumps are then genuinely absent."""
    importlib.reload(zen_europe_industry)
    existing_model_path = Path(".//tests//end_to_end//fixtures//crystal_ball")
    config = Config.load_from_existing_model(existing_model_path)
    config.elements.insert.energy_system = "zen_europe_industry_energy_system"

    model = Model.from_existing(existing_model_path=existing_model_path, config=config)
    for sector_name in ("industry_heat", "industry_tes", "industry_dsm_optimistic"):
        model.add_sector_by_name(sector_name)
    model.build()

    assert "heat_pump_industry_0_100_water" not in model.elements
    assert "heat_pump_industry_150_200_water" in model.elements


def test_full_industry_model_per_sector_heat_builds_and_writes(tmp_path: Path):
    """Per-sector heat (V11, the *_per_sector sectors): every heat carrier / heat
    technology / TES exists once per sector, nothing pooled is left, and each sector's
    production technology draws only on its own heat carriers."""
    model = _build_industry_model(tmp_path, PER_SECTOR_MAIN_SECTORS)

    for sector in INDUSTRY_HEAT_SECTORS:
        for expected in (
            sector, f"{sector}_production", f"{sector}_DSM",
            f"heat_industry_0_100_{sector}", f"heat_industry_150_200_{sector}",
            f"biomass_boiler_industry_{sector}", f"heat_pump_industry_0_100_water_{sector}",
            f"heat_industry_temp_conversion_150_{sector}", f"industry_TES_water_0_100_{sector}",
        ):
            assert expected in model.elements, expected
    for sector in ("glass", "ceramic"):
        assert f"fuel_to_kiln_{sector}" in model.elements
        assert f"natural_gas_to_kilnfuel_{sector}" in model.elements
    for pooled in (
        "heat_industry_0_100", "heat_industry_100_150", "heat_industry_150_200", "fuel_to_kiln",
        "biomass_boiler_industry", "natural_gas_to_kilnfuel", "industry_TES_water_0_100",
        "heat_industry_temp_conversion_100", "heat_pump_industry_150_200_water",
    ):
        assert pooled not in model.elements, pooled

    for sector in INDUSTRY_HEAT_SECTORS:
        production = model.elements[f"{sector}_production"]
        heat_inputs = [
            c for c in production.input_carrier.default_value if c.startswith(("heat_industry_", "fuel_to_kiln"))
        ]
        assert heat_inputs and all(c.endswith(f"_{sector}") for c in heat_inputs), (sector, heat_inputs)

    model.write()
    written = model.output_folder / model.name
    techs = written / "set_technologies" / "set_conversion_technologies"
    assert (techs / "natural_gas_boiler_industry_paper" / "attributes.yaml").exists()
    assert (written / "set_carriers" / "heat_industry_150_200_food" / "attributes.yaml").exists()
    assert not (written / "set_carriers" / "heat_industry_150_200").exists()


def test_mixing_pooled_and_per_sector_heat_sectors_fails(tmp_path: Path):
    """Pooled low-temp heat pumps on top of the per-sector heat chain reference the
    pooled heat_industry_* carriers, which that model does not have."""
    model = _build_industry_model(tmp_path, ["industry_heat_per_sector", "industry_low_temp_heat"])
    with pytest.raises(ValueError, match="heat_industry_0_100"):
        model.write()


if __name__ == "__main__":
    pytest.main([__file__])
