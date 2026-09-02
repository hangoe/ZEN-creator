"""Unit tests for industry_ccs.py: ceramic/glass post-combustion carbon capture
retrofits.

Neither CeramicPostComb nor GlassPostComb -- nor RetrofittingTechnology's
contract in general -- had any test coverage before this (see cleanup plan,
Phase 2 item 9).
"""

from __future__ import annotations

import pytest

from zen_creator.elements.conversion_technologies.industry_ccs import (
    CeramicPostComb,
    GlassPostComb,
)
from zen_creator.model import Model

RETROFIT_CLASSES = [CeramicPostComb, GlassPostComb]


@pytest.mark.parametrize("technology_cls", RETROFIT_CLASSES)
def test_build_succeeds_and_carbon_flows_are_wired(technology_cls, model: Model):
    technology = technology_cls(model=model)
    technology.build()

    assert technology.reference_carrier.default_value == ["carbon"]
    assert technology.retrofit_reference_carrier.default_value == ["carbon"]
    assert set(technology.output_carrier.default_value) == {"carbon", "district_heat"}
    assert technology.lifetime.default_value > 0


@pytest.mark.parametrize("technology_cls", RETROFIT_CLASSES)
def test_base_technology_own_process_carbon_intensity_is_zero(technology_cls, model: Model):
    """The retrofit's own carbon_intensity_technology is 0 -- process CO2 is
    tracked via retrofit_flow_coupling_factor against the base production tech
    instead (see method docstring / ASSUMPTIONS.md)."""
    technology = technology_cls(model=model)
    technology.build()
    assert technology.carbon_intensity_technology.default_value == pytest.approx(0.0)


@pytest.mark.parametrize(
    "technology_cls,sector", [(CeramicPostComb, "ceramic"), (GlassPostComb, "glass")]
)
def test_retrofit_flow_coupling_factor_points_at_correct_base_technology(technology_cls, sector, model: Model):
    technology = technology_cls(model=model)
    technology.build()
    assert technology.retrofit_flow_coupling_factor.base_technology == f"{sector}_production"
    assert technology.retrofit_flow_coupling_factor.default_value > 0


if __name__ == "__main__":
    pytest.main([__file__])
