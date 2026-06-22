"""Industry heat carrier Element subclasses.

Product carriers: Glass, Ceramic, Paper, Food
Energy carriers: HeatIndustry0100, HeatIndustry100200

Attributes are set from the exact same templates and Excel overrides that
compute_params.py uses, ensuring identical output.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

import pandas as pd

from zen_creator.elements.carriers.carrier import Carrier
from zen_creator.utils.attribute import Attribute

from zen_creator.elements.industry_heat._apply import apply_attrs_dict
from zen_creator.elements.industry_heat._params import (
    BAT_PAPER_CSV,
    FEC_YEAR,
    carrier_overrides,
)
from zen_creator.industry_heat_eu.capacity_and_demand import (
    food_demand_df,
    industry_demand_df,
)
from zen_creator.industry_heat_eu.excel_io import apply_excel_overrides
from zen_creator.industry_heat_eu.json_templates import (
    ENERGY_CARRIER_TEMPLATE,
    PRODUCT_CARRIER_TEMPLATE,
)


def _build_carrier_dict(carrier_name: str, template: dict) -> dict:
    """Build the final carrier attributes dict, matching compute_params.write_carrier."""
    data = copy.deepcopy(template)
    overrides = carrier_overrides(carrier_name)
    return apply_excel_overrides(data, overrides)


class Glass(Carrier):
    name = "glass"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")
        apply_attrs_dict(self, _build_carrier_dict("glass", PRODUCT_CARRIER_TEMPLATE))

    def _set_demand(self) -> Attribute:
        attr = Attribute("demand", default_value=0.0, unit="tonproduct/hour", element=self)
        df = industry_demand_df("glass", FEC_YEAR)
        attr.df = df.set_index("node")["demand"]
        return attr


class Ceramic(Carrier):
    name = "ceramic"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")
        apply_attrs_dict(self, _build_carrier_dict("ceramic", PRODUCT_CARRIER_TEMPLATE))

    def _set_demand(self) -> Attribute:
        attr = Attribute("demand", default_value=0.0, unit="tonproduct/hour", element=self)
        df = industry_demand_df("ceramic", FEC_YEAR)
        attr.df = df.set_index("node")["demand"]
        return attr


class Paper(Carrier):
    name = "paper"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")
        apply_attrs_dict(self, _build_carrier_dict("paper", PRODUCT_CARRIER_TEMPLATE))

    def _set_demand(self) -> Attribute:
        attr = Attribute("demand", default_value=0.0, unit="tonproduct/hour", element=self)
        df = industry_demand_df("paper", FEC_YEAR)
        bat = pd.read_csv(BAT_PAPER_CSV)
        bat_nodes = {"Switzerland": "CH", "Norway": "NO", "United Kingdom": "UK"}
        bat = bat[bat["country"].isin(bat_nodes)]
        for _, row in bat.iterrows():
            node = bat_nodes[row["country"]]
            df.loc[df["node"] == node, "demand"] = row["consumption_1000t_2008"] * 1000 / 8760
        attr.df = df.set_index("node")["demand"]
        return attr


class Food(Carrier):
    name = "food"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")
        apply_attrs_dict(self, _build_carrier_dict("food", PRODUCT_CARRIER_TEMPLATE))

    def _set_demand(self) -> Attribute:
        attr = Attribute("demand", default_value=0.0, unit="tonproduct/hour", element=self)
        df = food_demand_df(FEC_YEAR)
        attr.df = df.set_index("node")["demand"]
        return attr


class HeatIndustry0100(Carrier):
    name = "heat_industry_0_100"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_carrier_dict("heat_industry_0_100", ENERGY_CARRIER_TEMPLATE))


class HeatIndustry100200(Carrier):
    name = "heat_industry_100_200"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="GW")
        apply_attrs_dict(self, _build_carrier_dict("heat_industry_100_200", ENERGY_CARRIER_TEMPLATE))
