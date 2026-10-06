"""Industry heat supply technology Element subclasses.

3 heat pump variants, 3 boilers, 2 temperature conversion techs.

Every class below exists twice: once pooled (V10, e.g. `biomass_boiler_industry`, shared by
all sectors) and once per sector (V11, e.g. `biomass_boiler_industry_paper`, wired to that
sector's own heat carriers and capacity splits). The per-sector classes are generated at the
bottom of this module from the same factories with `sector=<sector>`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets._industry_heat_utils import (
    INDUSTRY_HEAT_SECTORS,
    KILN_FUEL_SECTORS,
    heat_carrier_name,
    kiln_fuel_carrier_name,
    sector_suffixed,
)
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
    TEMP_CONVERSION_LIFETIME,
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


def _hp_waste_heat_limit(element, temp_level: str, sector: str | None = None) -> Attribute:
    return ProcessParametrizationDataset().get_waste_heat_capacity_limit(element, temp_level, sector)


# -- Heat pumps ---------------------------------------------------------------
# Two variants per temperature level:
#   _waste_heat: source = waste heat at 50°C (Bever2024, Agora_IGE2023); capacity limited
#   _water:      source = water at 15°C (Agora_IGE2023); unconstrained

def _hp_methods(base_tech: str, dea_tech: str, temp_level: str, cop: float, waste_heat: bool = False,
                sector: str | None = None):
    """Return a dict of _set_* methods shared across all HP variants.

    `base_tech` (always "heat_pump_industry") still parametrizes conversion_factor
    (via the Carnot-based `cop` override, unrelated to DEA), carbon intensity, and
    max_diffusion_rate. `dea_tech` selects which DEA temperature tier backs capex/
    opex/lifetime: "heat_pump_industry_0_100" (DEA "up to 125°C") for the 0-100°C
    band, "heat_pump_industry_100_200" (DEA "up to 150°C") for both 100-150°C and
    150-200°C — DEA has no tier above 150°C, so its highest tier is reused as the
    cost proxy for the top band too (see ASSUMPTIONS.md, "Heat pump & boiler
    cost/efficiency parametrization (DEA)"). With `waste_heat=True`, capex also gets
    the flat heat-recovery add-on from Stark et al. 2025 (see
    WASTE_HEAT_RECOVERY_CAPEX_EUR_PER_KW in dea_industrial_heat.py). With `sector`, the
    heat pump serves that sector's own heat carrier and its seed is that sector's share.
    """
    carrier = heat_carrier_name(temp_level, sector)

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
            return DeaIndustrialHeatDataset().get_capex_specific_conversion(self, dea_tech, waste_heat=waste_heat)

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

        def _set_capacity_addition_unbounded(self) -> Attribute:
            return ProcessParametrizationDataset().get_industry_hp_capacity_addition_unbounded(
                self, temp_level, sector
            )

    return _Mixin


# --- 0–100°C ---

class HeatPumpIndustry0100WasteHeat(_hp_methods("heat_pump_industry", "heat_pump_industry_0_100", "0_100", HP_COP_WASTE_HEAT["0_100"], waste_heat=True), ConversionTechnology):
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

class HeatPumpIndustry100150WasteHeat(_hp_methods("heat_pump_industry", "heat_pump_industry_100_200", "100_150", HP_COP_WASTE_HEAT["100_150"], waste_heat=True), ConversionTechnology):
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

class HeatPumpIndustry150200WasteHeat(_hp_methods("heat_pump_industry", "heat_pump_industry_100_200", "150_200", HP_COP_WASTE_HEAT["150_200"], waste_heat=True), ConversionTechnology):
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

def _boiler_carrier_methods(tech_name: str, carrier: str, sector: str | None = None):
    """Return a dict of _set_* methods shared by every boiler regardless of
    its cost/efficiency data source. With `sector`, the boiler supplies that
    sector's heat_industry_150_200_<sector> carrier and is sized on its heat demand."""
    heat_carrier = heat_carrier_name("150_200", sector)

    class _Mixin:
        def _set_reference_carrier(self) -> Attribute:
            return Attribute("reference_carrier", default_value=[heat_carrier], element=self)

        def _set_input_carrier(self) -> Attribute:
            return Attribute("input_carrier", default_value=[carrier], element=self)

        def _set_output_carrier(self) -> Attribute:
            return Attribute("output_carrier", default_value=[heat_carrier], element=self)

        def _set_carbon_intensity_technology(self) -> Attribute:
            return HeatTechParametrizationDataset().get_carbon_intensity_technology(self, tech_name)

        def _set_max_diffusion_rate(self) -> Attribute:
            return HeatTechParametrizationDataset().get_max_diffusion_rate(self, tech_name)

        def _set_capacity_existing(self) -> Attribute:
            return EurostatBoilerDataset().get_boiler_capacity(self, tech_name, FEC_YEAR, CAPACITY_YEAR, sector=sector)

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

def _temp_conversion_methods(output_carrier: str, input_carrier: str, served_levels: tuple[str, ...],
                             sector: str | None = None):
    """Return a dict of _set_* methods shared by the two temperature-downgrade
    conversion techs (150-200 -> 100-150 band, 100-150 -> 0-100 band): lossless
    (conversion_factor = 1.0), zero variable OPEX, TEMP_CONVERSION_LIFETIME.

    `served_levels` are the heat bands whose demand flows through the tech (its own
    output band plus every band further down the cascade). They size its
    capacity_existing (today's boiler-supplied cascade flow) and capacity_limit -
    both needed so its zero-cost capacity can't inflate the heat pumps'
    market-share diffusion term (see ZERO_COST_CAPACITY_LIMIT_MARGIN). With `sector`, both
    are sized on that sector's heat demand only (carriers are passed already suffixed).
    """

    class _Mixin:
        def _set_reference_carrier(self) -> Attribute:
            return Attribute("reference_carrier", default_value=[output_carrier], element=self)

        def _set_input_carrier(self) -> Attribute:
            return Attribute("input_carrier", default_value=[input_carrier], element=self)

        def _set_output_carrier(self) -> Attribute:
            return Attribute("output_carrier", default_value=[output_carrier], element=self)

        def _set_conversion_factor(self) -> Attribute:
            return Attribute(
                "conversion_factor",
                default_value=[{input_carrier: {"default_value": 1.0, "unit": "GW/GW"}}],
                element=self,
            )

        def _set_lifetime(self) -> Attribute:
            return Attribute("lifetime", default_value=TEMP_CONVERSION_LIFETIME, unit="1", element=self)

        def _set_opex_specific_variable(self) -> Attribute:
            return Attribute("opex_specific_variable", default_value=0.0, unit="Euro/GWh", element=self)

        def _set_capacity_existing(self) -> Attribute:
            return ProcessParametrizationDataset().get_temp_conversion_capacity_existing(self, served_levels, sector)

        def _set_capacity_limit(self) -> Attribute:
            return ProcessParametrizationDataset().get_temp_conversion_capacity_limit(self, served_levels, sector)

    return _Mixin


class HeatIndustryTempConversion150(
    _temp_conversion_methods("heat_industry_100_150", "heat_industry_150_200", ("0_100", "100_150")),
    ConversionTechnology,
):
    name = "heat_industry_temp_conversion_150"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


class HeatIndustryTempConversion100(
    _temp_conversion_methods("heat_industry_0_100", "heat_industry_100_150", ("0_100",)),
    ConversionTechnology,
):
    name = "heat_industry_temp_conversion_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")


# -- Kiln fuel switching (fuel_to_kiln) --------------------------------------
#
# natural_gas_to_kilnfuel / hydrogen_to_kilnfuel / electricity_to_kilnfuel each convert
# one primary carrier into the shared fuel_to_kiln carrier, which ceramic_production/
# glass_production consume instead of a direct natural_gas input (see
# ProcessParametrizationDataset._kiln_fuel_shares / ASSUMPTIONS.md "Ceramic and glass
# kiln fuel switching"). Zero capex/opex (base Technology/ConversionTechnology
# defaults) — this models only the fuel-choice decision, not burner-conversion capex;
# conversion_factor carries the real, AIDRES-derived route efficiency instead.

def _kiln_fuel_methods(fuel: str, with_diffusion_cap: bool, sector: str | None = None):
    """Return a dict of _set_* methods shared by every kiln-fuel-switching
    technology. `max_diffusion_rate` is only defined when `with_diffusion_cap`
    is true -- natural_gas_to_kilnfuel (the incumbent) has no diffusion cap;
    hydrogen/electricity_to_kilnfuel (the switching alternatives) do. With `sector`
    ("glass"/"ceramic"), the tech feeds that sector's own fuel_to_kiln_<sector> carrier."""
    kiln_carrier = kiln_fuel_carrier_name(sector)

    class _Mixin:
        def _set_reference_carrier(self) -> Attribute:
            return Attribute("reference_carrier", default_value=[kiln_carrier], element=self)

        def _set_input_carrier(self) -> Attribute:
            return Attribute("input_carrier", default_value=[fuel], element=self)

        def _set_output_carrier(self) -> Attribute:
            return Attribute("output_carrier", default_value=[kiln_carrier], element=self)

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
            return ProcessParametrizationDataset().get_kiln_fuel_switch_capacity_existing(self, fuel, sector)

        def _set_capacity_limit(self) -> Attribute:
            return ProcessParametrizationDataset().get_kiln_fuel_switch_capacity_limit(self, fuel, sector)

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


# -- Per-sector copies (V11) ----------------------------------------------------
# Same technologies, wired to <carrier>_<sector> and named <name>_<sector>. Generated
# with the same factories as the pooled classes above (sector=<sector>) and
# type(), the same pattern as the DSM classes in storage_technologies/industry_DSM.py.
# Registered at import like any Element subclass; only instantiated when the
# *_per_sector sectors (industry_heat_per_sector & co.) are added.

def _make_tech_class(class_name: str, tech_name: str, bases: tuple[type, ...]) -> type[ConversionTechnology]:
    def __init__(self, model: Model) -> None:
        ConversionTechnology.__init__(self, model=model, power_unit="GW")

    return type(
        class_name,
        (*bases, ConversionTechnology),
        {"__module__": __name__, "__qualname__": class_name, "__init__": __init__, "name": tech_name},
    )


def _waste_boiler_cost_methods():
    """Cost/efficiency of waste_boiler_industry (proxy of waste_boiler_DH), as a mixin
    so the per-sector waste boilers can reuse it (WasteBoilerIndustry defines the same
    five methods directly on the class)."""

    class _Mixin:
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

    return _Mixin


# (class-name prefix, tech_name, input carrier, DEA-backed?) for every pooled boiler
_BOILER_SPECS = (
    ("BiomassBoilerIndustry", "biomass_boiler_industry", "biomass", True),
    ("ElectrodeBoilerIndustry", "electrode_boiler_industry", "electricity", True),
    ("NaturalGasBoilerIndustry", "natural_gas_boiler_industry", "natural_gas", True),
    ("OilBoilerIndustry", "oil_boiler_industry", "oil", True),
    ("CoalBoilerIndustry", "coal_boiler_industry", "hard_coal", True),
    ("WasteBoilerIndustry", "waste_boiler_industry", "waste", False),
)

# (class-name prefix, tech_name, DEA tier, temp level, waste-heat variant?)
_HP_SPECS = tuple(
    (
        f"HeatPumpIndustry{level.replace('_', '')}{'WasteHeat' if waste else 'Water'}",
        f"heat_pump_industry_{level}_{'waste_heat' if waste else 'water'}",
        "heat_pump_industry_0_100" if level == "0_100" else "heat_pump_industry_100_200",
        level,
        waste,
    )
    for level in ("0_100", "100_150", "150_200")
    for waste in (True, False)
)

# (class-name prefix, tech_name, output band, input band, served bands)
_CASCADE_SPECS = (
    ("HeatIndustryTempConversion150", "heat_industry_temp_conversion_150", "100_150", "150_200", ("0_100", "100_150")),
    ("HeatIndustryTempConversion100", "heat_industry_temp_conversion_100", "0_100", "100_150", ("0_100",)),
)

# (class-name prefix, tech_name, fuel, has diffusion cap?)
_KILN_SPECS = (
    ("NaturalGasToKilnfuel", "natural_gas_to_kilnfuel", "natural_gas", False),
    ("HydrogenToKilnfuel", "hydrogen_to_kilnfuel", "hydrogen", True),
    ("ElectricityToKilnfuel", "electricity_to_kilnfuel", "electricity", True),
)

HEAT_PUMP_CLASSES_BY_SECTOR: dict[str, dict[str, type[ConversionTechnology]]] = {}
BOILER_CLASSES_BY_SECTOR: dict[str, list[type[ConversionTechnology]]] = {}
CASCADE_CLASSES_BY_SECTOR: dict[str, list[type[ConversionTechnology]]] = {}
KILN_FUEL_CLASSES_BY_SECTOR: dict[str, list[type[ConversionTechnology]]] = {}

for _sector in INDUSTRY_HEAT_SECTORS:
    _suffix = _sector.capitalize()

    HEAT_PUMP_CLASSES_BY_SECTOR[_sector] = {}
    for _prefix, _name, _dea_tech, _level, _waste in _HP_SPECS:
        _cop = (HP_COP_WASTE_HEAT if _waste else HP_COP_WATER)[_level]
        _mixin = _hp_methods("heat_pump_industry", _dea_tech, _level, _cop, waste_heat=_waste, sector=_sector)
        if _waste:
            # bind the loop variables: the setter runs later, at build time
            def _set_capacity_limit(self, _level=_level, _sector=_sector) -> Attribute:
                return _hp_waste_heat_limit(self, _level, _sector)

            _mixin._set_capacity_limit = _set_capacity_limit
        _cls = _make_tech_class(f"{_prefix}{_suffix}", sector_suffixed(_name, _sector), (_mixin,))
        HEAT_PUMP_CLASSES_BY_SECTOR[_sector][f"{_level}_{'waste_heat' if _waste else 'water'}"] = _cls
        globals()[_cls.__name__] = _cls

    BOILER_CLASSES_BY_SECTOR[_sector] = []
    for _prefix, _name, _fuel, _dea in _BOILER_SPECS:
        _carrier_mixin = _boiler_carrier_methods(_name, _fuel, sector=_sector)
        _cost_mixin = _dea_boiler_cost_methods(_name, _fuel) if _dea else _waste_boiler_cost_methods()
        _cls = _make_tech_class(f"{_prefix}{_suffix}", sector_suffixed(_name, _sector), (_cost_mixin, _carrier_mixin))
        BOILER_CLASSES_BY_SECTOR[_sector].append(_cls)
        globals()[_cls.__name__] = _cls

    CASCADE_CLASSES_BY_SECTOR[_sector] = []
    for _prefix, _name, _out_level, _in_level, _served in _CASCADE_SPECS:
        _mixin = _temp_conversion_methods(
            heat_carrier_name(_out_level, _sector), heat_carrier_name(_in_level, _sector), _served, sector=_sector
        )
        _cls = _make_tech_class(f"{_prefix}{_suffix}", sector_suffixed(_name, _sector), (_mixin,))
        CASCADE_CLASSES_BY_SECTOR[_sector].append(_cls)
        globals()[_cls.__name__] = _cls

    if _sector in KILN_FUEL_SECTORS:
        KILN_FUEL_CLASSES_BY_SECTOR[_sector] = []
        for _prefix, _name, _fuel, _cap in _KILN_SPECS:
            _mixin = _kiln_fuel_methods(_fuel, with_diffusion_cap=_cap, sector=_sector)
            _cls = _make_tech_class(f"{_prefix}{_suffix}", sector_suffixed(_name, _sector), (_mixin,))
            KILN_FUEL_CLASSES_BY_SECTOR[_sector].append(_cls)
            globals()[_cls.__name__] = _cls

del _sector, _suffix, _prefix, _name, _dea_tech, _level, _waste, _cop, _mixin, _cls
del _fuel, _dea, _carrier_mixin, _cost_mixin, _out_level, _in_level, _served, _cap
