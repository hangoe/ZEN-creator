"""Industry heat supply technology Element subclasses.

3 heat pump variants, 3 boilers, 2 temperature conversion techs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.dea_industrial_heat import DeaIndustrialHeatDataset
from zen_creator.datasets.datasets.eurostat_boiler import EurostatBoilerDataset
from zen_creator.datasets.datasets.faostat_food import FaostatFoodDataset
from zen_creator.datasets.datasets.heat_tech_parametrization import (
    HP_COP_WASTE_HEAT,
    HP_COP_WATER,
    HeatTechParametrizationDataset,
)
from zen_creator.datasets.datasets.jrc_idees_industry import JrcIdeesIndustryDataset
from zen_creator.datasets.datasets.metadata import SourceInformation
from zen_creator.datasets.datasets.process_parametrization import (
    CAPACITY_YEAR,
    FEC_YEAR,
    ProcessParametrizationDataset,
)
from zen_creator.elements.conversion_technologies.conversion_technology import (
    ConversionTechnology,
)
from zen_creator.utils.attribute import Attribute


def _hp_capacity(element, temp_level: str) -> Attribute:
    base_attr = EurostatBoilerDataset().get_heat_pump_capacity(element, CAPACITY_YEAR)
    split = ProcessParametrizationDataset().get_heat_capacity_split()
    if base_attr.df is not None:
        df = base_attr.df.copy()
        # divide by 2: existing capacity split equally between waste-heat and water variants
        df["capacity_existing"] = df["capacity_existing"] * split[temp_level] / 2
        base_attr.df = df
    return base_attr


def _hp_waste_heat_limit(element, temp_level: str) -> Attribute:
    return ProcessParametrizationDataset().get_waste_heat_capacity_limit(element, temp_level)


UPSTREAM_MAX_DIFFUSION_RATE = 0.29  # heat_tech_parametrization.xlsx, all boilers/heat pumps


# -- Cascade capacity_existing for the temp-conversion techs -------------------
# `HeatIndustryTempConversion150`/`100` cascade excess heat down the ladder
# (`heat_industry_150_200` -> `heat_industry_100_150` -> `heat_industry_0_100`,
# lossless). They have no Eurostat/DEA analogue - they're a modeling construct,
# not a deployed technology - so `capacity_existing = 0` by default. Combined
# with `constraint_technology_diffusion_limit_total` pooling capacity_addition/
# capacity_previous across every technology sharing a reference_carrier (capped
# at `market_share_unbounded * sum(capacity_previous)`), a zero starting point
# meant the *entire* 0-100°C/100-150°C group - both temp-conversion techs plus
# all four heat pump variants at those bands, which also have zero
# capacity_existing (no deployed industrial heat pump capacity in Eurostat) -
# had zero pooled capacity_previous, so the constraint allowed zero
# capacity_addition in the first model year regardless of demand. (Tried and
# discarded: an inflated back-solved `max_diffusion_rate`, and a flat
# `capacity_addition_unbounded` seed - both just delayed the same infeasibility
# to a later year/node as demand grew, since neither gave the group a real
# capacity base to grow from.)
#
# Fix: give the temp-conversion techs a real, physically-grounded
# capacity_existing instead. They cascade heat down from the boiler fleet
# (`*_boiler_industry`, reference_carrier `heat_industry_150_200`), so "how
# much of that boiler fleet isn't already spoken for by demand at the band(s)
# above" is a reasonable starting capacity:
#   temp_conversion_150: total boiler capacity - demand at 150-200°C
#   temp_conversion_100: total boiler capacity - demand at 150-200°C and 100-150°C
# glass/ceramic/paper/food each draw at *all three* bands (per-sector,
# per-band shares from process_parametrization.xlsx / the Wolf2017 split), so
# both subtractions are real, not zero. Floored at 0 per node - unlike
# temp_conversion_150 (positive everywhere, EU-wide margin ~20 GW),
# temp_conversion_100 floors to 0 in about a third of nodes (mostly small
# boiler fleets relative to their own 100-150°C draw, e.g. SE, FI, UK), still
# leaving a real EU-wide pooled base (~3.6 GW) for
# `constraint_technology_diffusion_limit_total` rather than 0. If a 0-100°C
# infeasibility shows up in one of the floored nodes, that's the next place to
# look - this fix resolves the 100-150°C cold start confirmed by solving, not
# a guarantee the 0-100°C band is fully clear of the same failure mode.
# With a real non-zero capacity_previous, the ordinary diffusion rate
# (0.29/yr, same as every other heat-supply technology) and the ordinary
# `market_share_unbounded` bootstrap both work as intended - no special-cased
# rate or seed needed.
_HEAT_SECTORS = ("glass", "ceramic", "paper", "food")


def _sector_demand_attr(element, sector: str) -> Attribute:
    """Node-indexed demand (tonproduct/hour) for one industry sector."""
    jrc = JrcIdeesIndustryDataset()
    if sector == "ceramic":
        return jrc.get_ceramic_demand_as_capacity_existing(element, FEC_YEAR)
    if sector == "food":
        return FaostatFoodDataset().get_food_demand_as_capacity_existing(element, FEC_YEAR)
    return jrc.get_demand_as_capacity_existing(element, sector, FEC_YEAR)


def _heat_demand_at_level(element, temp_level: str) -> pd.Series:
    """Node-indexed heat draw (GW) at `temp_level`, summed across glass/ceramic/paper/food."""
    carrier = f"heat_industry_{temp_level}"
    process_ds = ProcessParametrizationDataset()
    total = None
    for sector in _HEAT_SECTORS:
        demand_attr = _sector_demand_attr(element, sector)  # tonproduct/hour, per node
        conversion_factor = process_ds.get_conversion_factor(element, sector).default_value
        cf_value = next((entry[carrier]["default_value"] for entry in conversion_factor if carrier in entry), 0.0)
        if cf_value == 0.0:
            continue
        # demand (tonproduct/hour) and conversion_factor (GW/(tonproduct/hour))
        # are both in their as-declared units here - multiply directly for GW.
        # (The solver rescales both by 1000x internally for the ktonproduct
        # base unit, which cancels out - do not rescale only one side.)
        contribution = demand_attr.df * cf_value
        total = contribution if total is None else total.add(contribution, fill_value=0.0)
    return total if total is not None else pd.Series(dtype=float)


def _boiler_capacity_existing_total(element) -> pd.Series:
    """Node-indexed total existing capacity (GW) across all four industry boilers."""
    boiler_ds = EurostatBoilerDataset()
    getters = [
        boiler_ds.get_biomass_boiler_capacity,
        boiler_ds.get_electrode_boiler_capacity,
        boiler_ds.get_natural_gas_boiler_capacity,
        boiler_ds.get_oil_boiler_capacity,
    ]
    total = None
    for getter in getters:
        by_node = getter(element, FEC_YEAR, CAPACITY_YEAR).df["capacity_existing"].groupby(level="node").sum()
        total = by_node if total is None else total.add(by_node, fill_value=0.0)
    return total


def _cascade_capacity_existing(element, exclude_levels: tuple[str, ...]) -> Attribute:
    capacity = _boiler_capacity_existing_total(element)
    for level in exclude_levels:
        capacity = capacity.subtract(_heat_demand_at_level(element, level), fill_value=0.0)
    capacity = capacity.clip(lower=0.0)
    df = pd.DataFrame({
        "node": capacity.index,
        "year_construction": CAPACITY_YEAR,
        "capacity_existing": capacity.values,
    }).set_index(["node", "year_construction"])
    attr = Attribute("capacity_existing", default_value=0.0, unit="GW", element=element)
    attr.set_data(
        df=df,
        source=SourceInformation(
            description=(
                "Derived: total existing industry boiler capacity (EurostatBoilerDataset) "
                f"minus demand at {exclude_levels or 'no'} higher temperature band(s), "
                "floored at 0. Gives this modeling-construct technology a physically-"
                "grounded starting capacity instead of 0 - see industry_heat_supply.py "
                "comment above _cascade_capacity_existing."
            ),
            metadata=EurostatBoilerDataset().metadata,
        ),
    )
    return attr


# -- Heat pumps ---------------------------------------------------------------
# Two variants per temperature level:
#   _waste_heat: source = waste heat at 50°C (Bever2024, Agora_IGE2023); capacity limited
#   _water:      source = water at 15°C (Agora_IGE2023); unconstrained

def _hp_methods(base_tech: str, dea_tech: str, temp_level: str, cop: float):
    """Return a dict of _set_* methods shared across all HP variants.

    `base_tech` (always "heat_pump_industry") still parametrizes conversion_factor
    (via the Carnot-based `cop` override, unrelated to DEA), carbon intensity, and
    max_diffusion_rate. `dea_tech` selects which DEA temperature tier backs capex/
    opex/lifetime: "heat_pump_industry_0_100" (DEA "up to 125°C") for the 0-100°C
    band, "heat_pump_industry_100_200" (DEA "up to 150°C") for both 100-150°C and
    150-200°C — DEA has no tier above 150°C, so its highest tier is reused as the
    cost proxy for the top band too (see ASSUMPTIONS.md, "New in sector v7.0").
    """
    carrier = f"heat_industry_{temp_level}"

    class _Mixin:
        def _set_reference_carrier(self) -> Attribute:
            return Attribute("reference_carrier", default_value=[carrier], element=self)

        def _set_input_carrier(self) -> Attribute:
            return Attribute("input_carrier", default_value=["electricity"], element=self)

        def _set_output_carrier(self) -> Attribute:
            return Attribute("output_carrier", default_value=[carrier], element=self)

        def _set_conversion_factor(self) -> Attribute:
            return HeatTechParametrizationDataset().get_conversion_factor(self, base_tech, temp_level, cop_override=cop)

        def _set_lifetime(self) -> Attribute:
            return DeaIndustrialHeatDataset().get_lifetime(self, dea_tech)

        def _set_capex_specific_conversion(self) -> Attribute:
            return DeaIndustrialHeatDataset().get_capex_specific_conversion(self, dea_tech)

        def _set_opex_specific_fixed(self) -> Attribute:
            return DeaIndustrialHeatDataset().get_opex_specific_fixed(self, dea_tech)

        def _set_opex_specific_variable(self) -> Attribute:
            return DeaIndustrialHeatDataset().get_opex_specific_variable(self, dea_tech)

        def _set_carbon_intensity_technology(self) -> Attribute:
            return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, base_tech)

        def _set_max_diffusion_rate(self) -> Attribute:
            return HeatTechParametrizationDataset().get_max_diffusion_rate(self, base_tech)

        def _set_capacity_existing(self) -> Attribute:
            return _hp_capacity(self, temp_level)

    return _Mixin


# --- 0–100°C ---

class HeatPumpIndustry0100WasteHeat(_hp_methods("heat_pump_industry", "heat_pump_industry_0_100", "0_100", HP_COP_WASTE_HEAT["0_100"]), ConversionTechnology):
    name = "heat_pump_industry_0_100_waste_heat"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_capacity_limit(self) -> Attribute:
        return _hp_waste_heat_limit(self, "0_100")


class HeatPumpIndustry0100Water(_hp_methods("heat_pump_industry", "heat_pump_industry_0_100", "0_100", HP_COP_WATER["0_100"]), ConversionTechnology):
    name = "heat_pump_industry_0_100_water"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


# --- 100–150°C ---

class HeatPumpIndustry100150WasteHeat(_hp_methods("heat_pump_industry", "heat_pump_industry_100_200", "100_150", HP_COP_WASTE_HEAT["100_150"]), ConversionTechnology):
    name = "heat_pump_industry_100_150_waste_heat"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_capacity_limit(self) -> Attribute:
        return _hp_waste_heat_limit(self, "100_150")


class HeatPumpIndustry100150Water(_hp_methods("heat_pump_industry", "heat_pump_industry_100_200", "100_150", HP_COP_WATER["100_150"]), ConversionTechnology):
    name = "heat_pump_industry_100_150_water"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


# --- 150–200°C ---

class HeatPumpIndustry150200WasteHeat(_hp_methods("heat_pump_industry", "heat_pump_industry_100_200", "150_200", HP_COP_WASTE_HEAT["150_200"]), ConversionTechnology):
    name = "heat_pump_industry_150_200_waste_heat"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_capacity_limit(self) -> Attribute:
        return _hp_waste_heat_limit(self, "150_200")


class HeatPumpIndustry150200Water(_hp_methods("heat_pump_industry", "heat_pump_industry_100_200", "150_200", HP_COP_WATER["150_200"]), ConversionTechnology):
    name = "heat_pump_industry_150_200_water"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


# -- Boilers (produce heat_industry_150_200 only) ----------------------------

class BiomassBoilerIndustry(ConversionTechnology):
    name = "biomass_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["biomass"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_conversion_factor(self, "biomass_boiler_industry", "biomass")

    def _set_lifetime(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_lifetime(self, "biomass_boiler_industry")

    def _set_capex_specific_conversion(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_capex_specific_conversion(self, "biomass_boiler_industry")

    def _set_opex_specific_fixed(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_opex_specific_fixed(self, "biomass_boiler_industry")

    def _set_opex_specific_variable(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_opex_specific_variable(self, "biomass_boiler_industry")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, "biomass_boiler_industry")

    def _set_max_diffusion_rate(self) -> Attribute:
        return HeatTechParametrizationDataset().get_max_diffusion_rate(self, "biomass_boiler_industry")

    def _set_capacity_existing(self) -> Attribute:
        return EurostatBoilerDataset().get_biomass_boiler_capacity(self, FEC_YEAR, CAPACITY_YEAR)


class ElectrodeBoilerIndustry(ConversionTechnology):
    name = "electrode_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_conversion_factor(self, "electrode_boiler_industry", "electricity")

    def _set_lifetime(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_lifetime(self, "electrode_boiler_industry")

    def _set_capex_specific_conversion(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_capex_specific_conversion(self, "electrode_boiler_industry")

    def _set_opex_specific_fixed(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_opex_specific_fixed(self, "electrode_boiler_industry")

    def _set_opex_specific_variable(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_opex_specific_variable(self, "electrode_boiler_industry")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, "electrode_boiler_industry")

    def _set_max_diffusion_rate(self) -> Attribute:
        return HeatTechParametrizationDataset().get_max_diffusion_rate(self, "electrode_boiler_industry")

    def _set_capacity_existing(self) -> Attribute:
        return EurostatBoilerDataset().get_electrode_boiler_capacity(self, FEC_YEAR, CAPACITY_YEAR)


class NaturalGasBoilerIndustry(ConversionTechnology):
    name = "natural_gas_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["natural_gas"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_conversion_factor(self, "natural_gas_boiler_industry", "natural_gas")

    def _set_lifetime(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_lifetime(self, "natural_gas_boiler_industry")

    def _set_capex_specific_conversion(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_capex_specific_conversion(self, "natural_gas_boiler_industry")

    def _set_opex_specific_fixed(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_opex_specific_fixed(self, "natural_gas_boiler_industry")

    def _set_opex_specific_variable(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_opex_specific_variable(self, "natural_gas_boiler_industry")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, "natural_gas_boiler_industry")

    def _set_max_diffusion_rate(self) -> Attribute:
        return HeatTechParametrizationDataset().get_max_diffusion_rate(self, "natural_gas_boiler_industry")

    def _set_capacity_existing(self) -> Attribute:
        return EurostatBoilerDataset().get_natural_gas_boiler_capacity(self, FEC_YEAR, CAPACITY_YEAR)


class OilBoilerIndustry(ConversionTechnology):
    name = "oil_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["oil"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_conversion_factor(self, "oil_boiler_industry", "oil")

    def _set_lifetime(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_lifetime(self, "oil_boiler_industry")

    def _set_capex_specific_conversion(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_capex_specific_conversion(self, "oil_boiler_industry")

    def _set_opex_specific_fixed(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_opex_specific_fixed(self, "oil_boiler_industry")

    def _set_opex_specific_variable(self) -> Attribute:
        return DeaIndustrialHeatDataset().get_opex_specific_variable(self, "oil_boiler_industry")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, "oil_boiler_industry")

    def _set_max_diffusion_rate(self) -> Attribute:
        return HeatTechParametrizationDataset().get_max_diffusion_rate(self, "oil_boiler_industry")

    def _set_capacity_existing(self) -> Attribute:
        return EurostatBoilerDataset().get_oil_boiler_capacity(self, FEC_YEAR, CAPACITY_YEAR)


# -- Temperature conversion cascade ------------------------------------------

class HeatIndustryTempConversion150(ConversionTechnology):
    name = "heat_industry_temp_conversion_150"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["heat_industry_150_200"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return Attribute("conversion_factor", default_value=[{"heat_industry_150_200": {"default_value": 1.0, "unit": "GW/GW"}}], element=self)

    def _set_lifetime(self) -> Attribute:
        return Attribute("lifetime", default_value=30, unit="1", element=self)

    def _set_opex_specific_variable(self) -> Attribute:
        return Attribute("opex_specific_variable", default_value=0.0, unit="Euro/GWh", element=self)

    def _set_max_diffusion_rate(self) -> Attribute:
        return Attribute("max_diffusion_rate", default_value=UPSTREAM_MAX_DIFFUSION_RATE, unit="1", element=self)

    def _set_capacity_existing(self) -> Attribute:
        return _cascade_capacity_existing(self, exclude_levels=("150_200",))


class HeatIndustryTempConversion100(ConversionTechnology):
    name = "heat_industry_temp_conversion_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["heat_industry_100_150"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["heat_industry_0_100"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return Attribute("conversion_factor", default_value=[{"heat_industry_100_150": {"default_value": 1.0, "unit": "GW/GW"}}], element=self)

    def _set_lifetime(self) -> Attribute:
        return Attribute("lifetime", default_value=30, unit="1", element=self)

    def _set_opex_specific_variable(self) -> Attribute:
        return Attribute("opex_specific_variable", default_value=0.0, unit="Euro/GWh", element=self)

    def _set_max_diffusion_rate(self) -> Attribute:
        return Attribute("max_diffusion_rate", default_value=UPSTREAM_MAX_DIFFUSION_RATE, unit="1", element=self)

    def _set_capacity_existing(self) -> Attribute:
        return _cascade_capacity_existing(self, exclude_levels=("150_200", "100_150"))
