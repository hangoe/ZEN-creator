import json

import pytest

from zen_creator.industry_heat_eu.json_templates import (
    ENERGY_CARRIER_TEMPLATE,
    PRODUCT_CARRIER_TEMPLATE,
    build_conversion_tech,
    write_json,
)
from zen_creator.industry_heat_eu.process_params import SectorParams

PARAMS = SectorParams(
    fuel_GJ_t=3.6,
    lt_GJ_t_0_100=1.8,
    lt_GJ_t_100_200=0.0,
    elec_GJ_t=0.9,
    temp_dist={"<100": 0.5, "100-200": 0.0, "200-500": 0.0, "500-1000": 0.0, ">1000": 0.5},
)


def test_build_conversion_tech_carriers_and_factors():
    fuel_shares = {"natural_gas": 0.6, "hard_coal": 0.4}

    tech = build_conversion_tech(
        product="glass",
        fuel_shares=fuel_shares,
        params=PARAMS,
        opex_specific_variable=15.0,
    )

    assert tech["reference_carrier"]["default_value"] == ["glass"]
    assert tech["input_carrier"]["default_value"] == ["natural_gas", "hard_coal", "heat_industry_0_100", "heat_industry_100_200", "electricity"]
    assert tech["output_carrier"]["default_value"] == ["glass"]
    # lifetime and carbon_intensity_technology are placeholder 0; real values come from Excel.
    assert tech["lifetime"]["default_value"] == 0
    assert tech["carbon_intensity_technology"]["default_value"] == 0
    assert tech["opex_specific_variable"]["default_value"] == 15.0

    factors = {list(entry)[0]: entry for entry in tech["conversion_factor"]}
    assert factors["natural_gas"]["natural_gas"]["default_value"] == pytest.approx(PARAMS.cf_fuel * 0.6)
    assert factors["hard_coal"]["hard_coal"]["default_value"] == pytest.approx(PARAMS.cf_fuel * 0.4)
    assert factors["heat_industry_0_100"]["heat_industry_0_100"]["default_value"] == pytest.approx(PARAMS.cf_lt_0_100)
    assert factors["heat_industry_100_200"]["heat_industry_100_200"]["default_value"] == pytest.approx(PARAMS.cf_lt_100_200)
    assert factors["electricity"]["electricity"]["default_value"] == pytest.approx(PARAMS.cf_elec)


def test_build_conversion_tech_default_capex_has_placeholder():
    tech = build_conversion_tech(
        product="ceramic",
        fuel_shares={"natural_gas": 1.0},
        params=PARAMS,
        opex_specific_variable=10.0,
    )
    assert tech["capex_specific_conversion"]["default_value"] == 1.0
    assert tech["capex_specific_conversion"]["unit"] == "Euro/(tonproduct/h)"


def test_write_json_creates_file_and_directories(tmp_path):
    path = tmp_path / "set_carriers" / "glass"
    result = write_json(path, PRODUCT_CARRIER_TEMPLATE)

    assert result == path / "attributes.json"
    assert result.exists()
    assert json.loads(result.read_text()) == PRODUCT_CARRIER_TEMPLATE


def test_carrier_templates_are_distinct():
    assert PRODUCT_CARRIER_TEMPLATE["demand"]["unit"] == "tonproduct/hour"
    assert ENERGY_CARRIER_TEMPLATE["demand"]["unit"] == "GW"
