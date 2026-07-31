"""Unit tests for the temperature conversion cascade's diffusion rate.

See ASSUMPTIONS.md ("Temperature conversion cascade diffusion rate") for the
back-solve methodology this locks in.
"""

from __future__ import annotations

import pytest

from zen_creator.elements.conversion_technologies.industry_heat_supply import (
    MODEL_HORIZON_YEARS,
    UPSTREAM_MAX_DIFFUSION_RATE,
    HeatIndustryTempConversion100,
    HeatIndustryTempConversion150,
)
from zen_creator.elements.energy_systems.energy_system import GenericEnergySystem
from zen_creator.model import Model


@pytest.fixture
def model_with_energy_system(model: Model) -> Model:
    model.energy_system = GenericEnergySystem(model)
    model.energy_system.build()
    return model


def test_temp_conversion_150_diffusion_rate(model_with_energy_system: Model):
    """Cascade level 1: back-solved from the upstream boiler fleet's 0.29 rate."""
    technology = HeatIndustryTempConversion150(model=model_with_energy_system)
    technology.build()

    market_share_unbounded = model_with_energy_system.energy_system.market_share_unbounded.default_value
    expected = (1 + UPSTREAM_MAX_DIFFUSION_RATE) / market_share_unbounded ** (1 / MODEL_HORIZON_YEARS) - 1

    assert technology.max_diffusion_rate.default_value == pytest.approx(expected)
    assert technology.max_diffusion_rate.default_value == pytest.approx(0.483431, abs=1e-6)
    assert technology.max_diffusion_rate.unit == "1"


def test_temp_conversion_100_diffusion_rate(model_with_energy_system: Model):
    """Cascade level 2: nested inside temp_conversion_150's own derived trajectory."""
    technology = HeatIndustryTempConversion100(model=model_with_energy_system)
    technology.build()

    market_share_unbounded = model_with_energy_system.energy_system.market_share_unbounded.default_value
    expected = (1 + UPSTREAM_MAX_DIFFUSION_RATE) / market_share_unbounded ** (2 / MODEL_HORIZON_YEARS) - 1

    assert technology.max_diffusion_rate.default_value == pytest.approx(expected)
    assert technology.max_diffusion_rate.default_value == pytest.approx(0.705865, abs=1e-6)


def test_temp_conversion_100_rate_exceeds_150_rate(model_with_energy_system: Model):
    """Each cascade level starts from a smaller relative base, so needs a higher rate."""
    t150 = HeatIndustryTempConversion150(model=model_with_energy_system)
    t150.build()
    t100 = HeatIndustryTempConversion100(model=model_with_energy_system)
    t100.build()

    assert t100.max_diffusion_rate.default_value > t150.max_diffusion_rate.default_value > UPSTREAM_MAX_DIFFUSION_RATE


if __name__ == "__main__":
    pytest.main([__file__])
