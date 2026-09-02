"""Unit tests for zen_creator.elements.storage_technologies.industry_DSM
(the industry DSM/product storage *technologies* -- not the same-named
zen_creator.sectors.industry_dsm sector-grouping module; see test_sectors.py
for that).

See ASSUMPTIONS.md ("Product DSM storage efficiency") for why efficiency is not 1.0.
"""

from __future__ import annotations

import pandas as pd
import pytest

from zen_creator.elements.storage_technologies.industry_DSM import (
    AmmoniaDSMOptimistic,
    AmmoniaDSMPessimistic,
    CeramicDSMOptimistic,
    CeramicDSMPessimistic,
    ClinkerDSMOptimistic,
    ClinkerDSMPessimistic,
    FoodDSMOptimistic,
    FoodDSMPessimistic,
    GlassDSMOptimistic,
    GlassDSMPessimistic,
    MethanolDSMOptimistic,
    MethanolDSMPessimistic,
    OlefinDSMOptimistic,
    OlefinDSMPessimistic,
    PaperDSMOptimistic,
    PaperDSMPessimistic,
    PrimarysteelDSMOptimistic,
    PrimarysteelDSMPessimistic,
    SecondarysteelDSMOptimistic,
    SecondarysteelDSMPessimistic,
    _SECTOR_CATEGORIES,
)
from zen_creator.model import Model

ALL_DSM_CLASSES = [
    GlassDSMOptimistic, GlassDSMPessimistic,
    CeramicDSMOptimistic, CeramicDSMPessimistic,
    PaperDSMOptimistic, PaperDSMPessimistic,
    FoodDSMOptimistic, FoodDSMPessimistic,
    AmmoniaDSMOptimistic, AmmoniaDSMPessimistic,
    ClinkerDSMOptimistic, ClinkerDSMPessimistic,
    MethanolDSMOptimistic, MethanolDSMPessimistic,
    PrimarysteelDSMOptimistic, PrimarysteelDSMPessimistic,
    SecondarysteelDSMOptimistic, SecondarysteelDSMPessimistic,
    OlefinDSMOptimistic, OlefinDSMPessimistic,
]


@pytest.mark.parametrize("technology_cls", ALL_DSM_CLASSES)
def test_build_succeeds_and_matches_declared_category(technology_cls, model: Model):
    """Every DSM technology class must build successfully and its
    energy_to_power_ratio_max must match the _CATEGORY_PARAMS entry for its
    declared (_carrier_name, _variant) category -- catches a dropped/mismatched
    entry in _SECTOR_CATEGORIES for any of the 20 classes."""
    from zen_creator.elements.storage_technologies.industry_DSM import _CATEGORY_PARAMS

    technology = technology_cls(model=model)
    technology.build()

    category = _SECTOR_CATEGORIES[technology._carrier_name][technology._variant]
    _, _, expected_e2p_max = _CATEGORY_PARAMS[category]
    assert technology.energy_to_power_ratio_max.default_value == pytest.approx(expected_e2p_max)
    assert technology.reference_carrier.default_value == [technology._carrier_name]


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


def test_dsm_capacity_limit_uses_real_carrier_demand(model: Model):
    """The non-early-return branch of _dsm_capacity_limit: when the carrier is
    registered on model.elements with a populated demand, capacity_limit must
    equal exactly 1x that per-node demand (see _dsm_capacity_limit docstring)."""
    from zen_creator.elements.carriers.industry_carriers import Glass

    glass = Glass(model=model)
    glass.build()
    model.elements["glass"] = glass

    technology = GlassDSMOptimistic(model=model)
    technology.build()

    assert technology.capacity_limit.df is not None
    limit = technology.capacity_limit.df["capacity_limit"]
    demand = glass.demand.df
    pd.testing.assert_series_equal(
        limit.sort_index(), demand.rename("capacity_limit").sort_index(), check_dtype=False
    )


def test_dsm_capacity_limit_early_returns_without_registered_carrier(model: Model):
    """When the carrier isn't registered on model.elements, capacity_limit must
    fall back to an unset Attribute (no default_value, no df) -- the early-return
    branch every other existing test in this file exercises."""
    technology = GlassDSMOptimistic(model=model)
    technology.build()
    assert technology.capacity_limit.df is None
    assert technology.capacity_limit.default_value is None


if __name__ == "__main__":
    pytest.main([__file__])
