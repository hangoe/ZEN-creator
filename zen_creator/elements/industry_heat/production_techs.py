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
    HEAT_CARRIER_NAMES,
    HEAT_TEMP_LEVELS,
    fuel_mix_shares,
    process_tech_overrides,
    sector_heat_cfs,
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


def _active_heat_carriers(sector: str) -> list[str]:
    """Return only heat carriers with non-zero conversion factor for this sector."""
    cfs = sector_heat_cfs()[sector]
    return [HEAT_CARRIER_NAMES[l] for l in HEAT_TEMP_LEVELS if cfs[l] > 0]


def _build_production_tech_dict(sector: str, product: str, tech_name: str) -> dict:
    """Build the final attributes dict with 3 temperature levels.

    Uses build_conversion_tech for the base structure, then replaces the
    2-level heat carriers with 3 levels (0-100, 100-150, 150-200) using
    Wolf2017-based splits.
    """
    params = sector_params()[sector]
    shares = fuel_mix_shares()[sector]
    cfs = sector_heat_cfs()[sector]

    opex_var = {"glass": 15.0, "ceramic": 10.0, "paper": 0.0, "food": 0.0}

    data = build_conversion_tech(
        product=product,
        fuel_shares=shares,
        params=params,
        opex_specific_variable=opex_var.get(sector, 0.0),
    )

    # Only include heat carriers with non-zero conversion factor
    active_heat_levels = [l for l in HEAT_TEMP_LEVELS if cfs[l] > 0]
    active_heat_carriers = [HEAT_CARRIER_NAMES[l] for l in active_heat_levels]
    data["input_carrier"]["default_value"] = [*shares.keys(), *active_heat_carriers, "electricity"]

    new_cf = [entry for entry in data["conversion_factor"]
              if not any(k.startswith("heat_industry") for k in entry)]
    for level in active_heat_levels:
        carrier = HEAT_CARRIER_NAMES[level]
        new_cf.append({carrier: {
            "default_value": round(cfs[level], 12),
            "unit": "GW/(tonproduct/hour)",
        }})
    data["conversion_factor"] = new_cf

    conversion_factor_map = {
        **{f"conversion_factor:{carrier}": carrier for carrier in shares},
        **{f"conversion_factor:{HEAT_CARRIER_NAMES[l]}": HEAT_CARRIER_NAMES[l] for l in HEAT_TEMP_LEVELS},
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
        return Attribute("input_carrier", default_value=[*shares.keys(), *_active_heat_carriers("glass"), "electricity"], element=self)

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
        return Attribute("input_carrier", default_value=[*shares.keys(), *_active_heat_carriers("ceramic"), "electricity"], element=self)

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
        return Attribute("input_carrier", default_value=[*shares.keys(), *_active_heat_carriers("paper"), "electricity"], element=self)

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
        return Attribute("input_carrier", default_value=[*shares.keys(), *_active_heat_carriers("food"), "electricity"], element=self)

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
