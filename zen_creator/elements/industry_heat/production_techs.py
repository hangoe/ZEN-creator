"""Industry production technology Element subclasses.

Attributes are set from the exact same functions that compute_params.py uses
(build_conversion_tech + apply_excel_overrides), ensuring identical output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

import pandas as pd

from zen_creator.elements.conversion_technologies.conversion_technology import (
    ConversionTechnology,
)
from zen_creator.utils.attribute import Attribute

from zen_creator.elements.industry_heat._apply import apply_attrs_dict
from zen_creator.elements.industry_heat._params import (
    BAT_PAPER_CSV,
    CAPACITY_YEAR,
    FEC_YEAR,
    fuel_mix_shares,
    process_tech_overrides,
    sector_params,
)
from zen_creator.industry_heat_eu.capacity_and_demand import (
    capacity_existing_df,
    food_capacity_existing_df,
)
from zen_creator.industry_heat_eu.excel_io import apply_excel_overrides
from zen_creator.industry_heat_eu.json_templates import build_conversion_tech


def _index_capacity_df(df: pd.DataFrame) -> pd.DataFrame:
    """Set the proper index on a capacity_existing DataFrame."""
    return df.set_index(["node", "year_construction"])


def _build_production_tech_dict(sector: str, product: str, tech_name: str) -> dict:
    """Build the final attributes dict, matching compute_params.write_production_tech.

    Cost parameters (capex, opex, lifetime, carbon_intensity) are NOT applied
    here — they come from process_parametrization.xlsx via apply_excel_overrides,
    which is the source of truth (compute_params.py writes cost values into the
    Excel before reading them back).
    """
    params = sector_params()[sector]
    shares = fuel_mix_shares()[sector]

    opex_var = {"glass": 15.0, "ceramic": 10.0, "paper": 0.0, "food": 0.0}

    data = build_conversion_tech(
        product=product,
        fuel_shares=shares,
        params=params,
        opex_specific_variable=opex_var.get(sector, 0.0),
    )

    conversion_factor_map = {
        **{f"conversion_factor:{carrier}": carrier for carrier in shares},
        "conversion_factor:heat_industry_0_100": "heat_industry_0_100",
        "conversion_factor:heat_industry_100_200": "heat_industry_100_200",
        "conversion_factor:electricity": "electricity",
    }

    overrides = process_tech_overrides(tech_name)
    return apply_excel_overrides(data, overrides, conversion_factor_map=conversion_factor_map)


class GlassProduction(ConversionTechnology):
    name = "glass_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")
        apply_attrs_dict(self, _build_production_tech_dict("glass", "glass", self.name))

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["glass"], element=self)

    def _set_input_carrier(self) -> Attribute:
        shares = fuel_mix_shares()["glass"]
        return Attribute("input_carrier", default_value=[*shares.keys(), "heat_industry_0_100", "heat_industry_100_200", "electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["glass"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_production_tech_dict("glass", "glass", self.name)
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        attr = Attribute("capacity_existing", default_value=0.0, unit="tonproduct/hour", element=self)
        df = capacity_existing_df("glass", FEC_YEAR, year_construction=CAPACITY_YEAR)
        attr.df = _index_capacity_df(df)
        return attr


class CeramicProduction(ConversionTechnology):
    name = "ceramic_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")
        apply_attrs_dict(self, _build_production_tech_dict("ceramic", "ceramic", self.name))

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["ceramic"], element=self)

    def _set_input_carrier(self) -> Attribute:
        shares = fuel_mix_shares()["ceramic"]
        return Attribute("input_carrier", default_value=[*shares.keys(), "heat_industry_0_100", "heat_industry_100_200", "electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["ceramic"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_production_tech_dict("ceramic", "ceramic", self.name)
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        attr = Attribute("capacity_existing", default_value=0.0, unit="tonproduct/hour", element=self)
        df = capacity_existing_df("ceramic", FEC_YEAR, year_construction=CAPACITY_YEAR)
        attr.df = _index_capacity_df(df)
        return attr


class PaperProduction(ConversionTechnology):
    name = "paper_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")
        apply_attrs_dict(self, _build_production_tech_dict("paper", "paper", self.name))

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["paper"], element=self)

    def _set_input_carrier(self) -> Attribute:
        shares = fuel_mix_shares()["paper"]
        return Attribute("input_carrier", default_value=[*shares.keys(), "heat_industry_0_100", "heat_industry_100_200", "electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["paper"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_production_tech_dict("paper", "paper", self.name)
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        attr = Attribute("capacity_existing", default_value=0.0, unit="tonproduct/hour", element=self)
        df = capacity_existing_df("paper", FEC_YEAR, year_construction=CAPACITY_YEAR)
        bat = pd.read_csv(BAT_PAPER_CSV)
        bat_nodes = {"Switzerland": "CH", "Norway": "NO", "United Kingdom": "UK"}
        bat = bat[bat["country"].isin(bat_nodes)]
        for _, row in bat.iterrows():
            node = bat_nodes[row["country"]]
            df.loc[df["node"] == node, "capacity_existing"] = row["consumption_1000t_2008"] * 1000 / 8000
        attr.df = _index_capacity_df(df)
        return attr


class FoodProduction(ConversionTechnology):
    name = "food_production"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="tonproduct/hour")
        apply_attrs_dict(self, _build_production_tech_dict("food", "food", self.name))

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["food"], element=self)

    def _set_input_carrier(self) -> Attribute:
        shares = fuel_mix_shares()["food"]
        return Attribute("input_carrier", default_value=[*shares.keys(), "heat_industry_0_100", "heat_industry_100_200", "electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["food"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        data = _build_production_tech_dict("food", "food", self.name)
        return Attribute("conversion_factor", default_value=data["conversion_factor"], element=self)

    def _set_lifetime(self) -> Attribute:
        return self.lifetime

    def _set_capacity_existing(self) -> Attribute:
        attr = Attribute("capacity_existing", default_value=0.0, unit="tonproduct/hour", element=self)
        df = food_capacity_existing_df(FEC_YEAR, year_construction=CAPACITY_YEAR)
        attr.df = _index_capacity_df(df)
        return attr
