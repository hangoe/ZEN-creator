import pandas as pd
import pytest

from zen_creator.industry_heat_eu.capacity_and_demand import (
    HOURS_PER_YEAR,
    MODEL_NODES,
    NODES_WITHOUT_IDEES,
    OPERATING_HOURS,
    biomass_boiler_capacity_existing_df,
    capacity_existing_df,
    electrode_boiler_capacity_existing_df,
    eurostat_gross_heat_gwh,
    food_capacity_existing_df,
    food_demand_df,
    heat_pump_capacity_existing_df,
    industry_demand_df,
    installed_capacity_kt,
    natural_gas_boiler_capacity_existing_df,
    physical_output_kt,
    section_by_label,
)
from zen_creator.industry_heat_eu.data.rehfeldt2017 import REHFELDT2017_FOOD


def test_section_by_label_reads_section_until_next_header():
    df = pd.DataFrame({0: [
        "Cement (kt)",
        "Installed capacity (kt production)",
        "Ceramics & other NMM (kt bricks eq.)",
        "Glass production  (kt)",
        "Capacity investment (kt production)",
        "Ceramics & other NMM (kt bricks eq.)",
    ], 1: [999, 0, 10.0, 20.0, 0, 999]})

    result = section_by_label(df, year=2000, header="Installed capacity (kt production)")

    assert result == {"Ceramics & other NMM (kt bricks eq.)": 10.0, "Glass production  (kt)": 20.0}


def test_installed_capacity_kt_de_glass_2023():
    kt = installed_capacity_kt("DE", "glass", 2023)
    assert kt == pytest.approx(8487.512516604324)


def test_installed_capacity_kt_de_paper_2023_sums_pulp_paper_printing():
    kt = installed_capacity_kt("DE", "paper", 2023)
    assert kt == pytest.approx(2458.988532598328 + 24460.53910487243 + 2018.638378999645)


def test_capacity_existing_df_covers_all_model_nodes_and_converts_units():
    df = capacity_existing_df("glass", 2023)

    assert set(df["node"]) == set(MODEL_NODES)
    assert (df["year_construction"] == 2023).all()

    de = df.set_index("node").loc["DE", "capacity_existing"]
    assert de == pytest.approx(8487.512516604324 * 1000 / OPERATING_HOURS)


def test_capacity_existing_df_zeroes_nodes_without_idees():
    df = capacity_existing_df("ceramic", 2023)

    for node in NODES_WITHOUT_IDEES:
        assert df.set_index("node").loc[node, "capacity_existing"] == 0.0


def test_food_capacity_existing_df_covers_all_model_nodes_and_sums_to_rehfeldt_activity():
    df = food_capacity_existing_df(2023)

    assert set(df["node"]) == set(MODEL_NODES)
    assert (df["year_construction"] == 2023).all()

    total_activity_mt = sum(entry["activity_Mt"] for entry in REHFELDT2017_FOOD.values())
    total_capacity = df["capacity_existing"].sum()
    assert total_capacity * OPERATING_HOURS / 1e6 == pytest.approx(total_activity_mt)


def test_food_capacity_existing_df_de_is_positive():
    df = food_capacity_existing_df(2023)

    de = df.set_index("node").loc["DE", "capacity_existing"]
    assert de > 0


def test_physical_output_kt_de_glass_2023():
    kt = physical_output_kt("DE", "glass", 2023)
    assert kt > 0


def test_industry_demand_df_covers_all_model_nodes_and_converts_units():
    df = industry_demand_df("glass", 2023)

    assert set(df["node"]) == set(MODEL_NODES)

    de = df.set_index("node").loc["DE", "demand"]
    assert de == pytest.approx(physical_output_kt("DE", "glass", 2023) * 1000 / HOURS_PER_YEAR)


def test_industry_demand_df_zeroes_nodes_without_idees():
    df = industry_demand_df("paper", 2023)

    for node in NODES_WITHOUT_IDEES:
        assert df.set_index("node").loc[node, "demand"] == 0.0


def test_food_demand_df_covers_all_model_nodes():
    df = food_demand_df(2023)

    assert set(df["node"]) == set(MODEL_NODES)
    assert (df["demand"] >= 0).all()


def test_food_demand_df_de_is_positive():
    df = food_demand_df(2023)

    de = df.set_index("node").loc["DE", "demand"]
    assert de > 0


def test_heat_pump_capacity_existing_df_one_row_per_node():
    df = heat_pump_capacity_existing_df()

    assert list(df.columns) == ["node", "year_construction", "capacity_existing"]
    assert set(df["node"]) <= set(MODEL_NODES)
    assert (df["capacity_existing"] > 0).all()
    assert df["node"].is_unique


def test_heat_pump_capacity_existing_df_converts_mw_to_gw_and_sums_plants():
    df = heat_pump_capacity_existing_df()

    # Total across all plants (1580.0 MW per the David2017 source table).
    total_capacity_gw = df["capacity_existing"].sum()
    assert total_capacity_gw == pytest.approx(1580.0 / 1000)


def test_heat_pump_capacity_existing_df_uses_default_year_for_single_plant_with_missing_est_year():
    df = heat_pump_capacity_existing_df()

    # Slovakia/Sereď (1.8 MW, only plant, no est_year) -> DAVID2017_DEFAULT_YEAR.
    sk = df.set_index("node").loc["SK"]
    assert sk["year_construction"] == 1998


def test_biomass_boiler_capacity_existing_df_covers_all_model_nodes_and_converts_units():
    df = biomass_boiler_capacity_existing_df(2023)

    assert set(df["node"]) == set(MODEL_NODES)
    assert (df["year_construction"] == 2023).all()
    assert (df["capacity_existing"] >= 0).all()

    heat_gwh = eurostat_gross_heat_gwh("Sheet 74", 2023)
    de = df.set_index("node").loc["DE", "capacity_existing"]
    assert de == pytest.approx(heat_gwh["Germany"] / OPERATING_HOURS)


def test_biomass_boiler_capacity_existing_df_zeroes_switzerland():
    df = biomass_boiler_capacity_existing_df(2023)

    assert df.set_index("node").loc["CH", "capacity_existing"] == 0.0


def test_eurostat_gross_heat_gwh_uses_latest_available_year_for_uk():
    # The Eurostat extract has no 2023 (":") value for the United Kingdom;
    # the latest available year (2019) should be used instead.
    heat_gwh = eurostat_gross_heat_gwh("Sheet 74", 2023)
    assert heat_gwh["United Kingdom"] == pytest.approx(1168.056)


def test_natural_gas_boiler_capacity_existing_df_covers_all_model_nodes_and_converts_units():
    df = natural_gas_boiler_capacity_existing_df(2023)

    assert set(df["node"]) == set(MODEL_NODES)
    assert (df["year_construction"] == 2023).all()
    assert (df["capacity_existing"] >= 0).all()

    heat_gwh = eurostat_gross_heat_gwh("Sheet 72", 2023)
    de = df.set_index("node").loc["DE", "capacity_existing"]
    assert de == pytest.approx(heat_gwh["Germany"] / OPERATING_HOURS)


def test_electrode_boiler_capacity_existing_df_covers_all_model_nodes():
    df = electrode_boiler_capacity_existing_df(2023)

    assert set(df["node"]) == set(MODEL_NODES)
    assert (df["year_construction"] == 2023).all()
    assert (df["capacity_existing"] >= 0).all()


def test_electrode_boiler_capacity_existing_df_subtracts_heat_pump_capacity():
    heat_gwh = eurostat_gross_heat_gwh("Sheet 83", 2023)
    heat_pump_capacity = heat_pump_capacity_existing_df().set_index("node")["capacity_existing"]

    # Belgium has no David2017 heat pump capacity, so its
    # electrode_boiler capacity_existing equals the unadjusted Eurostat value.
    with pytest.warns(UserWarning):
        df = electrode_boiler_capacity_existing_df(2023)

    be_electricity_capacity = heat_gwh["Belgium"] / OPERATING_HOURS
    be = df.set_index("node").loc["BE", "capacity_existing"]
    assert "BE" not in heat_pump_capacity.index
    assert be == pytest.approx(be_electricity_capacity)


def test_electrode_boiler_capacity_existing_df_warns_and_zeroes_on_negative(monkeypatch):
    import pandas as pd

    from industry_heat_eu import capacity_and_demand

    monkeypatch.setattr(
        capacity_and_demand,
        "boiler_capacity_existing_df",
        lambda sheet, year, year_construction=None: pd.DataFrame(
            {"node": ["AT"], "year_construction": [year_construction or year], "capacity_existing": [0.0]}
        ),
    )
    monkeypatch.setattr(
        capacity_and_demand,
        "heat_pump_capacity_existing_df",
        lambda: pd.DataFrame({"node": ["AT"], "year_construction": [2015], "capacity_existing": [0.0026]}),
    )

    with pytest.warns(UserWarning, match="AT"):
        df = capacity_and_demand.electrode_boiler_capacity_existing_df(2023)

    assert df.set_index("node").loc["AT", "capacity_existing"] == 0.0
