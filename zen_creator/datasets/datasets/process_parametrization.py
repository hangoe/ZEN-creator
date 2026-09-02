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
    MODEL_NODES,
    PAPER_REHFELDT_TO_JRC,
    PARAM_BASE_YEAR,
    REHFELDT2017_CERAMIC,
    REHFELDT2017_FOOD,
    REHFELDT2017_GLASS,
    REHFELDT2017_PAPER,
    HOURS_PER_YEAR,
    _boiler_capacity_df_from_node_caps,
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

# Ceramic/glass kiln fuel switching (fuel_to_kiln carrier, see ASSUMPTIONS.md "Ceramic
# and glass kiln fuel switching"). Share of each sector's direct high-temp natural_gas
# input that is rerouted through fuel_to_kiln (switchable to hydrogen_to_kilnfuel/
# electricity_to_kilnfuel); the remainder (ceramic only) stays a fixed natural_gas input.
# Glass: 100% (all NG is kiln-fired melting, fully substitutable). Ceramic: 97.4%,
# derived from Rehfeldt2017 temperature bins + JRC-BAT-CER-2026's >1600°C electrification
# ceiling (the 2.6% locked remainder is a conservative "can't convert to any alternative
# fuel" proxy, not a literal hydrogen limit — JRC-BAT-CER-2026 documents no equivalent
# temperature ceiling for hydrogen firing).
KILN_NG_SWITCHABLE_SHARE = {"glass": 1.0, "ceramic": 46.26 / 47.49}

# Lifetime (years) for natural_gas_to_kilnfuel/hydrogen_to_kilnfuel/
# electricity_to_kilnfuel, matching the external cement fuel-mix hub's *_to_cement_fuel
# techs (no fuel_to_kiln-specific lifetime source available).
KILN_FUEL_TECH_LIFETIME = 20

# natural_gas_to_kilnfuel/hydrogen_to_kilnfuel/electricity_to_kilnfuel conversion_factor
# (GW input per GW fuel_to_kiln output). AIDRES2023-derived from glass's own container/
# flat/fibre production-route energy tables (Tables 19/21/23), weighted by the same
# 60/30/10 AIDRES activity shares used elsewhere for glass, comparing each route's own
# fuel GJ/t against the NG-reference route's natural_gas GJ/t (electricity route netted
# against the ~constant baseline auxiliary electricity already captured separately in
# glass_production's own electricity conversion factor). Ceramic reuses the same ratios
# as a documented cross-sector proxy — JRC-BAT-CER-2026 documents no quantitative
# electric/hydrogen-vs-gas kiln efficiency figure (Ch. 6 explicit data gap), and both
# processes are high-temperature kiln/furnace firing. See ASSUMPTIONS.md, "Ceramic and
# glass kiln fuel switching".
KILN_FUEL_SWITCH_CF = {
    "natural_gas": 1.0,
    "hydrogen": 1.0577,
    "electricity": 0.8438,
}

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


def _kiln_fuel_shares(sector: str, shares: dict[str, float]) -> dict[str, float]:
    """Replace `shares["natural_gas"]` with a `fuel_to_kiln` entry (scaled by
    KILN_NG_SWITCHABLE_SHARE) plus, for ceramic only, a reduced natural_gas remainder.

    hard_coal/biomass entries are untouched. No-op for sectors without a kiln
    fuel-switching split (paper, food) or without a natural_gas share to begin with.
    """
    if sector not in KILN_NG_SWITCHABLE_SHARE or "natural_gas" not in shares:
        return shares
    switchable = KILN_NG_SWITCHABLE_SHARE[sector]
    ng_share = shares["natural_gas"]
    new_shares = {k: v for k, v in shares.items() if k != "natural_gas"}
    new_shares["fuel_to_kiln"] = ng_share * switchable
    remaining = ng_share * (1 - switchable)
    if remaining > 1e-12:
        new_shares["natural_gas"] = remaining
    return new_shares


class ProcessParametrizationDataset(Dataset[pd.DataFrame]):

    name = "process_parametrization"

    def __init__(self, source_path: Path | str | None = None):
        super().__init__(source_path=source_path)
        self._sector_params = self._compute_sector_params()
        self._wolf_split = self._compute_wolf_split()
        self._heat_cfs = self._compute_heat_cfs()
        self._fuel_shares = self._compute_fuel_shares()
        self._cost_params = {s: self._compute_jrc_cost_params(s) for s in ("glass", "ceramic", "paper", "food")}
        self._production_tech_dicts: dict[str, dict] = {}

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
        if sector in self._production_tech_dicts:
            return self._production_tech_dicts[sector]
        data = self._build_production_tech_dict(sector)
        self._production_tech_dicts[sector] = data
        return data

    def _build_production_tech_dict(self, sector: str) -> dict:
        params = self._sector_params[sector]
        shares = _kiln_fuel_shares(sector, self._fuel_shares[sector])
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

    # attr_name -> (source description template, whether to pass unit=)
    _SIMPLE_ATTRS: dict[str, tuple[str, bool]] = {
        "lifetime": ("Lifetime for {sector}_production from process_parametrization.xlsx.", False),
        "capex_specific_conversion": ("CAPEX for {sector}_production.", True),
        "opex_specific_fixed": ("Fixed OPEX for {sector}_production.", True),
        "opex_specific_variable": ("Variable OPEX for {sector}_production.", True),
        "carbon_intensity_technology": ("Carbon intensity for {sector}_production.", True),
        "max_diffusion_rate": ("Max diffusion rate for {sector}_production.", False),
    }

    def _get_attr_from_tech_dict(self, element: Element, sector: str, attr_name: str) -> Attribute:
        data = self.get_production_tech_dict(sector)
        val = data[attr_name]["default_value"]
        if val == "inf":
            val = np.inf
        description, has_unit = self._SIMPLE_ATTRS[attr_name]
        attr = Attribute(attr_name, element=element)
        kwargs = {"default_value": float(val), "source": self._source_info(description.format(sector=sector))}
        if has_unit:
            kwargs["unit"] = data[attr_name].get("unit")
        attr.set_data(**kwargs)
        return attr

    def get_lifetime(self, element: Element, sector: str) -> Attribute:
        return self._get_attr_from_tech_dict(element, sector, "lifetime")

    def get_capex_specific_conversion(self, element: Element, sector: str) -> Attribute:
        return self._get_attr_from_tech_dict(element, sector, "capex_specific_conversion")

    def get_opex_specific_fixed(self, element: Element, sector: str) -> Attribute:
        return self._get_attr_from_tech_dict(element, sector, "opex_specific_fixed")

    def get_opex_specific_variable(self, element: Element, sector: str) -> Attribute:
        return self._get_attr_from_tech_dict(element, sector, "opex_specific_variable")

    def get_carbon_intensity_technology(self, element: Element, sector: str) -> Attribute:
        return self._get_attr_from_tech_dict(element, sector, "carbon_intensity_technology")

    def get_max_diffusion_rate(self, element: Element, sector: str) -> Attribute:
        return self._get_attr_from_tech_dict(element, sector, "max_diffusion_rate")

    def get_kiln_fuel_switch_capacity_existing(self, element: Element, fuel: str) -> Attribute:
        """Per-node capacity_existing (GW) for natural_gas_to_kilnfuel/hydrogen_to_kilnfuel/
        electricity_to_kilnfuel.

        Only natural_gas_to_kilnfuel gets non-zero capacity: sized so its reference-year
        output reproduces today's fuel_to_kiln-eligible natural_gas flow from glass and
        ceramic combined (both sectors draw on the shared fuel_to_kiln carrier — see
        ASSUMPTIONS.md, "Ceramic and glass kiln fuel switching"). Spread across the tech's
        own lifetime ending at CAPACITY_YEAR, same vintage-spreading convention as the
        boiler/production-tech capacities (`_boiler_capacity_df_from_node_caps`).
        hydrogen_to_kilnfuel/electricity_to_kilnfuel start at 0 (built from scratch).
        """
        attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=element)
        if fuel != "natural_gas":
            return attr

        demands = {
            "glass": industry_demand_df("glass", FEC_YEAR).set_index("node")["demand"],
            "ceramic": _ceramic_demand_series(FEC_YEAR),
        }
        node_caps: dict[str, float] = {node: 0.0 for node in MODEL_NODES}
        for sector, demand in demands.items():
            data = self.get_production_tech_dict(sector)
            cf = next(
                (e["fuel_to_kiln"]["default_value"] for e in data["conversion_factor"] if "fuel_to_kiln" in e),
                0.0,
            )
            for node in MODEL_NODES:
                node_caps[node] += demand.get(node, 0.0) * cf

        df = _boiler_capacity_df_from_node_caps(node_caps, FEC_YEAR, KILN_FUEL_TECH_LIFETIME, CAPACITY_YEAR)
        attr.set_data(
            df=df.set_index(["node", "year_construction"]),
            source=self._source_info(
                "natural_gas_to_kilnfuel capacity_existing: sized to reproduce today's "
                "fuel_to_kiln-eligible natural_gas flow from glass+ceramic combined. See "
                "ASSUMPTIONS.md, 'Ceramic and glass kiln fuel switching'."
            ),
        )
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
