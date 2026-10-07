"""Shared pytest fixtures for unit tests."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from zen_creator.model import Model
from zen_creator.utils.singleton_registry_meta import SingletonRegistryMeta


@pytest.fixture(autouse=True)
def reset_singleton_registries() -> Iterator[None]:
    """Reset singleton registries for test isolation.

    Note: this does NOT clear the module-level `functools.lru_cache` caches in
    `zen_creator/datasets/datasets/_industry_heat_utils.py` (e.g.
    `faostat_production_by_node`, `read_sector_thermal_fec`) -- those cache real
    Excel/CSV reads across the whole test session for speed. Harmless as long as
    no test monkeypatches the underlying source-data paths after an earlier test
    has already populated one of those caches; if a future test needs to do that,
    it must explicitly call `.cache_clear()` on the relevant function(s) itself.
    """
    SingletonRegistryMeta._registries.clear()
    yield
    SingletonRegistryMeta._registries.clear()


@pytest.fixture
def model(tmp_path: Path, request: pytest.FixtureRequest) -> Model:
    """Create a minimal model object that is sufficient for element tests.

    The element ``write()`` path resolution requires ``output_folder`` and
    ``name`` to be defined, while templates using datasets require
    ``source_path``.
    """
    model = Model()
    model.name = f"{request.module.__name__.split('.')[-1]}_model"
    model.output_folder = tmp_path / "outputs"
    model.source_path = tmp_path
    return model


@pytest.fixture
def register_attribute():
    """Register a standalone dataset-built Attribute on its element as already built.

    ``Attribute`` data reads (``.df``, ``.default_value``) are redirected to the attribute
    currently registered on the element (auto-building the element's own ``_set_<name>``
    first). A test that calls a dataset method directly, with a non-default argument, would
    otherwise read the element's own value instead of the returned one. In production
    ``Element._build_attribute`` does exactly this registration.
    """

    def _register(attribute):
        element = attribute.element
        setattr(element, attribute.name, attribute)
        element._built_attribute_names.add(attribute.name)
        return attribute

    return _register
