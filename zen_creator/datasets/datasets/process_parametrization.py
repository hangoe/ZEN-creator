"""Dataset for production technology parametrization: sector cost/heat
parameters, fuel-mix shares, and the production technology dict builder."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from zen_creator.elements.element import Element

from zen_creator.datasets.datasets._industry_heat_utils import (
    AIDRES2023_GLASS_SHARES,
    GLASS_AIDRES_TO_JRC,
    INPUT_DATA,
    MODEL_NODES,
    PAPER_REHFELDT_TO_JRC,
    PARAM_BASE_YEAR,
    REHFELDT2017_PAPER,
    HOURS_PER_YEAR,
    HEAT_CARRIER_NAMES,
    OPERATING_HOURS,
    _capacity_df_from_node_caps,
    activity_weights,
    all_sector_params,
    build_conversion_tech,
    capacity_existing_df,
    ceramic_demand_from_fec_df,
    fec_shares,
    food_capacity_existing_df,
    gdp_deflator_ratio,
    industry_demand_df,
    renormalized_fuel_shares,
    read_sector_thermal_fec,
    sector_weighted_params,
)
from zen_creator.datasets.datasets.dataset import Dataset
from zen_creator.datasets.datasets.jrc_idees_industry import _apply_paper_bat_override
from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.utils.attribute import Attribute

FEC_YEAR = 2023
FEC_COUNTRY = "EU27"
CAPACITY_YEAR = 2022
JRC_COST_TARGET_YEAR = 2019

HEAT_TEMP_LEVELS = ("0_100", "100_150", "150_200")
SECTOR_TO_WOLF = {"food": "Nahrung", "paper": "Papier", "glass": "Nichtmetall", "ceramic": "Nichtmetall"}

# Process-emission carbon intensity (ton/tonproduct) for {sector}_production -- the one
# *_production cost/emission field that isn't derived by _compute_jrc_cost_params(). Sources:
# JRC-EU-TIMES, IPCC2006, JRC BAT (ceramics). Paper: only direct emissions from the Kraft
# process (calcination) are excluded/neglected, matching the JRC-EU-TIMES convention. Food: no
# direct process CO2 emissions (combustion emissions from fuel/heating techs are captured on
# the carriers/heating techs, not here). Glass: average across glass types (~0.2 t/t) assuming a
# 50% EU recycling share -> 0.1 t/t. Ceramic: back-calculated from JRC BAT (process emissions =
# 15% of total ceramic emissions, the remaining 85% = combustion emissions already captured by
# the carriers ceramic_production consumes). Combustion emissions/t = ceramic total thermal
# energy (8.04 GJ/t, sum of the hard_coal/natural_gas/biomass/heat_industry_0_100/
# heat_industry_100_200 conversion_factor entries) x weighted-average carbon intensity of the
# sector's own hard_coal/natural_gas/biomass fuel mix, applied uniformly across all thermal
# energy as a representative heating-tech mix (biomass treated as biogenic/zero, consistent with
# paper); weighted EF = 0.0453 tCO2/GJ, combustion = 0.364 tCO2/t. Process = combustion x
# (0.15/0.85) = 0.0642 tCO2/t. See ASSUMPTIONS.md (Ceramic).
CARBON_INTENSITY_TECHNOLOGY = {"glass": 0.1, "ceramic": 0.064234, "paper": 0.0, "food": 0.0}

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

# Lifetime (years) of the two heat_industry_temp_conversion_* techs.
TEMP_CONVERSION_LIFETIME = 30

# capacity_limit of the zero-capex, max_diffusion_rate=inf pass-through techs
# (heat_industry_temp_conversion_100/150, natural_gas_to_kilnfuel), as a multiple of the
# flat (annual-average) demand they serve. Needed because ZEN-garden's diffusion
# constraint adds market_share_unbounded × capacity_previous of every same-class tech with
# the same reference carrier to a technology's allowed capacity addition: unbounded, these
# techs' cost-free capacity was degenerate (54,000-209,000 GW in v9.0, ~5,000x peak flow)
# and made the heat pumps' / electric+hydrogen kiln-fuel techs' diffusion limits inactive.
# 2.0 sits ~10% above the largest per-node peak-to-mean ratio observed in the v9.0 DSM
# runs (band heat 1.58, fuel_to_kiln 1.80), so it never restricts dispatch, while keeping
# the market-share base within 2x of the real market. Same value in every scenario so the
# diffusion headroom stays comparable across them. Must stay > 1: ZEN-garden forbids any
# capacity_addition at nodes where capacity_existing >= capacity_limit.
ZERO_COST_CAPACITY_LIMIT_MARGIN = 2.0

# Seed (capacity_addition_unbounded, GW per year, EU total) for the industry heat pumps,
# which start with no installed base. Frozen snapshot of the Crystal Ball base model's
# heat_pump_DH capacity_existing summed over nodes (1.8745 GW; present in only 8 nodes,
# hence redistributed by industrial heat demand below). DH and industry HPs are the same
# technology with a different heat sink; the DH fleet is the market's observed build-out
# so far. Shared equally across the INDUSTRY_HP_SEED_N_TECHS industry HP variants
# (3 bands x water/waste heat). See ASSUMPTIONS.md, "Technology diffusion".
DH_HEAT_PUMP_EXISTING_EU_GW = 1.8745402241776512
INDUSTRY_HP_SEED_N_TECHS = 6

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

_WOLF_CSV = INPUT_DATA / "Wolf2017" / "Wolf2017_Tabelle4_7.csv"


def _ceramic_demand_series(year: int) -> pd.Series:
    """Per-node ceramic demand (ton/hr), matching the ceramic carrier's own demand.

    Uses ceramic_demand_from_fec_df() (JRC-IDEES thermal FEC / Rehfeldt specific
    energy), not the plain industry_demand_df("ceramic", ...) physical-output figure,
    which is ~3.5-6x higher (see ASSUMPTIONS.md, Ceramic section).
    """
    return ceramic_demand_from_fec_df(year).set_index("node")["kt_yr"] * 1000.0 / HOURS_PER_YEAR


def _sector_demand_series(sectors: tuple[str, ...], year: int = FEC_YEAR) -> dict[str, pd.Series]:
    """Per-node demand (ton/hr) for each of `sectors`, keyed by sector name.

    ceramic uses _ceramic_demand_series (FEC-derived); food uses FAOSTAT
    production-based capacity_existing (matching the food carrier's own demand,
    = capacity_existing since v4.2+); other sectors use industry_demand_df.
    """
    result: dict[str, pd.Series] = {}
    for sector in sectors:
        if sector == "ceramic":
            result[sector] = _ceramic_demand_series(year)
        elif sector == "food":
            result[sector] = food_capacity_existing_df(year).set_index("node")["capacity_existing"]
        else:
            result[sector] = industry_demand_df(sector, year).set_index("node")["demand"]
    return result


def _carrier_demand_series() -> dict[str, pd.Series]:
    """Per-node demand (ton/hr) exactly as the glass/ceramic/paper/food carriers write it
    (industry_carriers.py `_set_demand`: demand = capacity_existing at FEC_YEAR, i.e.
    installed capacity / OPERATING_HOURS, with the paper BAT override for CH/NO/UK).
    Keep in sync with those setters. Differs from _sector_demand_series (physical
    output / HOURS_PER_YEAR for glass/paper, HOURS_PER_YEAR for ceramic)."""
    result: dict[str, pd.Series] = {}
    for sector in ("glass", "paper"):
        df = capacity_existing_df(sector, FEC_YEAR)[["node", "capacity_existing"]]
        df = df.rename(columns={"capacity_existing": "demand"})
        if sector == "paper":
            df = _apply_paper_bat_override(df, "demand", OPERATING_HOURS)
        result[sector] = df.set_index("node")["demand"]
    result["ceramic"] = ceramic_demand_from_fec_df(FEC_YEAR).set_index("node")["kt_yr"] * 1000.0 / OPERATING_HOURS
    result["food"] = food_capacity_existing_df(FEC_YEAR).set_index("node")["capacity_existing"]
    return result


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
        return None

    def _set_data(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _source_info(self, description: str) -> SourceInformation:
        return SourceInformation(description=description, metadata=self.metadata)

    # -- Cached computations (run once in __init__) --

    def _compute_sector_params(self):
        return all_sector_params()

    def _compute_wolf_split(self):
        with open(_WOLF_CSV) as f:
            reader = csv.DictReader(f)
            wolf = {row["industriezweig"]: row for row in reader}
        result = {}
        for sector, wolf_name in SECTOR_TO_WOLF.items():
            if wolf_name not in wolf:
                raise KeyError(
                    f"_compute_wolf_split: SECTOR_TO_WOLF maps {sector!r} to "
                    f"{wolf_name!r}, which has no row in {_WOLF_CSV.name}."
                )
            row = wolf[wolf_name]
            try:
                s100 = float(row["PW_bis_150C"].strip("%")) / 100
                s150 = float(row["PW_bis_200C"].strip("%")) / 100
            except ValueError as e:
                raise ValueError(
                    f"_compute_wolf_split: malformed percentage for {wolf_name!r} "
                    f"in {_WOLF_CSV.name}: {e}"
                ) from e
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
        cost = self._cost_params[sector]
        data = build_conversion_tech(
            product=sector, fuel_shares=shares, params=params,
            opex_specific_variable=cost["opex_specific_variable"],
        )
        active_levels = [l for l in HEAT_TEMP_LEVELS if cfs[l] > 0]
        active_carriers = [HEAT_CARRIER_NAMES[l] for l in active_levels]
        data["input_carrier"]["default_value"] = [*shares.keys(), *active_carriers, "electricity"]
        new_cf = [e for e in data["conversion_factor"] if not any(k.startswith("heat_industry") for k in e)]
        for level in active_levels:
            carrier = HEAT_CARRIER_NAMES[level]
            new_cf.append({carrier: {"default_value": round(cfs[level], 12), "unit": "GW/(tonproduct/hour)"}})
        data["conversion_factor"] = new_cf
        for field in ("lifetime", "capex_specific_conversion", "opex_specific_fixed"):
            data[field]["default_value"] = cost[field]
        data["carbon_intensity_technology"]["default_value"] = CARBON_INTENSITY_TECHNOLOGY[sector]
        data["reference_carrier"]["default_value"] = [sector]
        data["output_carrier"]["default_value"] = [sector]
        return data

    # -- get_* methods for Element classes --

    def get_conversion_factor(self, element: Element, sector: str) -> Attribute:
        data = self.get_production_tech_dict(sector)
        attr = Attribute("conversion_factor", element=element)
        attr.set_data(
            default_value=data["conversion_factor"],
            source=self._source_info(f"Conversion factors for {sector}_production."),
        )
        return attr

    def get_input_carrier(self, element: Element, sector: str) -> Attribute:
        data = self.get_production_tech_dict(sector)
        attr = Attribute("input_carrier", element=element)
        attr.set_data(
            default_value=data["input_carrier"]["default_value"],
            source=self._source_info(f"Input carriers for {sector}_production."),
        )
        return attr

    # attr_name -> (source description template, whether to pass unit=)
    _SIMPLE_ATTRS: dict[str, tuple[str, bool]] = {
        "lifetime": ("Lifetime for {sector}_production.", False),
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
        boiler/production-tech capacities (`_capacity_df_from_node_caps`).
        hydrogen_to_kilnfuel/electricity_to_kilnfuel start at 0 (built from scratch).
        """
        attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=element)
        if fuel != "natural_gas":
            return attr

        node_caps = self._kiln_fuel_demand_gw()
        df = _capacity_df_from_node_caps(node_caps, FEC_YEAR, KILN_FUEL_TECH_LIFETIME, CAPACITY_YEAR)
        attr.set_data(
            df=df.set_index(["node", "year_construction"]),
            source=self._source_info(
                "natural_gas_to_kilnfuel capacity_existing: sized to reproduce today's "
                "fuel_to_kiln-eligible natural_gas flow from glass+ceramic combined. See "
                "ASSUMPTIONS.md, 'Ceramic and glass kiln fuel switching'."
            ),
        )
        return attr

    def _kiln_fuel_demand_gw(self, use_carrier_demand: bool = False) -> dict[str, float]:
        """Per-node flat fuel_to_kiln demand (GW) of glass+ceramic:
        Σ_sector demand[sector, node] × fuel_to_kiln_conversion_factor[sector].
        `use_carrier_demand` switches from _sector_demand_series (the v9.0 sizing of
        natural_gas_to_kilnfuel's capacity_existing, kept unchanged) to
        _carrier_demand_series (what the model actually has to produce - used for the
        capacity_limit, which must never undercut real flows)."""
        if use_carrier_demand:
            demands = {s: d for s, d in _carrier_demand_series().items() if s in ("glass", "ceramic")}
        else:
            demands = _sector_demand_series(("glass", "ceramic"))
        node_caps: dict[str, float] = {node: 0.0 for node in MODEL_NODES}
        for sector, demand in demands.items():
            data = self.get_production_tech_dict(sector)
            cf = next(
                (e["fuel_to_kiln"]["default_value"] for e in data["conversion_factor"] if "fuel_to_kiln" in e),
                0.0,
            )
            for node in MODEL_NODES:
                node_caps[node] += demand.get(node, 0.0) * cf
        return node_caps

    def get_kiln_fuel_switch_capacity_limit(self, element: Element, fuel: str) -> Attribute:
        """Per-node capacity_limit (GW) for natural_gas_to_kilnfuel only (inf for the
        hydrogen/electricity alternatives): flat fuel_to_kiln demand ×
        ZERO_COST_CAPACITY_LIMIT_MARGIN. Bounds the otherwise degenerate (zero-capex,
        max_diffusion_rate=inf) capacity that enters the alternatives' market-share
        diffusion term - see ZERO_COST_CAPACITY_LIMIT_MARGIN."""
        attr = Attribute("capacity_limit", default_value=np.inf, unit="GW", element=element)
        if fuel != "natural_gas":
            return attr
        node_caps = self._kiln_fuel_demand_gw(use_carrier_demand=True)
        df = pd.Series(node_caps, name="capacity_limit").mul(ZERO_COST_CAPACITY_LIMIT_MARGIN).to_frame()
        df.index.name = "node"
        attr.set_data(df=df, source=self._source_info(
            f"natural_gas_to_kilnfuel capacity_limit: flat fuel_to_kiln demand (glass+ceramic) "
            f"× {ZERO_COST_CAPACITY_LIMIT_MARGIN}. Bounds the market-share diffusion term of "
            "hydrogen/electricity_to_kilnfuel. See ASSUMPTIONS.md, 'Technology diffusion'."
        ))
        return attr

    def _heat_demand_gw(self, temp_levels: tuple[str, ...]) -> dict[str, float]:
        """Per-node flat heat demand (GW) of glass/ceramic/paper/food, summed over
        `temp_levels`: Σ_sector Σ_level carrier_demand[sector, node] × heat_cf[sector][level].
        Uses _carrier_demand_series (what the model actually has to produce), not
        _sector_demand_series, which differs for glass/paper/ceramic."""
        demands = _carrier_demand_series()
        total = sum(demands[s] * sum(self._heat_cfs[s][lvl] for lvl in temp_levels) for s in demands)
        return {node: float(total.get(node, 0.0)) for node in MODEL_NODES}

    def get_industry_hp_capacity_addition_unbounded(self, element: Element, temp_level: str) -> Attribute:
        """Scalar capacity_addition_unbounded (GW/yr, the diffusion 'seed') for an
        industry heat pump: DH_HEAT_PUMP_EXISTING_EU_GW / INDUSTRY_HP_SEED_N_TECHS,
        divided by the number of nodes (the per-node mean). ZEN-garden reads this
        parameter as one value per technology (index_sets=[]) and applies it at every
        node, so the EU total is recovered when summed over nodes. `temp_level` is kept
        for the call signature only: the seed is not spread by band heat demand."""
        tech_total = DH_HEAT_PUMP_EXISTING_EU_GW / INDUSTRY_HP_SEED_N_TECHS
        per_node = tech_total / len(MODEL_NODES)
        attr = Attribute("capacity_addition_unbounded", element=element)
        attr.set_data(default_value=per_node, unit="GW", source=self._source_info(
            f"{element.name} capacity_addition_unbounded: Crystal Ball heat_pump_DH installed capacity "
            f"({DH_HEAT_PUMP_EXISTING_EU_GW:.3f} GW EU) / {INDUSTRY_HP_SEED_N_TECHS} industry HP variants "
            f"/ {len(MODEL_NODES)} nodes = {per_node:.5f} GW per node, same value at every node, applied "
            "per year. See ASSUMPTIONS.md, 'Technology diffusion'."
        ))
        return attr

    def get_temp_conversion_capacity_existing(self, element: Element, temp_levels: tuple[str, ...]) -> Attribute:
        """Per-node capacity_existing (GW) for a temperature-conversion tech: the flat
        heat demand of every band it passes heat down to (`temp_levels`; e.g. both
        0_100 and 100_150 for heat_industry_temp_conversion_150), i.e. the reference-year
        cascade flow when all sub-150/sub-100 °C heat comes from boilers, as it does
        today. Spread over TEMP_CONVERSION_LIFETIME vintages ending at CAPACITY_YEAR
        (same convention as natural_gas_to_kilnfuel/boilers). Without it the
        heat pumps' market-share diffusion term is exactly 0 in the first year."""
        node_caps = self._heat_demand_gw(temp_levels)
        df = _capacity_df_from_node_caps(node_caps, FEC_YEAR, TEMP_CONVERSION_LIFETIME, CAPACITY_YEAR)
        attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=element)
        attr.set_data(
            df=df.set_index(["node", "year_construction"]),
            source=self._source_info(
                f"{element.name} capacity_existing: flat heat demand of bands {', '.join(temp_levels)} "
                "(glass/ceramic/paper/food), today supplied via boilers. See ASSUMPTIONS.md, "
                "'Technology diffusion'."
            ),
        )
        return attr

    def get_temp_conversion_capacity_limit(self, element: Element, temp_levels: tuple[str, ...]) -> Attribute:
        """Per-node capacity_limit (GW) for a temperature-conversion tech: the same flat
        heat demand as get_temp_conversion_capacity_existing × ZERO_COST_CAPACITY_LIMIT_MARGIN.
        Bounds the otherwise degenerate (zero-capex, max_diffusion_rate=inf) capacity that
        enters the heat pumps' market-share diffusion term."""
        node_caps = self._heat_demand_gw(temp_levels)
        df = pd.Series(node_caps, name="capacity_limit").mul(ZERO_COST_CAPACITY_LIMIT_MARGIN).to_frame()
        df.index.name = "node"
        attr = Attribute("capacity_limit", default_value=np.inf, unit="GW", element=element)
        attr.set_data(df=df, source=self._source_info(
            f"{element.name} capacity_limit: flat heat demand of bands {', '.join(temp_levels)} "
            f"× {ZERO_COST_CAPACITY_LIMIT_MARGIN}. See ASSUMPTIONS.md, 'Technology diffusion'."
        ))
        return attr

    def get_heat_capacity_split(self) -> dict[str, float]:
        cfs = self._heat_cfs
        demand_volumes = {
            sector: series.sum()
            for sector, series in _sector_demand_series(("glass", "ceramic", "paper", "food")).items()
        }
        totals = {}
        for level in HEAT_TEMP_LEVELS:
            totals[level] = sum(demand_volumes[s] * cfs[s][level] for s in demand_volumes)
        grand_total = sum(totals.values())
        if grand_total == 0:
            raise ValueError(
                "get_heat_capacity_split: total heat demand across all sectors is 0; "
                "cannot compute a capacity split."
            )
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
        demands = _sector_demand_series(("glass", "ceramic", "paper", "food"))
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
