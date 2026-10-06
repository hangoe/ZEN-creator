"""Utility functions for industry heat datasets: process parameters, fuel
shares, JRC-IDEES/FAOSTAT loaders, capacity/demand helpers, JSON templates,
and Rehfeldt2017/AIDRES2023/JRC-EU-TIMES data access.
"""

import functools
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import xlrd

logger = logging.getLogger(__name__)

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
    if not data:
        raise ValueError("activity_weights: `data` is empty, cannot compute weights.")
    total = sum(e["activity_Mt"] for e in data.values())
    if total == 0:
        raise ValueError("activity_weights: all activity_Mt values are zero.")
    return {k: e["activity_Mt"] / total for k, e in data.items()}


def weighted_average(data: dict, weights: dict, key: str) -> float:
    if not weights:
        raise ValueError("weighted_average: `weights` is empty.")
    return sum(weights[k] * data[k][key] for k in weights)


def weighted_avg_temp_dist(data: dict, weights: dict) -> dict:
    result = {b: sum(weights[k] * data[k]["temp_dist"][b] for k in weights) for b in TEMP_BINS}
    total = sum(result.values())
    if abs(total - 1.0) >= 1e-6:
        raise ValueError(f"Temperature shares do not sum to 1: {total}")
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


def all_sector_params() -> dict[str, SectorParams]:
    """SectorParams for glass/ceramic/paper/food. Glass uses AIDRES2023 energy data with
    Rehfeldt2017 temperature distribution; ceramic/paper/food use their own Rehfeldt2017
    data throughout. Shared by process_parametrization.py and total_industry_heat_demand_gw().
    """
    return {
        "glass": compute_sector_params(
            AIDRES2023_GLASS, REHFELDT2017_GLASS, AIDRES2023_GLASS_SHARES, fuel_key="ng_GJ_t"
        ),
        "ceramic": compute_sector_params(
            REHFELDT2017_CERAMIC, REHFELDT2017_CERAMIC, activity_weights(REHFELDT2017_CERAMIC)
        ),
        "paper": compute_sector_params(
            REHFELDT2017_PAPER, REHFELDT2017_PAPER, activity_weights(REHFELDT2017_PAPER)
        ),
        "food": compute_sector_params(
            REHFELDT2017_FOOD, REHFELDT2017_FOOD, activity_weights(REHFELDT2017_FOOD)
        ),
    }


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
            cell = df.iat[i, col]
            if pd.isna(cell):
                raise ValueError(
                    f"thermal_fec_by_carrier: blank/NaN cell for carrier "
                    f"{labels[i]!r} under {parent!r} (row {i}, col {col})."
                )
            totals[labels[i]] = totals.get(labels[i], 0.0) + float(cell)
            i += 1
    return totals


@functools.lru_cache(maxsize=None)
def read_sector_thermal_fec(country: str, sector: str, year: int) -> dict[str, float]:
    sheet, parent_rows = SECTOR_THERMAL_FEC_ROWS[sector]
    df = pd.read_excel(idees_workbook_path(country, "Industry"), sheet_name=sheet, header=None)
    return thermal_fec_by_carrier(df, parent_rows, year)


def fec_shares(breakdown: dict[str, float]) -> dict[str, float]:
    total = sum(breakdown.values())
    if total == 0:
        raise ValueError("fec_shares: breakdown sums to 0, cannot compute shares.")
    return {c: v / total for c, v in breakdown.items()}


def renormalized_fuel_shares(shares: dict[str, float], cutoff: float = 0.10) -> dict[str, float]:
    kept = {
        MODEL_CARRIER_MAP[c]: s for c, s in shares.items()
        if c in MODEL_CARRIER_MAP and s >= cutoff
    }
    total = sum(kept.values())
    if total == 0:
        raise ValueError(
            f"renormalized_fuel_shares: no carrier in {list(shares)} reached the "
            f"cutoff ({cutoff}); nothing to renormalize."
        )
    return {c: s / total for c, s in kept.items()}


def _single_row_index(matches, description: str) -> int:
    """Return the sole index in `matches`, raising a descriptive KeyError otherwise."""
    if len(matches) == 0:
        raise KeyError(f"{description}: no matching row found.")
    if len(matches) > 1:
        raise KeyError(f"{description}: expected exactly one matching row, found {len(matches)}.")
    return matches[0]


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
    matched_tech = False
    for i in range(ws.nrows):
        name = ws.cell_value(i, col["TechName"])
        if name and name != "TechName":
            current_tech = name
        if current_tech != tech_name:
            continue
        matched_tech = True
        for key, col_key in [("INVCOST", "INVCOST"), ("FIXOM", "FIXOM"), ("VAROM", "VAROM"),
                             ("LIFE", "LIFE"), ("EMISSIONS_INDCO2P", "CO2")]:
            v = ws.cell_value(i, col[col_key])
            if isinstance(v, (int, float)) and v != 0:
                result[key] = float(v)
            elif isinstance(v, str) and v.strip() not in ("", "0"):
                try:
                    result[key] = float(v)
                except ValueError:
                    logger.warning(
                        f"read_ind_process_params({tech_name!r}): row {i}, "
                        f"column {col_key!r} has an unparseable value {v!r}; "
                        "left at its 0.0 default."
                    )
    if not matched_tech:
        raise ValueError(
            f"read_ind_process_params: tech_name {tech_name!r} not found in "
            f"{_SUBRES_IND_FILE.name}!IND."
        )
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
    if not obs:
        raise ValueError(
            f"gdp_deflator_ratio: no numeric GDP-deflator observations found in "
            f"{_SUBRES_IND_FILE.name}!GDPdeflator rows 3-12."
        )
    years_sorted = sorted(obs)
    first_y, last_y = years_sorted[0], years_sorted[-1]
    if first_y == last_y:
        raise ValueError(
            f"gdp_deflator_ratio: only one observation year ({first_y}) found; "
            "cannot compute a CAGR."
        )
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
        if sub_key not in activity_wts:
            raise KeyError(
                f"sector_weighted_params: jrc_mapping key {sub_key!r} has no "
                f"matching entry in activity_wts ({list(activity_wts)})."
            )
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

# Heat-carrier name per temperature level, shared by heat_tech_parametrization.py
# (boiler/heat-pump techs) and process_parametrization.py (production techs).
HEAT_CARRIER_NAMES = {
    "0_100": "heat_industry_0_100",
    "100_150": "heat_industry_100_150",
    "150_200": "heat_industry_150_200",
}

# --- Per-sector industry heat (V11) -----------------------------------------
# In the per-sector structure the whole industry heat chain (heat carriers, heat
# pumps, boilers, temperature cascade, TES, kiln-fuel switching) exists once per
# sector, named `<base name>_<sector>`, so heat carriers, waste heat and heat
# technologies can no longer be shared between sectors. It is selected by adding the
# `*_per_sector` sectors (industry_heat_per_sector & co.) instead of the pooled V10
# ones; the production technologies (shared by both structures) read the structure
# off their model via model_uses_per_sector_heat().
INDUSTRY_HEAT_SECTORS = ("glass", "ceramic", "paper", "food")
KILN_FUEL_SECTORS = ("glass", "ceramic")  # sectors with a fuel_to_kiln carrier


def model_uses_per_sector_heat(model) -> bool:
    """True if `model` holds the per-sector heat carriers (V11), False for the pooled
    ones (V10) or none. Raises if it holds both, i.e. pooled and per-sector industry
    heat sectors were mixed in one model."""
    names = model.elements
    pooled = [n for n in (*HEAT_CARRIER_NAMES.values(), "fuel_to_kiln") if n in names]
    per_sector = [
        n for s in INDUSTRY_HEAT_SECTORS
        for n in (*(heat_carrier_name(l, s) for l in HEAT_CARRIER_NAMES), kiln_fuel_carrier_name(s))
        if n in names
    ]
    if pooled and per_sector:
        raise ValueError(
            "Model mixes pooled (V10) and per-sector (V11) industry heat carriers "
            f"({pooled[0]!r} and {per_sector[0]!r}): add either industry_heat/"
            "industry_low_temp_heat/industry_tes or their *_per_sector variants, not both."
        )
    return bool(per_sector)


def sector_suffixed(name: str, sector: str | None) -> str:
    """`name` unchanged for sector=None (V10), else `<name>_<sector>`."""
    return name if sector is None else f"{name}_{sector}"


def heat_carrier_name(temp_level: str, sector: str | None = None) -> str:
    return sector_suffixed(HEAT_CARRIER_NAMES[temp_level], sector)


def kiln_fuel_carrier_name(sector: str | None = None) -> str:
    return sector_suffixed("fuel_to_kiln", sector)


# Population-proxy scaling for UK (not covered by JRC-IDEES): DE 2023 population
# 83.5M, UK 2023 population 69.9M (Eurostat/ONS). Used to scale glass/ceramic
# capacity_existing/demand from DE as a population proxy.
UK_DE_POPULATION_RATIO = 69.9 / 83.5


def _apply_population_proxy(values: dict[str, float]) -> dict[str, float]:
    """Override CH/NO/UK (not covered by JRC-IDEES) with a population proxy:
    CH<-AT (9.1M vs 9.2M — nearly identical), NO<-FI (5.6M vs 5.6M — same),
    UK<-DE*UK_DE_POPULATION_RATIO (69.9M/83.5M). Returns a new dict."""
    values = dict(values)
    values["CH"] = values["AT"]
    values["NO"] = values["FI"]
    values["UK"] = values["DE"] * UK_DE_POPULATION_RATIO
    return values

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
    header_idx = _single_row_index(
        df.index[labels == header], f"section_by_label: header {header!r}"
    )
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


def _capacity_df_from_node_caps(node_caps, year, lifetime, year_construction):
    """Spread per-node capacity/demand totals into vintage-year rows.

    With `lifetime` given, spreads each node's total uniformly over `lifetime`
    vintage years ending at `year_construction` (or `year`). Without it, returns
    one row per node at that reference year (the backward-compatible path used
    by demand methods).
    """
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
def _capacity_existing_df_cached(sector, year, lifetime=None, year_construction=None):
    # Compute total capacity per node
    node_caps: dict[str, float] = {}
    for node in MODEL_NODES:
        node_caps[node] = 0.0 if node in NODES_WITHOUT_IDEES else installed_capacity_kt(node, sector, year) * 1000 / OPERATING_HOURS

    # Population-proxy override for glass (CH/NO/UK not covered by IDEES); ceramic
    # capacity comes from ceramic_demand_from_fec_df, never from this function.
    if sector == "glass":
        node_caps = _apply_population_proxy(node_caps)

    return _capacity_df_from_node_caps(node_caps, year, lifetime, year_construction)


def capacity_existing_df(sector, year, lifetime=None, year_construction=None):
    """Per-node capacity_existing DataFrame for `sector`.

    Returns a fresh copy on every call: the inner cache holds one shared
    DataFrame, and a caller mutating an uncopied result would silently corrupt
    every later call with the same arguments.
    """
    return _capacity_existing_df_cached(sector, year, lifetime, year_construction).copy()


@functools.lru_cache(maxsize=None)
def _industry_demand_df_cached(sector, year):
    demand = {
        node: (
            0.0 if node in NODES_WITHOUT_IDEES
            else physical_output_kt(node, sector, year) * 1000 / HOURS_PER_YEAR
        )
        for node in MODEL_NODES
    }
    if sector == "glass":
        demand = _apply_population_proxy(demand)
    return pd.DataFrame([{"node": node, "demand": v} for node, v in demand.items()])


def industry_demand_df(sector, year):
    """Per-node demand DataFrame for `sector`. Returns a fresh copy each call
    (see `capacity_existing_df`)."""
    return _industry_demand_df_cached(sector, year).copy()


@functools.lru_cache(maxsize=None)
def _ceramic_demand_from_fec_df_cached(year: int) -> pd.DataFrame:
    ceramic_w = activity_weights(REHFELDT2017_CERAMIC)
    rehfeldt_fuel_GJ_t = weighted_average(REHFELDT2017_CERAMIC, ceramic_w, "fuels_GJ_t")
    kt_yr = {}
    for node in MODEL_NODES:
        if node in NODES_WITHOUT_IDEES:
            kt_yr[node] = 0.0
        else:
            fec = read_sector_thermal_fec(node, "ceramic", year)
            kt_yr[node] = sum(fec.values()) * KTOE_TO_GJ / (rehfeldt_fuel_GJ_t * 1000)
    # Population-proxy scaling for nodes without JRC-IDEES coverage
    kt_yr = _apply_population_proxy(kt_yr)
    return pd.DataFrame([{"node": node, "kt_yr": v} for node, v in kt_yr.items()])


def ceramic_demand_from_fec_df(year: int) -> pd.DataFrame:
    """Derive ceramic production (kt/yr) from JRC-IDEES thermal FEC ÷ Rehfeldt specific energy.

    JRC-IDEES 'Ceramics & other NMM (kt bricks eq.)' is dominated by bricks (~1-2 GJ/t),
    which are not covered by Rehfeldt2017 (tiles/technical/houseware, ~8 GJ/t weighted avg).
    Using thermal FEC from NMM_fec kiln/furnace rows (the same rows used for fuel shares)
    divided by Rehfeldt's weighted specific energy gives a production volume consistent
    with Rehfeldt's energy intensity.

    Returns a DataFrame with columns ['node', 'kt_yr'] — a fresh copy each call
    (see `capacity_existing_df`).
    """
    return _ceramic_demand_from_fec_df_cached(year).copy()


@functools.lru_cache(maxsize=None)
def _food_capacity_existing_df_cached(year, lifetime=None, year_construction=None):
    activity_mt = {node: 0.0 for node in MODEL_NODES}
    for subsector, item in FOOD_PRODUCTION_ITEMS.items():
        production = faostat_production_by_node(item, year)
        total = sum(production[node] for node in MODEL_NODES)
        for node in MODEL_NODES:
            share = production[node] / total if total else 0.0
            activity_mt[node] += share * REHFELDT2017_FOOD[subsector]["activity_Mt"]
    node_caps = {node: activity_mt[node] * 1e6 / OPERATING_HOURS for node in MODEL_NODES}
    return _capacity_df_from_node_caps(node_caps, year, lifetime, year_construction)


def food_capacity_existing_df(year, lifetime=None, year_construction=None):
    """Per-node food capacity_existing DataFrame. Returns a fresh copy each call
    (see `capacity_existing_df`)."""
    return _food_capacity_existing_df_cached(year, lifetime, year_construction).copy()


@functools.lru_cache(maxsize=None)
def eurostat_gross_heat_gwh(sheet, year, xlsx=EUROSTAT_EB_XLSX):
    df = pd.read_excel(INPUT_DATA / "Eurostat" / xlsx, sheet_name=sheet, header=None)
    header_row = _single_row_index(
        df.index[df[0] == "TIME"], f"eurostat_gross_heat_gwh: sheet {sheet!r}"
    )
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
        else:
            logger.warning(
                f"eurostat_gross_heat_gwh: no data for {label!r} in sheet {sheet!r} "
                f"between {EUROSTAT_HEAT_FIRST_YEAR} and {year}; omitted from result."
            )
    return values


def total_industry_heat_demand_gw(year: int, sector: str | None = None) -> dict[str, float]:
    """Total heat carrier demand (GW) per node, summed over glass/paper/food/ceramic
    (or only over `sector`, for the per-sector heat structure).

    Covers heat_industry_0_100 + heat_industry_100_150 + heat_industry_150_200
    via SectorParams.cf_lt = (lt_GJ_t_0_100 + lt_GJ_t_100_200) / 3600 per sector.
    Glass uses AIDRES2023 energy data with Rehfeldt2017 temperature distribution,
    matching process_parametrization._compute_sector_params().
    """
    if sector is not None and sector not in INDUSTRY_HEAT_SECTORS:
        raise ValueError(f"total_industry_heat_demand_gw: unknown sector {sector!r}.")
    params = all_sector_params()
    glass_params, ceramic_params, paper_params, food_params = (
        params["glass"], params["ceramic"], params["paper"], params["food"]
    )
    glass_demand = industry_demand_df("glass", year).set_index("node")["demand"]   # ton/hr
    paper_demand = industry_demand_df("paper", year).set_index("node")["demand"]   # ton/hr
    # Production-based (FAOSTAT "Production"), matching the food carrier's own
    # demand; see get_waste_heat_capacity_limit() in process_parametrization.py.
    food_demand_s = food_capacity_existing_df(year).set_index("node")["capacity_existing"]  # ton/hr
    ceramic_demand = (
        ceramic_demand_from_fec_df(year).set_index("node")["kt_yr"] * 1000.0 / HOURS_PER_YEAR
    )  # ton/hr
    include = INDUSTRY_HEAT_SECTORS if sector is None else (sector,)
    return {
        node: (
            (glass_demand[node] * glass_params.cf_lt if "glass" in include else 0.0)
            + (paper_demand[node] * paper_params.cf_lt if "paper" in include else 0.0)
            + (food_demand_s[node] * food_params.cf_lt if "food" in include else 0.0)
            + (ceramic_demand[node] * ceramic_params.cf_lt if "ceramic" in include else 0.0)
        )
        for node in MODEL_NODES
    }


FUEL_KEYS = ("biomass", "natural_gas", "electrode", "oil", "coal", "waste")


def _normalized_shares(values: dict[str, float]) -> dict[str, float]:
    """Normalize `values` (keyed by fuel name) to shares summing to 1.

    Falls back to 100% natural_gas if the total is zero (no fuel data for this
    node/country) rather than dividing by zero.
    """
    total = sum(values.values())
    if total > 0.0:
        return {fuel: v / total for fuel, v in values.items()}
    return {fuel: (1.0 if fuel == "natural_gas" else 0.0) for fuel in values}


def _eurostat_fuel_shares(
    biomass_gwh: dict[str, float], ng_gwh: dict[str, float], elec_gwh: dict[str, float],
    oil_gwh: dict[str, float], coal_gwh: dict[str, float], waste_gwh: dict[str, float],
    country: str,
) -> dict[str, float]:
    """Fuel-mix shares (biomass, natural_gas, electrode, oil, coal, waste), all
    from Eurostat "Gross heat production". `biomass_gwh` is expected to already
    include biogases (Sheet 63) alongside primary solid biofuels (Sheet 74) —
    see the call site in _demand_based_boiler_capacity_gw. `waste_gwh` is
    expected to already sum industrial + renewable/non-renewable municipal
    waste (Sheets 64-66).
    """
    return _normalized_shares({
        "biomass": biomass_gwh.get(country, 0.0) / OPERATING_HOURS,
        "natural_gas": ng_gwh.get(country, 0.0) / OPERATING_HOURS,
        "electrode": elec_gwh.get(country, 0.0) / OPERATING_HOURS,
        "oil": oil_gwh.get(country, 0.0) / OPERATING_HOURS,
        "coal": coal_gwh.get(country, 0.0) / OPERATING_HOURS,
        "waste": waste_gwh.get(country, 0.0) / OPERATING_HOURS,
    })


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
    header_row = _single_row_index(
        df.index[df[0] == "BranchenNr."], f"_bfe_ch_branch_total_tj: sheet {sheet!r}"
    )
    header = df.iloc[header_row]
    year_cols = [c for c in header.index if isinstance(header[c], (int, float)) and header[c] <= year]
    if not year_cols:
        return 0.0
    col = max(year_cols, key=lambda c: header[c])
    total = 0.0
    for branch in BFE_CH_BRANCHES:
        row = _single_row_index(
            df.index[df[0] == branch], f"_bfe_ch_branch_total_tj: sheet {sheet!r}, branch {branch}"
        )
        value = df.iat[row, col]
        if pd.isna(value):
            continue
        total += float(value)
    return total


@functools.lru_cache(maxsize=4)
def _bfe_ch_fuel_shares(year: int) -> dict[str, float]:
    """Switzerland-specific boiler fuel-mix shares (biomass, natural_gas, electrode, oil, coal, waste).

    Derived from BFE2025, summing final energy consumption across the three branches
    matching this model's process-heat scope (food, paper, glass/ceramics), restricted
    to combustion carriers (Erdgas, Heizöl extra-leicht + mittel/schwer, Holz, Kohle,
    Industrieabfälle). Electricity is excluded from the mix — in these branches it is
    dominated by drives and lighting rather than boilers, and heat-pump/electrode
    boiler capacity is assumed zero for Switzerland (see David2017, "Heat pump
    (industry) capacity"). Kohle (coal, ~2% of the combustion total) and
    Industrieabfälle (industrial waste, ~7%) are included because
    coal_boiler_industry/waste_boiler_industry consume them — see
    ASSUMPTIONS.md, "Boiler (industry) capacity".
    """
    return _normalized_shares({
        "biomass": _bfe_ch_branch_total_tj(BFE_CH_BIOMASS_SHEET, year),
        "natural_gas": _bfe_ch_branch_total_tj(BFE_CH_GAS_SHEET, year),
        "electrode": 0.0,
        "oil": sum(_bfe_ch_branch_total_tj(sheet, year) for sheet in BFE_CH_OIL_SHEETS),
        "coal": _bfe_ch_branch_total_tj(BFE_CH_COAL_SHEET, year),
        "waste": _bfe_ch_branch_total_tj(BFE_CH_WASTE_SHEET, year),
    })


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
def _demand_based_boiler_capacity_gw_cached(year: int) -> dict[str, dict[str, float]]:
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
    default_shares = {fuel: (1.0 if fuel == "natural_gas" else 0.0) for fuel in FUEL_KEYS}
    result: dict[str, dict[str, float]] = {}
    for node in MODEL_NODES:
        country = NODE_TO_EUROSTAT_COUNTRY.get(node)
        if country is not None:
            shares = _eurostat_fuel_shares(biomass_gwh, ng_gwh, elec_gwh, oil_gwh, coal_gwh, waste_gwh, country)
        elif node == "CH":
            shares = ch_shares
        else:
            logger.warning(
                f"_demand_based_boiler_capacity_gw: node {node!r} has no Eurostat "
                "country mapping and is not 'CH'; defaulting to 100% natural gas."
            )
            shares = default_shares
        total = total_demand[node]
        result[node] = {fuel: total * share for fuel, share in shares.items()}
    return result


# --- Per-sector boiler fuel mix (V11) ----------------------------------------
# JRC-IDEES thermal carrier row -> boiler fuel key. "Biomass and waste" is split into
# biomass/waste by the node's own Eurostat/BFE biomass:waste ratio (JRC does not separate
# them). Electricity (electrode boilers) is not among the JRC thermal rows, and
# "Distributed steam" is bought-in heat, not a boiler fuel.
JRC_THERMAL_TO_BOILER_FUEL = {
    "Natural gas and biogas": "natural_gas",
    "Solids": "coal",
    "Derived gases": "coal",
    "LPG": "oil",
    "Diesel oil and liquid biofuels": "oil",
    "Fuel oil": "oil",
    "Other liquids": "oil",
    "Refinery gas": "oil",
}
IDEES_FALLBACK_COUNTRY = "EU27"  # sector fuel mix for the nodes without JRC-IDEES (CH, NO, UK)
# Added to every (normalized) seed share so the fit always has a solution: a sector with
# no reported use of a fuel can still get a little of it if the node's fuel total needs it.
BOILER_FIT_SEED_FLOOR = 1e-3
BOILER_FIT_MAX_ITER = 1000
BOILER_FIT_TOL = 1e-10


def _sector_boiler_fuel_seed(node: str, sector: str, year: int, pooled: dict[str, float]) -> dict[str, float]:
    """Normalized fuel mix (combustion fuels only, no electrode) of `sector`'s thermal
    final energy at `node` from JRC-IDEES; uniform when the sector reports none there."""
    fuels = [f for f in FUEL_KEYS if f != "electrode"]
    country = IDEES_FALLBACK_COUNTRY if node in NODES_WITHOUT_IDEES else node
    breakdown = read_sector_thermal_fec(country, sector, year)
    seed = {f: 0.0 for f in fuels}
    for label, value in breakdown.items():
        if label in JRC_THERMAL_TO_BOILER_FUEL:
            seed[JRC_THERMAL_TO_BOILER_FUEL[label]] += value
    bio_waste = breakdown.get("Biomass and waste", 0.0)
    node_bio_waste = pooled["biomass"] + pooled["waste"]
    waste_frac = pooled["waste"] / node_bio_waste if node_bio_waste > 0 else 0.0
    seed["biomass"] += bio_waste * (1.0 - waste_frac)
    seed["waste"] += bio_waste * waste_frac
    total = sum(seed.values())
    if total <= 0.0:
        return {f: 1.0 / len(fuels) for f in fuels}
    return {f: v / total for f, v in seed.items()}


def _fit_sector_fuel_matrix(
    seed: dict[str, dict[str, float]], row_totals: dict[str, float], col_totals: dict[str, float]
) -> dict[str, dict[str, float]]:
    """Iterative proportional fitting: scale `seed` (sector x fuel) so its rows sum to
    `row_totals` and its columns to `col_totals` (both must have the same grand total)."""
    m = {s: {f: seed[s][f] + BOILER_FIT_SEED_FLOOR for f in col_totals} for s in row_totals}
    for _ in range(BOILER_FIT_MAX_ITER):
        for s, target in row_totals.items():
            row = sum(m[s].values())
            m[s] = {f: (v * target / row if row > 0 else 0.0) for f, v in m[s].items()}
        max_err = 0.0
        for f, target in col_totals.items():
            col = sum(m[s][f] for s in row_totals)
            for s in row_totals:
                m[s][f] = m[s][f] * target / col if col > 0 else 0.0
            max_err = max(max_err, abs(col - target))
        row_err = max(abs(sum(m[s].values()) - t) for s, t in row_totals.items())
        if max(max_err, row_err) <= BOILER_FIT_TOL * max(1.0, sum(row_totals.values())):
            break
    else:
        logger.warning("_fit_sector_fuel_matrix: no convergence after %d iterations.", BOILER_FIT_MAX_ITER)
    return m


@functools.lru_cache(maxsize=4)
def _per_sector_boiler_capacity_gw_cached(year: int) -> dict[str, dict[str, dict[str, float]]]:
    """{sector: {node: {fuel: GW}}}: the pooled boiler capacity of every node split
    between the four sectors such that (a) each sector's boilers sum to its own heat
    demand (total_industry_heat_demand_gw(year, sector)) and (b) each fuel sums over
    the sectors to the pooled Eurostat/BFE value, with the sectors' own JRC-IDEES fuel
    mix deciding who gets which fuel (iterative proportional fitting). Electrode
    capacity has no JRC counterpart and is split by heat demand directly."""
    pooled_caps = _demand_based_boiler_capacity_gw_cached(year)
    demand = {s: total_industry_heat_demand_gw(year, s) for s in INDUSTRY_HEAT_SECTORS}
    result: dict[str, dict[str, dict[str, float]]] = {s: {} for s in INDUSTRY_HEAT_SECTORS}
    for node in MODEL_NODES:
        pooled = pooled_caps[node]
        node_demand = {s: demand[s][node] for s in INDUSTRY_HEAT_SECTORS}
        total = sum(node_demand.values())
        demand_share = {s: (d / total if total > 0 else 0.0) for s, d in node_demand.items()}
        electrode = {s: pooled["electrode"] * demand_share[s] for s in INDUSTRY_HEAT_SECTORS}
        rows = {s: node_demand[s] - electrode[s] for s in INDUSTRY_HEAT_SECTORS}
        cols = {f: v for f, v in pooled.items() if f != "electrode"}
        seed = {s: _sector_boiler_fuel_seed(node, s, year, pooled) for s in INDUSTRY_HEAT_SECTORS}
        fitted = _fit_sector_fuel_matrix(seed, rows, cols)
        for s in INDUSTRY_HEAT_SECTORS:
            result[s][node] = {**fitted[s], "electrode": electrode[s]}
    return result


def _demand_based_boiler_capacity_gw(year: int, sector: str | None = None) -> dict[str, dict[str, float]]:
    """Per-node boiler capacity (GW) scaled to total heat demand with Eurostat fuel shares.

    Returns {node: {"biomass": GW, "natural_gas": GW, "electrode": GW, "oil": GW,
    "coal": GW, "waste": GW}}. CH has no Eurostat entry; it uses Switzerland-specific
    fuel shares derived from BFE's industry-energy survey (BFE2025) instead — see
    _bfe_ch_fuel_shares(). "biomass" includes biogases (Sheet 63) alongside primary
    solid biofuels (Sheet 74) — see ASSUMPTIONS.md, "Boiler (industry) capacity".

    `sector` (per-sector heat structure): that sector's part of it, sized on the
    sector's heat demand and with its own fuel mix — see _per_sector_boiler_capacity_gw_cached().

    Returns a fresh copy on every call: the inner cache holds one shared dict, and
    a caller mutating an uncopied result would silently corrupt every later call.
    """
    if sector is None:
        caps = _demand_based_boiler_capacity_gw_cached(year)
    else:
        if sector not in INDUSTRY_HEAT_SECTORS:
            raise ValueError(f"_demand_based_boiler_capacity_gw: unknown sector {sector!r}.")
        caps = _per_sector_boiler_capacity_gw_cached(year)[sector]
    return {node: dict(v) for node, v in caps.items()}


def boiler_capacity_existing_df_for_fuel(fuel_key: str, year, lifetime=None, year_construction=None, sector=None):
    """Per-node boiler capacity_existing (GW) for one fuel ("biomass",
    "natural_gas", "electrode", "oil", "coal", or "waste"), scaled from
    total industry heat demand via Eurostat/BFE fuel-mix shares (or `sector`'s
    part of it) -- see _demand_based_boiler_capacity_gw()."""
    caps = _demand_based_boiler_capacity_gw(year, sector)
    return _capacity_df_from_node_caps(
        {node: caps[node][fuel_key] for node in MODEL_NODES}, year, lifetime, year_construction
    )
