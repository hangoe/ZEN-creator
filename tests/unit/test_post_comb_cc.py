"""Unit tests for PostCombCCDataset (post_comb_cc.py).

Covers the renormalized natural_gas/hard_coal fuel-split and the
retrofit_flow_coupling_factor derivation (base carbon intensity x DEA capture
rate).
"""

from __future__ import annotations

import pytest

from zen_creator.datasets.datasets.post_comb_cc import (
    _CAPEX_LABEL,
    _OPEX_FIXED_LABEL,
    MAX_DIFFUSION_RATE,
    MODEL_FIRST_YEAR,
    PostCombCCDataset,
    _interpolate_to_model_years,
    _year_values,
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
    # raw value: .default_value would redirect to the retrofit's own (zero) intensity
    base_intensity = ProcessParametrizationDataset().get_carbon_intensity_technology(
        element, "ceramic"
    )._default_value
    attr = dataset.get_retrofit_flow_coupling_factor(element, "ceramic")

    capture_rate = attr.default_value * 1000.0 / base_intensity if base_intensity else 0.0
    assert 0.0 < capture_rate <= 1.0
    assert attr.unit == "kilotCO2/tonproduct"
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


@pytest.mark.parametrize("attr_name,label", [
    ("capex_specific_conversion", _CAPEX_LABEL),
    ("opex_specific_fixed", _OPEX_FIXED_LABEL),
])
def test_capex_and_fixed_opex_are_per_kilotco2(dataset, model, attr_name, label):
    """DEA reports mill EUR/(tCO2/h); the attribute is in EUR/(kilotCO2/h), so the
    model-first-year value must equal the DEA value x 1e6 x 1e3 (same EUR/(tCO2/h)
    magnitude as cement_post_comb, not 1000x smaller)."""
    from zen_creator.elements.conversion_technologies.industry_ccs import GlassPostComb

    element = GlassPostComb(model=model)
    attr = getattr(dataset, f"get_{attr_name}")(element, "glass")
    dea_value = _interpolate_to_model_years(_year_values(label)).loc[MODEL_FIRST_YEAR]
    assert attr.unit == "Euro/(kilotCO2/hour)"
    assert attr.default_value == pytest.approx(dea_value * 1e9)


if __name__ == "__main__":
    pytest.main([__file__])
