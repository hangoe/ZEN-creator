"""Unit tests for Mannhardt2026CarbonBudgetDataset."""

from __future__ import annotations

import pandas as pd
import pytest

from zen_creator.datasets.datasets.carbon_budget_allocation import (
    Mannhardt2026CarbonBudgetDataset,
)
from zen_creator.elements.energy_systems.crystal_ball_industry import (
    CrystalBallIndustryEnergySystem,
)
from zen_creator.model import Model
from zen_creator.utils.attribute import Attribute

OLD_BUDGET_VALUE = 23.152036605496253


def _old_budget(energy_system) -> Attribute:
    return Attribute(
        "carbon_emissions_budget",
        element=energy_system,
        default_value=OLD_BUDGET_VALUE,
        unit="gigatons",
    )


def test_old_and_new_sector_emissions_from_real_data():
    """The committed sector_emissions_2022.csv reproduces the derived variant totals.

    New-sector totals include each sector's UK contribution (BEIS2023 for
    glass/ceramic, ONS2026 for food/paper) on top of the 28-country EEA total.
    """
    dataset = Mannhardt2026CarbonBudgetDataset()

    assert dataset.get_old_sector_emissions() == pytest.approx(2_563_680.158, abs=1)
    assert dataset.get_new_sector_emissions("A") == pytest.approx(64_573.077, abs=1)
    assert dataset.get_new_sector_emissions("C") == pytest.approx(79_402.382, abs=1)
    assert dataset.get_new_sector_emissions("B") == pytest.approx(158_890.730, abs=1)


def test_get_carbon_emissions_budget_variant_b(model: Model):
    """Variant B (chosen default) extends the budget to ~24.5869 Gt."""
    energy_system = CrystalBallIndustryEnergySystem(model=model)
    dataset = Mannhardt2026CarbonBudgetDataset()

    new_budget = dataset.get_carbon_emissions_budget(energy_system, _old_budget(energy_system), variant="B")

    assert new_budget.default_value == pytest.approx(24.5869, abs=1e-3)
    assert new_budget.unit == "gigatons"
    assert len(new_budget.sources) == 1


def test_get_carbon_emissions_budget_variant_a(model: Model):
    """Variant A (zero increment for glass/ceramics) extends the budget to ~23.7352 Gt."""
    energy_system = CrystalBallIndustryEnergySystem(model=model)
    dataset = Mannhardt2026CarbonBudgetDataset()

    new_budget = dataset.get_carbon_emissions_budget(energy_system, _old_budget(energy_system), variant="A")

    assert new_budget.default_value == pytest.approx(23.7352, abs=1e-3)


def test_get_carbon_emissions_budget_variant_c(model: Model):
    """Variant C (process-only for glass/ceramics) extends the budget to ~23.8691 Gt.

    Unlike A/B (each already exercised end-to-end above), variant C was
    previously only checked in isolation via get_new_sector_emissions("C")
    (see test_old_and_new_sector_emissions_from_real_data) -- this closes that
    gap by running the actual code path used when variant C is selected.
    """
    energy_system = CrystalBallIndustryEnergySystem(model=model)
    dataset = Mannhardt2026CarbonBudgetDataset()

    new_budget = dataset.get_carbon_emissions_budget(energy_system, _old_budget(energy_system), variant="C")

    assert new_budget.default_value == pytest.approx(23.8691, abs=1e-3)


def test_get_carbon_emissions_budget_zero_new_sectors_is_a_noop(model: Model):
    """If no sector contributes new emissions, the budget must stay unchanged."""
    energy_system = CrystalBallIndustryEnergySystem(model=model)
    dataset = Mannhardt2026CarbonBudgetDataset()
    dataset.data = pd.DataFrame(
        [
            {"sector": "electricity", "crf_category": "1.A.1.a", "component": "combustion",
             "bucket": "old", "emissions_kt_co2_28countries": 100.0, "emissions_kt_co2_uk": 0.0,
             "variant_tags": "A,B,C"},
            {"sector": "paper", "crf_category": "1.A.2.d", "component": "combustion",
             "bucket": "new", "emissions_kt_co2_28countries": 0.0, "emissions_kt_co2_uk": 0.0,
             "variant_tags": "A,B,C"},
        ]
    )

    new_budget = dataset.get_carbon_emissions_budget(energy_system, _old_budget(energy_system), variant="B")

    assert new_budget.default_value == pytest.approx(OLD_BUDGET_VALUE)


if __name__ == "__main__":
    pytest.main([__file__])
