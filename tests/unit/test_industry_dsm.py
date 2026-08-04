"""Unit tests for industry DSM (product storage) technologies.

See ASSUMPTIONS.md ("Product DSM storage efficiency") for why efficiency is not 1.0.
"""

from __future__ import annotations

import pytest

from zen_creator.elements.storage_technologies.industry_DSM import (
    AmmoniaDSMPessimistic,
    GlassDSMOptimistic,
    MethanolDSMOptimistic,
)
from zen_creator.model import Model


@pytest.mark.parametrize("technology_cls", [GlassDSMOptimistic, AmmoniaDSMPessimistic])
def test_product_dsm_efficiency_is_not_lossless(technology_cls, model: Model):
    """Charge/discharge efficiency must be < 1.0 so simultaneous charge+discharge
    (a free, physically meaningless cycle under lossless efficiency) is costly."""
    technology = technology_cls(model=model)
    technology.build()

    assert technology.efficiency_charge.default_value == pytest.approx(0.999)
    assert technology.efficiency_discharge.default_value == pytest.approx(0.999)


def test_mass_based_dsm_cost_is_unconverted(model: Model):
    """glass_DSM has power_unit='tonproduct/hour' (mass-based) — the category's
    placeholder value (Cat 3 = 1000) must be used as-is, in Euro/tonproduct."""
    technology = GlassDSMOptimistic(model=model)
    technology.build()

    assert technology.capex_specific_storage_energy.default_value == pytest.approx(1000.0)
    assert technology.opex_specific_variable.default_value == pytest.approx(1000.0)
    assert technology.capex_specific_storage_energy.unit == "Euro/(tonproduct/hour*h)"


def test_ammonia_dsm_cost_is_lhv_converted(model: Model):
    """ammonia_DSM has power_unit='GW' (energy-based) — the category's placeholder
    value (Cat 3, pessimistic = 1000 Euro/tonproduct) must be divided by ammonia's
    LHV (18.6 GJ/t = 18.6/3600 GWh/t) to get an equivalent Euro/GWh value."""
    technology = AmmoniaDSMPessimistic(model=model)
    technology.build()

    expected = 1000.0 / (18.6 / 3600.0)
    assert technology.capex_specific_storage_energy.default_value == pytest.approx(expected)
    assert technology.opex_specific_variable.default_value == pytest.approx(expected)
    assert technology.capex_specific_storage_energy.unit == "Euro/(GW*h)"


def test_methanol_dsm_cost_is_lhv_converted(model: Model):
    """methanol_DSM, optimistic variant is Cat 1 (value = 1 Euro/tonproduct);
    converted via methanol's LHV (19.9 GJ/t = 19.9/3600 GWh/t)."""
    technology = MethanolDSMOptimistic(model=model)
    technology.build()

    expected = 1.0 / (19.9 / 3600.0)
    assert technology.capex_specific_storage_energy.default_value == pytest.approx(expected)
    assert technology.opex_specific_variable.default_value == pytest.approx(expected)


def test_energy_to_power_ratio_is_not_lhv_converted(model: Model):
    """energy_to_power_ratio_max is a duration (hours) and must stay unconverted
    for energy-based DSM techs too — it is dimensionally identical regardless of
    whether power_unit is tonproduct/hour or GW."""
    ammonia = AmmoniaDSMPessimistic(model=model)
    ammonia.build()
    glass = GlassDSMOptimistic(model=model)
    glass.build()

    assert ammonia.energy_to_power_ratio_max.default_value == pytest.approx(2.0)
    assert glass.energy_to_power_ratio_max.default_value == pytest.approx(2.0)


if __name__ == "__main__":
    pytest.main([__file__])
