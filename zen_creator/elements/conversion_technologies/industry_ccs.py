"""Post-combustion carbon-capture retrofit Element subclasses for the
industry_heat sector (ceramic_post_comb, glass_post_comb).

Both retrofit ceramic_production/glass_production the same way cement's
(externally-defined) cement_post_comb retrofits cement_kiln — see
zen_creator/datasets/datasets/post_comb_cc.py and ASSUMPTIONS.md ("Ceramic
and glass post-combustion carbon capture") for the full derivation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.post_comb_cc import PostCombCCDataset
from zen_creator.elements.conversion_technologies.retrofitting_technology import (
    RetrofittingTechnology,
)
from zen_creator.utils.attribute import Attribute


class CeramicPostComb(RetrofittingTechnology):
    name = "ceramic_post_comb"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="kilotCO2eq/hour")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["carbon"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["natural_gas", "hard_coal", "electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["carbon", "district_heat"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return PostCombCCDataset().get_conversion_factor(self, "ceramic")

    def _set_lifetime(self) -> Attribute:
        return PostCombCCDataset().get_lifetime(self, "ceramic")

    def _set_capex_specific_conversion(self) -> Attribute:
        return PostCombCCDataset().get_capex_specific_conversion(self, "ceramic")

    def _set_opex_specific_fixed(self) -> Attribute:
        return PostCombCCDataset().get_opex_specific_fixed(self, "ceramic")

    def _set_opex_specific_variable(self) -> Attribute:
        return PostCombCCDataset().get_opex_specific_variable(self, "ceramic")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return Attribute("carbon_intensity_technology", default_value=0.0, unit="ton/tCO2eq", element=self)

    def _set_max_diffusion_rate(self) -> Attribute:
        return PostCombCCDataset().get_max_diffusion_rate(self, "ceramic")

    def _set_capacity_addition_unbounded(self) -> Attribute:
        return PostCombCCDataset().get_capacity_addition_unbounded(self, "ceramic")

    def _set_retrofit_flow_coupling_factor(self) -> Attribute:
        return PostCombCCDataset().get_retrofit_flow_coupling_factor(self, "ceramic")

    def _set_retrofit_reference_carrier(self) -> Attribute:
        return Attribute("retrofit_reference_carrier", default_value=["carbon"], element=self)


class GlassPostComb(RetrofittingTechnology):
    name = "glass_post_comb"

    def __init__(self, model: Model):
        super().__init__(model=model, power_unit="kilotCO2eq/hour")

    def _set_reference_carrier(self) -> Attribute:
        return Attribute("reference_carrier", default_value=["carbon"], element=self)

    def _set_input_carrier(self) -> Attribute:
        return Attribute("input_carrier", default_value=["natural_gas", "hard_coal", "electricity"], element=self)

    def _set_output_carrier(self) -> Attribute:
        return Attribute("output_carrier", default_value=["carbon", "district_heat"], element=self)

    def _set_conversion_factor(self) -> Attribute:
        return PostCombCCDataset().get_conversion_factor(self, "glass")

    def _set_lifetime(self) -> Attribute:
        return PostCombCCDataset().get_lifetime(self, "glass")

    def _set_capex_specific_conversion(self) -> Attribute:
        return PostCombCCDataset().get_capex_specific_conversion(self, "glass")

    def _set_opex_specific_fixed(self) -> Attribute:
        return PostCombCCDataset().get_opex_specific_fixed(self, "glass")

    def _set_opex_specific_variable(self) -> Attribute:
        return PostCombCCDataset().get_opex_specific_variable(self, "glass")

    def _set_carbon_intensity_technology(self) -> Attribute:
        return Attribute("carbon_intensity_technology", default_value=0.0, unit="ton/tCO2eq", element=self)

    def _set_max_diffusion_rate(self) -> Attribute:
        return PostCombCCDataset().get_max_diffusion_rate(self, "glass")

    def _set_capacity_addition_unbounded(self) -> Attribute:
        return PostCombCCDataset().get_capacity_addition_unbounded(self, "glass")

    def _set_retrofit_flow_coupling_factor(self) -> Attribute:
        return PostCombCCDataset().get_retrofit_flow_coupling_factor(self, "glass")

    def _set_retrofit_reference_carrier(self) -> Attribute:
        return Attribute("retrofit_reference_carrier", default_value=["carbon"], element=self)
