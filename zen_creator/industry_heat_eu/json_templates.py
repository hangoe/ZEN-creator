"""
Templates and helpers for writing Crystal Ball `attributes.json` files for
product carriers, fuel/energy carriers, and conversion technologies.
"""

import json
import pathlib

from zen_creator.industry_heat_eu.process_params import SectorParams

# Product carriers (e.g. glass, ceramic, paper, food) use "tonproduct" units.
PRODUCT_CARRIER_TEMPLATE = {
    "carbon_intensity_carrier_import": {"default_value": 0, "unit": "tons/tonproduct"},
    "carbon_intensity_carrier_export": {"default_value": 0, "unit": "tons/tonproduct"},
    "demand":                          {"default_value": 0, "unit": "tonproduct/hour"},
    "price_shed_demand":               {"default_value": "inf", "unit": "Euro/tonproduct"},
    "max_shed_demand":                 {"default_value": "inf", "unit": "1"},
    "availability_import":             {"default_value": 0, "unit": "tonproduct/hour"},
    "availability_export":             {"default_value": 0, "unit": "tonproduct/hour"},
    "availability_import_yearly":      {"default_value": "inf", "unit": "tonproduct"},
    "availability_export_yearly":      {"default_value": "inf", "unit": "tonproduct"},
    "price_export":                    {"default_value": 0, "unit": "Euro/tonproduct"},
    "price_import":                    {"default_value": 0, "unit": "Euro/tonproduct"},
}

# Fuel and heat carriers (e.g. heat_industry_0_100, heat_industry_100_200) use
# "GW" / "GWh" energy units.
ENERGY_CARRIER_TEMPLATE = {
    "carbon_intensity_carrier_import": {"default_value": 0.0, "unit": "kilotons/GWh"},
    "carbon_intensity_carrier_export": {"default_value": 0,   "unit": "kilotons/GWh"},
    "demand":                          {"default_value": 0,   "unit": "GW"},
    "price_shed_demand":               {"default_value": "inf","unit": "Euro/MWh"},
    "max_shed_demand":                 {"default_value": "inf","unit": "1"},
    "availability_import":             {"default_value": 0,   "unit": "GW"},
    "availability_export":             {"default_value": 0,   "unit": "GW"},
    "availability_import_yearly":      {"default_value": "inf","unit": "GWh"},
    "availability_export_yearly":      {"default_value": "inf","unit": "GWh"},
    "price_export":                    {"default_value": 0,   "unit": "Euro/MWh"},
    "price_import":                    {"default_value": 0,   "unit": "Euro/MWh"},
}


def _generic_tech_fields(
    *,
    capacity_unit: str,
    opex_specific_variable: float,
    opex_specific_variable_unit: str,
    opex_specific_fixed_unit: str,
    capex_specific_conversion: float,
    capex_unit: str,
) -> dict:
    """The technology attributes common to all conversion technologies, parametrized by unit."""
    return {
        "capacity_addition_min":        {"default_value": 0,     "unit": capacity_unit},
        "capacity_addition_max":        {"default_value": "inf", "unit": capacity_unit},
        "capacity_addition_unbounded":  {"default_value": 0,     "unit": capacity_unit},
        "capacity_existing":            {"default_value": 0,     "unit": capacity_unit},
        "capacity_limit":               {"default_value": "inf", "unit": capacity_unit},
        "min_load":                     {"default_value": 0,     "unit": "1"},
        "max_load":                     {"default_value": 1,     "unit": "1"},
        "lifetime":                     {"default_value": 0,     "unit": "1"},
        "opex_specific_variable":       {"default_value": opex_specific_variable, "unit": opex_specific_variable_unit},
        "carbon_intensity_technology":  {"default_value": 0,     "unit": "ton/tonproduct"},
        "construction_time":            {"default_value": 0,   "unit": "1"},
        "capacity_investment_existing": {"default_value": 0,   "unit": capacity_unit},
        "opex_specific_fixed":          {"default_value": 0.0, "unit": opex_specific_fixed_unit},
        "max_diffusion_rate":           {"default_value": "inf", "unit": "1"},
        "capex_specific_conversion":    {"default_value": capex_specific_conversion, "unit": capex_unit},
    }


def build_conversion_tech(
    *,
    product: str,
    fuel_shares: dict[str, float],
    params: SectorParams,
    opex_specific_variable: float,
) -> dict:
    """Assemble the attributes.json contents for a generic conversion technology.

    `fuel_shares` maps Crystal Ball fuel carrier names (e.g. "natural_gas",
    "hard_coal", "biomass") to their share of the technology's total fuel
    demand (`params.cf_fuel`), e.g. as produced by
    `fuel_shares.renormalized_fuel_shares`. Each carrier becomes its own
    input with conversion_factor = `params.cf_fuel * share`, so the
    technology draws its fuel mix directly rather than via an intermediate
    "fuel_for_X" carrier.

    `capex_specific_conversion`, `lifetime`, and `carbon_intensity_technology`
    are left at placeholder defaults (0); the real values are filled in from
    `input_data/Parametrization/process_parametrization.xlsx` via
    `excel_io.apply_excel_overrides`.
    """
    return {
        **_generic_tech_fields(
            capacity_unit="tonproduct/hour",
            opex_specific_variable=opex_specific_variable,
            opex_specific_variable_unit="Euro/tonproduct",
            opex_specific_fixed_unit="Euro/(tonproduct/h)",
            capex_specific_conversion=1.0,
            capex_unit="Euro/(tonproduct/h)",
        ),
        "reference_carrier": {"default_value": [product]},
        "input_carrier":     {"default_value": [*fuel_shares.keys(), "heat_industry_0_100", "heat_industry_100_200", "electricity"]},
        "output_carrier":    {"default_value": [product]},
        "conversion_factor": [
            *[
                {carrier: {"default_value": round(params.cf_fuel * share, 12), "unit": "GW/(tonproduct/hour)"}}
                for carrier, share in fuel_shares.items()
            ],
            {"heat_industry_0_100":   {"default_value": round(params.cf_lt_0_100,   12), "unit": "GW/(tonproduct/hour)"}},
            {"heat_industry_100_200": {"default_value": round(params.cf_lt_100_200, 12), "unit": "GW/(tonproduct/hour)"}},
            {"electricity":           {"default_value": round(params.cf_elec,        12), "unit": "GW/(tonproduct/hour)"}},
        ],
    }


def write_json(path: pathlib.Path, data: dict) -> pathlib.Path:
    """Write `data` to `path/attributes.json`, creating directories as needed."""
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / "attributes.json"
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    return file_path
