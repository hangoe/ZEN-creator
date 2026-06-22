#!/usr/bin/env python3
"""
compute_params.py

Computes conversion technology parameters for generic industrial processes
in the Crystal Ball energy system model and writes the corresponding JSON
files into the dataset directory structure.

Sectors
-------
- glass_production           (Rehfeldt + AIDRES)
- ceramic_production          (Rehfeldt only)
- paper_production              (Rehfeldt only)
- food_production                (Rehfeldt only)

Raw data sources
-----------------
Rehfeldt et al. (2017): Table 1 - specific energy consumption (SEC, GJ/t),
    temperature distribution (shares per level), and EU28+3 activity (Mt).
    See industry_heat_eu/data/rehfeldt2017.py.
    doi: 10.1007/s12053-017-9571-y

AIDRES (2023): Section 7 - glass production routes (container, flat, fibre),
    energy flows per tonne [GJ/t] for the natural-gas reference route, and
    direct process emissions [tCO2/t]. See industry_heat_eu/data/aidres2023.py.

General design decisions
-------------------------
1. Low-temperature heat separation:
   Fuel heat demand is split by Rehfeldt temperature bin into three ranges:
   '<100' → heat_industry_0_100, '100-200' → heat_industry_100_200, and
   '>200' remains as high-temperature 'fuel' input. The optimizer can then
   choose the cheapest supply technology per temperature level.
   Only the fuel demand is split; electricity is kept as a single input.

2. Unit conversion:
   Crystal Ball stores conversion factors in GW / (tonproduct/h).
   1 GJ/t -> 1/3600 GW / (tonproduct/h)

3. CAPEX and other table-driven defaults:
   capex_specific_conversion (and several other attributes such as
   opex_specific_fixed and max_diffusion_rate) are not computed here.
   Code builds each technology with placeholder defaults
   (capex_specific_conversion = 1.0 EUR/(tonproduct/h), consistent with
   cement_kiln), then `write_production_tech` overwrites these defaults with
   the values from `input_data/Parametrization/process_parametrization.xlsx`,
   which is the source of truth for these table-driven parameters.

4. Fuel mix:
   Each X_production technology takes its high-temperature fuel demand
   (`params.cf_fuel`) directly as a mix of primary energy carriers
   (natural_gas, hard_coal, biomass), split according to the sector's
   JRC-IDEES-2023 EU27 2023 thermal FEC shares (>=10% cutoff, see
   industry_heat_eu.fuel_shares). There is no intermediate "fuel_for_X"
   carrier or "fuels_to_X_fuel" mixing technology.

5. Carrier defaults:
   The new carriers (glass, ceramic, paper, food, heat_industry_0_100,
   heat_industry_100_200) are built from `PRODUCT_CARRIER_TEMPLATE` /
   `ENERGY_CARRIER_TEMPLATE`,
   then `write_carrier` overwrites their defaults with the corresponding
   column of `input_data/Parametrization/industry_carriers.xlsx`, the
   source of truth for these carriers' attributes.

Output
------
Writes attributes.json under outputs/model/industry_heat_eu/:
  - set_carriers/{glass, ceramic, paper, food}/
  - set_carriers/heat_industry_0_100/
  - set_carriers/heat_industry_100_200/
  - set_technologies/set_conversion_technologies/{glass,ceramic,paper,food}_production/

Also writes capacity_existing.csv (one row per node, see
industry_heat_eu.capacity_and_demand) for glass_production, ceramic_production
and paper_production, from JRC-IDEES-2023's "Installed capacity (kt
production)", and for food_production from FAOSTAT production data combined
with Rehfeldt's subsector activity shares (IDEES only reports a production
index for food, not a tonnage).

Also writes demand.csv (one row per node) for:
  - the "glass", "ceramic" and "paper" carriers, from JRC-IDEES-2023's
    "Physical output (kt)" (see industry_heat_eu.capacity_and_demand.industry_demand_df).
    ASSUMPTION: demand is approximated by national physical output (net trade
    is not modelled).
  - the "food" carrier, from FAOSTAT Food Balance Sheet "Feed" use of the
    Rehfeldt subsector proxy items (see industry_heat_eu.capacity_and_demand.food_demand_df).
"""

import copy
import pathlib
import shutil

import pandas as pd

import openpyxl
from openpyxl.styles import PatternFill

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
from zen_creator.industry_heat_eu.data.aidres2023 import AIDRES2023_GLASS, AIDRES2023_GLASS_SHARES
from zen_creator.industry_heat_eu.data.jrc_eu_times import (
    GLASS_AIDRES_TO_JRC,
    PAPER_REHFELDT_TO_JRC,
    PARAM_BASE_YEAR,
    gdp_deflator_ratio,
    sector_weighted_params,
)
from zen_creator.industry_heat_eu.data.rehfeldt2017 import REHFELDT2017_CERAMIC, REHFELDT2017_FOOD, REHFELDT2017_GLASS, REHFELDT2017_PAPER
from zen_creator.industry_heat_eu.excel_io import apply_excel_overrides, build_tech_from_table, load_param_column, tech_columns, write_param_column
from zen_creator.industry_heat_eu.fuel_shares import SECTOR_THERMAL_FEC_ROWS, fec_shares, read_sector_thermal_fec, renormalized_fuel_shares
from zen_creator.industry_heat_eu.json_templates import (
    ENERGY_CARRIER_TEMPLATE,
    PRODUCT_CARRIER_TEMPLATE,
    build_conversion_tech,
    write_json,
)
from zen_creator.industry_heat_eu.process_params import activity_weights, compute_sector_params, print_summary

FEC_YEAR = 2023
FEC_COUNTRY = "EU27"
# Must be <= Crystal Ball system.json reference_year (currently 2022).
# ZEN-garden only recognises capacity_existing entries with year_construction <= reference_year.
CAPACITY_YEAR = 2022
# Reference price year for JRC-EU-TIMES cost parameters (matches model publication year).
JRC_COST_TARGET_YEAR = 2019

SCRIPT_DIR = pathlib.Path(__file__).parent
MODEL_DIR = SCRIPT_DIR.parent / "outputs" / "model" / "industry_heat_eu"
CARRIERS = MODEL_DIR / "set_carriers"
CONV_TECH = MODEL_DIR / "set_technologies" / "set_conversion_technologies"

PROCESS_XLSX = SCRIPT_DIR.parent / "input_data" / "Parametrization" / "process_parametrization.xlsx"
PROCESS_SHEET = "process_techs"

CARRIER_XLSX = SCRIPT_DIR.parent / "input_data" / "Parametrization" / "industry_carriers.xlsx"
CARRIER_SHEET = "carriers"

HEAT_XLSX = SCRIPT_DIR.parent / "input_data" / "Parametrization" / "heat_tech_parametrization.xlsx"
HEAT_SHEET = "heat_techs"

BAT_PAPER_CSV = SCRIPT_DIR.parent / "input_data" / "JRC-BAT" / "JRC_BAT_Paper2014_Table1_2.csv"
BAT_PAPER_NODES = {"Switzerland": "CH", "Norway": "NO", "United Kingdom": "UK"}


def write_production_tech(tech_name, *, product, fuel_shares, params, opex_specific_variable):
    """Compute, persist, and write the attributes.json for a production technology.

    1. Writes the freshly computed conversion factors (including one per
       fuel-mix carrier in `fuel_shares`, each `params.cf_fuel * share`) and
       the resulting `input_carrier` list into `process_parametrization.xlsx`
       (column `tech_name`), so the table always reflects the current model.
    2. Builds the attributes dict from the code-computed parameters.
    3. Overwrites its default_values with `process_parametrization.xlsx`, which is the
       source of truth for capex, opex_fixed, max_diffusion_rate, lifetime,
       carbon_intensity_technology, etc.
    """
    conversion_factor_map = {
        **{f"conversion_factor:{carrier}": carrier for carrier in fuel_shares},
        "conversion_factor:heat_industry_0_100":   "heat_industry_0_100",
        "conversion_factor:heat_industry_100_200": "heat_industry_100_200",
        "conversion_factor:electricity": "electricity",
    }
    write_param_column(PROCESS_XLSX, PROCESS_SHEET, tech_name, {
        **{f"conversion_factor:{carrier}": round(params.cf_fuel * share, 12) for carrier, share in fuel_shares.items()},
        "conversion_factor:heat_industry_0_100":   round(params.cf_lt_0_100,   12),
        "conversion_factor:heat_industry_100_200": round(params.cf_lt_100_200, 12),
        "conversion_factor:electricity": round(params.cf_elec, 12),
        "input_carrier": "; ".join([*fuel_shares.keys(), "heat_industry_0_100", "heat_industry_100_200", "electricity"]),
    })

    data = build_conversion_tech(
        product=product, fuel_shares=fuel_shares, params=params,
        opex_specific_variable=opex_specific_variable,
    )
    overrides = load_param_column(PROCESS_XLSX, PROCESS_SHEET, tech_name)
    data = apply_excel_overrides(data, overrides, conversion_factor_map=conversion_factor_map)
    return write_json(CONV_TECH / tech_name, data)


def write_capacity_existing(tech_name, sector):
    """Write capacity_existing.csv for `tech_name` from `sector`'s IDEES
    "Installed capacity" (see industry_heat_eu.capacity_and_demand)."""
    df = capacity_existing_df(sector, FEC_YEAR, year_construction=CAPACITY_YEAR)
    path = CONV_TECH / tech_name / "capacity_existing.csv"
    df.to_csv(path, index=False)
    return path


def write_food_capacity_existing():
    """Write capacity_existing.csv for food_production from FAOSTAT
    production shares and Rehfeldt's subsector activity (see
    industry_heat_eu.capacity_and_demand.food_capacity_existing_df)."""
    df = food_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR)
    path = CONV_TECH / "food_production" / "capacity_existing.csv"
    df.to_csv(path, index=False)
    return path




def write_food_demand():
    """Write demand.csv for the "food" carrier from FAOSTAT Food Balance
    Sheet "Feed" use (see industry_heat_eu.capacity_and_demand.food_demand_df)."""
    df = food_demand_df(FEC_YEAR)
    path = CARRIERS / "food" / "demand.csv"
    df.to_csv(path, index=False)
    return path


def write_industry_demand(carrier, sector):
    """Write demand.csv for `carrier` from `sector`'s IDEES "Physical output"
    (see industry_heat_eu.capacity_and_demand.industry_demand_df).

    ASSUMPTION: demand is approximated by national physical output (net trade
    is not modelled).
    """
    df = industry_demand_df(sector, FEC_YEAR)
    path = CARRIERS / carrier / "demand.csv"
    df.to_csv(path, index=False)
    return path


def write_carrier(carrier_name, template):
    """Build the attributes.json for a carrier from `template`, overwritten
    with `industry_carriers.xlsx`'s `carrier_name` column."""
    data = copy.deepcopy(template)
    overrides = load_param_column(CARRIER_XLSX, CARRIER_SHEET, carrier_name)
    data = apply_excel_overrides(data, overrides)
    return write_json(CARRIERS / carrier_name, data)


def write_direct_cost_params(
    tech_col: str,
    *,
    invcost: float,
    fixom: float,
    varom: float,
    lifetime: int,
) -> None:
    """Write cost parameters directly (no JRC lookup) to
    process_parametrization.xlsx (green fill), applying the same 2006→target
    year deflator and ×8760 unit conversion as `write_sector_cost_params`.
    """
    deflator = gdp_deflator_ratio(PARAM_BASE_YEAR, JRC_COST_TARGET_YEAR)
    updates = {
        "capex_specific_conversion": round(invcost * deflator * 8760, 2),
        "opex_specific_fixed":       round(fixom * deflator * 8760, 2),
        "opex_specific_variable":    round(varom * deflator, 2),
        "lifetime":                  lifetime,
    }

    green_fill = PatternFill("solid", fgColor="C6EFCE")
    wb = openpyxl.load_workbook(PROCESS_XLSX)
    ws = wb[PROCESS_SHEET]

    headers   = {ws.cell(1, j).value: j for j in range(1, ws.max_column + 1)}
    col_tech  = headers[tech_col]
    param_rows = {ws.cell(i, 1).value: i for i in range(2, ws.max_row + 1) if ws.cell(i, 1).value}

    for param, value in updates.items():
        if param not in param_rows:
            continue
        r = param_rows[param]
        cell = ws.cell(r, col_tech)
        cell.value = value
        cell.fill  = green_fill

    wb.save(PROCESS_XLSX)
    print(
        f"  {tech_col} written to Excel ({JRC_COST_TARGET_YEAR} prices, "
        f"deflator 2006→{JRC_COST_TARGET_YEAR}={deflator:.3f}):"
    )
    for param, value in updates.items():
        fmt = "d" if param == "lifetime" else ",.2f"
        print(f"    {param}: {value:{fmt}}")


def write_sector_cost_params(
    tech_col: str,
    sector_label: str,
    jrc_mapping: dict[str, str],
    activity_wts: dict[str, float],
) -> None:
    """Write JRC-EU-TIMES capex/opex/lifetime values for `tech_col` to
    process_parametrization.xlsx (green fill). Derivation documented in
    ASSUMPTIONS.md. Call before write_production_tech so apply_excel_overrides
    picks up the new values when building the JSON.
    """
    cost = sector_weighted_params(jrc_mapping, activity_wts, JRC_COST_TARGET_YEAR)

    updates = {
        "capex_specific_conversion": round(cost["capex_specific_conversion"], 2),
        "opex_specific_fixed":       round(cost["opex_specific_fixed"],       2),
        "opex_specific_variable":    round(cost["opex_specific_variable"],     2),
        "lifetime":                  int(cost["lifetime"]),
    }

    green_fill = PatternFill("solid", fgColor="C6EFCE")
    wb = openpyxl.load_workbook(PROCESS_XLSX)
    ws = wb[PROCESS_SHEET]

    headers   = {ws.cell(1, j).value: j for j in range(1, ws.max_column + 1)}
    col_tech  = headers[tech_col]
    param_rows = {ws.cell(i, 1).value: i for i in range(2, ws.max_row + 1) if ws.cell(i, 1).value}

    for param, value in updates.items():
        if param not in param_rows:
            continue
        r = param_rows[param]
        cell = ws.cell(r, col_tech)
        cell.value = value
        cell.fill  = green_fill

    wb.save(PROCESS_XLSX)
    deflator = gdp_deflator_ratio(PARAM_BASE_YEAR, JRC_COST_TARGET_YEAR)
    print(
        f"  {tech_col} written to Excel ({JRC_COST_TARGET_YEAR} prices, "
        f"deflator 2006→{JRC_COST_TARGET_YEAR}={deflator:.3f}):"
    )
    for param, value in updates.items():
        fmt = "d" if param == "lifetime" else ",.2f"
        print(f"    {param}: {value:{fmt}}")


# ─────────────────────────────────────────────────────────────────────────────
# GLASS
# ─────────────────────────────────────────────────────────────────────────────
# - Three sub-processes (container/flat/fibre) weighted by the AIDRES EU
#   production mix (60/30/10 %).
# - Energy (fuel + electricity) from the AIDRES NG-reference route.
# - Temperature distribution from Rehfeldt for the same three sub-processes,
#   weighted with the same AIDRES shares for consistency.
glass_params = compute_sector_params(AIDRES2023_GLASS, REHFELDT2017_GLASS, AIDRES2023_GLASS_SHARES, fuel_key="ng_GJ_t")

# ─────────────────────────────────────────────────────────────────────────────
# CERAMIC
# ─────────────────────────────────────────────────────────────────────────────
# - Three sub-processes (tiles/technical/houseware) weighted by EU28+3
#   activity from Rehfeldt (AIDRES does not cover ceramics).
# - Energy and temperature distribution entirely from Rehfeldt.
ceramic_shares = activity_weights(REHFELDT2017_CERAMIC)
ceramic_params = compute_sector_params(REHFELDT2017_CERAMIC, REHFELDT2017_CERAMIC, ceramic_shares)

# ─────────────────────────────────────────────────────────────────────────────
# PULP & PAPER
# ─────────────────────────────────────────────────────────────────────────────
# - Top 3 sub-processes by EU28+3 activity (paper, recovered fibres, chemical
#   pulp), covering 95.2 % of the sector total. Mechanical pulp is excluded
#   (see industry_heat_eu/data/rehfeldt2017.py for why).
# - Rehfeldt only; AIDRES does not cover pulp & paper.
# - No significant inorganic process CO2; carbon_intensity_technology = 0.
#   (Black-liquor combustion CO2 is biogenic, not counted here.)
paper_w = activity_weights(REHFELDT2017_PAPER)
paper_params = compute_sector_params(REHFELDT2017_PAPER, REHFELDT2017_PAPER, paper_w)

# ─────────────────────────────────────────────────────────────────────────────
# FOOD & BEVERAGE
# ─────────────────────────────────────────────────────────────────────────────
# - All 5 Rehfeldt sub-processes are used. The top 3 by activity (dairy,
#   meat, brewing) ALL have 100 % of heat demand below 200 degC; restricting
#   to the top 3 would incorrectly set fuel_for_food to zero and ignore the
#   medium-temperature demand from bread-baking and sugar.
# - Rehfeldt only; AIDRES does not cover food & beverage.
# - carbon_intensity_technology = 0 (no inorganic process CO2; fermentation
#   CO2 is biogenic).
food_w = activity_weights(REHFELDT2017_FOOD)
food_params = compute_sector_params(REHFELDT2017_FOOD, REHFELDT2017_FOOD, food_w)

# ─────────────────────────────────────────────────────────────────────────────
# FUEL MIX SHARES
# ─────────────────────────────────────────────────────────────────────────────
# For each sector, the high-temperature fuel demand (params.cf_fuel) is split
# directly into primary energy carriers according to their share of
# {FEC_COUNTRY} {FEC_YEAR} thermal final energy consumption (JRC-IDEES-2023
# "_fec" sheets), keeping only carriers with a Crystal Ball equivalent and a
# share >= 10% (see industry_heat_eu.fuel_shares).
fuel_mix_shares = {}
for sector in ["glass", "ceramic", "paper", "food"]:
    breakdown = read_sector_thermal_fec(FEC_COUNTRY, sector, FEC_YEAR)
    fuel_mix_shares[sector] = renormalized_fuel_shares(fec_shares(breakdown))

# ─────────────────────────────────────────────────────────────────────────────
# CLEAN OUTPUT DIRECTORIES
# ─────────────────────────────────────────────────────────────────────────────
# Remove stale carriers and technologies from previous runs (e.g.
# heat_low_temp_industry, old split variants) before writing fresh output.
for directory in (CARRIERS, CONV_TECH):
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)

# ─────────────────────────────────────────────────────────────────────────────
# WRITE JSON FILES
# ─────────────────────────────────────────────────────────────────────────────
written_files = []

for carrier in ["glass", "ceramic", "paper", "food"]:
    written_files.append(write_carrier(carrier, PRODUCT_CARRIER_TEMPLATE))
for carrier in ["glass", "ceramic", "paper"]:
    written_files.append(write_industry_demand(carrier, carrier))
written_files.append(write_food_demand())

# Two low-temperature heat carriers split by temperature bin (used as inputs
# by all four production technologies).
written_files.append(write_carrier("heat_industry_0_100",   ENERGY_CARRIER_TEMPLATE))
written_files.append(write_carrier("heat_industry_100_200", ENERGY_CARRIER_TEMPLATE))

# Each call: (1) writes the freshly computed conversion factors (including
# the fuel-mix split) into process_parametrization.xlsx, (2) builds the
# attributes dict, then (3) overwrites its defaults with
# process_parametrization.xlsx (the source of truth for capex, opex_fixed,
# max_diffusion_rate, etc.).
# Glass: JRC-EU-TIMES has product-level capex for flat and container glass.
# AIDRES2023_GLASS_SHARES (container 60%, flat 30%, fibre 10%) used as activity weights.
# fibre glass uses flat glass (IGFFLATGL01) as proxy; see jrc_eu_times.GLASS_AIDRES_TO_JRC.
write_sector_cost_params("glass_production", "Glass", GLASS_AIDRES_TO_JRC, AIDRES2023_GLASS_SHARES)
written_files.append(write_production_tech(
    "glass_production", product="glass", fuel_shares=fuel_mix_shares["glass"], params=glass_params,
    opex_specific_variable=15.0,
))
written_files.append(write_capacity_existing("glass_production", "glass"))

# Ceramics: JRC-EU-TIMES only has generic process-heat boiler technologies (INMPRCxxx,
# INMSTMxxx), which represent heat-supply equipment costs, NOT ceramic kiln capex.
# No appropriate JRC-EU-TIMES proxy → cost parameters set manually in process_parametrization.xlsx.
written_files.append(write_production_tech(
    "ceramic_production", product="ceramic", fuel_shares=fuel_mix_shares["ceramic"], params=ceramic_params,
    opex_specific_variable=10.0,
))
written_files.append(write_capacity_existing("ceramic_production", "ceramic"))

# Paper: JRC-EU-TIMES has product-level capex for three IPP sub-processes.
# Rehfeldt2017 EU28+3 activity shares used as weights.
write_sector_cost_params("paper_production", "Paper", PAPER_REHFELDT_TO_JRC, paper_w)
written_files.append(write_production_tech(
    "paper_production", product="paper", fuel_shares=fuel_mix_shares["paper"], params=paper_params,
    opex_specific_variable=0.0,  # set from Excel by apply_excel_overrides (opex_specific_variable row)
))
written_files.append(write_capacity_existing("paper_production", "paper"))

# CH, NO, UK have no JRC-IDEES data → demand and capacity default to 0 above.
# Fill them from JRC BAT Paper 2014 Table 1.2 (2008 paper consumption in kt).
bat_paper = pd.read_csv(BAT_PAPER_CSV)
bat_paper = bat_paper[bat_paper["country"].isin(BAT_PAPER_NODES)]
bat_consumption = {
    BAT_PAPER_NODES[row["country"]]: row["consumption_1000t_2008"]
    for _, row in bat_paper.iterrows()
}

paper_demand_path = CARRIERS / "paper" / "demand.csv"
df_demand = pd.read_csv(paper_demand_path)
for node, kt in bat_consumption.items():
    df_demand.loc[df_demand["node"] == node, "demand"] = kt * 1000 / 8760
df_demand.to_csv(paper_demand_path, index=False)

paper_cap_path = CONV_TECH / "paper_production" / "capacity_existing.csv"
df_cap = pd.read_csv(paper_cap_path)
for node, kt in bat_consumption.items():
    df_cap.loc[df_cap["node"] == node, "capacity_existing"] = kt * 1000 / 8000
df_cap.to_csv(paper_cap_path, index=False)

print(f"\nBAT Paper 2014 (CH/NO/UK, 2008 consumption kt):")
for node, kt in sorted(bat_consumption.items()):
    print(f"  {node}: {kt:.0f} kt → demand={kt*1000/8760:.1f} t/h, capacity={kt*1000/8000:.1f} t/h")

# Food: JRC-EU-TIMES has no product-level food processing technology. Cost
# parameters based on the capital-light industrial cluster average (Glass
# Hollow IGHHOLLOW01, Quick Lime ILMQLMPRO01, Copper Finishing ICUFINPRO01):
# INVCOST=300 EUR/(t/yr), FIXOM=15 EUR/(t/yr)/yr, VAROM=0, LIFE=20yr
# (all in 2006 base-year EUR, converted via deflator + ×8760).
write_direct_cost_params(
    "food_production", invcost=300, fixom=15, varom=0, lifetime=20,
)
written_files.append(write_production_tech(
    "food_production", product="food", fuel_shares=fuel_mix_shares["food"], params=food_params,
    opex_specific_variable=0.0,
))
written_files.append(write_food_capacity_existing())

# ─────────────────────────────────────────────────────────────────────────────
# HEAT TECHNOLOGIES
# ─────────────────────────────────────────────────────────────────────────────
# Each heat technology from heat_tech_parametrization.xlsx is split into two
# single-output variants — {tech}_0_100 producing heat_industry_0_100 and
# {tech}_100_200 producing heat_industry_100_200.
# The total capacity_existing per heat tech is split between the two variants
# proportionally to the demand-weighted share of each temperature level
# across all four production sectors.
HEAT_CARRIERS = {"0_100": "heat_industry_0_100", "100_200": "heat_industry_100_200"}

# Demand-weighted temperature split: for each sector, total low-temp heat
# demand = production_volume × conversion_factor. Sum across sectors to get
# the overall 0-100 vs 100-200 ratio.
sector_params_map = {
    "glass": glass_params, "ceramic": ceramic_params,
    "paper": paper_params, "food": food_params,
}
demand_volumes = {
    "glass": industry_demand_df("glass", FEC_YEAR)["demand"].sum(),
    "ceramic": industry_demand_df("ceramic", FEC_YEAR)["demand"].sum(),
    "paper": industry_demand_df("paper", FEC_YEAR)["demand"].sum(),
    "food": food_demand_df(FEC_YEAR)["demand"].sum(),
}
total_heat_0_100 = sum(
    demand_volumes[s] * sector_params_map[s].cf_lt_0_100 for s in demand_volumes
)
total_heat_100_200 = sum(
    demand_volumes[s] * sector_params_map[s].cf_lt_100_200 for s in demand_volumes
)
total_heat = total_heat_0_100 + total_heat_100_200
heat_share = {
    "0_100": total_heat_0_100 / total_heat,
    "100_200": total_heat_100_200 / total_heat,
}
print(f"\nheat capacity split: 0_100={heat_share['0_100']:.1%}, 100_200={heat_share['100_200']:.1%}")

for tech_name in tech_columns(HEAT_XLSX, HEAT_SHEET):
    base_data = build_tech_from_table(HEAT_XLSX, HEAT_SHEET, tech_name)
    for suffix, carrier in HEAT_CARRIERS.items():
        data = copy.deepcopy(base_data)
        data["reference_carrier"]["default_value"] = [carrier]
        data["output_carrier"]["default_value"] = [carrier]
        variant_name = f"{tech_name}_{suffix}"
        written_files.append(write_json(CONV_TECH / variant_name, data))

heat_capacity_dfs = {
    "heat_pump_industry": heat_pump_capacity_existing_df(),
    "biomass_boiler_industry": biomass_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR),
    "natural_gas_boiler_industry": natural_gas_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR),
    "electrode_boiler_industry": electrode_boiler_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR),
}
for tech_name, df in heat_capacity_dfs.items():
    for suffix, share in heat_share.items():
        variant_df = df.copy()
        variant_df["capacity_existing"] = variant_df["capacity_existing"] * share
        path = CONV_TECH / f"{tech_name}_{suffix}" / "capacity_existing.csv"
        variant_df.to_csv(path, index=False)
        written_files.append(path)

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print_summary(
    sectors={"Glass": glass_params, "Ceramic": ceramic_params, "Paper": paper_params, "Food": food_params},
)

print(f"\nfuel mix input shares ({FEC_COUNTRY} {FEC_YEAR} thermal FEC, >=10% cutoff):")
for sector, shares in fuel_mix_shares.items():
    shares_str = ", ".join(f"{carrier} {share:.1%}" for carrier, share in shares.items())
    print(f"  {sector:<8} {shares_str}")

print(f"\nWrote {len(written_files)} files:")
for f in written_files:
    print(f"  {f.relative_to(MODEL_DIR.parent.parent.parent)}")
