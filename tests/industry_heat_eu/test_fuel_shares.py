import pandas as pd
import pytest

from zen_creator.industry_heat_eu.fuel_shares import (
    fec_shares,
    read_sector_thermal_fec,
    renormalized_fuel_shares,
    thermal_fec_by_carrier,
)


def test_thermal_fec_by_carrier_sums_blocks_across_parent_rows():
    df = pd.DataFrame(
        {
            0: [
                "Sector: Thermal A",
                "Solids",
                "Natural gas and biogas",
                "Sector: Thermal B",
                "Solids",
                "Biomass and waste",
                "Sector: Electric",
            ],
            1: [0, 10, 20, 0, 5, 15, 999],  # year 2000 column
        }
    )

    result = thermal_fec_by_carrier(df, ["Sector: Thermal A", "Sector: Thermal B"], year=2000)

    assert result == {"Solids": 15, "Natural gas and biogas": 20, "Biomass and waste": 15}


def test_thermal_fec_by_carrier_missing_row_raises():
    df = pd.DataFrame({0: ["Sector: Thermal A"], 1: [0]})
    with pytest.raises(ValueError, match="not found"):
        thermal_fec_by_carrier(df, ["Sector: Thermal B"], year=2000)


def test_fec_shares_normalises_to_one():
    shares = fec_shares({"a": 30.0, "b": 70.0})
    assert shares == {"a": pytest.approx(0.3), "b": pytest.approx(0.7)}
    assert sum(shares.values()) == pytest.approx(1.0)


def test_renormalized_fuel_shares_applies_cutoff_and_carrier_map():
    shares = {
        "Natural gas and biogas": 0.6,
        "Solids": 0.15,
        "Other liquids": 0.2,  # unmapped, excluded even though >= cutoff
        "Biomass and waste": 0.05,  # below cutoff, excluded
    }

    result = renormalized_fuel_shares(shares, cutoff=0.10)

    assert set(result) == {"natural_gas", "hard_coal"}
    assert result["natural_gas"] == pytest.approx(0.6 / 0.75)
    assert result["hard_coal"] == pytest.approx(0.15 / 0.75)
    assert sum(result.values()) == pytest.approx(1.0)


def test_read_sector_thermal_fec_glass_2023():
    breakdown = read_sector_thermal_fec("EU27", "glass", 2023)
    shares = renormalized_fuel_shares(fec_shares(breakdown))

    assert set(shares) == {"natural_gas", "hard_coal"}
    assert shares["natural_gas"] > shares["hard_coal"]
    assert sum(shares.values()) == pytest.approx(1.0)


def test_read_sector_thermal_fec_food_2023_is_natural_gas_only():
    breakdown = read_sector_thermal_fec("EU27", "food", 2023)
    shares = renormalized_fuel_shares(fec_shares(breakdown))

    assert shares == {"natural_gas": pytest.approx(1.0)}


def test_read_sector_thermal_fec_ceramic_2023_excludes_other_liquids():
    breakdown = read_sector_thermal_fec("EU27", "ceramic", 2023)
    shares = fec_shares(breakdown)

    # "Other liquids" is a sizeable share of ceramic thermal FEC but has no
    # Crystal Ball equivalent and must be excluded regardless of its share.
    assert shares["Other liquids"] > 0.10

    result = renormalized_fuel_shares(shares)
    assert set(result) == {"natural_gas", "hard_coal", "biomass"}
    assert sum(result.values()) == pytest.approx(1.0)
