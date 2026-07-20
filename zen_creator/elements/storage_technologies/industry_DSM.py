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

_CATEGORY_METADATA = MetaData(
    name="dsm_literature_review",
    title="DSM demand-shiftability categorization plan",
    author=["ZEN Creator"],
    publication="input_data/DSM_parametrization/DSM_literature_review.md",
    publication_year=2026,
)

# Placeholder cost/duration shape per category: (capex, opex_var, energy_to_power_ratio_max).
# Cat 1 cheap + long horizon, Cat 3 expensive + short horizon (effectively priced
# out), Cat 2 in between. Units: EUR/(power_unit*h), EUR/(power_unit*h), hours.
_CATEGORY_PARAMS: dict[int, tuple[float, float, float]] = {
    1: (1.0, 1.0, 336.0),  # fully flexible: near-free, 2-week horizon
    2: (20.0, 20.0, 48.0),  # partially flexible: moderate cost, 2-day horizon
    3: (1000.0, 1000.0, 2.0),  # not flexible: priced out, 2h horizon
}

# carrier_name -> {"pessimistic": category, "optimistic": category}, transcribed from
# input_data/DSM_parametrization/DSM_literature_review.md. Clinker has no row in that
# table (it predates the categorization plan); it is assigned Cat 3 in both variants,
# matching Golmohamadi2021's characterization of clinker production as an
# uninterruptible process with only low/very-low/medium flexibility potential.
_SECTOR_CATEGORIES: dict[str, dict[str, int]] = {
    "glass": {"pessimistic": 3, "optimistic": 3},
    "ceramic": {"pessimistic": 3, "optimistic": 2},
    "paper": {"pessimistic": 2, "optimistic": 1},
    "food": {"pessimistic": 3, "optimistic": 2},
    "methanol": {"pessimistic": 2, "optimistic": 1},
    "primary_steel": {"pessimistic": 3, "optimistic": 2},
    "secondary_steel": {"pessimistic": 2, "optimistic": 1},
    "olefin": {"pessimistic": 3, "optimistic": 2},
    "ammonia": {"pessimistic": 3, "optimistic": 2},
    "clinker": {"pessimistic": 3, "optimistic": 3},
}


def _category(carrier_name: str, variant: str) -> int:
    return _SECTOR_CATEGORIES[carrier_name][variant]


def _category_source(carrier_name: str, variant: str) -> SourceInformation:
    category = _category(carrier_name, variant)
    return SourceInformation(
        description=(
            f"{carrier_name} DSM, {variant} variant: Cat {category} per "
            "DSM_literature_review.md (Cat 1 = fully flexible, Cat 2 = partially "
            "flexible/short timescales, Cat 3 = not flexible at all)."
        ),
        metadata=_CATEGORY_METADATA,
    )


def _dsm_capacity_limit(element, carrier_name: str) -> Attribute:
    """Per-node capacity_limit = 2 × carrier demand (200% buffer)."""
    carrier = element.model.elements.get(carrier_name)
    attr = Attribute("capacity_limit", element=element)
    if carrier is None or carrier.demand.df is None:
        return attr
    raw = carrier.demand.df
    # df may be a Series (node index) or a DataFrame (node index, "demand" column)
    demand_series = raw if hasattr(raw, "iloc") and raw.ndim == 1 else raw.iloc[:, 0]
    limit_df = (demand_series * 2.0).rename("capacity_limit").to_frame()
    attr.set_data(
        default_value=np.inf,
        unit=element.power_unit,
        df=limit_df,
        source=SourceInformation(
            description=(
                f"capacity_limit = 2 × per-node {carrier_name} carrier demand "
                "(200% of demand — bounds DSM stock without blocking flexibility)."
            ),
            metadata=_DSM_METADATA,
        ),
    )
    return attr


class _IndustryDSMTechnology(StorageTechnology):
    """Shared logic for category-parametrized industry DSM technologies.

    Subclasses set `_carrier_name` (the reference carrier) and `_variant`
    ("optimistic" or "pessimistic"); cost and duration are looked up from
    `_SECTOR_CATEGORIES` / `_CATEGORY_PARAMS` accordingly.
    """

    _carrier_name: str
    _variant: str

    def __init__(self, model: Model, power_unit: str = "tonproduct/hour"):
        super().__init__(model=model, power_unit=power_unit)

    def _set_reference_carrier(self) -> Attribute:
        return Attribute(name="reference_carrier", default_value=[self._carrier_name], element=self)

    def _set_capacity_limit(self) -> Attribute:
        return _dsm_capacity_limit(self, self._carrier_name)

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
            default_value=capex,
            unit=f"Euro/({self.power_unit}*h)",
            source=_category_source(self._carrier_name, self._variant),
        )
        return attr

    def _set_opex_specific_variable(self) -> Attribute:
        _, opex_var, _ = _CATEGORY_PARAMS[_category(self._carrier_name, self._variant)]
        attr = Attribute("opex_specific_variable", element=self)
        attr.set_data(
            default_value=opex_var,
            unit=f"Euro/({self.power_unit}*h)",
            source=_category_source(self._carrier_name, self._variant),
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
# industry_heat sector products
# ---------------------------------------------------------------------------

class GlassDSMOptimistic(_IndustryDSMTechnology):
    name: str = "glass_DSM"
    _carrier_name = "glass"
    _variant = "optimistic"


class GlassDSMPessimistic(_IndustryDSMTechnology):
    name: str = "glass_DSM"
    _carrier_name = "glass"
    _variant = "pessimistic"


class CeramicDSMOptimistic(_IndustryDSMTechnology):
    name: str = "ceramic_DSM"
    _carrier_name = "ceramic"
    _variant = "optimistic"


class CeramicDSMPessimistic(_IndustryDSMTechnology):
    name: str = "ceramic_DSM"
    _carrier_name = "ceramic"
    _variant = "pessimistic"


class PaperDSMOptimistic(_IndustryDSMTechnology):
    name: str = "paper_DSM"
    _carrier_name = "paper"
    _variant = "optimistic"


class PaperDSMPessimistic(_IndustryDSMTechnology):
    name: str = "paper_DSM"
    _carrier_name = "paper"
    _variant = "pessimistic"


class FoodDSMOptimistic(_IndustryDSMTechnology):
    name: str = "food_DSM"
    _carrier_name = "food"
    _variant = "optimistic"


class FoodDSMPessimistic(_IndustryDSMTechnology):
    name: str = "food_DSM"
    _carrier_name = "food"
    _variant = "pessimistic"


# ---------------------------------------------------------------------------
# Existing Crystal Ball carriers (no zen_creator carrier class needed)
# ---------------------------------------------------------------------------

class AmmoniaDSMOptimistic(_IndustryDSMTechnology):
    name: str = "ammonia_DSM"
    _carrier_name = "ammonia"
    _variant = "optimistic"

    def __init__(self, model: Model, power_unit: str = "GW"):
        super().__init__(model=model, power_unit=power_unit)


class AmmoniaDSMPessimistic(_IndustryDSMTechnology):
    name: str = "ammonia_DSM"
    _carrier_name = "ammonia"
    _variant = "pessimistic"

    def __init__(self, model: Model, power_unit: str = "GW"):
        super().__init__(model=model, power_unit=power_unit)


class ClinkerDSMOptimistic(_IndustryDSMTechnology):
    name: str = "clinker_DSM"
    _carrier_name = "clinker"
    _variant = "optimistic"


class ClinkerDSMPessimistic(_IndustryDSMTechnology):
    name: str = "clinker_DSM"
    _carrier_name = "clinker"
    _variant = "pessimistic"


class MethanolDSMOptimistic(_IndustryDSMTechnology):
    name: str = "methanol_DSM"
    _carrier_name = "methanol"
    _variant = "optimistic"

    def __init__(self, model: Model, power_unit: str = "GW"):
        super().__init__(model=model, power_unit=power_unit)


class MethanolDSMPessimistic(_IndustryDSMTechnology):
    name: str = "methanol_DSM"
    _carrier_name = "methanol"
    _variant = "pessimistic"

    def __init__(self, model: Model, power_unit: str = "GW"):
        super().__init__(model=model, power_unit=power_unit)


class PrimarysteelDSMOptimistic(_IndustryDSMTechnology):
    name: str = "primary_steel_DSM"
    _carrier_name = "primary_steel"
    _variant = "optimistic"


class PrimarysteelDSMPessimistic(_IndustryDSMTechnology):
    name: str = "primary_steel_DSM"
    _carrier_name = "primary_steel"
    _variant = "pessimistic"


class SecondarysteelDSMOptimistic(_IndustryDSMTechnology):
    name: str = "secondary_steel_DSM"
    _carrier_name = "secondary_steel"
    _variant = "optimistic"


class SecondarysteelDSMPessimistic(_IndustryDSMTechnology):
    name: str = "secondary_steel_DSM"
    _carrier_name = "secondary_steel"
    _variant = "pessimistic"


class OlefinDSMOptimistic(_IndustryDSMTechnology):
    name: str = "olefin_DSM"
    _carrier_name = "olefin"
    _variant = "optimistic"


class OlefinDSMPessimistic(_IndustryDSMTechnology):
    name: str = "olefin_DSM"
    _carrier_name = "olefin"
    _variant = "pessimistic"
