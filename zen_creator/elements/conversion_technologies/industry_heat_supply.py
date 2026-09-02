"""Industry heat supply technology Element subclasses.

3 heat pump variants, 3 boilers, 2 temperature conversion techs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.dea_industrial_heat import DeaIndustrialHeatDataset
from zen_creator.datasets.datasets.eurostat_boiler import EurostatBoilerDataset
from zen_creator.datasets.datasets.heat_tech_parametrization import (
    HP_COP_WASTE_HEAT,
    HP_COP_WATER,
    HeatTechParametrizationDataset,
)
from zen_creator.datasets.datasets.process_parametrization import (
    CAPACITY_YEAR,
    FEC_YEAR,
    KILN_FUEL_SWITCH_CF,
    KILN_FUEL_TECH_LIFETIME,
    ProcessParametrizationDataset,
)
from zen_creator.datasets.datasets.waste_boiler_dh_proxy import WasteBoilerDhProxyDataset
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
#
# Every boiler shares the same carrier wiring, carbon-intensity/diffusion-rate
# source (HeatTechParametrizationDataset), and capacity_existing source
# (EurostatBoilerDataset) -- see _boiler_carrier_methods(). Five of the six
# also share the same cost/efficiency source (DeaIndustrialHeatDataset) -- see
# _dea_boiler_cost_methods(). waste_boiler_industry has no DEA sheet, so it
# supplies its own conversion_factor/lifetime/capex/opex from
# WasteBoilerDhProxyDataset instead, reusing only _boiler_carrier_methods().

def _boiler_carrier_methods(tech_name: str, carrier: str):
    """Return a dict of _set_* methods shared by every boiler regardless of
    its cost/efficiency data source."""

    class _Mixin:
        def _set_reference_carrier(self) -> Attribute:
            return Attribute("reference_carrier", default_value=["heat_industry_150_200"], element=self)

        def _set_input_carrier(self) -> Attribute:
            return Attribute("input_carrier", default_value=[carrier], element=self)

        def _set_output_carrier(self) -> Attribute:
            return Attribute("output_carrier", default_value=["heat_industry_150_200"], element=self)

        def _set_carbon_intensity_technology(self) -> Attribute:
            return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, tech_name)

        def _set_max_diffusion_rate(self) -> Attribute:
            return HeatTechParametrizationDataset().get_max_diffusion_rate(self, tech_name)

        def _set_capacity_existing(self) -> Attribute:
            return EurostatBoilerDataset().get_boiler_capacity(self, tech_name, FEC_YEAR, CAPACITY_YEAR)

    return _Mixin


def _dea_boiler_cost_methods(tech_name: str, carrier: str):
    """Return a dict of _set_* methods for the five boilers whose cost and
    efficiency data comes from the Danish Energy Agency catalogue."""

    class _Mixin:
        def _set_conversion_factor(self) -> Attribute:
            return DeaIndustrialHeatDataset().get_conversion_factor(self, tech_name, carrier)

        def _set_lifetime(self) -> Attribute:
            return DeaIndustrialHeatDataset().get_lifetime(self, tech_name)

        def _set_capex_specific_conversion(self) -> Attribute:
            return DeaIndustrialHeatDataset().get_capex_specific_conversion(self, tech_name)

        def _set_opex_specific_fixed(self) -> Attribute:
            return DeaIndustrialHeatDataset().get_opex_specific_fixed(self, tech_name)

        def _set_opex_specific_variable(self) -> Attribute:
            return DeaIndustrialHeatDataset().get_opex_specific_variable(self, tech_name)

    return _Mixin


class BiomassBoilerIndustry(
    _dea_boiler_cost_methods("biomass_boiler_industry", "biomass"),
    _boiler_carrier_methods("biomass_boiler_industry", "biomass"),
    ConversionTechnology,
):
    """Biomass-fired boiler producing heat_industry_150_200; cost/efficiency
    from DEA sheet "6.2 Boiler, biomass"."""

    name = "biomass_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


class ElectrodeBoilerIndustry(
    _dea_boiler_cost_methods("electrode_boiler_industry", "electricity"),
    _boiler_carrier_methods("electrode_boiler_industry", "electricity"),
    ConversionTechnology,
):
    """Electric boiler producing heat_industry_150_200; cost/efficiency from
    DEA sheet "5.1a Electric boiler steam"."""

    name = "electrode_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


class NaturalGasBoilerIndustry(
    _dea_boiler_cost_methods("natural_gas_boiler_industry", "natural_gas"),
    _boiler_carrier_methods("natural_gas_boiler_industry", "natural_gas"),
    ConversionTechnology,
):
    """Natural-gas-fired boiler producing heat_industry_150_200;
    cost/efficiency from DEA sheet "6.1 Boiler, gas and oil"."""

    name = "natural_gas_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


class OilBoilerIndustry(
    _dea_boiler_cost_methods("oil_boiler_industry", "oil"),
    _boiler_carrier_methods("oil_boiler_industry", "oil"),
    ConversionTechnology,
):
    """Oil-fired boiler producing heat_industry_150_200; cost/efficiency from
    DEA sheet "6.1 Boiler, gas and oil" (shared with the natural-gas boiler)."""

    name = "oil_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


class CoalBoilerIndustry(
    _dea_boiler_cost_methods("coal_boiler_industry", "hard_coal"),
    _boiler_carrier_methods("coal_boiler_industry", "hard_coal"),
    ConversionTechnology,
):
    """Hard-coal-fired boiler producing heat_industry_150_200;
    cost/efficiency from DEA sheet "6.3 Boiler, coal"."""

    name = "coal_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


class WasteBoilerIndustry(
    _boiler_carrier_methods("waste_boiler_industry", "waste"),
    ConversionTechnology,
):
    """Waste-fired boiler producing heat_industry_150_200. No DEA sheet
    exists for this technology; cost/efficiency are proxied from Crystal
    Ball's own waste_boiler_DH (see waste_boiler_dh_proxy.py)."""

    name = "waste_boiler_industry"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")

    def _set_conversion_factor(self) -> Attribute:
        return WasteBoilerDhProxyDataset().get_conversion_factor(self)

    def _set_lifetime(self) -> Attribute:
        return WasteBoilerDhProxyDataset().get_lifetime(self)

    def _set_capex_specific_conversion(self) -> Attribute:
        return WasteBoilerDhProxyDataset().get_capex_specific_conversion(self)

    def _set_opex_specific_fixed(self) -> Attribute:
        return WasteBoilerDhProxyDataset().get_opex_specific_fixed(self)

    def _set_opex_specific_variable(self) -> Attribute:
        return WasteBoilerDhProxyDataset().get_opex_specific_variable(self)


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


# -- Kiln fuel switching (fuel_to_kiln) --------------------------------------
#
# natural_gas_to_kilnfuel / hydrogen_to_kilnfuel / electricity_to_kilnfuel each convert
# one primary carrier into the shared fuel_to_kiln carrier, which ceramic_production/
# glass_production consume instead of a direct natural_gas input (see
# ProcessParametrizationDataset._kiln_fuel_shares / ASSUMPTIONS.md "Ceramic and glass
# kiln fuel switching"). Zero capex/opex (base Technology/ConversionTechnology
# defaults) — this models only the fuel-choice decision, not burner-conversion capex;
# conversion_factor carries the real, AIDRES-derived route efficiency instead.

def _kiln_fuel_methods(fuel: str, with_diffusion_cap: bool):
    """Return a dict of _set_* methods shared by every kiln-fuel-switching
    technology. `max_diffusion_rate` is only defined when `with_diffusion_cap`
    is true -- natural_gas_to_kilnfuel (the incumbent) has no diffusion cap;
    hydrogen/electricity_to_kilnfuel (the switching alternatives) do."""

    class _Mixin:
        def _set_reference_carrier(self) -> Attribute:
            return Attribute("reference_carrier", default_value=["fuel_to_kiln"], element=self)

        def _set_input_carrier(self) -> Attribute:
            return Attribute("input_carrier", default_value=[fuel], element=self)

        def _set_output_carrier(self) -> Attribute:
            return Attribute("output_carrier", default_value=["fuel_to_kiln"], element=self)

        def _set_conversion_factor(self) -> Attribute:
            cf = KILN_FUEL_SWITCH_CF[fuel]
            return Attribute(
                "conversion_factor",
                default_value=[{fuel: {"default_value": cf, "unit": "GW/GW"}}],
                element=self,
            )

        def _set_lifetime(self) -> Attribute:
            return Attribute("lifetime", default_value=float(KILN_FUEL_TECH_LIFETIME), unit="1", element=self)

        def _set_capacity_existing(self) -> Attribute:
            return ProcessParametrizationDataset().get_kiln_fuel_switch_capacity_existing(self, fuel)

    if with_diffusion_cap:
        def _set_max_diffusion_rate(self) -> Attribute:
            return Attribute("max_diffusion_rate", default_value=0.13, unit="1", element=self)

        _Mixin._set_max_diffusion_rate = _set_max_diffusion_rate

    return _Mixin


class NaturalGasToKilnfuel(_kiln_fuel_methods("natural_gas", with_diffusion_cap=False), ConversionTechnology):
    """Converts natural_gas into the shared fuel_to_kiln carrier -- the
    incumbent kiln fuel route, with existing capacity and no diffusion cap."""

    name = "natural_gas_to_kilnfuel"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


class HydrogenToKilnfuel(_kiln_fuel_methods("hydrogen", with_diffusion_cap=True), ConversionTechnology):
    """Converts hydrogen into the shared fuel_to_kiln carrier -- a switching
    alternative to natural_gas_to_kilnfuel, built from scratch."""

    name = "hydrogen_to_kilnfuel"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


class ElectricityToKilnfuel(_kiln_fuel_methods("electricity", with_diffusion_cap=True), ConversionTechnology):
    """Converts electricity into the shared fuel_to_kiln carrier -- a
    switching alternative to natural_gas_to_kilnfuel, built from scratch."""

    name = "electricity_to_kilnfuel"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
