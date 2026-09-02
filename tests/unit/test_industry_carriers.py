"""Unit tests for industry_carriers.py: glass/ceramic/paper/food product
carriers and the heat_industry_*/fuel_to_kiln energy carriers.

None of these 8 Element subclasses -- nor the _add_carrier_setters/
_make_carrier_setter metaprogramming helpers that wire up their shared
attributes -- had any test coverage before this (see cleanup plan, Phase 2
item 9).
"""

from __future__ import annotations

import pytest

from zen_creator.elements.carriers.industry_carriers import (
    Ceramic,
    Food,
    FuelToKiln,
    Glass,
    HeatIndustry0100,
    HeatIndustry100150,
    HeatIndustry150200,
    Paper,
    _CARRIER_ATTRS,
)
from zen_creator.model import Model

PRODUCT_CARRIERS = [Glass, Ceramic, Paper, Food]
ENERGY_CARRIERS = [HeatIndustry0100, HeatIndustry100150, HeatIndustry150200, FuelToKiln]
ALL_CARRIERS = PRODUCT_CARRIERS + ENERGY_CARRIERS


@pytest.mark.parametrize("carrier_cls", ALL_CARRIERS)
def test_build_succeeds_and_shared_attrs_are_set(carrier_cls, model: Model):
    """Every carrier must build, and every attribute in its own
    _attribute_names (the list build() actually iterates) must resolve to a
    real Attribute."""
    carrier = carrier_cls(model=model)
    carrier.build()

    for attr_name in carrier._attribute_names:
        attr = getattr(carrier, attr_name)
        assert attr.name == attr_name


def test_max_shed_demand_setter_is_dead_code(model: Model):
    """KNOWN BUG (found while writing this test, not yet fixed -- see cleanup
    plan follow-up): _CARRIER_ATTRS includes "max_shed_demand" and
    _add_carrier_setters wires up a _set_max_shed_demand method for every
    industry carrier, but the base Carrier class (carrier.py) never declares
    "max_shed_demand" as a real attribute (no property, not in
    _attribute_names) -- so Element.build(), which only calls _set_{name}()
    for names in _attribute_names, never invokes it. Any max_shed_demand
    values configured in industry_carriers.xlsx are silently discarded for
    every industry carrier today. This test pins the current (buggy) behavior
    so a silent fix doesn't go unnoticed -- flip/remove it once
    max_shed_demand is wired into Carrier._subclass_attribute_names."""
    assert "max_shed_demand" in _CARRIER_ATTRS
    glass = Glass(model=model)
    assert "max_shed_demand" not in glass._attribute_names
    assert hasattr(glass, "_set_max_shed_demand")
    assert not hasattr(glass, "max_shed_demand")


@pytest.mark.parametrize("carrier_cls", PRODUCT_CARRIERS)
def test_product_carriers_use_tonproduct_power_unit(carrier_cls, model: Model):
    carrier = carrier_cls(model=model)
    carrier.build()
    assert carrier.power_unit == "tonproduct/hour"


@pytest.mark.parametrize("carrier_cls", ENERGY_CARRIERS)
def test_energy_carriers_use_gw_power_unit(carrier_cls, model: Model):
    carrier = carrier_cls(model=model)
    carrier.build()
    assert carrier.power_unit == "GW"


@pytest.mark.parametrize("carrier_cls", PRODUCT_CARRIERS)
def test_product_carrier_demand_is_non_negative_for_every_node(carrier_cls, model: Model):
    from zen_creator.datasets.datasets._industry_heat_utils import MODEL_NODES

    carrier = carrier_cls(model=model)
    carrier.build()

    demand = carrier.demand.df
    assert demand is not None
    assert (demand >= 0).all()
    assert set(demand.index) == set(MODEL_NODES)


def test_heat_industry_100_150_and_150_200_share_the_same_excel_column():
    """industry_carrier_data.get_carrier_dict redirects both
    heat_industry_100_150 and heat_industry_150_200 to the same
    "heat_industry_100_200" Excel column -- confirm they get identical
    non-shared-setter attribute values as a result."""
    from zen_creator.datasets.datasets.industry_carrier_data import IndustryCarrierDataset

    dataset = IndustryCarrierDataset()
    dict_100_150 = dataset.get_carrier_dict("heat_industry_100_150")
    dict_150_200 = dataset.get_carrier_dict("heat_industry_150_200")
    assert dict_100_150 == dict_150_200


if __name__ == "__main__":
    pytest.main([__file__])
