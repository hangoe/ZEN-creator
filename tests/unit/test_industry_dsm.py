"""Unit tests for industry DSM (product storage) technologies.

See ASSUMPTIONS.md ("Product DSM storage efficiency") for why efficiency is not 1.0.
"""

from __future__ import annotations

import pytest

from zen_creator.elements.storage_technologies.industry_DSM import (
    AmmoniaDSMPessimistic,
    GlassDSMOptimistic,
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


if __name__ == "__main__":
    pytest.main([__file__])
