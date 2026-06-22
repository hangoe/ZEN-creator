"""Lazily computed and cached parameters for industry heat elements.

All expensive computations (Excel reads, FAOSTAT queries) happen once on
first access and are cached for subsequent use by the Element subclasses.
"""

import copy
import functools
import pathlib

from zen_creator.industry_heat_eu.capacity_and_demand import (
    biomass_boiler_capacity_existing_df,
    capacity_existing_df,
    electrode_boiler_capacity_existing_df,
    food_capacity_existing_df,
    food_demand_df,
    heat_pump_capacity_existing_df,
    industry_demand_df,
    natural_gas_boiler_capacity_existing_df,
)
from zen_creator.industry_heat_eu.data.aidres2023 import (
    AIDRES2023_GLASS,
    AIDRES2023_GLASS_SHARES,
)
from zen_creator.industry_heat_eu.data.jrc_eu_times import (
    GLASS_AIDRES_TO_JRC,
    PAPER_REHFELDT_TO_JRC,
    PARAM_BASE_YEAR,
    gdp_deflator_ratio,
    sector_weighted_params,
)
from zen_creator.industry_heat_eu.data.rehfeldt2017 import (
    REHFELDT2017_CERAMIC,
    REHFELDT2017_FOOD,
    REHFELDT2017_GLASS,
    REHFELDT2017_PAPER,
)
from zen_creator.industry_heat_eu.excel_io import (
    build_tech_from_table,
    load_param_column,
    tech_columns,
)
from zen_creator.industry_heat_eu.fuel_shares import (
    fec_shares,
    read_sector_thermal_fec,
    renormalized_fuel_shares,
)
from zen_creator.industry_heat_eu.process_params import (
    activity_weights,
    compute_sector_params,
)

FEC_YEAR = 2023
FEC_COUNTRY = "EU27"
CAPACITY_YEAR = 2022
JRC_COST_TARGET_YEAR = 2019

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
INPUT_DATA = REPO_ROOT / "input_data"
PROCESS_XLSX = INPUT_DATA / "Parametrization" / "process_parametrization.xlsx"
PROCESS_SHEET = "process_techs"
CARRIER_XLSX = INPUT_DATA / "Parametrization" / "industry_carriers.xlsx"
CARRIER_SHEET = "carriers"
HEAT_XLSX = INPUT_DATA / "Parametrization" / "heat_tech_parametrization.xlsx"
HEAT_SHEET = "heat_techs"
BAT_PAPER_CSV = INPUT_DATA / "JRC-BAT" / "JRC_BAT_Paper2014_Table1_2.csv"


@functools.cache
def sector_params():
    """Compute SectorParams for all four sectors."""
    glass = compute_sector_params(
        AIDRES2023_GLASS, REHFELDT2017_GLASS, AIDRES2023_GLASS_SHARES, fuel_key="ng_GJ_t",
    )
    ceramic_w = activity_weights(REHFELDT2017_CERAMIC)
    ceramic = compute_sector_params(REHFELDT2017_CERAMIC, REHFELDT2017_CERAMIC, ceramic_w)
    paper_w = activity_weights(REHFELDT2017_PAPER)
    paper = compute_sector_params(REHFELDT2017_PAPER, REHFELDT2017_PAPER, paper_w)
    food_w = activity_weights(REHFELDT2017_FOOD)
    food = compute_sector_params(REHFELDT2017_FOOD, REHFELDT2017_FOOD, food_w)
    return {"glass": glass, "ceramic": ceramic, "paper": paper, "food": food}


@functools.cache
def fuel_mix_shares():
    """Compute fuel mix shares for all four sectors."""
    result = {}
    for sector in ["glass", "ceramic", "paper", "food"]:
        breakdown = read_sector_thermal_fec(FEC_COUNTRY, sector, FEC_YEAR)
        result[sector] = renormalized_fuel_shares(fec_shares(breakdown))
    return result


@functools.cache
def process_tech_overrides(tech_name: str) -> dict:
    """Load parameter overrides from process_parametrization.xlsx."""
    return load_param_column(PROCESS_XLSX, PROCESS_SHEET, tech_name)


@functools.cache
def carrier_overrides(carrier_name: str) -> dict:
    """Load parameter overrides from industry_carriers.xlsx."""
    return load_param_column(CARRIER_XLSX, CARRIER_SHEET, carrier_name)


@functools.cache
def heat_tech_base_data(tech_name: str) -> dict:
    """Load a heat technology's full attributes from heat_tech_parametrization.xlsx."""
    return build_tech_from_table(HEAT_XLSX, HEAT_SHEET, tech_name)


@functools.cache
def heat_tech_names() -> list[str]:
    """List heat technology column names from heat_tech_parametrization.xlsx."""
    return tech_columns(HEAT_XLSX, HEAT_SHEET)


@functools.cache
def heat_capacity_split() -> dict[str, float]:
    """Compute the demand-weighted temperature-level capacity split."""
    params = sector_params()
    demand_volumes = {
        "glass": industry_demand_df("glass", FEC_YEAR)["demand"].sum(),
        "ceramic": industry_demand_df("ceramic", FEC_YEAR)["demand"].sum(),
        "paper": industry_demand_df("paper", FEC_YEAR)["demand"].sum(),
        "food": food_demand_df(FEC_YEAR)["demand"].sum(),
    }
    total_0_100 = sum(demand_volumes[s] * params[s].cf_lt_0_100 for s in demand_volumes)
    total_100_200 = sum(demand_volumes[s] * params[s].cf_lt_100_200 for s in demand_volumes)
    total = total_0_100 + total_100_200
    return {"0_100": total_0_100 / total, "100_200": total_100_200 / total}


@functools.cache
def jrc_cost_params(sector: str) -> dict:
    """Compute JRC-EU-TIMES cost parameters for a sector."""
    if sector == "glass":
        return sector_weighted_params(GLASS_AIDRES_TO_JRC, AIDRES2023_GLASS_SHARES, JRC_COST_TARGET_YEAR)
    elif sector == "paper":
        paper_w = activity_weights(REHFELDT2017_PAPER)
        return sector_weighted_params(PAPER_REHFELDT_TO_JRC, paper_w, JRC_COST_TARGET_YEAR)
    elif sector == "food":
        deflator = gdp_deflator_ratio(PARAM_BASE_YEAR, JRC_COST_TARGET_YEAR)
        return {
            "capex_specific_conversion": round(300 * deflator * 8760, 2),
            "opex_specific_fixed": round(15 * deflator * 8760, 2),
            "opex_specific_variable": 0.0,
            "lifetime": 20,
        }
    else:
        return {}
