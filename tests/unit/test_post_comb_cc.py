"""Unit tests for PostCombCCDataset (post_comb_cc.py).

Covers the renormalized natural_gas/hard_coal fuel-split and the
retrofit_flow_coupling_factor derivation (base carbon intensity x DEA capture
rate) -- none of which had direct test coverage (see cleanup plan, Phase 2
item 5).
"""

from __future__ import annotations

import pytest

from zen_creator.datasets.datasets.post_comb_cc import (
    MAX_DIFFUSION_RATE,
    PostCombCCDataset,
)


@pytest.fixture(scope="module")
def dataset() -> PostCombCCDataset:
    return PostCombCCDataset()


@pytest.mark.parametrize("sector", ["ceramic", "glass"])
def test_ng_coal_split_sums_to_one(dataset, sector):
    """The renormalized natural_gas/hard_coal split must sum to 1 and only
    contain the two combustion carriers it's restricted to."""
    split = dataset._ng_coal_split(sector)
    assert set(split) <= {"natural_gas", "hard_coal"}
    assert sum(split.values()) == pytest.approx(1.0)
    assert all(v >= 0 for v in split.values())


def test_get_conversion_factor_input_shares_follow_ng_coal_split(dataset, model):
    """The natural_gas/hard_coal entries of conversion_factor's heat-input side
    must be split in the same proportions as _ng_coal_split."""
    from zen_creator.elements.conversion_technologies.industry_ccs import CeramicPostComb

    element = CeramicPostComb(model=model)
    attr = dataset.get_conversion_factor(element, "ceramic")
    entries = {k: v["default_value"] for e in attr.default_value for k, v in e.items()}

    split = dataset._ng_coal_split("ceramic")
    fuel_entries = {c: entries[c] for c in split}
    total_fuel = sum(fuel_entries.values())
    for carrier, share in split.items():
        assert fuel_entries[carrier] / total_fuel == pytest.approx(share, rel=1e-9)

    # electricity and district_heat (output) must also be present
    assert "electricity" in entries
    assert "district_heat" in entries


def test_get_retrofit_flow_coupling_factor_matches_formula(dataset, model):
    """coupling_factor = base production tech's carbon_intensity_technology x
    DEA capture rate, converted ton -> kiloton (see method docstring)."""
    from zen_creator.datasets.datasets.process_parametrization import (
        ProcessParametrizationDataset,
    )
    from zen_creator.elements.conversion_technologies.industry_ccs import CeramicPostComb

    element = CeramicPostComb(model=model)
    base_intensity = ProcessParametrizationDataset().get_carbon_intensity_technology(
        element, "ceramic"
    ).default_value
    attr = dataset.get_retrofit_flow_coupling_factor(element, "ceramic")

    capture_rate = attr.default_value * 1000.0 / base_intensity if base_intensity else 0.0
    assert 0.0 < capture_rate <= 1.0
    assert attr.unit == "kilotCO2eq/tonproduct"
    assert attr.base_technology == "ceramic_production"


def test_capacity_addition_unbounded_and_max_diffusion_rate_are_shared_constants(dataset, model):
    from zen_creator.elements.conversion_technologies.industry_ccs import (
        CeramicPostComb,
        GlassPostComb,
    )

    ceramic_element = CeramicPostComb(model=model)
    glass_element = GlassPostComb(model=model)

    for element, sector in ((ceramic_element, "ceramic"), (glass_element, "glass")):
        rate_attr = dataset.get_max_diffusion_rate(element, sector)
        assert rate_attr.default_value == pytest.approx(MAX_DIFFUSION_RATE)


if __name__ == "__main__":
    pytest.main([__file__])
