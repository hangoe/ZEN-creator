"""Unit tests for Mannhardt2026CarbonBudgetDataset."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from zen_creator.datasets.datasets.carbon_budget_allocation import (
    Mannhardt2026CarbonBudgetDataset,
)
from zen_creator.elements.energy_systems.zen_europe_industry import (
    ZenEuropeIndustryEnergySystem,
)
from zen_creator.model import Model
from zen_creator.utils.attribute import Attribute

OLD_BUDGET_VALUE = 23.152036605496253


def _old_budget(energy_system) -> SimpleNamespace:
    """Stand-in for the base budget (only default_value and unit are read).

    A real Attribute on the energy system would be auto-built from the element's own
    _set_carbon_emissions_budget on first read, replacing OLD_BUDGET_VALUE (inf on a
    bare Model). The element's own attribute is marked built for the same reason, so
    reading the returned new budget doesn't trigger that rebuild either.
    """
    energy_system._built_attribute_names.add("carbon_emissions_budget")
    return SimpleNamespace(default_value=OLD_BUDGET_VALUE, unit="gigatons")


def _extend_budget(dataset, energy_system, variant: str) -> Attribute:
    """Run get_carbon_emissions_budget and register the result on the element, as
    Element._build_attribute does in production (reads redirect to the registered one)."""
    new_budget = dataset.get_carbon_emissions_budget(
        energy_system, _old_budget(energy_system), variant=variant
    )
    energy_system.carbon_emissions_budget = new_budget
    return new_budget


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
    energy_system = ZenEuropeIndustryEnergySystem(model=model)
    dataset = Mannhardt2026CarbonBudgetDataset()

    new_budget = _extend_budget(dataset, energy_system, "B")

    assert new_budget.default_value == pytest.approx(24.5869, abs=1e-3)
    assert new_budget.unit == "gigatons"
    assert len(new_budget.sources) == 1


def test_get_carbon_emissions_budget_variant_a(model: Model):
    """Variant A (zero increment for glass/ceramics) extends the budget to ~23.7352 Gt."""
    energy_system = ZenEuropeIndustryEnergySystem(model=model)
    dataset = Mannhardt2026CarbonBudgetDataset()

    new_budget = _extend_budget(dataset, energy_system, "A")

    assert new_budget.default_value == pytest.approx(23.7352, abs=1e-3)


def test_get_carbon_emissions_budget_variant_c(model: Model):
    """Variant C (process-only for glass/ceramics) extends the budget to ~23.8691 Gt,
    via the actual code path used when variant C is selected (unlike
    test_old_and_new_sector_emissions_from_real_data, which checks
    get_new_sector_emissions("C") in isolation).
    """
    energy_system = ZenEuropeIndustryEnergySystem(model=model)
    dataset = Mannhardt2026CarbonBudgetDataset()

    new_budget = _extend_budget(dataset, energy_system, "C")

    assert new_budget.default_value == pytest.approx(23.8691, abs=1e-3)


def test_get_carbon_emissions_budget_zero_new_sectors_is_a_noop(model: Model):
    """If no sector contributes new emissions, the budget must stay unchanged."""
    energy_system = ZenEuropeIndustryEnergySystem(model=model)
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

    new_budget = _extend_budget(dataset, energy_system, "B")

    assert new_budget.default_value == pytest.approx(OLD_BUDGET_VALUE)


if __name__ == "__main__":
    pytest.main([__file__])
