"""Helper to apply a complete attributes dict (as produced by json_templates /
excel_io) onto a ZEN-creator Element, setting both default_value and unit."""

from __future__ import annotations

import numpy as np

from zen_creator.elements.element import Element
from zen_creator.utils.attribute import Attribute


def apply_attrs_dict(element: Element, data: dict) -> None:
    """Overwrite an Element's attributes from a raw attributes-dict.

    `data` is the dict that would be written to attributes.json by
    compute_params.py (keys = attribute names, values = dicts with
    'default_value' and optionally 'unit').

    For each key in `data` that matches an attribute on `element`, both the
    default_value and the unit are overwritten.  The special list-valued
    attributes (conversion_factor, reference_carrier, input_carrier,
    output_carrier) are handled correctly.
    """
    # These are set by _set_* methods during build() and must not be
    # pre-populated here (the setters reject changes to non-empty values).
    SKIP_ATTRS = {"reference_carrier", "input_carrier", "output_carrier", "conversion_factor"}

    for key, entry in data.items():
        if key in SKIP_ATTRS:
            continue

        if not hasattr(element, key):
            continue
        attr = getattr(element, key)
        if not isinstance(attr, Attribute):
            continue

        if isinstance(entry, dict):
            value = entry.get("default_value")
            unit = entry.get("unit")
        else:
            value = entry
            unit = None

        if value is not None:
            if value == "inf":
                value = np.inf
            attr._default_value = value
        if unit is not None:
            attr._unit = unit
