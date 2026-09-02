"""Unit tests for industry_production.py: glass/ceramic/paper/food production
technologies.

None of these 4 Element subclasses had any test coverage before this (see
cleanup plan, Phase 2 item 9).
"""

from __future__ import annotations

import pytest

from zen_creator.elements.conversion_technologies.industry_production import (
    CeramicProduction,
    FoodProduction,
    GlassProduction,
    PaperProduction,
)
from zen_creator.model import Model

PRODUCTION_CLASSES = [GlassProduction, CeramicProduction, PaperProduction, FoodProduction]


@pytest.mark.parametrize(
    "technology_cls,carrier",
    [(GlassProduction, "glass"), (CeramicProduction, "ceramic"), (PaperProduction, "paper"), (FoodProduction, "food")],
)
def test_build_succeeds_and_carriers_match_product(technology_cls, carrier, model: Model):
    technology = technology_cls(model=model)
    technology.build()

    assert technology.reference_carrier.default_value == [carrier]
    assert technology.output_carrier.default_value == [carrier]
    # input_carrier is the tech's fuel/heat mix (e.g. natural_gas, biomass,
    # heat_industry_*, electricity) -- it never includes the product itself
    assert carrier not in technology.input_carrier.default_value
    assert technology.lifetime.default_value > 0
    assert technology.capex_specific_conversion.default_value > 0


@pytest.mark.parametrize("technology_cls", PRODUCTION_CLASSES)
def test_capacity_existing_is_non_negative_for_every_node(technology_cls, model: Model):
    from zen_creator.datasets.datasets._industry_heat_utils import MODEL_NODES

    technology = technology_cls(model=model)
    technology.build()

    attr = technology.capacity_existing
    assert attr.df is not None
    # capacity_existing.df is a Series for some sources (get_ceramic_capacity_from_fec)
    # and a single-column DataFrame for others (get_capacity_existing) -- normalize.
    values = attr.df if attr.df.ndim == 1 else attr.df["capacity_existing"]
    assert (values >= 0).all()
    nodes_present = set(attr.df.index.get_level_values("node"))
    assert nodes_present == set(MODEL_NODES)


@pytest.mark.parametrize("technology_cls", PRODUCTION_CLASSES)
def test_conversion_factor_includes_active_heat_temperature_bands_only(technology_cls, model: Model):
    """input_carrier/conversion_factor must only reference heat_industry_* bands
    with a strictly positive share -- see get_production_tech_dict's active_levels
    filtering."""
    technology = technology_cls(model=model)
    technology.build()

    cf_carriers = {next(iter(e)) for e in technology.conversion_factor.default_value}
    heat_carriers_in_cf = {c for c in cf_carriers if c.startswith("heat_industry")}
    heat_carriers_in_input = {c for c in technology.input_carrier.default_value if c.startswith("heat_industry")}
    assert heat_carriers_in_cf == heat_carriers_in_input


if __name__ == "__main__":
    pytest.main([__file__])
