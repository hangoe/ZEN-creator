"""Industry demand-side management (DSM) storage technologies.

Product carriers get a DSM storage that allows the optimizer to shift production
in time. Every DSM technology is parametrized from one of three demand-shiftability
categories (Cat 1/2/3), assigned per carrier and per "optimistic"/"pessimistic"
variant according to `input_data/DSM_parametrization/DSM_literature_review.md`:

  - Cat 1 = fully flexible: low cost, long shifting horizon.
  - Cat 2 = partially flexible / short timescales: moderate cost and horizon.
  - Cat 3 = not flexible at all: very high cost (effectively priced out) and a
    short horizon.

Each carrier has two technology classes, e.g. `GlassDSMOptimistic` and
`GlassDSMPessimistic`, so that a model can be built with either the optimistic or
the pessimistic assumption set (see `zen_creator/sectors/industry_dsm.py`).

Covered carriers:
  - glass, ceramic, paper, food  (industry_heat sector products)
  - ammonia, clinker, methanol, primary_steel, secondary_steel, olefin
    (existing Crystal Ball carriers; no zen_creator carrier class needed)

Ammonia and methanol are modeled on an energy basis (`power_unit = "GW"`, reference
carrier demand in GW/GWh) rather than the `tonproduct/hour` mass basis every other
DSM technology uses. `capex_specific_storage_energy` and `opex_specific_variable`
are converted from the category's per-tonne placeholder value to an equivalent
per-GWh value using each carrier's lower heating value (LHV), so the same real cost
per tonne of product is preserved across all DSM technologies regardless of unit
basis — see `_storage_cost_value` / `_LHV_GJ_PER_TONNE` below.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

import numpy as np

from zen_creator.datasets.datasets.metadata import MetaData, SourceInformation
from zen_creator.elements.storage_technologies.storage_technology import (
    StorageTechnology,
)
from zen_creator.utils.attribute import Attribute

_DSM_METADATA = MetaData(
    name="industry_DSM",
    title="Industry demand-side management assumption",
    author=["ZEN Creator"],
    publication="Internal assumption",
    publication_year=2024,
)

_DSM_LIFETIME = 50.0

_DSM_EFFICIENCY = 0.999

_DSM_EFFICIENCY_SOURCE = SourceInformation(
    description=(
        f"efficiency_charge = efficiency_discharge = {_DSM_EFFICIENCY} (not 1.0) for "
        "all product DSM technologies — with lossless charge/discharge, simultaneous "
        "charging and discharging of the same product stock is a free, physically "
        "meaningless cycle for the optimizer, since it costs nothing and nets to zero "
        "stock change. A small round-trip loss makes any such cycling strictly costly, "
        "without materially affecting the shifting behaviour the DSM storage is meant "
        "to represent."
    ),
    metadata=_DSM_METADATA,
)

_CATEGORY_METADATA = MetaData(
    name="dsm_literature_review",
    title="DSM demand-shiftability categorization plan",
    author=["ZEN Creator"],
    publication="input_data/DSM_parametrization/DSM_literature_review.md",
    publication_year=2026,
)

_LHV_METADATA = MetaData(
    name="lhv_conversion",
    title="Ammonia/methanol LHV used to convert DSM cost params to an energy basis",
    author=["ZEN Creator"],
    publication=(
        "IEA-AMF fuel properties (ammonia, https://www.iea-amf.org/content/"
        "fuel_information/ammonia/fuel_properties); H2Tools/EngineeringToolbox "
        "calorific value references (methanol)"
    ),
    publication_year=2026,
)

# Lower heating value, GJ/t (numerically equal to MJ/kg). Standard literature
# figures, not calibrated to a specific process — same caveat as _CATEGORY_PARAMS.
_LHV_GJ_PER_TONNE: dict[str, float] = {
    "ammonia": 18.6,
    "methanol": 19.9,
}


def _lhv_gwh_per_tonproduct(carrier_name: str) -> float | None:
    """GWh contained in one tonproduct of `carrier_name`, or None if carrier_name is
    not energy-based. 1 tonproduct/hour x 1 GJ/t = 1 GJ/h = 1/3600 GW, so dividing
    GJ/t by 3600 gives GWh per tonproduct (same identity as
    _industry_heat_utils.GJ_per_t_to_conversion_factor, kept local here to avoid
    pulling that module's pandas/openpyxl/xlrd dependencies into this file)."""
    gj_per_t = _LHV_GJ_PER_TONNE.get(carrier_name)
    return None if gj_per_t is None else gj_per_t / 3600.0


def _storage_cost_value(carrier_name: str, category_value: float) -> float:
    """Convert a category's Euro/tonproduct placeholder value into the equivalent
    Euro/GWh value for energy-based carriers (ammonia, methanol), so the same real
    cost per tonne of product applies regardless of the technology's unit basis.
    No-op for mass-based carriers."""
    lhv = _lhv_gwh_per_tonproduct(carrier_name)
    return category_value if lhv is None else category_value / lhv


# Placeholder cost/duration shape per category: (capex, opex_var, energy_to_power_ratio_max).
# Cat 1 cheap + long horizon, Cat 3 expensive + short horizon (effectively priced
# out), Cat 2 in between. Units: EUR/(power_unit*h), EUR/(power_unit*h), hours.
_CATEGORY_PARAMS: dict[int, tuple[float, float, float]] = {
    1: (1.0, 1.0, 336.0),  # fully flexible: near-free, 2-week horizon
    2: (20.0, 20.0, 48.0),  # partially flexible: moderate cost, 2-day horizon
    3: (1000.0, 1000.0, 2.0),  # not flexible: priced out, 2h horizon
}

# carrier_name -> {"pessimistic": category, "optimistic": category}, transcribed from
# input_data/DSM_parametrization/DSM_literature_review.md. Clinker is assigned Cat 3 in
# both variants, matching Golmohamadi2021's characterization of clinker production as an
# uninterruptible process with only low/very-low/medium flexibility potential.
#
# primary_steel is Cat 3 in both variants, overriding what
# DSM_literature_review.md's cited sources (Boldrini2024, Golmohamadi2021) suggest
# for the optimistic (H2-DRI-EAF) case (Cat 2); see _CATEGORY_OVERRIDE_NOTES below.
_SECTOR_CATEGORIES: dict[str, dict[str, int]] = {
    "glass": {"pessimistic": 3, "optimistic": 3},
    "ceramic": {"pessimistic": 3, "optimistic": 2},
    "paper": {"pessimistic": 2, "optimistic": 1},
    "food": {"pessimistic": 3, "optimistic": 2},
    "methanol": {"pessimistic": 2, "optimistic": 1},
    "primary_steel": {"pessimistic": 3, "optimistic": 3},
    "secondary_steel": {"pessimistic": 2, "optimistic": 1},
    "olefin": {"pessimistic": 3, "optimistic": 2},
    "ammonia": {"pessimistic": 3, "optimistic": 2},
    "clinker": {"pessimistic": 3, "optimistic": 3},
}

# Per-carrier/variant notes appended to the source description where the assigned
# category deviates from a literal reading of DSM_literature_review.md's cited
# sources — e.g. a newer internal re-evaluation rather than a new citation.
_CATEGORY_OVERRIDE_NOTES: dict[tuple[str, str], str] = {
    ("primary_steel", "optimistic"): (
        " Re-evaluated to Cat 3 (from Cat 2) as a new evaluation; sources "
        "(Boldrini2024, Golmohamadi2021) unchanged."
    ),
}


def _category(carrier_name: str, variant: str) -> int:
    return _SECTOR_CATEGORIES[carrier_name][variant]


def _category_source(carrier_name: str, variant: str) -> SourceInformation:
    category = _category(carrier_name, variant)
    note = _CATEGORY_OVERRIDE_NOTES.get((carrier_name, variant), "")
    return SourceInformation(
        description=(
            f"{carrier_name} DSM, {variant} variant: Cat {category} per "
            "DSM_literature_review.md (Cat 1 = fully flexible, Cat 2 = partially "
            f"flexible/short timescales, Cat 3 = not flexible at all).{note}"
        ),
        metadata=_CATEGORY_METADATA,
    )


def _storage_cost_source(carrier_name: str, variant: str) -> SourceInformation:
    source = _category_source(carrier_name, variant)
    lhv = _LHV_GJ_PER_TONNE.get(carrier_name)
    if lhv is None:
        return source
    return SourceInformation(
        description=(
            f"{source.description} Converted from Euro/tonproduct to Euro/GWh via "
            f"{carrier_name}'s LHV of {lhv} GJ/t."
        ),
        metadata={"dsm_literature_review": _CATEGORY_METADATA, "lhv_conversion": _LHV_METADATA},
    )


def _dsm_capacity_limit(element, carrier_name: str) -> Attribute:
    """Per-node capacity_limit = 1 × carrier demand."""
    carrier = element.model.elements.get(carrier_name)
    attr = Attribute("capacity_limit", element=element)
    if carrier is None or carrier.demand.df is None:
        # No per-node demand data available: fall back to the same unbounded
        # default_value used for any node missing from `limit_df` below, so this
        # branch returns an Attribute shaped the same way as the success path
        # (unit/source set, no df) rather than a bare, unpopulated one.
        reason = "carrier not found" if carrier is None else "demand.df is None"
        attr.set_data(
            default_value=np.inf,
            unit=element.power_unit,
            source=SourceInformation(
                description=(
                    f"capacity_limit for {carrier_name} DSM: no per-node demand "
                    f"data available for carrier {carrier_name!r} ({reason}); "
                    "defaulting to unbounded (no limit)."
                ),
                metadata=_DSM_METADATA,
            ),
        )
        return attr
    raw = carrier.demand.df
    # df may be a Series (node index) or a DataFrame (node index, "demand" column)
    demand_series = raw if raw.ndim == 1 else raw.iloc[:, 0]
    limit_df = (demand_series * 1.0).rename("capacity_limit").to_frame()
    attr.set_data(
        default_value=np.inf,
        unit=element.power_unit,
        df=limit_df,
        source=SourceInformation(
            description=(
                f"capacity_limit = 1 × per-node {carrier_name} carrier demand "
                "(100% of demand — bounds DSM stock without blocking flexibility)."
            ),
            metadata=_DSM_METADATA,
        ),
    )
    return attr


class _IndustryDSMTechnology:
    """Shared logic for category-parametrized industry DSM technologies, mixed in
    alongside `StorageTechnology` by every concrete class below (rather than
    subclassed directly) so it does not add an extra level to the MRO between the
    concrete class and `StorageTechnology`. `Element.relative_output_path` prepends
    a path segment for every ancestor class that carries a `subpath` attribute —
    including ones that only inherit it — so an intermediate `StorageTechnology`
    subclass here would double up the `set_storage_technologies` folder segment for
    every DSM technology.

    Subclasses set `_carrier_name` (the reference carrier) and `_variant`
    ("optimistic" or "pessimistic"); cost and duration are looked up from
    `_SECTOR_CATEGORIES` / `_CATEGORY_PARAMS` accordingly. Relies on being combined
    with `StorageTechnology` (via `class Foo(_IndustryDSMTechnology,
    StorageTechnology)`) for `self.power_unit`, `super().__init__`, etc.
    """

    _carrier_name: str
    _variant: str

    def __init__(self, model: Model, power_unit: str = "tonproduct/hour"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=[self._carrier_name], element=self)

    def _set_capacity_limit(self) -> Attribute:
        return _dsm_capacity_limit(self, self._carrier_name)

    def _set_efficiency_charge(self) -> Attribute:
        attr = Attribute("efficiency_charge", element=self)
        attr.set_data(default_value=_DSM_EFFICIENCY, unit="1", source=_DSM_EFFICIENCY_SOURCE)
        return attr

    def _set_efficiency_discharge(self) -> Attribute:
        attr = Attribute("efficiency_discharge", element=self)
        attr.set_data(default_value=_DSM_EFFICIENCY, unit="1", source=_DSM_EFFICIENCY_SOURCE)
        return attr

    def _set_lifetime(self) -> Attribute:
        attr = Attribute("lifetime", element=self)
        attr.set_data(
            default_value=_DSM_LIFETIME,
            unit="1",
            source=_category_source(self._carrier_name, self._variant),
        )
        return attr

    def _set_capex_specific_storage_energy(self) -> Attribute:
        capex, _, _ = _CATEGORY_PARAMS[_category(self._carrier_name, self._variant)]
        attr = Attribute("capex_specific_storage_energy", element=self)
        attr.set_data(
            default_value=_storage_cost_value(self._carrier_name, capex),
            unit=f"Euro/({self.power_unit}*h)",
            source=_storage_cost_source(self._carrier_name, self._variant),
        )
        return attr

    def _set_opex_specific_variable(self) -> Attribute:
        _, opex_var, _ = _CATEGORY_PARAMS[_category(self._carrier_name, self._variant)]
        attr = Attribute("opex_specific_variable", element=self)
        attr.set_data(
            default_value=_storage_cost_value(self._carrier_name, opex_var),
            unit=f"Euro/({self.power_unit}*h)",
            source=_storage_cost_source(self._carrier_name, self._variant),
        )
        return attr

    def _set_energy_to_power_ratio_max(self) -> Attribute:
        _, _, e2p_max = _CATEGORY_PARAMS[_category(self._carrier_name, self._variant)]
        attr = Attribute("energy_to_power_ratio_max", element=self)
        attr.set_data(
            default_value=e2p_max,
            unit="h",
            source=_category_source(self._carrier_name, self._variant),
        )
        return attr


# ---------------------------------------------------------------------------
# One concrete class pair (Optimistic/Pessimistic) per carrier, generated from a
# table instead of hand-written: every class only ever set `name`, `_carrier_name`,
# `_variant`, and (ammonia/methanol only) a `power_unit="GW"` default -- all other
# behaviour comes from `_IndustryDSMTechnology`. carrier_name -> (class-name prefix,
# default power_unit). Prefixes are not a mechanical camel-case of carrier_name
# (e.g. "primary_steel" -> "Primarysteel", matching the class names already in use
# elsewhere in this codebase/tests).
#
#   glass, ceramic, paper, food: industry_heat sector products
#   ammonia, clinker, methanol, primary_steel, secondary_steel, olefin: existing
#     Crystal Ball carriers (no zen_creator carrier class needed)
_DSM_CARRIERS: dict[str, tuple[str, str]] = {
    "glass": ("Glass", "tonproduct/hour"),
    "ceramic": ("Ceramic", "tonproduct/hour"),
    "paper": ("Paper", "tonproduct/hour"),
    "food": ("Food", "tonproduct/hour"),
    "ammonia": ("Ammonia", "GW"),
    "clinker": ("Clinker", "tonproduct/hour"),
    "methanol": ("Methanol", "GW"),
    "primary_steel": ("Primarysteel", "tonproduct/hour"),
    "secondary_steel": ("Secondarysteel", "tonproduct/hour"),
    "olefin": ("Olefin", "tonproduct/hour"),
}


def _make_dsm_technology_class(
    carrier_name: str, variant: str, class_prefix: str, power_unit: str
) -> type[_IndustryDSMTechnology]:
    class_name = f"{class_prefix}DSM{variant.capitalize()}"

    def __init__(self, model: Model, power_unit: str = power_unit) -> None:
        _IndustryDSMTechnology.__init__(self, model=model, power_unit=power_unit)

    namespace = {
        "__module__": __name__,
        "__qualname__": class_name,
        "__init__": __init__,
        "name": f"{carrier_name}_DSM",
        "_carrier_name": carrier_name,
        "_variant": variant,
    }
    return type(class_name, (_IndustryDSMTechnology, StorageTechnology), namespace)


for _carrier_name, (_class_prefix, _power_unit) in _DSM_CARRIERS.items():
    for _variant in ("optimistic", "pessimistic"):
        _cls = _make_dsm_technology_class(_carrier_name, _variant, _class_prefix, _power_unit)
        globals()[_cls.__name__] = _cls
del _carrier_name, _class_prefix, _power_unit, _variant, _cls
