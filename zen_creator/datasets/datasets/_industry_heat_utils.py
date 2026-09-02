"""Consolidated utility functions for industry heat datasets.

Absorbs all logic previously in zen_creator/industry_heat_eu/:
  process_params, fuel_shares, jrc_idees, faostat, capacity_and_demand,
  excel_io (read-only), json_templates, data/rehfeldt2017, data/aidres2023,
  data/jrc_eu_times.
"""

import csv
import functools
import json
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import xlrd

# ---------------------------------------------------------------------------
# Path anchors — all relative to the repo root
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT_DATA = _REPO_ROOT / "input_data"

# ---------------------------------------------------------------------------
# Rehfeldt 2017 — temperature distributions and energy demands
# ---------------------------------------------------------------------------
_REHFELDT_DIR = INPUT_DATA / "Rehfeldt2017"
TEMP_BINS = ["<100", "100-200", "200-500", "500-1000", ">1000"]
_TEMP_COLUMNS = {
    "<100": "temp_lt100",
    "100-200": "temp_100_200",
    "200-500": "temp_200_500",
    "500-1000": "temp_500_1000",
    ">1000": "temp_gt1000",
}

def _load_rehfeldt_sector(sector: str) -> dict:
    df = pd.read_csv(_REHFELDT_DIR / "Rehfeldt2017.csv")
    df = df[df["sector"] == sector]
    sector_data = {}
    for _, row in df.iterrows():
        entry = {
            "fuels_GJ_t": float(row["fuels_GJ_t"]),
            "elec_GJ_t": float(row["elec_GJ_t"]),
            "activity_Mt": float(row["activity_Mt"]),
            "temp_dist": {b: float(row[c]) for b, c in _TEMP_COLUMNS.items()},
            "source": row["source"],
        }
        if pd.notna(row["note"]):
            entry["note"] = row["note"]
        sector_data[row["sub_process"]] = entry
    return sector_data


REHFELDT2017_GLASS = _load_rehfeldt_sector("glass")
REHFELDT2017_CERAMIC = _load_rehfeldt_sector("ceramic")
REHFELDT2017_PAPER = _load_rehfeldt_sector("paper")
REHFELDT2017_FOOD = _load_rehfeldt_sector("food")

# ---------------------------------------------------------------------------
# AIDRES 2023 — glass process data
# ---------------------------------------------------------------------------
_AIDRES_DIR = INPUT_DATA / "AIDRES2023"
_aidres_df = pd.read_csv(_AIDRES_DIR / "AIDRES2023_glass.csv").set_index("sub_process")

AIDRES2023_GLASS = {
    sub: {
        "ng_GJ_t": float(row["ng_GJ_t"]),
        "elec_GJ_t": float(row["elec_GJ_t"]),
        "capex_eur_t_yr": int(row["capex_eur_t_yr"]),
        "emit_ng_ref": float(row["emit_ng_ref"]),
        "emit_elec": float(row["emit_elec"]),
        "source": row["source"],
    }
    for sub, row in _aidres_df.iterrows()
}
AIDRES2023_GLASS_SHARES = {
    sub: float(s) for sub, s in _aidres_df["eu_production_share"].items()
}

# ---------------------------------------------------------------------------
# SectorParams — per-sector energy parameters
# ---------------------------------------------------------------------------

def activity_weights(data: dict) -> dict:
    total = sum(e["activity_Mt"] for e in data.values())
    return {k: e["activity_Mt"] / total for k, e in data.items()}


def weighted_average(data: dict, weights: dict, key: str) -> float:
    return sum(weights[k] * data[k][key] for k in weights)


def weighted_avg_temp_dist(data: dict, weights: dict) -> dict:
    result = {b: sum(weights[k] * data[k]["temp_dist"][b] for k in weights) for b in TEMP_BINS}
    total = sum(result.values())
    assert abs(total - 1.0) < 1e-6, f"Temperature shares do not sum to 1: {total}"
    return result


def GJ_per_t_to_conversion_factor(energy_GJ_t: float) -> float:
    return energy_GJ_t / 3600.0


@dataclass
class SectorParams:
    fuel_GJ_t: float
    lt_GJ_t_0_100: float
    lt_GJ_t_100_200: float
    elec_GJ_t: float
    temp_dist: dict

    @property
    def cf_fuel(self) -> float:
        return GJ_per_t_to_conversion_factor(self.fuel_GJ_t)

    @property
    def cf_lt_0_100(self) -> float:
        return GJ_per_t_to_conversion_factor(self.lt_GJ_t_0_100)

    @property
    def cf_lt_100_200(self) -> float:
        return GJ_per_t_to_conversion_factor(self.lt_GJ_t_100_200)

    @property
    def cf_elec(self) -> float:
        return GJ_per_t_to_conversion_factor(self.elec_GJ_t)

    @property
    def lt_GJ_t(self) -> float:
        return self.lt_GJ_t_0_100 + self.lt_GJ_t_100_200

    @property
    def cf_lt(self) -> float:
        return GJ_per_t_to_conversion_factor(self.lt_GJ_t)


def compute_sector_params(
    energy_data: dict, temp_data: dict, weights: dict, fuel_key: str = "fuels_GJ_t",
) -> SectorParams:
    fuel_total = weighted_average(energy_data, weights, fuel_key)
    elec = weighted_average(energy_data, weights, "elec_GJ_t")
    temp_dist = weighted_avg_temp_dist(temp_data, weights)
    frac_0_100 = temp_dist["<100"]
    frac_100_200 = temp_dist["100-200"]
    return SectorParams(
        fuel_GJ_t=fuel_total * (1.0 - frac_0_100 - frac_100_200),
        lt_GJ_t_0_100=fuel_total * frac_0_100,
        lt_GJ_t_100_200=fuel_total * frac_100_200,
        elec_GJ_t=elec,
        temp_dist=temp_dist,
    )


# ---------------------------------------------------------------------------
# JRC-IDEES helpers
# ---------------------------------------------------------------------------
_IDEES_ROOT = INPUT_DATA / "JRC-IDEES-2023"
IDEES_FIRST_YEAR = 2000


def idees_workbook_path(country: str, dataset: str) -> Path:
    return _IDEES_ROOT / country / f"JRC-IDEES-2023_{dataset}_{country}.xlsx"


def idees_year_column(year: int) -> int:
    return year - IDEES_FIRST_YEAR + 1


# ---------------------------------------------------------------------------
# FAOSTAT helpers
# ---------------------------------------------------------------------------
_FAOSTAT_DIR = INPUT_DATA / "FAOSTAT"
_FAOSTAT_PROD_FILE = _FAOSTAT_DIR / "Production_Crops_Livestock_E_Europe.csv"

NODE_TO_AREA = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CH": "Switzerland",
    "CZ": "Czechia", "DE": "Germany", "DK": "Denmark", "EE": "Estonia",
    "EL": "Greece", "ES": "Spain", "FI": "Finland", "FR": "France",
    "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IT": "Italy",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "NL": "Netherlands (Kingdom of the)",
    "NO": "Norway", "PL": "Poland", "PT": "Portugal", "RO": "Romania",
    "SE": "Sweden", "SI": "Slovenia", "SK": "Slovakia",
    "UK": "United Kingdom of Great Britain and Northern Ireland",
}


@functools.lru_cache(maxsize=None)
def faostat_production_by_node(item: str, year: int) -> dict[str, float]:
    df = pd.read_csv(_FAOSTAT_PROD_FILE, encoding="latin1", usecols=["Area", "Item", "Element", f"Y{year}"])
    rows = df[(df["Element"] == "Production") & (df["Item"] == item)].set_index("Area")[f"Y{year}"]
    return {
        node: float(rows[area]) if area in rows.index and pd.notna(rows[area]) else 0.0
        for node, area in NODE_TO_AREA.items()
    }


# ---------------------------------------------------------------------------
# Fuel shares — from JRC-IDEES thermal FEC
# ---------------------------------------------------------------------------
THERMAL_CARRIER_LABELS = {
    "Solids", "Refinery gas", "LPG", "Diesel oil and liquid biofuels",
    "Fuel oil", "Other liquids", "Natural gas and biogas", "Derived gases",
    "Biomass and waste", "Distributed steam",
}
MODEL_CARRIER_MAP = {
    "Natural gas and biogas": "natural_gas",
    "Solids": "hard_coal",
    "Biomass and waste": "biomass",
    "Other liquids": "oil",
}
SECTOR_THERMAL_FEC_ROWS = {
    "glass": ("NMM_fec", ["Glass: Thermal melting tank", "Glass: Annealing - thermal"]),
    "ceramic": ("NMM_fec", [
        "Ceramics: Thermal drying and sintering", "Ceramics: Steam drying and sintering",
        "Ceramics: Thermal kiln", "Ceramics: Thermal furnace",
    ]),
    "paper": ("PPA_fec", [
        "Paper: Stock preparation - Thermal", "Paper: Paper machine - Steam use",
        "Paper: Product finishing - Steam use",
    ]),
    "food": ("FBT_fec", [
        "Food: Direct Heat - Thermal", "Food: Process Heat - Thermal",
        "Food: Steam processing", "Food: Thermal drying", "Food: Steam drying",
        "Food: Steam cooling",
    ]),
}


def thermal_fec_by_carrier(df: pd.DataFrame, parent_rows: list[str], year: int) -> dict[str, float]:
    col = idees_year_column(year)
    labels = df[0]
    totals: dict[str, float] = {}
    for parent in parent_rows:
        matches = df.index[labels == parent]
        if len(matches) == 0:
            raise ValueError(f"Row {parent!r} not found in sheet")
        i = matches[0] + 1
        while i < len(df) and labels[i] in THERMAL_CARRIER_LABELS:
            totals[labels[i]] = totals.get(labels[i], 0.0) + float(df.iat[i, col])
            i += 1
    return totals


@functools.lru_cache(maxsize=None)
def read_sector_thermal_fec(country: str, sector: str, year: int) -> dict[str, float]:
    sheet, parent_rows = SECTOR_THERMAL_FEC_ROWS[sector]
    df = pd.read_excel(idees_workbook_path(country, "Industry"), sheet_name=sheet, header=None)
    return thermal_fec_by_carrier(df, parent_rows, year)


def fec_shares(breakdown: dict[str, float]) -> dict[str, float]:
    total = sum(breakdown.values())
    return {c: v / total for c, v in breakdown.items()}


def renormalized_fuel_shares(shares: dict[str, float], cutoff: float = 0.10) -> dict[str, float]:
    kept = {
        MODEL_CARRIER_MAP[c]: s for c, s in shares.items()
        if c in MODEL_CARRIER_MAP and s >= cutoff
    }
    total = sum(kept.values())
    return {c: s / total for c, s in kept.items()}


# ---------------------------------------------------------------------------
# Excel I/O (read-only) — from excel_io.py
# ---------------------------------------------------------------------------
LIST_FIELDS = ("reference_carrier", "input_carrier", "output_carrier")
CONVERSION_FACTOR_PREFIX = "conversion_factor:"


def _label_to_row(ws) -> dict[str, int]:
    return {
        ws.cell(row=row, column=1).value: row
        for row in range(2, ws.max_row + 1)
        if ws.cell(row=row, column=1).value is not None
    }


def _column_index(ws, column_header: str) -> int:
    for cell in ws[1]:
        if cell.value == column_header:
            return cell.column
    raise KeyError(f"Column {column_header!r} not found in sheet {ws.title!r}")


def load_param_column(xlsx_path: Path, sheet_name: str, column_header: str) -> dict[str, object]:
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb[sheet_name]
    col = _column_index(ws, column_header)
    return {label: ws.cell(row=row, column=col).value for label, row in _label_to_row(ws).items()}


def build_tech_from_table(xlsx_path: Path, sheet_name: str, column_header: str) -> dict:
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb[sheet_name]
    col = _column_index(ws, column_header)
    rows = {label: (ws.cell(row=row, column=col).value, ws.cell(row=row, column=2).value) for label, row in _label_to_row(ws).items()}
    missing = [label for label, (value, _) in rows.items() if value is None]
    if missing:
        raise ValueError(f"{xlsx_path.name}!{sheet_name}: column {column_header!r} is missing values for {missing}")
    list_field_values = {label: value for label, (value, _) in rows.items() if label in LIST_FIELDS}
    data: dict[str, object] = {}
    conversion_factor = []
    for label, (value, unit) in rows.items():
        if label.startswith(CONVERSION_FACTOR_PREFIX):
            suffix = label[len(CONVERSION_FACTOR_PREFIX):]
            carrier = str(list_field_values.get(suffix, suffix)).strip()
            conversion_factor.append({carrier: {"default_value": value, "unit": unit}})
        elif label in LIST_FIELDS:
            data[label] = {"default_value": [v.strip() for v in str(value).split(";")]}
        else:
            data[label] = {"default_value": value, "unit": unit}
    data["conversion_factor"] = conversion_factor
    return data


def apply_excel_overrides(data: dict, overrides: dict[str, object], conversion_factor_map: dict[str, str] | None = None) -> dict:
    conversion_factor_map = conversion_factor_map or {}
    for label, value in overrides.items():
        if value is None or label is None:
            continue
        if label.startswith(CONVERSION_FACTOR_PREFIX):
            carrier = conversion_factor_map.get(label, label[len(CONVERSION_FACTOR_PREFIX):])
            for entry in data["conversion_factor"]:
                if carrier in entry:
                    entry[carrier]["default_value"] = value
                    break
            continue
        if label not in data:
            continue
        if label in LIST_FIELDS:
            data[label]["default_value"] = [v.strip() for v in str(value).split(";")]
        else:
            data[label]["default_value"] = value
    return data


# ---------------------------------------------------------------------------
# JSON templates — carrier and tech attribute templates
# ---------------------------------------------------------------------------
PRODUCT_CARRIER_TEMPLATE = {
    "carbon_intensity_carrier_import": {"default_value": 0, "unit": "tons/tonproduct"},
    "carbon_intensity_carrier_export": {"default_value": 0, "unit": "tons/tonproduct"},
    "demand": {"default_value": 0, "unit": "tonproduct/hour"},
    "price_shed_demand": {"default_value": "inf", "unit": "Euro/tonproduct"},
    "max_shed_demand": {"default_value": "inf", "unit": "1"},
    "availability_import": {"default_value": 0, "unit": "tonproduct/hour"},
    "availability_export": {"default_value": 0, "unit": "tonproduct/hour"},
    "availability_import_yearly": {"default_value": "inf", "unit": "tonproduct"},
    "availability_export_yearly": {"default_value": "inf", "unit": "tonproduct"},
    "price_export": {"default_value": 0, "unit": "Euro/tonproduct"},
    "price_import": {"default_value": 0, "unit": "Euro/tonproduct"},
}

ENERGY_CARRIER_TEMPLATE = {
    "carbon_intensity_carrier_import": {"default_value": 0.0, "unit": "kilotons/GWh"},
    "carbon_intensity_carrier_export": {"default_value": 0, "unit": "kilotons/GWh"},
    "demand": {"default_value": 0, "unit": "GW"},
    "price_shed_demand": {"default_value": "inf", "unit": "Euro/MWh"},
    "max_shed_demand": {"default_value": "inf", "unit": "1"},
    "availability_import": {"default_value": 0, "unit": "GW"},
    "availability_export": {"default_value": 0, "unit": "GW"},
    "availability_import_yearly": {"default_value": "inf", "unit": "GWh"},
    "availability_export_yearly": {"default_value": "inf", "unit": "GWh"},
    "price_export": {"default_value": 0, "unit": "Euro/MWh"},
    "price_import": {"default_value": 0, "unit": "Euro/MWh"},
}


def _generic_tech_fields(*, capacity_unit, opex_specific_variable, opex_specific_variable_unit,
                         opex_specific_fixed_unit, capex_specific_conversion, capex_unit) -> dict:
    return {
        "capacity_addition_min": {"default_value": 0, "unit": capacity_unit},
        "capacity_addition_max": {"default_value": "inf", "unit": capacity_unit},
        "capacity_addition_unbounded": {"default_value": 0, "unit": capacity_unit},
        "capacity_existing": {"default_value": 0, "unit": capacity_unit},
        "capacity_limit": {"default_value": "inf", "unit": capacity_unit},
        "min_load": {"default_value": 0, "unit": "1"},
        "max_load": {"default_value": 1, "unit": "1"},
        "lifetime": {"default_value": 0, "unit": "1"},
        "opex_specific_variable": {"default_value": opex_specific_variable, "unit": opex_specific_variable_unit},
        "carbon_intensity_technology": {"default_value": 0, "unit": "ton/tonproduct"},
        "construction_time": {"default_value": 0, "unit": "1"},
        "capacity_investment_existing": {"default_value": 0, "unit": capacity_unit},
        "opex_specific_fixed": {"default_value": 0.0, "unit": opex_specific_fixed_unit},
        "max_diffusion_rate": {"default_value": "inf", "unit": "1"},
        "capex_specific_conversion": {"default_value": capex_specific_conversion, "unit": capex_unit},
    }


def build_conversion_tech(*, product, fuel_shares, params, opex_specific_variable) -> dict:
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
        "input_carrier": {"default_value": [*fuel_shares.keys(), "heat_industry_0_100", "heat_industry_100_200", "electricity"]},
        "output_carrier": {"default_value": [product]},
        "conversion_factor": [
            *[{c: {"default_value": round(params.cf_fuel * s, 12), "unit": "GW/(tonproduct/hour)"}} for c, s in fuel_shares.items()],
            {"heat_industry_0_100": {"default_value": round(params.cf_lt_0_100, 12), "unit": "GW/(tonproduct/hour)"}},
            {"heat_industry_100_200": {"default_value": round(params.cf_lt_100_200, 12), "unit": "GW/(tonproduct/hour)"}},
            {"electricity": {"default_value": round(params.cf_elec, 12), "unit": "GW/(tonproduct/hour)"}},
        ],
    }


# ---------------------------------------------------------------------------
# JRC-EU-TIMES cost data
# ---------------------------------------------------------------------------
_JRC_DIR = INPUT_DATA / "JRC-EU-TIMES_2019_11"
_SUBRES_IND_FILE = _JRC_DIR / "SubRES_TMPL" / "SUBRES_10_TECHS_CHP_SUP_IND.xls"
PARAM_BASE_YEAR = 2006
JRC_HOURS_PER_YEAR = 8760

GLASS_AIDRES_TO_JRC = {"container": "IGHHOLLOW01", "flat": "IGFFLATGL01", "fibre": "IGFFLATGL01"}
PAPER_REHFELDT_TO_JRC = {"paper": "IPPHIGQUA01", "recovered_fibres": "IPPLOWQUA01", "chemical_pulp": "IPPPUPCHE01"}


def read_ind_process_params(tech_name: str) -> dict:
    wb = xlrd.open_workbook(_SUBRES_IND_FILE)
    ws = wb.sheet_by_name("IND")
    headers = {ws.cell_value(4, j): j for j in range(ws.ncols)}
    col = {
        "TechName": headers["TechName"], "INVCOST": headers["INVCOST"],
        "FIXOM": headers["FIXOM"], "VAROM": headers["VAROM"],
        "LIFE": headers["LIFE"], "CO2": headers["EMISSIONS~INDCO2P"],
    }
    result = {k: 0.0 for k in ("INVCOST", "FIXOM", "VAROM", "LIFE", "EMISSIONS_INDCO2P")}
    current_tech = None
    for i in range(ws.nrows):
        name = ws.cell_value(i, col["TechName"])
        if name and name != "TechName":
            current_tech = name
        if current_tech != tech_name:
            continue
        for key, col_key in [("INVCOST", "INVCOST"), ("FIXOM", "FIXOM"), ("VAROM", "VAROM"),
                             ("LIFE", "LIFE"), ("EMISSIONS_INDCO2P", "CO2")]:
            v = ws.cell_value(i, col[col_key])
            if isinstance(v, (int, float)) and v != 0:
                result[key] = float(v)
            elif isinstance(v, str) and v.strip() not in ("", "0"):
                try:
                    result[key] = float(v)
                except ValueError:
                    pass
    return result


def gdp_deflator_ratio(from_year: int, to_year: int) -> float:
    wb = xlrd.open_workbook(_SUBRES_IND_FILE)
    ws = wb.sheet_by_name("GDPdeflator")
    obs: dict[int, float] = {}
    for i in range(3, 12):
        label = str(ws.cell_value(i, 0)).strip()
        val = ws.cell_value(i, 1)
        if label and isinstance(val, (int, float)):
            obs[int(label[:4])] = float(val)
    years_sorted = sorted(obs)
    first_y, last_y = years_sorted[0], years_sorted[-1]
    cagr = (obs[last_y] / obs[first_y]) ** (1 / (last_y - first_y)) - 1

    def _index(year: int) -> float:
        if year in obs:
            return obs[year]
        if year < first_y:
            return obs[first_y] / (1 + cagr) ** (first_y - year)
        return obs[last_y] * (1 + cagr) ** (year - last_y)

    return _index(to_year) / _index(from_year)


def sector_weighted_params(jrc_mapping, activity_wts, target_year) -> dict[str, float]:
    deflator = gdp_deflator_ratio(PARAM_BASE_YEAR, target_year)
    capex = fixom = varom = co2 = life = 0.0
    for sub_key, jrc_code in jrc_mapping.items():
        w = activity_wts[sub_key]
        p = read_ind_process_params(jrc_code)
        capex += w * p["INVCOST"]
        fixom += w * p["FIXOM"]
        varom += w * p["VAROM"]
        co2 += w * p["EMISSIONS_INDCO2P"]
        life += w * p["LIFE"]
    return {
        "capex_specific_conversion": capex * deflator * JRC_HOURS_PER_YEAR,
        "opex_specific_fixed": fixom * deflator * JRC_HOURS_PER_YEAR,
        "opex_specific_variable": varom * deflator,
        "carbon_intensity_technology": co2,
        "lifetime": round(life),
    }


# ---------------------------------------------------------------------------
# Capacity and demand — per-node DataFrames
# ---------------------------------------------------------------------------
MODEL_NODES = (
    "AT", "BE", "BG", "CH", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU",
    "IE", "IT", "LT", "LU", "LV", "NL", "NO", "PL", "PT", "RO", "SE", "SI", "SK", "UK",
)
NODES_WITHOUT_IDEES = ("CH", "NO", "UK")
OPERATING_HOURS = 8000
HOURS_PER_YEAR = 8760
KTOE_TO_GJ = 41868.0  # 1 ktoe = 1000 toe × 41.868 GJ/toe

# Population-proxy scaling for UK (not covered by JRC-IDEES): DE 2023 population
# 83.5M, UK 2023 population 69.9M (Eurostat/ONS). Used to scale glass/ceramic
# capacity_existing/demand from DE as a population proxy.
UK_DE_POPULATION_RATIO = 69.9 / 83.5

# Lifetimes (years) used to spread existing capacity across vintage cohorts.
# Production tech lifetimes from process_parametrization.xlsx / JRC-EU-TIMES (see ASSUMPTIONS.md).
# Boiler lifetimes from heat_tech_parametrization.xlsx (Crystal Ball values).
SECTOR_LIFETIMES: dict[str, int] = {"glass": 28, "ceramic": 20, "paper": 25, "food": 20}
BOILER_LIFETIMES: dict[str, int] = {
    "biomass_boiler_industry": 25,
    "natural_gas_boiler_industry": 25,
    "electrode_boiler_industry": 25,
    "oil_boiler_industry": 25,
    "coal_boiler_industry": 25,  # DEA sheet "6.3 Boiler, coal"
    "waste_boiler_industry": 30,  # Crystal Ball's waste_boiler_DH (no DEA industrial sheet exists)
}

INSTALLED_CAPACITY_HEADER = "Installed capacity (kt production)"
PHYSICAL_OUTPUT_HEADER = "Physical output (kt)"

SECTOR_CAPACITY_ROWS = {
    "glass": ("NMM", ["Glass production  (kt)"]),
    "ceramic": ("NMM", ["Ceramics & other NMM (kt bricks eq.)"]),
    "paper": ("PPA", ["Pulp production (kt)", "Paper production  (kt)", "Printing and media reproduction (kt paper eq.)"]),
}

FOOD_PRODUCTION_ITEMS = {
    "dairy": "Milk, Total", "meat_processing": "Meat, Total",
    "brewing": "Beer of barley, malted", "bread_bakery": "Wheat",
    "sugar": "Raw cane or beet sugar (centrifugal only)",
}

EUROSTAT_COUNTRY_TO_NODE = {
    "Belgium": "BE", "Bulgaria": "BG", "Czechia": "CZ", "Denmark": "DK",
    "Germany": "DE", "Estonia": "EE", "Ireland": "IE", "Greece": "EL",
    "Spain": "ES", "France": "FR", "Croatia": "HR", "Italy": "IT",
    "Latvia": "LV", "Lithuania": "LT", "Luxembourg": "LU", "Hungary": "HU",
    "Netherlands": "NL", "Austria": "AT", "Poland": "PL", "Portugal": "PT",
    "Romania": "RO", "Slovenia": "SI", "Slovakia": "SK", "Finland": "FI",
    "Sweden": "SE", "Norway": "NO", "United Kingdom": "UK",
}
NODE_TO_EUROSTAT_COUNTRY = {n: c for c, n in EUROSTAT_COUNTRY_TO_NODE.items()}

EUROSTAT_EB_XLSX = "Eurostat_EB_GWh.xlsx"
EUROSTAT_NATURAL_GAS_HEAT_SHEET = "Sheet 72"
EUROSTAT_BIOMASS_HEAT_SHEET = "Sheet 74"
EUROSTAT_ELECTRICITY_HEAT_SHEET = "Sheet 83"
EUROSTAT_HEAT_FIRST_YEAR = 2015

# Separate extract (custom_22192472) that additionally includes oil products,
# which the original custom_21840385 query (EUROSTAT_EB_XLSX) never selected.
# This same extract also carries the full SIEC breakdown of "Gross heat
# production" (84 sheets), including coal, waste, and biogases — carriers the
# original EB_GWh.xlsx query never selected either. See ASSUMPTIONS.md,
# "Boiler (industry) capacity" for the full carrier ranking that justified
# adding these.
EUROSTAT_NEW_EB_XLSX = "Eurostat_new.xlsx"
EUROSTAT_OIL_HEAT_SHEET = "Sheet 23"  # "Oil and petroleum products (excluding biofuel portion)"
EUROSTAT_COAL_HEAT_SHEET = "Sheet 2"  # "Solid fossil fuels"
EUROSTAT_BIOGAS_HEAT_SHEET = "Sheet 63"  # "Biogases" — folded into the biomass total
EUROSTAT_IND_WASTE_HEAT_SHEET = "Sheet 64"  # "Industrial waste (non-renewable)"
EUROSTAT_REN_MUN_WASTE_HEAT_SHEET = "Sheet 65"  # "Renewable municipal waste"
EUROSTAT_NONREN_MUN_WASTE_HEAT_SHEET = "Sheet 66"  # "Non-renewable municipal waste"


def section_by_label(df: pd.DataFrame, year: int, header: str) -> dict[str, float]:
    col = idees_year_column(year)
    labels = df[0]
    [header_idx] = df.index[labels == header]
    values: dict[str, float] = {}
    for i in range(header_idx + 1, len(df)):
        label = labels[i]
        if not isinstance(label, str):
            continue
        if label.endswith("(kt production)"):
            break
        values[label] = float(df.iat[i, col])
    return values


@functools.lru_cache(maxsize=None)
def _sector_kt(country: str, sector: str, year: int, header: str) -> float:
    sheet, row_labels = SECTOR_CAPACITY_ROWS[sector]
    df = pd.read_excel(idees_workbook_path(country, "Industry"), sheet_name=sheet, header=None)
    values = section_by_label(df, year, header)
    return sum(values[label] for label in row_labels)


def installed_capacity_kt(country, sector, year):
    return _sector_kt(country, sector, year, INSTALLED_CAPACITY_HEADER)


def physical_output_kt(country, sector, year):
    return _sector_kt(country, sector, year, PHYSICAL_OUTPUT_HEADER)


@functools.lru_cache(maxsize=None)
def capacity_existing_df(sector, year, lifetime=None, year_construction=None):
    # Compute total capacity per node
    node_caps: dict[str, float] = {}
    for node in MODEL_NODES:
        node_caps[node] = 0.0 if node in NODES_WITHOUT_IDEES else installed_capacity_kt(node, sector, year) * 1000 / OPERATING_HOURS

    # Population-proxy overrides for glass/ceramic (CH/NO/UK not covered by IDEES)
    if sector in ("glass", "ceramic"):
        node_caps["CH"] = node_caps["AT"]
        node_caps["NO"] = node_caps["FI"]
        node_caps["UK"] = node_caps["DE"] * UK_DE_POPULATION_RATIO

    # Build rows: spread uniformly over `lifetime` vintage years ending at reference_year,
    # or return a single row (backward-compatible path used by demand methods).
    ref_year = year_construction or year
    rows = []
    if lifetime is not None:
        for node in MODEL_NODES:
            cap_per_yr = node_caps[node] / lifetime
            for yc in range(ref_year - lifetime + 1, ref_year + 1):
                rows.append({"node": node, "year_construction": yc, "capacity_existing": cap_per_yr})
    else:
        for node in MODEL_NODES:
            rows.append({"node": node, "year_construction": ref_year, "capacity_existing": node_caps[node]})
    return pd.DataFrame(rows)


@functools.lru_cache(maxsize=None)
def industry_demand_df(sector, year):
    rows = []
    for node in MODEL_NODES:
        if node in NODES_WITHOUT_IDEES:
            demand = 0.0
        else:
            demand = physical_output_kt(node, sector, year) * 1000 / HOURS_PER_YEAR
        rows.append({"node": node, "demand": demand})
    df = pd.DataFrame(rows)
    if sector in ("glass", "ceramic"):
        at_demand = float(df.loc[df["node"] == "AT", "demand"].values[0])
        fi_demand = float(df.loc[df["node"] == "FI", "demand"].values[0])
        de_demand = float(df.loc[df["node"] == "DE", "demand"].values[0])
        # CH: use AT values (9.1M vs 9.2M — nearly identical population)
        df.loc[df["node"] == "CH", "demand"] = at_demand
        # NO: use FI values (5.6M vs 5.6M — same population)
        df.loc[df["node"] == "NO", "demand"] = fi_demand
        # UK: scale from DE by population ratio (69.9M / 83.5M)
        df.loc[df["node"] == "UK", "demand"] = de_demand * UK_DE_POPULATION_RATIO
    return df


@functools.lru_cache(maxsize=None)
def ceramic_demand_from_fec_df(year: int) -> pd.DataFrame:
    """Derive ceramic production (kt/yr) from JRC-IDEES thermal FEC ÷ Rehfeldt specific energy.

    JRC-IDEES 'Ceramics & other NMM (kt bricks eq.)' is dominated by bricks (~1-2 GJ/t),
    which are not covered by Rehfeldt2017 (tiles/technical/houseware, ~8 GJ/t weighted avg).
    Using thermal FEC from NMM_fec kiln/furnace rows (the same rows used for fuel shares)
    divided by Rehfeldt's weighted specific energy gives a production volume consistent
    with Rehfeldt's energy intensity.

    Returns a DataFrame with columns ['node', 'kt_yr'].
    """
    ceramic_w = activity_weights(REHFELDT2017_CERAMIC)
    rehfeldt_fuel_GJ_t = weighted_average(REHFELDT2017_CERAMIC, ceramic_w, "fuels_GJ_t")
    rows = []
    for node in MODEL_NODES:
        if node in NODES_WITHOUT_IDEES:
            kt_yr = 0.0
        else:
            fec = read_sector_thermal_fec(node, "ceramic", year)
            kt_yr = sum(fec.values()) * KTOE_TO_GJ / (rehfeldt_fuel_GJ_t * 1000)
        rows.append({"node": node, "kt_yr": kt_yr})
    df = pd.DataFrame(rows)
    # Population-based scaling for nodes without JRC-IDEES coverage
    at_kt = float(df.loc[df["node"] == "AT", "kt_yr"].values[0])
    fi_kt = float(df.loc[df["node"] == "FI", "kt_yr"].values[0])
    de_kt = float(df.loc[df["node"] == "DE", "kt_yr"].values[0])
    df.loc[df["node"] == "CH", "kt_yr"] = at_kt
    df.loc[df["node"] == "NO", "kt_yr"] = fi_kt
    df.loc[df["node"] == "UK", "kt_yr"] = de_kt * UK_DE_POPULATION_RATIO
    return df


@functools.lru_cache(maxsize=None)
def food_capacity_existing_df(year, lifetime=None, year_construction=None):
    activity_mt = {node: 0.0 for node in MODEL_NODES}
    for subsector, item in FOOD_PRODUCTION_ITEMS.items():
        production = faostat_production_by_node(item, year)
        total = sum(production[node] for node in MODEL_NODES)
        for node in MODEL_NODES:
            share = production[node] / total if total else 0.0
            activity_mt[node] += share * REHFELDT2017_FOOD[subsector]["activity_Mt"]
    node_caps = {node: activity_mt[node] * 1e6 / OPERATING_HOURS for node in MODEL_NODES}
    ref_year = year_construction or year
    rows = []
    if lifetime is not None:
        for node in MODEL_NODES:
            cap_per_yr = node_caps[node] / lifetime
            for yc in range(ref_year - lifetime + 1, ref_year + 1):
                rows.append({"node": node, "year_construction": yc, "capacity_existing": cap_per_yr})
    else:
        for node in MODEL_NODES:
            rows.append({"node": node, "year_construction": ref_year, "capacity_existing": node_caps[node]})
    return pd.DataFrame(rows)


def heat_pump_capacity_existing_df():
    return pd.DataFrame([
        {"node": node, "year_construction": 2022, "capacity_existing": 0.0}
        for node in MODEL_NODES
    ])


@functools.lru_cache(maxsize=None)
def eurostat_gross_heat_gwh(sheet, year, xlsx=EUROSTAT_EB_XLSX):
    df = pd.read_excel(INPUT_DATA / "Eurostat" / xlsx, sheet_name=sheet, header=None)
    [header_row] = df.index[df[0] == "TIME"]
    values: dict[str, float] = {}
    for i in range(header_row + 1, len(df)):
        label = df.iat[i, 0]
        if label not in EUROSTAT_COUNTRY_TO_NODE:
            continue
        for y in range(year, EUROSTAT_HEAT_FIRST_YEAR - 1, -1):
            cell = df.iat[i, 1 + 2 * (y - EUROSTAT_HEAT_FIRST_YEAR)]
            if cell != ":":
                values[label] = float(cell)
                break
    return values


def _boiler_capacity_df_from_node_caps(node_caps, year, lifetime, year_construction):
    ref_year = year_construction or year
    rows = []
    if lifetime is not None:
        for node in MODEL_NODES:
            cap_per_yr = node_caps[node] / lifetime
            for yc in range(ref_year - lifetime + 1, ref_year + 1):
                rows.append({"node": node, "year_construction": yc, "capacity_existing": cap_per_yr})
    else:
        for node in MODEL_NODES:
            rows.append({"node": node, "year_construction": ref_year, "capacity_existing": node_caps[node]})
    return pd.DataFrame(rows)


def total_industry_heat_demand_gw(year: int) -> dict[str, float]:
    """Total heat carrier demand (GW) per node, summed over glass/paper/food/ceramic.

    Covers heat_industry_0_100 + heat_industry_100_150 + heat_industry_150_200
    via SectorParams.cf_lt = (lt_GJ_t_0_100 + lt_GJ_t_100_200) / 3600 per sector.
    Glass uses AIDRES2023 energy data with Rehfeldt2017 temperature distribution,
    matching process_parametrization._compute_sector_params().
    """
    glass_params = compute_sector_params(
        AIDRES2023_GLASS, REHFELDT2017_GLASS, AIDRES2023_GLASS_SHARES, fuel_key="ng_GJ_t"
    )
    ceramic_params = compute_sector_params(
        REHFELDT2017_CERAMIC, REHFELDT2017_CERAMIC, activity_weights(REHFELDT2017_CERAMIC)
    )
    paper_params = compute_sector_params(
        REHFELDT2017_PAPER, REHFELDT2017_PAPER, activity_weights(REHFELDT2017_PAPER)
    )
    food_params = compute_sector_params(
        REHFELDT2017_FOOD, REHFELDT2017_FOOD, activity_weights(REHFELDT2017_FOOD)
    )
    glass_demand = industry_demand_df("glass", year).set_index("node")["demand"]   # ton/hr
    paper_demand = industry_demand_df("paper", year).set_index("node")["demand"]   # ton/hr
    # Production-based (FAOSTAT "Production"), matching the food carrier's own
    # demand; see get_waste_heat_capacity_limit() in process_parametrization.py.
    food_demand_s = food_capacity_existing_df(year).set_index("node")["capacity_existing"]  # ton/hr
    ceramic_demand = (
        ceramic_demand_from_fec_df(year).set_index("node")["kt_yr"] * 1000.0 / HOURS_PER_YEAR
    )  # ton/hr
    return {
        node: (
            glass_demand[node] * glass_params.cf_lt
            + paper_demand[node] * paper_params.cf_lt
            + food_demand_s[node] * food_params.cf_lt
            + ceramic_demand[node] * ceramic_params.cf_lt
        )
        for node in MODEL_NODES
    }


def _eurostat_fuel_shares(
    biomass_gwh: dict[str, float], ng_gwh: dict[str, float], elec_gwh: dict[str, float],
    oil_gwh: dict[str, float], coal_gwh: dict[str, float], waste_gwh: dict[str, float],
    country: str,
) -> tuple[float, float, float, float, float, float]:
    """Fuel-mix shares (biomass, natural_gas, electrode, oil, coal, waste), all
    from Eurostat "Gross heat production". `biomass_gwh` is expected to already
    include biogases (Sheet 63) alongside primary solid biofuels (Sheet 74) —
    see the call site in _demand_based_boiler_capacity_gw. `waste_gwh` is
    expected to already sum industrial + renewable/non-renewable municipal
    waste (Sheets 64-66).
    """
    bio_gw = biomass_gwh.get(country, 0.0) / OPERATING_HOURS
    ng_gw = ng_gwh.get(country, 0.0) / OPERATING_HOURS
    elec_gw = elec_gwh.get(country, 0.0) / OPERATING_HOURS
    oil_gw = oil_gwh.get(country, 0.0) / OPERATING_HOURS
    coal_gw = coal_gwh.get(country, 0.0) / OPERATING_HOURS
    waste_gw = waste_gwh.get(country, 0.0) / OPERATING_HOURS
    total_euro = bio_gw + ng_gw + elec_gw + oil_gw + coal_gw + waste_gw
    if total_euro > 0.0:
        return (
            bio_gw / total_euro, ng_gw / total_euro, elec_gw / total_euro,
            oil_gw / total_euro, coal_gw / total_euro, waste_gw / total_euro,
        )
    return 0.0, 1.0, 0.0, 0.0, 0.0, 0.0


# BFE (2025) "Energieverbrauch in der Industrie und im Dienstleistungssektor" —
# annual survey of ~13'000 Swiss establishments, hochgerechnet by BFS. Branch
# groups matching this model's process-heat scope (cement, branch 5, is reported
# separately and excluded): see BFE2025 in ASSUMPTIONS.md.
BFE_CH_XLSX = "BFE2025.xlsx"
BFE_CH_BRANCHES = (1, 3, 6)  # Nahrungsmittel (food), Papier und Druck (paper), Andere Nicht-Eisen-Mineralien (glass/ceramics)
BFE_CH_GAS_SHEET = "Erdgas"
BFE_CH_OIL_SHEETS = ("Heizöl extra-leicht", "Heizöl mittel und schwer")
BFE_CH_BIOMASS_SHEET = "Holz"
BFE_CH_COAL_SHEET = "Kohle"
BFE_CH_WASTE_SHEET = "Industrieabfälle"


def _bfe_ch_branch_total_tj(sheet: str, year: int) -> float:
    df = pd.read_excel(INPUT_DATA / "BFE2025" / BFE_CH_XLSX, sheet_name=sheet, header=None)
    [header_row] = df.index[df[0] == "BranchenNr."]
    header = df.iloc[header_row]
    year_cols = [c for c in header.index if isinstance(header[c], (int, float)) and header[c] <= year]
    if not year_cols:
        return 0.0
    col = max(year_cols, key=lambda c: header[c])
    total = 0.0
    for branch in BFE_CH_BRANCHES:
        [row] = df.index[df[0] == branch]
        value = df.iat[row, col]
        total += float(value) if value is not None else 0.0
    return total


@functools.lru_cache(maxsize=4)
def _bfe_ch_fuel_shares(year: int) -> tuple[float, float, float, float, float, float]:
    """Switzerland-specific boiler fuel-mix shares (biomass, natural_gas, electrode, oil, coal, waste).

    Derived from BFE2025, summing final energy consumption across the three branches
    matching this model's process-heat scope (food, paper, glass/ceramics), restricted
    to combustion carriers (Erdgas, Heizöl extra-leicht + mittel/schwer, Holz, Kohle,
    Industrieabfälle). Electricity is excluded from the mix — in these branches it is
    dominated by drives and lighting rather than boilers, and heat-pump/electrode
    boiler capacity is assumed zero for Switzerland (see David2017, "Heat pump
    (industry) capacity"). Kohle (coal, ~2% of the combustion total) and
    Industrieabfälle (industrial waste, ~7%) were previously dropped entirely; both
    are now included now that coal_boiler_industry/waste_boiler_industry exist — see
    ASSUMPTIONS.md, "Boiler (industry) capacity".
    """
    ng = _bfe_ch_branch_total_tj(BFE_CH_GAS_SHEET, year)
    oil = sum(_bfe_ch_branch_total_tj(sheet, year) for sheet in BFE_CH_OIL_SHEETS)
    bio = _bfe_ch_branch_total_tj(BFE_CH_BIOMASS_SHEET, year)
    coal = _bfe_ch_branch_total_tj(BFE_CH_COAL_SHEET, year)
    waste = _bfe_ch_branch_total_tj(BFE_CH_WASTE_SHEET, year)
    total = ng + oil + bio + coal + waste
    if total > 0.0:
        return bio / total, ng / total, 0.0, oil / total, coal / total, waste / total
    return 0.0, 1.0, 0.0, 0.0, 0.0, 0.0


def _eurostat_waste_gwh(year: int) -> dict[str, float]:
    """Total waste heat production (GWh): industrial + renewable/non-renewable
    municipal waste (Eurostat Sheets 64-66), summed to avoid double-counting
    against Sheet 67 ("Non-renewable waste", itself industrial + non-renewable
    municipal — a subtotal we don't need separately).
    """
    ind = eurostat_gross_heat_gwh(EUROSTAT_IND_WASTE_HEAT_SHEET, year, xlsx=EUROSTAT_NEW_EB_XLSX)
    ren_mun = eurostat_gross_heat_gwh(EUROSTAT_REN_MUN_WASTE_HEAT_SHEET, year, xlsx=EUROSTAT_NEW_EB_XLSX)
    nonren_mun = eurostat_gross_heat_gwh(EUROSTAT_NONREN_MUN_WASTE_HEAT_SHEET, year, xlsx=EUROSTAT_NEW_EB_XLSX)
    countries = set(ind) | set(ren_mun) | set(nonren_mun)
    return {c: ind.get(c, 0.0) + ren_mun.get(c, 0.0) + nonren_mun.get(c, 0.0) for c in countries}


@functools.lru_cache(maxsize=4)
def _demand_based_boiler_capacity_gw(year: int) -> dict[str, dict[str, float]]:
    """Per-node boiler capacity (GW) scaled to total heat demand with Eurostat fuel shares.

    Returns {node: {"biomass": GW, "natural_gas": GW, "electrode": GW, "oil": GW,
    "coal": GW, "waste": GW}}. CH has no Eurostat entry; it uses Switzerland-specific
    fuel shares derived from BFE's industry-energy survey (BFE2025) instead — see
    _bfe_ch_fuel_shares(). "biomass" includes biogases (Sheet 63) alongside primary
    solid biofuels (Sheet 74) — see ASSUMPTIONS.md, "Boiler (industry) capacity".
    """
    total_demand = total_industry_heat_demand_gw(year)
    biomass_gwh = eurostat_gross_heat_gwh(EUROSTAT_BIOMASS_HEAT_SHEET, year)
    biogas_gwh = eurostat_gross_heat_gwh(EUROSTAT_BIOGAS_HEAT_SHEET, year, xlsx=EUROSTAT_NEW_EB_XLSX)
    biomass_gwh = {c: biomass_gwh.get(c, 0.0) + biogas_gwh.get(c, 0.0) for c in set(biomass_gwh) | set(biogas_gwh)}
    ng_gwh = eurostat_gross_heat_gwh(EUROSTAT_NATURAL_GAS_HEAT_SHEET, year)
    elec_gwh = eurostat_gross_heat_gwh(EUROSTAT_ELECTRICITY_HEAT_SHEET, year)
    oil_gwh = eurostat_gross_heat_gwh(EUROSTAT_OIL_HEAT_SHEET, year, xlsx=EUROSTAT_NEW_EB_XLSX)
    coal_gwh = eurostat_gross_heat_gwh(EUROSTAT_COAL_HEAT_SHEET, year, xlsx=EUROSTAT_NEW_EB_XLSX)
    waste_gwh = _eurostat_waste_gwh(year)
    ch_shares = _bfe_ch_fuel_shares(year)
    result: dict[str, dict[str, float]] = {}
    for node in MODEL_NODES:
        country = NODE_TO_EUROSTAT_COUNTRY.get(node)
        if country is not None:
            share_bio, share_ng, share_elec, share_oil, share_coal, share_waste = _eurostat_fuel_shares(
                biomass_gwh, ng_gwh, elec_gwh, oil_gwh, coal_gwh, waste_gwh, country
            )
        elif node == "CH":
            share_bio, share_ng, share_elec, share_oil, share_coal, share_waste = ch_shares
        else:
            share_bio, share_ng, share_elec, share_oil, share_coal, share_waste = 0.0, 1.0, 0.0, 0.0, 0.0, 0.0
        total = total_demand[node]
        result[node] = {
            "biomass": total * share_bio,
            "natural_gas": total * share_ng,
            "electrode": total * share_elec,
            "oil": total * share_oil,
            "coal": total * share_coal,
            "waste": total * share_waste,
        }
    return result


def boiler_capacity_existing_df_for_fuel(fuel_key: str, year, lifetime=None, year_construction=None):
    """Per-node boiler capacity_existing (GW) for one fuel ("biomass",
    "natural_gas", "electrode", "oil", "coal", or "waste"), scaled from
    total industry heat demand via Eurostat/BFE fuel-mix shares -- see
    _demand_based_boiler_capacity_gw()."""
    caps = _demand_based_boiler_capacity_gw(year)
    return _boiler_capacity_df_from_node_caps(
        {node: caps[node][fuel_key] for node in MODEL_NODES}, year, lifetime, year_construction
    )
