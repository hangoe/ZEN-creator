"""Unit tests for ProcessParametrizationDataset (process_parametrization.py).

Covers the kiln-fuel-switching share split, the Wolf2017 100-150/150-200
temperature split, the hand-derived JRC/Gardarsdottir cost formulas per sector,
and the heat-capacity/waste-heat allocation helpers -- none of which had direct
test coverage (see cleanup plan, Phase 2 item 2).
"""

from __future__ import annotations

import pytest

from zen_creator.datasets.datasets.process_parametrization import (
    KILN_NG_SWITCHABLE_SHARE,
    ProcessParametrizationDataset,
    _kiln_fuel_shares,
)


# -- _kiln_fuel_shares (pure function) ---------------------------------------

def test_kiln_fuel_shares_glass_is_fully_switchable():
    """Glass: KILN_NG_SWITCHABLE_SHARE == 1.0, so all natural_gas becomes
    fuel_to_kiln with no natural_gas remainder."""
    shares = {"natural_gas": 0.6, "hard_coal": 0.4}
    result = _kiln_fuel_shares("glass", shares)
    assert result == pytest.approx({"hard_coal": 0.4, "fuel_to_kiln": 0.6})


def test_kiln_fuel_shares_ceramic_splits_natural_gas():
    """Ceramic: only a fraction of natural_gas is switchable; the remainder
    stays a direct natural_gas share."""
    shares = {"natural_gas": 0.5, "biomass": 0.5}
    result = _kiln_fuel_shares("ceramic", shares)
    switchable = KILN_NG_SWITCHABLE_SHARE["ceramic"]
    assert result["fuel_to_kiln"] == pytest.approx(0.5 * switchable)
    assert result["natural_gas"] == pytest.approx(0.5 * (1 - switchable))
    assert result["biomass"] == pytest.approx(0.5)
    # total mass/energy share is conserved across the split
    assert sum(result.values()) == pytest.approx(sum(shares.values()))


def test_kiln_fuel_shares_noop_for_sectors_without_switching():
    """Paper/food have no kiln fuel-switching split -- shares pass through unchanged."""
    shares = {"natural_gas": 0.5, "biomass": 0.5}
    for sector in ("paper", "food"):
        assert _kiln_fuel_shares(sector, shares) == shares


def test_kiln_fuel_shares_noop_without_natural_gas():
    shares = {"biomass": 1.0}
    assert _kiln_fuel_shares("glass", shares) == shares


# -- ProcessParametrizationDataset (real data, computed once in __init__) ---

@pytest.fixture(scope="module")
def dataset() -> ProcessParametrizationDataset:
    return ProcessParametrizationDataset()


def test_wolf_split_sums_to_one(dataset):
    """Each sector's Wolf2017-derived (100-150, 150-200) split must be a
    normalized share pair, even where the raw percentages don't sum to 100%."""
    for sector, (share_100, share_150) in dataset._wolf_split.items():
        assert share_100 + share_150 == pytest.approx(1.0)
        assert share_100 >= 0
        assert share_150 >= 0


def test_cost_params_pinned_values(dataset):
    """Characterization test for _compute_jrc_cost_params -- these are the
    hand-derived Gardarsdottir2022 (ceramic)/literature-anchored (paper)/
    JRC-EU-TIMES-deflated (glass, food) cost formulas documented in the module.
    Pins current output so a refactor (e.g. moving these into a shared helper)
    can be checked for exact equivalence."""
    glass = dataset._cost_params["glass"]
    assert glass["lifetime"] == 28
    assert glass["capex_specific_conversion"] == pytest.approx(2183366.386198919)
    assert glass["opex_specific_fixed"] == pytest.approx(166351.72466277477)
    assert glass["opex_specific_variable"] == pytest.approx(59.343509083467026)

    ceramic = dataset._cost_params["ceramic"]
    assert ceramic["lifetime"] == 25
    assert ceramic["capex_specific_conversion"] == pytest.approx(1820124.59)
    assert ceramic["opex_specific_fixed"] == pytest.approx(156958.98)
    assert ceramic["opex_specific_variable"] == pytest.approx(7.27)

    paper = dataset._cost_params["paper"]
    assert paper["lifetime"] == 25
    assert paper["capex_specific_conversion"] == pytest.approx(6132000)
    assert paper["opex_specific_fixed"] == pytest.approx(950445.4215673686)
    assert paper["opex_specific_variable"] == pytest.approx(4.990975245475023)

    food = dataset._cost_params["food"]
    assert food["lifetime"] == 20
    assert food["capex_specific_conversion"] == pytest.approx(3119094.84)
    assert food["opex_specific_fixed"] == pytest.approx(155954.74)
    assert food["opex_specific_variable"] == pytest.approx(0.0)


def test_get_heat_capacity_split_sums_to_one(dataset):
    """The 0-100/100-150/150-200 demand-weighted heat-capacity split across
    glass/ceramic/paper/food must sum to 1 (it partitions total heat demand)."""
    split = dataset.get_heat_capacity_split()
    assert set(split) == {"0_100", "100_150", "150_200"}
    assert sum(split.values()) == pytest.approx(1.0)
    assert all(v >= 0 for v in split.values())


def test_get_waste_heat_capacity_limit_sums_to_level_independent_total(dataset, model):
    """capacity_limit at each level = total high-temp waste heat x share_at_level,
    where the three levels' shares (per sector) sum to 1 -- so summed *across* the
    three levels, the per-node total must equal sum_s demand[s] x cf_fuel[s],
    independent of the Wolf2017 100-150/150-200 split."""
    from zen_creator.datasets.datasets._industry_heat_utils import (
        ceramic_demand_from_fec_df,
        food_capacity_existing_df,
        industry_demand_df,
    )
    from zen_creator.datasets.datasets.process_parametrization import FEC_YEAR
    from zen_creator.elements.conversion_technologies.industry_heat_supply import (
        HeatPumpIndustry0100WasteHeat,
    )

    element = HeatPumpIndustry0100WasteHeat(model=model)
    dfs = {}
    for level in ("0_100", "100_150", "150_200"):
        attr = dataset.get_waste_heat_capacity_limit(element, level)
        dfs[level] = attr.df["capacity_limit"]
        assert (dfs[level] >= 0).all()

    summed = dfs["0_100"] + dfs["100_150"] + dfs["150_200"]

    demands = {
        "glass": industry_demand_df("glass", FEC_YEAR).set_index("node")["demand"],
        "ceramic": ceramic_demand_from_fec_df(FEC_YEAR).set_index("node")["kt_yr"] * 1000.0 / 8760,
        "paper": industry_demand_df("paper", FEC_YEAR).set_index("node")["demand"],
        "food": food_capacity_existing_df(FEC_YEAR).set_index("node")["capacity_existing"],
    }
    cf_fuel = {s: dataset._sector_params[s].cf_fuel for s in demands}
    expected_total = sum(demands[s] * cf_fuel[s] for s in demands)

    for node in expected_total.index:
        assert summed[node] == pytest.approx(expected_total[node], rel=1e-9)


def test_kiln_fuel_switch_capacity_existing_only_natural_gas_nonzero(dataset, model):
    """Only natural_gas_to_kilnfuel starts with existing capacity; hydrogen/
    electricity_to_kilnfuel are built from scratch (see method docstring)."""
    from zen_creator.elements.conversion_technologies.industry_heat_supply import (
        HydrogenToKilnfuel,
        NaturalGasToKilnfuel,
    )

    ng_element = NaturalGasToKilnfuel(model=model)
    h2_element = HydrogenToKilnfuel(model=model)

    ng_attr = dataset.get_kiln_fuel_switch_capacity_existing(ng_element, "natural_gas")
    h2_attr = dataset.get_kiln_fuel_switch_capacity_existing(h2_element, "hydrogen")
    elec_attr = dataset.get_kiln_fuel_switch_capacity_existing(h2_element, "electricity")

    assert ng_attr.df is not None
    assert (ng_attr.df["capacity_existing"] >= 0).all()
    assert ng_attr.df["capacity_existing"].sum() > 0

    assert h2_attr.df is None
    assert h2_attr.default_value == 0.0
    assert elec_attr.df is None
    assert elec_attr.default_value == 0.0


if __name__ == "__main__":
    pytest.main([__file__])
