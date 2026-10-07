"""Unit tests for the per-sector industry heat structure (V11, the *_per_sector
sectors): the whole industry heat chain exists once per sector (`<name>_<sector>`) so
heat carriers, waste heat and heat technologies cannot be shared between sectors, and
every capacity seed / limit is split so the totals over the sectors equal the pooled
(V10) values."""

from __future__ import annotations

import pandas as pd
import pytest

from zen_creator.datasets.datasets._industry_heat_utils import (
    FUEL_KEYS,
    INDUSTRY_HEAT_SECTORS,
    KILN_FUEL_SECTORS,
    MODEL_NODES,
    _demand_based_boiler_capacity_gw,
    boiler_capacity_existing_df_for_fuel,
    model_uses_per_sector_heat,
    total_industry_heat_demand_gw,
)
from zen_creator.datasets.datasets.process_parametrization import (
    DH_HEAT_PUMP_EXISTING_EU_GW,
    FEC_YEAR,
    HEAT_TEMP_LEVELS,
    ProcessParametrizationDataset,
)
from zen_creator.elements.carriers.industry_carriers import (
    FUEL_TO_KILN_CARRIER_CLASSES_BY_SECTOR,
    HEAT_CARRIER_CLASSES_BY_SECTOR,
    HeatIndustry150200,
)
from zen_creator.elements.conversion_technologies.industry_heat_supply import (
    BOILER_CLASSES_BY_SECTOR,
    CASCADE_CLASSES_BY_SECTOR,
    HEAT_PUMP_CLASSES_BY_SECTOR,
    KILN_FUEL_CLASSES_BY_SECTOR,
    HeatPumpIndustry150200WasteHeat,
    NaturalGasBoilerIndustry,
)
from zen_creator.elements.conversion_technologies.industry_production import GlassProduction
from zen_creator.elements.storage_technologies.industry_TES import TES_CLASSES_BY_SECTOR
from zen_creator.model import Model
from zen_creator.sectors.industry_heat import IndustryHeat, IndustryHeatPerSector
from zen_creator.sectors.industry_low_temp_heat import IndustryLowTempHeat, IndustryLowTempHeatPerSector
from zen_creator.sectors.industry_tes import IndustryTES, IndustryTESPerSector

HEAT_CARRIER_PREFIXES = ("heat_industry_", "fuel_to_kiln")


# -- structure selection ------------------------------------------------------------

def test_pooled_sectors_keep_v10_structure():
    heat = IndustryHeat().elements
    assert HeatPumpIndustry150200WasteHeat in heat and NaturalGasBoilerIndustry in heat
    assert len(IndustryLowTempHeat().elements) == 4
    assert len(IndustryTES().elements) == 3


def test_model_uses_per_sector_heat_reads_the_models_carriers(model: Model):
    assert model_uses_per_sector_heat(model) is False  # no industry heat at all
    model.add_element(HeatIndustry150200)
    assert model_uses_per_sector_heat(model) is False
    model.add_element(HEAT_CARRIER_CLASSES_BY_SECTOR["glass"]["150_200"])
    with pytest.raises(ValueError, match="mixes pooled"):
        model_uses_per_sector_heat(model)
    model.remove_element_by_name("heat_industry_150_200")
    assert model_uses_per_sector_heat(model) is True


def test_production_tech_follows_its_models_heat_structure(model: Model):
    pooled = GlassProduction(model=model)
    pooled.build()
    assert "fuel_to_kiln" in pooled.input_carrier.default_value

    for cls in (*HEAT_CARRIER_CLASSES_BY_SECTOR["glass"].values(), FUEL_TO_KILN_CARRIER_CLASSES_BY_SECTOR["glass"]):
        model.add_element(cls)
    per_sector = GlassProduction(model=model)
    per_sector.build()
    heat_inputs = [c for c in per_sector.input_carrier.default_value if c.startswith(HEAT_CARRIER_PREFIXES)]
    assert heat_inputs and all(c.endswith("_glass") for c in heat_inputs)


# -- structure ------------------------------------------------------------------

def test_per_sector_element_counts_and_names():
    heat = IndustryHeatPerSector().elements
    names = {cls.name for cls in heat}
    # 4 product carriers + 4 production + 2 post-comb = 10 shared; per sector: 3 heat carriers,
    # 2 top-band HPs, 6 boilers, 2 cascade techs = 13; glass/ceramic add fuel_to_kiln + 3 kiln techs
    assert len(heat) == 10 + 4 * 13 + 2 * 4
    assert len(names) == len(heat)  # no duplicates
    for sector in INDUSTRY_HEAT_SECTORS:
        assert f"heat_industry_150_200_{sector}" in names
        assert f"natural_gas_boiler_industry_{sector}" in names
        assert f"heat_industry_temp_conversion_100_{sector}" in names
        assert f"heat_pump_industry_150_200_waste_heat_{sector}" in names
    assert {f"fuel_to_kiln_{s}" for s in KILN_FUEL_SECTORS} <= names
    assert "fuel_to_kiln_paper" not in names and "fuel_to_kiln_food" not in names
    # none of the pooled heat elements remain
    assert not names & {"heat_industry_0_100", "heat_industry_150_200", "fuel_to_kiln", "biomass_boiler_industry"}

    assert len(IndustryLowTempHeatPerSector().elements) == 4 * 4
    assert len(IndustryTESPerSector().elements) == 3 * 4


@pytest.mark.parametrize("sector", INDUSTRY_HEAT_SECTORS)
def test_per_sector_technologies_only_use_their_own_sectors_heat_carriers(sector, model: Model):
    classes = [
        *HEAT_PUMP_CLASSES_BY_SECTOR[sector].values(),
        *BOILER_CLASSES_BY_SECTOR[sector],
        *CASCADE_CLASSES_BY_SECTOR[sector],
        *KILN_FUEL_CLASSES_BY_SECTOR.get(sector, []),
        *TES_CLASSES_BY_SECTOR[sector],
    ]
    for cls in classes:
        technology = cls(model=model)
        technology.build()
        assert technology.name.endswith(f"_{sector}")
        carriers = list(technology.reference_carrier.default_value)
        if hasattr(technology, "input_carrier"):
            carriers += technology.input_carrier.default_value + technology.output_carrier.default_value
        for carrier in carriers:
            if carrier.startswith(HEAT_CARRIER_PREFIXES):
                assert carrier.endswith(f"_{sector}"), (technology.name, carrier)


@pytest.mark.parametrize("sector", INDUSTRY_HEAT_SECTORS)
def test_per_sector_carriers_are_named_and_built(sector, model: Model):
    for level, cls in HEAT_CARRIER_CLASSES_BY_SECTOR[sector].items():
        carrier = cls(model=model)
        carrier.build()
        assert carrier.name == f"heat_industry_{level}_{sector}"
    if sector in KILN_FUEL_SECTORS:
        assert FUEL_TO_KILN_CARRIER_CLASSES_BY_SECTOR[sector].name == f"fuel_to_kiln_{sector}"


def test_production_techs_draw_on_their_own_sectors_heat_and_kiln_fuel():
    param = ProcessParametrizationDataset()
    for sector in INDUSTRY_HEAT_SECTORS:
        data = param.get_production_tech_dict(sector, per_sector_heat=True)
        carriers = data["input_carrier"]["default_value"]
        for carrier in carriers:
            if carrier.startswith(HEAT_CARRIER_PREFIXES):
                assert carrier.endswith(f"_{sector}"), (sector, carrier)
        cf_carriers = {c for entry in data["conversion_factor"] for c in entry}
        assert cf_carriers == set(carriers)
        assert not any(c in ("heat_industry_0_100", "heat_industry_150_200", "fuel_to_kiln") for c in carriers)
    for sector in KILN_FUEL_SECTORS:
        carriers = param.get_production_tech_dict(sector, per_sector_heat=True)["input_carrier"]["default_value"]
        assert f"fuel_to_kiln_{sector}" in carriers


def test_production_tech_dict_is_pooled_by_default():
    param = ProcessParametrizationDataset()
    carriers = param.get_production_tech_dict("glass")["input_carrier"]["default_value"]
    assert "fuel_to_kiln" in carriers
    assert not any(c.endswith("_glass") for c in carriers)
    assert "heat_industry_0_100" in carriers or "heat_industry_100_150" in carriers


# -- capacity seeds and limits sum to the pooled values -------------------------------

@pytest.mark.parametrize("level", HEAT_TEMP_LEVELS)
def test_hp_seed_is_split_over_sectors_not_multiplied(level, model: Model):
    param = ProcessParametrizationDataset()
    pooled = param.get_industry_hp_capacity_addition_unbounded(
        HeatPumpIndustry150200WasteHeat(model=model), level
    ).default_value
    per_sector_values = [
        param.get_industry_hp_capacity_addition_unbounded(
            HEAT_PUMP_CLASSES_BY_SECTOR[s][f"{level}_waste_heat"](model=model), level, s
        ).default_value
        for s in INDUSTRY_HEAT_SECTORS
    ]
    assert sum(per_sector_values) == pytest.approx(pooled)
    assert all(v > 0 for v in per_sector_values)
    assert max(per_sector_values) < pooled  # nobody gets the full pooled seed


def test_hp_seed_total_over_all_variants_equals_dh_snapshot(model: Model):
    """Σ over 3 bands × 2 variants × 4 sectors × nodes = DH_HEAT_PUMP_EXISTING_EU_GW."""
    param = ProcessParametrizationDataset()
    total = 0.0
    for level in HEAT_TEMP_LEVELS:
        for variant in ("waste_heat", "water"):
            for s in INDUSTRY_HEAT_SECTORS:
                cls = HEAT_PUMP_CLASSES_BY_SECTOR[s][f"{level}_{variant}"]
                total += param.get_industry_hp_capacity_addition_unbounded(
                    cls(model=model), level, s
                ).default_value * len(MODEL_NODES)
    assert total == pytest.approx(DH_HEAT_PUMP_EXISTING_EU_GW)


@pytest.mark.parametrize("level", HEAT_TEMP_LEVELS)
def test_waste_heat_limit_sums_to_pooled(level, model: Model, register_attribute):
    param = ProcessParametrizationDataset()
    element = HeatPumpIndustry150200WasteHeat(model=model)

    def limit(sector=None):
        attr = param.get_waste_heat_capacity_limit(element, level, sector)
        return register_attribute(attr).df["capacity_limit"].copy()

    pooled = limit()
    parts = [limit(s) for s in INDUSTRY_HEAT_SECTORS]
    pd.testing.assert_series_equal(sum(parts), pooled, check_names=False, rtol=1e-9)
    # a sector's waste heat can only be used by its own heat pumps, so each part is below the pool
    for part in parts:
        assert (part <= pooled + 1e-12).all()


def test_total_heat_demand_by_sector_sums_to_pooled():
    pooled = total_industry_heat_demand_gw(FEC_YEAR)
    parts = [total_industry_heat_demand_gw(FEC_YEAR, s) for s in INDUSTRY_HEAT_SECTORS]
    for node, value in pooled.items():
        assert sum(p[node] for p in parts) == pytest.approx(value)
    with pytest.raises(ValueError):
        total_industry_heat_demand_gw(FEC_YEAR, "cement")


@pytest.mark.parametrize("fuel", FUEL_KEYS)
def test_boiler_capacity_existing_sums_to_pooled(fuel):
    pooled = boiler_capacity_existing_df_for_fuel(fuel, FEC_YEAR, lifetime=20, year_construction=2022)
    parts = [
        boiler_capacity_existing_df_for_fuel(fuel, FEC_YEAR, lifetime=20, year_construction=2022, sector=s)
        for s in INDUSTRY_HEAT_SECTORS
    ]
    assert sum(p["capacity_existing"].sum() for p in parts) == pytest.approx(pooled["capacity_existing"].sum())


def test_per_sector_boiler_fuel_split_matches_both_totals_per_node():
    """Per node: each fuel sums over the sectors to the pooled value, and each sector's
    boilers sum to its own heat demand."""
    pooled = _demand_based_boiler_capacity_gw(FEC_YEAR)
    parts = {s: _demand_based_boiler_capacity_gw(FEC_YEAR, s) for s in INDUSTRY_HEAT_SECTORS}
    for node in MODEL_NODES:
        for fuel in FUEL_KEYS:
            assert sum(parts[s][node][fuel] for s in INDUSTRY_HEAT_SECTORS) == pytest.approx(
                pooled[node][fuel], rel=1e-6, abs=1e-9
            ), (node, fuel)
        for s in INDUSTRY_HEAT_SECTORS:
            assert sum(parts[s][node].values()) == pytest.approx(
                total_industry_heat_demand_gw(FEC_YEAR, s)[node], rel=1e-6, abs=1e-9
            ), (node, s)
            assert min(parts[s][node].values()) >= 0.0


def test_per_sector_boiler_fuel_split_follows_the_sectors_own_fuel_mix():
    """Swedish/Finnish biomass boilers belong to paper (JRC-IDEES: >90 % of SE paper's
    thermal energy is biomass), not spread evenly over the sectors as in V10."""
    for node in ("SE", "FI"):
        share = {}
        for s in INDUSTRY_HEAT_SECTORS:
            caps = _demand_based_boiler_capacity_gw(FEC_YEAR, s)[node]
            share[s] = caps["biomass"] / sum(caps.values())
        assert share["paper"] > share["glass"] and share["paper"] > share["ceramic"], (node, share)


@pytest.mark.parametrize("temp_levels", [("0_100",), ("0_100", "100_150")])
def test_cascade_demand_sums_to_pooled(temp_levels):
    param = ProcessParametrizationDataset()
    pooled = param._heat_demand_gw(temp_levels)
    parts = [param._heat_demand_gw(temp_levels, s) for s in INDUSTRY_HEAT_SECTORS]
    for node, value in pooled.items():
        assert sum(p[node] for p in parts) == pytest.approx(value)


def test_kiln_fuel_demand_sums_to_pooled_and_rejects_other_sectors():
    param = ProcessParametrizationDataset()
    for use_carrier_demand in (False, True):
        pooled = param._kiln_fuel_demand_gw(use_carrier_demand)
        parts = [param._kiln_fuel_demand_gw(use_carrier_demand, s) for s in KILN_FUEL_SECTORS]
        for node, value in pooled.items():
            assert sum(p[node] for p in parts) == pytest.approx(value)
    with pytest.raises(ValueError):
        param._kiln_fuel_demand_gw(sector="paper")


def test_kiln_fuel_demand_per_sector_finds_the_per_sector_carrier():
    """The per-sector production tech draws on fuel_to_kiln_<sector>, and the sizing must
    still find its conversion factor (a missing one would silently give 0 capacity)."""
    param = ProcessParametrizationDataset()
    for s in KILN_FUEL_SECTORS:
        assert sum(param._kiln_fuel_demand_gw(sector=s).values()) > 0.0
