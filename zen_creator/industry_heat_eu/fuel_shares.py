"""
Derives final-energy-consumption (FEC) shares by carrier for the "thermal"
(fuel) energy use of glass, ceramic, paper, and food production, from the
JRC-IDEES-2023 EU27 Industry workbook's per-sector "_fec" sheets.

These shares parametrize the fuel mix of the X_production conversion
technologies (X in glass, ceramic, paper, food), which take their
high-temperature fuel demand directly as a mix of primary energy carriers.

Carrier mapping and exclusions
-------------------------------
Of the carriers in THERMAL_CARRIER_LABELS, only natural gas, solid fuels
(coal), and biomass have a corresponding Crystal Ball carrier
(MODEL_CARRIER_MAP); all others (fuel oil, LPG, diesel, other liquids,
derived/refinery gases, distributed steam) are excluded because either they
are each below the 10% cutoff, or - for "Other liquids" and "Distributed
steam" specifically - no Crystal Ball carrier currently corresponds to them
even where their share exceeds 10% (e.g. ceramics "Other liquids" ~15% of
2023 thermal FEC, paper "Distributed steam" ~8%).
"""

import pandas as pd

from zen_creator.industry_heat_eu.jrc_idees import workbook_path, year_column

# Carrier-row labels used by JRC-IDEES-2023 "_fec" sheets to break down a
# "thermal"/"steam" process row into its fuel mix.
THERMAL_CARRIER_LABELS = {
    "Solids",
    "Refinery gas",
    "LPG",
    "Diesel oil and liquid biofuels",
    "Fuel oil",
    "Other liquids",
    "Natural gas and biogas",
    "Derived gases",
    "Biomass and waste",
    "Distributed steam",
}

# Map from JRC-IDEES carrier labels to Crystal Ball carrier names. Carriers
# not listed here have no corresponding Crystal Ball carrier and are
# excluded by `renormalized_fuel_shares`, regardless of their share.
MODEL_CARRIER_MAP = {
    "Natural gas and biogas": "natural_gas",
    "Solids": "hard_coal",
    "Biomass and waste": "biomass",
}

# sector -> (sheet, [process rows whose immediate carrier breakdown is the
# "thermal" fuel split for that sector]).
SECTOR_THERMAL_FEC_ROWS = {
    "glass": ("NMM_fec", ["Glass: Thermal melting tank", "Glass: Annealing - thermal"]),
    "ceramic": (
        "NMM_fec",
        [
            "Ceramics: Thermal drying and sintering",
            "Ceramics: Steam drying and sintering",
            "Ceramics: Thermal kiln",
            "Ceramics: Thermal furnace",
        ],
    ),
    "paper": (
        "PPA_fec",
        [
            "Paper: Stock preparation - Thermal",
            "Paper: Paper machine - Steam use",
            "Paper: Product finishing - Steam use",
        ],
    ),
    "food": (
        "FBT_fec",
        [
            "Food: Direct Heat - Thermal",
            "Food: Process Heat - Thermal",
            "Food: Steam processing",
            "Food: Thermal drying",
            "Food: Steam drying",
            "Food: Steam cooling",
        ],
    ),
}


def thermal_fec_by_carrier(df: pd.DataFrame, parent_rows: list[str], year: int) -> dict[str, float]:
    """Sum the fuel-carrier breakdown (ktoe) of `parent_rows` for `year`.

    Each row in `parent_rows` (e.g. "Glass: Thermal melting tank") is
    immediately followed in the sheet by a block of carrier rows (labels
    from THERMAL_CARRIER_LABELS); these blocks are summed across all
    `parent_rows`.
    """
    col = year_column(year)
    labels = df[0]
    totals: dict[str, float] = {}
    for parent in parent_rows:
        matches = df.index[labels == parent]
        if len(matches) == 0:
            raise ValueError(f"Row {parent!r} not found in sheet")
        i = matches[0] + 1
        while i < len(df) and labels[i] in THERMAL_CARRIER_LABELS:
            totals[labels[i]] = totals.get(labels[i], 0.0) + float(df.iat[i, col])
            i += 1
    return totals


def read_sector_thermal_fec(country: str, sector: str, year: int) -> dict[str, float]:
    """Read the thermal FEC-by-carrier breakdown (ktoe) for `sector` and `year`.

    `sector` is one of the keys of SECTOR_THERMAL_FEC_ROWS ("glass",
    "ceramic", "paper", "food").
    """
    sheet, parent_rows = SECTOR_THERMAL_FEC_ROWS[sector]
    df = pd.read_excel(workbook_path(country, "Industry"), sheet_name=sheet, header=None)
    return thermal_fec_by_carrier(df, parent_rows, year)


def fec_shares(breakdown: dict[str, float]) -> dict[str, float]:
    """Normalise a carrier -> FEC dict into shares of the total (summing to 1)."""
    total = sum(breakdown.values())
    return {carrier: value / total for carrier, value in breakdown.items()}


def renormalized_fuel_shares(shares: dict[str, float], cutoff: float = 0.10) -> dict[str, float]:
    """Map carrier shares to Crystal Ball carriers and renormalise to sum to 1.

    Carriers below `cutoff`, or without a Crystal Ball equivalent
    (MODEL_CARRIER_MAP), are dropped before renormalising the rest.
    """
    kept = {
        MODEL_CARRIER_MAP[carrier]: share
        for carrier, share in shares.items()
        if carrier in MODEL_CARRIER_MAP and share >= cutoff
    }
    total = sum(kept.values())
    return {carrier: share / total for carrier, share in kept.items()}
