from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zen_creator.model import Model

from zen_creator.datasets.datasets.carbon_budget_allocation import (
    Mannhardt2026CarbonBudgetDataset,
)
from zen_creator.utils.attribute import Attribute

from .energy_system import EnergySystem


class CrystalBallIndustryEnergySystem(EnergySystem):
    """Energy system for the Crystal Ball model extended with new industry sectors.

    Behaves like `GenericEnergySystem` (set_nodes/set_edges pass through the values
    loaded via `Model.from_existing`), except `carbon_emissions_budget` is extended
    to credit the glass/ceramic/paper/food sectors, per Mannhardt (2026) Appendix A.2
    methodology - see `carbon_budget_allocation.py` and `ASSUMPTIONS.md` ("Carbon
    emissions budget") for the full derivation.
    """

    name: str = "crystal_ball_industry_energy_system"

    def __init__(self, model: Model):
        super().__init__(model=model)

    def _set_set_nodes(self) -> Attribute:
        return self.set_nodes

    def _set_set_edges(self) -> Attribute:
        return self.set_edges

    def _set_carbon_emissions_budget(self) -> Attribute:
        return Mannhardt2026CarbonBudgetDataset().get_carbon_emissions_budget(
            self, self.carbon_emissions_budget
        )
