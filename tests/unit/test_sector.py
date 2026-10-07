"""Unit tests for the Sector mechanism: required_sectors, AND-membership and variant groups."""

from __future__ import annotations

import pytest

from zen_creator.elements.carriers.aa_template import TemplateCarrier
from zen_creator.elements.conversion_technologies.aa_template import (
    TemplateConversionTechnology,
)
from zen_creator.elements.storage_technologies.aa_template import (
    TemplateStorageTechnology,
)
from zen_creator.elements.transport_technologies.aa_template import (
    TemplateTransportTechnology,
)
from zen_creator.model import Model
from zen_creator.sectors import Sector
from zen_creator.utils.config.element import ElementTypeList


class _RootSector(Sector):
    """Owns an element required by ``_DependentSector``."""

    name = "test_root"
    required_sectors: list[str] = []

    def __init__(self) -> None:
        super().__init__()
        self.elements = [TemplateCarrier]


class _DependentSector(Sector):
    """Requires ``test_root``; owns an element solely."""

    name = "test_dependent"
    required_sectors = ["test_root"]

    def __init__(self) -> None:
        super().__init__()
        self.elements = [TemplateStorageTechnology]


class _SharedSectorA(Sector):
    """Shares ``TemplateConversionTechnology`` with ``_SharedSectorB``."""

    name = "test_shared_a"
    required_sectors: list[str] = []

    def __init__(self) -> None:
        super().__init__()
        self.elements = [TemplateConversionTechnology]


class _SharedSectorB(Sector):
    """Shares ``TemplateConversionTechnology`` with ``_SharedSectorA``."""

    name = "test_shared_b"
    required_sectors: list[str] = []

    def __init__(self) -> None:
        super().__init__()
        self.elements = [TemplateConversionTechnology]


# The sector registry is global, so the variant-group tests use an element
# (TemplateTransportTechnology) no other test sector declares.
class _VariantSectorPooled(Sector):
    """Pooled variant; shares its element with the per-sector variant and a third sector."""

    name = "test_variant_pooled"
    variant_group = "test_variant"

    def __init__(self) -> None:
        super().__init__()
        self.elements = [TemplateTransportTechnology]


class _VariantSectorPerSector(Sector):
    name = "test_variant_per_sector"
    variant_group = "test_variant"

    def __init__(self) -> None:
        super().__init__()
        self.elements = [TemplateTransportTechnology]


class _VariantOtherSector(Sector):
    """Declares the same element as the variant group but is not part of it."""

    name = "test_variant_other"

    def __init__(self) -> None:
        super().__init__()
        self.elements = [TemplateTransportTechnology]


def test_initialize_sectors_raises_on_missing_required_sector(model: Model) -> None:
    """Selecting a sector without its required sector raises ValueError."""
    with pytest.raises(ValueError, match="test_root"):
        model._initialize_sectors(["test_dependent"])


def test_initialize_sectors_succeeds_when_required_sector_included(
    model: Model,
) -> None:
    """Selecting a sector together with its required sector succeeds."""
    model._initialize_sectors(["test_root", "test_dependent"])

    assert TemplateCarrier.name in model.elements
    assert TemplateStorageTechnology.name in model.elements


def test_and_membership_waits_for_all_owning_sectors(model: Model) -> None:
    """An element declared by two sectors is added only once both are active."""
    model.add_sector_by_name("test_shared_a")
    assert TemplateConversionTechnology.name not in model.elements

    model.add_sector_by_name("test_shared_b")
    assert TemplateConversionTechnology.name in model.elements


def test_and_membership_is_order_independent(model: Model) -> None:
    """Activating the owning sectors in a different order gives the same result."""
    model.add_sector_by_name("test_shared_b")
    assert TemplateConversionTechnology.name not in model.elements

    model.add_sector_by_name("test_shared_a")
    assert TemplateConversionTechnology.name in model.elements


@pytest.mark.parametrize("variant", ["test_variant_pooled", "test_variant_per_sector"])
def test_variants_of_a_group_satisfy_shared_element_alone(
    model: Model, variant: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An element shared only by variants of one group is added with either variant."""
    monkeypatch.delitem(Sector._sector_registry, "test_variant_other")
    model.add_sector_by_name(variant)
    assert TemplateTransportTechnology.name in model.elements


def test_variant_group_still_ands_with_other_sectors(model: Model) -> None:
    """A group counts as one slot: an element also declared outside the group still
    needs that other sector."""
    model.add_sector_by_name("test_variant_per_sector")
    assert TemplateTransportTechnology.name not in model.elements

    model.add_sector_by_name("test_variant_other")
    assert TemplateTransportTechnology.name in model.elements


def test_two_variants_of_one_group_cannot_be_active_together(model: Model) -> None:
    model.add_sector_by_name("test_variant_pooled")
    with pytest.raises(ValueError, match="only one variant"):
        model.add_sector_by_name("test_variant_per_sector")


def test_remove_sector_by_name(model: Model) -> None:
    """Removing a sector removes the elements it declares."""
    model.add_sector_by_name("test_root")
    assert TemplateCarrier.name in model.elements

    model.remove_sector_by_name("test_root")
    assert TemplateCarrier.name not in model.elements


def test_exclude_set_sectors_removes_previously_inserted_elements(
    model: Model,
) -> None:
    """`_initialize_technologies_and_carriers` removes excluded sectors."""
    insert = ElementTypeList(set_sectors=["test_root"])

    model._initialize_sectors(insert.set_sectors)
    assert TemplateCarrier.name in model.elements

    model._initialize_technologies_and_carriers(insert, ["test_root"], [])
    assert TemplateCarrier.name not in model.elements


if __name__ == "__main__":
    pytest.main([__file__])
