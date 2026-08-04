"""Dataset for production technology parametrization.

Absorbs the cached computation logic from _params.py: sector_params,
wolf_100_200_split, sector_heat_cfs, fuel_mix_shares, jrc_cost_params,
and the production tech dict builder from production_techs.py.
"""

from __future__ import annotations

import copy
import csv
import functools
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from zen_creator.elements.element import Element

from zen_creator.datasets.datasets._industry_heat_utils import (
    AIDRES2023_GLASS,
    AIDRES2023_GLASS_SHARES,
    GLASS_AIDRES_TO_JRC,
    INPUT_DATA,
    PAPER_REHFELDT_TO_JRC,
    PARAM_BASE_YEAR,
    REHFELDT2017_CERAMIC,
    REHFELDT2017_FOOD,
    REHFELDT2017_GLASS,
    REHFELDT2017_PAPER,
    HOURS_PER_YEAR,
    activity_weights,
    apply_excel_overrides,
    build_conversion_tech,
    ceramic_demand_from_fec_df,
    compute_sector_params,
    fec_shares,
    food_capacity_existing_df,
    gdp_deflator_ratio,
    industry_demand_df,
    load_param_column,
    renormalized_fuel_shares,
    read_sector_thermal_fec,
    sector_weighted_params,
)
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

FEC_YEAR = 2023
FEC_COUNTRY = "EU27"
CAPACITY_YEAR = 2022
JRC_COST_TARGET_YEAR = 2019

HEAT_TEMP_LEVELS = ("0_100", "100_150", "150_200")
HEAT_CARRIER_NAMES = {
    "0_100": "heat_industry_0_100",
    "100_150": "heat_industry_100_150",
    "150_200": "heat_industry_150_200",
}
SECTOR_TO_WOLF = {"food": "Nahrung", "paper": "Papier", "glass": "Nichtmetall", "ceramic": "Nichtmetall"}
OPEX_VAR = {"glass": 15.0, "ceramic": 10.0, "paper": 0.0, "food": 0.0}

_PROCESS_XLSX = INPUT_DATA / "Parametrization" / "process_parametrization.xlsx"
_PROCESS_SHEET = "process_techs"
_WOLF_CSV = INPUT_DATA / "Wolf2017" / "Wolf2017_Tabelle4_7.csv"


def _ceramic_demand_series(year: int) -> pd.Series:
    """Per-node ceramic demand (ton/hr), matching the ceramic carrier's own demand.

    Uses ceramic_demand_from_fec_df() (JRC-IDEES thermal FEC / Rehfeldt specific
    energy), not the plain industry_demand_df("ceramic", ...) physical-output figure,
    which is ~3.5-6x higher (see ASSUMPTIONS.md, Ceramic section).
    """
    return ceramic_demand_from_fec_df(year).set_index("node")["kt_yr"] * 1000.0 / HOURS_PER_YEAR


class ProcessParametrizationDataset(Dataset[pd.DataFrame]):

    name = "process_parametrization"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self._sector_params = self._compute_sector_params()
        self._wolf_split = self._compute_wolf_split()
        self._heat_cfs = self._compute_heat_cfs()
        self._fuel_shares = self._compute_fuel_shares()
        self._cost_params = {s: self._compute_jrc_cost_params(s) for s in ("glass", "ceramic", "paper", "food")}

    def _set_metadata(self) -> MetaData:
        return MetaData(
            name=self.name,
            title="Industry process technology parametrization",
            author=["ZEN Creator"],
            publication="Internal parametrization workbook",
            publication_year=2024,
        )

    def _set_path(self) -> Path | None:
        return _PROCESS_XLSX

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(description=description, metadata=self.metadata)

    # -- Cached computations (run once in __init__) --

    def _compute_sector_params(self):
        glass = compute_sector_params(AIDRES2023_GLASS, REHFELDT2017_GLASS, AIDRES2023_GLASS_SHARES, fuel_key="ng_GJ_t")
        ceramic_w = activity_weights(REHFELDT2017_CERAMIC)
        ceramic = compute_sector_params(REHFELDT2017_CERAMIC, REHFELDT2017_CERAMIC, ceramic_w)
        paper_w = activity_weights(REHFELDT2017_PAPER)
        paper = compute_sector_params(REHFELDT2017_PAPER, REHFELDT2017_PAPER, paper_w)
        food_w = activity_weights(REHFELDT2017_FOOD)
        food = compute_sector_params(REHFELDT2017_FOOD, REHFELDT2017_FOOD, food_w)
        return {"glass": glass, "ceramic": ceramic, "paper": paper, "food": food}

    def _compute_wolf_split(self):
        with open(_WOLF_CSV) as f:
            reader = csv.DictReader(f)
            wolf = {row["industriezweig"]: row for row in reader}
        result = {}
        for sector, wolf_name in SECTOR_TO_WOLF.items():
            row = wolf[wolf_name]
            s100 = float(row["PW_bis_150C"].strip("%")) / 100
            s150 = float(row["PW_bis_200C"].strip("%")) / 100
            total = s100 + s150
            result[sector] = (s100 / total, s150 / total) if total > 0 else (0.5, 0.5)
        return result

    def _compute_heat_cfs(self):
        result = {}
        for sector in ("glass", "ceramic", "paper", "food"):
            p = self._sector_params[sector]
            r100, r150 = self._wolf_split[sector]
            result[sector] = {
                "0_100": p.cf_lt_0_100,
                "100_150": p.cf_lt_100_200 * r100,
                "150_200": p.cf_lt_100_200 * r150,
            }
        return result

    def _compute_fuel_shares(self):
        result = {}
        for sector in ("glass", "ceramic", "paper", "food"):
            breakdown = read_sector_thermal_fec(FEC_COUNTRY, sector, FEC_YEAR)
            result[sector] = renormalized_fuel_shares(fec_shares(breakdown))
        return result

    def _compute_jrc_cost_params(self, sector):
        if sector == "glass":
            return sector_weighted_params(GLASS_AIDRES_TO_JRC, AIDRES2023_GLASS_SHARES, JRC_COST_TARGET_YEAR)
        elif sector == "ceramic":
            # JRC-EU-TIMES has no ceramic-kiln/product-line CAPEX proxy (see "paper"/"food"
            # branches for the same gap in other sectors). No ceramic-specific techno-economic
            # source is available either; instead we use Gardarsdottir et al. 2019 ("Comparison
            # of Technologies for CO2 Capture from Cement Production - Part 2: Cost Analysis",
            # Energies 12, 542) as a documented proxy: cement clinker production is, like
            # ceramics, a non-metallic-mineral process whose core step is high-temperature
            # kiln-firing of a mineral/clay-based feedstock - a closer analogy than glass, whose
            # core step is continuous melting of a silica-soda-lime batch. See ASSUMPTIONS.md
            # (Ceramic section) for the full derivation and cross-check against glass.
            #
            # Reference cement plant (before CO2 capture), all in EUR_2014:
            #   capacity = 120.65 t clinker/h; TPC = 204e6 EUR; annual OPEX = 41e6 EUR/yr
            #   Fixed OPEX = maintenance (2.5% TPC/yr) + insurance (2% TPC/yr)
            #                + operating labor (100 persons x 60 k-EUR/yr)
            #                + admin/support (30% of operating + maintenance labor) = 17.592e6 EUR/yr
            #   non-fuel variable OPEX = raw meal (5 EUR/t) + NOx reagent (~0.65 EUR/t)
            #                            + misc. variable O&M (1.1 EUR/t) = 6.75 EUR/t
            #     (excludes fuel/electricity, which the model prices via conversion_factor,
            #     matching the JRC VAROM convention used for glass/paper/food)
            deflator = gdp_deflator_ratio(2014, JRC_COST_TARGET_YEAR)
            capacity_t_h = 120.65
            tpc = 204e6
            fixed_opex = 0.025 * tpc + 0.02 * tpc + 100 * 60e3 + 0.30 * (100 * 60e3 + 0.40 * 0.025 * tpc)
            variable_opex_per_t = 5.0 + 0.65 + 1.1
            return {
                "capex_specific_conversion": round(tpc / capacity_t_h * deflator, 2),
                "opex_specific_fixed": round(fixed_opex / capacity_t_h * deflator, 2),
                "opex_specific_variable": round(variable_opex_per_t * deflator, 2),
                "lifetime": 25,
            }
        elif sector == "paper":
            # JRC-EU-TIMES gives ~19,996 k€/(t/h) (~2,283 €/(t/yr)), which appears to
            # represent a fully integrated greenfield mill and overshoots real brownfield/
            # conversion projects. Literature values (Stora Enso Oulu 2026, Langerbrugge
            # 2022, Kotkamills 2016) range 425–1,333 €/(t/yr); 700 €/(t/yr) is used as
            # a conservative lower bound. See ASSUMPTIONS.md (Paper section).
            paper_w = activity_weights(REHFELDT2017_PAPER)
            jrc = sector_weighted_params(PAPER_REHFELDT_TO_JRC, paper_w, JRC_COST_TARGET_YEAR)
            jrc["capex_specific_conversion"] = round(700 * 8760, 2)  # 6_132_000 €/(t/h)
            return jrc
        elif sector == "food":
            deflator = gdp_deflator_ratio(PARAM_BASE_YEAR, JRC_COST_TARGET_YEAR)
            return {
                "capex_specific_conversion": round(300 * deflator * 8760, 2),
                "opex_specific_fixed": round(15 * deflator * 8760, 2),
                "opex_specific_variable": 0.0,
                "lifetime": 20,
            }
        return {}

    # -- Production tech dict builder (replicates _build_production_tech_dict) --

    def get_production_tech_dict(self, sector: str) -> dict:
        params = self._sector_params[sector]
        shares = self._fuel_shares[sector]
        cfs = self._heat_cfs[sector]
        data = build_conversion_tech(product=sector, fuel_shares=shares, params=params, opex_specific_variable=OPEX_VAR.get(sector, 0.0))
        active_levels = [l for l in HEAT_TEMP_LEVELS if cfs[l] > 0]
        active_carriers = [HEAT_CARRIER_NAMES[l] for l in active_levels]
        data["input_carrier"]["default_value"] = [*shares.keys(), *active_carriers, "electricity"]
        new_cf = [e for e in data["conversion_factor"] if not any(k.startswith("heat_industry") for k in e)]
        for level in active_levels:
            carrier = HEAT_CARRIER_NAMES[level]
            new_cf.append({carrier: {"default_value": round(cfs[level], 12), "unit": "GW/(tonproduct/hour)"}})
        data["conversion_factor"] = new_cf
        cf_map = {
            **{f"conversion_factor:{c}": c for c in shares},
            **{f"conversion_factor:{HEAT_CARRIER_NAMES[l]}": HEAT_CARRIER_NAMES[l] for l in HEAT_TEMP_LEVELS},
            "conversion_factor:electricity": "electricity",
        }
        overrides = load_param_column(_PROCESS_XLSX, _PROCESS_SHEET, f"{sector}_production")
        data = apply_excel_overrides(data, overrides, conversion_factor_map=cf_map)
        # Re-set carrier lists after Excel overrides — the Excel may still
        # have old 2-level carriers (heat_industry_100_200) which the code
        # has replaced with 3-level carriers. The old code avoided this
        # because apply_attrs_dict skipped list-valued carrier attributes.
        data["input_carrier"]["default_value"] = [*shares.keys(), *active_carriers, "electricity"]
        data["reference_carrier"]["default_value"] = [sector]
        data["output_carrier"]["default_value"] = [sector]
        return data

    # -- get_* methods for Element classes --

    def get_conversion_factor(self, element: Element, sector: str) -> Attribute:
        data = self.get_production_tech_dict(sector)
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=element)

    def get_input_carrier(self, element: Element, sector: str) -> Attribute:
        data = self.get_production_tech_dict(sector)
        return Attribute("input_carrier", default_value=data["input_carrier"]["default_value"], element=element)

    def get_lifetime(self, element: Element, sector: str) -> Attribute:
        data = self.get_production_tech_dict(sector)
        val = data["lifetime"]["default_value"]
        if val == "inf":
            val = np.inf
        attr = Attribute("lifetime", element=element)
        attr.set_data(default_value=float(val), source=self._source_info(f"Lifetime for {sector}_production from process_parametrization.xlsx."))
        return attr

    def get_capex_specific_conversion(self, element: Element, sector: str) -> Attribute:
        data = self.get_production_tech_dict(sector)
        val = data["capex_specific_conversion"]["default_value"]
        if val == "inf":
            val = np.inf
        attr = Attribute("capex_specific_conversion", element=element)
        attr.set_data(default_value=float(val), unit=data["capex_specific_conversion"].get("unit"), source=self._source_info(f"CAPEX for {sector}_production."))
        return attr

    def get_opex_specific_fixed(self, element: Element, sector: str) -> Attribute:
        data = self.get_production_tech_dict(sector)
        val = data["opex_specific_fixed"]["default_value"]
        if val == "inf":
            val = np.inf
        attr = Attribute("opex_specific_fixed", element=element)
        attr.set_data(default_value=float(val), unit=data["opex_specific_fixed"].get("unit"), source=self._source_info(f"Fixed OPEX for {sector}_production."))
        return attr

    def get_opex_specific_variable(self, element: Element, sector: str) -> Attribute:
        data = self.get_production_tech_dict(sector)
        val = data["opex_specific_variable"]["default_value"]
        if val == "inf":
            val = np.inf
        attr = Attribute("opex_specific_variable", element=element)
        attr.set_data(default_value=float(val), unit=data["opex_specific_variable"].get("unit"), source=self._source_info(f"Variable OPEX for {sector}_production."))
        return attr

    def get_carbon_intensity_technology(self, element: Element, sector: str) -> Attribute:
        data = self.get_production_tech_dict(sector)
        val = data["carbon_intensity_technology"]["default_value"]
        if val == "inf":
            val = np.inf
        attr = Attribute("carbon_intensity_technology", element=element)
        attr.set_data(default_value=float(val), unit=data["carbon_intensity_technology"].get("unit"), source=self._source_info(f"Carbon intensity for {sector}_production."))
        return attr

    def get_max_diffusion_rate(self, element: Element, sector: str) -> Attribute:
        data = self.get_production_tech_dict(sector)
        val = data["max_diffusion_rate"]["default_value"]
        if val == "inf":
            val = np.inf
        attr = Attribute("max_diffusion_rate", element=element)
        attr.set_data(default_value=float(val), source=self._source_info(f"Max diffusion rate for {sector}_production."))
        return attr

    def get_heat_capacity_split(self) -> dict[str, float]:
        cfs = self._heat_cfs
        demand_volumes = {
            "glass": industry_demand_df("glass", FEC_YEAR)["demand"].sum(),
            "ceramic": _ceramic_demand_series(FEC_YEAR).sum(),
            "paper": industry_demand_df("paper", FEC_YEAR)["demand"].sum(),
            # Production-based (FAOSTAT "Production"), matching the food carrier's own
            # demand (= capacity_existing since v4.2+); see get_waste_heat_capacity_limit().
            "food": food_capacity_existing_df(FEC_YEAR)["capacity_existing"].sum(),
        }
        totals = {}
        for level in HEAT_TEMP_LEVELS:
            totals[level] = sum(demand_volumes[s] * cfs[s][level] for s in demand_volumes)
        grand_total = sum(totals.values())
        return {level: totals[level] / grand_total for level in HEAT_TEMP_LEVELS}

    def get_waste_heat_capacity_limit(self, element: "Element", temp_level: str) -> Attribute:
        """Per-node capacity_limit for waste-heat HPs at a given temperature level.

        Waste heat available from sector s at node n = demand[s,n] × cf_fuel[s],
        where cf_fuel is the high-temperature (>200°C) fuel heat fraction (GW per
        tonproduct/hr). This is distributed to each temperature level proportionally
        to the sector's low-temp heat demand share at that level.

        capacity_limit is set equal to the available waste heat input (GW), which is a
        conservative bound on the HP heat output (true max output is
        waste_heat × COP/(COP-1), i.e. 1.17–2.26× larger depending on temperature
        level). Cross-checked against Mathiesen2026 (Heat Roadmap Europe) as a sanity
        check — no correction applied; see ASSUMPTIONS.md.
        """
        demands = {
            "glass":   industry_demand_df("glass",   FEC_YEAR).set_index("node")["demand"],
            "ceramic": _ceramic_demand_series(FEC_YEAR),
            "paper":   industry_demand_df("paper",   FEC_YEAR).set_index("node")["demand"],
            # Production-based (FAOSTAT "Production"), matching the food carrier's own
            # demand; see ASSUMPTIONS.md.
            "food":    food_capacity_existing_df(FEC_YEAR).set_index("node")["capacity_existing"],
        }
        cf_fuel = {s: self._sector_params[s].cf_fuel for s in demands}
        share_at_level = {}
        for s in demands:
            total_lt = sum(self._heat_cfs[s][l] for l in HEAT_TEMP_LEVELS)
            share_at_level[s] = (self._heat_cfs[s][temp_level] / total_lt) if total_lt > 0 else 0.0

        wh_series = sum(demands[s] * cf_fuel[s] * share_at_level[s] for s in demands)
        df = wh_series.rename("capacity_limit").to_frame()

        attr = Attribute("capacity_limit", default_value=np.inf, unit="GW", element=element)
        attr.set_data(df=df, source=self._source_info(
            f"Waste-heat HP capacity limit for {temp_level}: sector high-temp fuel demand "
            "(glass/ceramic/paper/food) × sector-specific low-temp heat share at this level. "
            "Source: Rehfeldt2017 temperature distributions, AIDRES2023 (glass), FAOSTAT "
            "production data (food); cross-checked against Mathiesen2026 (Heat Roadmap "
            "Europe) as a sanity check (see ASSUMPTIONS.md)."
        ))
        return attr
