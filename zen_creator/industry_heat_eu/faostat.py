"""Helpers for reading FAOSTAT production and food balance sheet data from
input_data/FAOSTAT/.
"""

from pathlib import Path

import pandas as pd

DATA_ROOT = Path(__file__).resolve().parents[2] / "input_data" / "FAOSTAT"
DATA_FILE = DATA_ROOT / "Production_Crops_Livestock_E_Europe.csv"
FOOD_BALANCE_FILE = DATA_ROOT / "FoodBalanceSheets_E_Europe.csv"

# Crystal Ball node (ISO2) -> FAOSTAT "Area" name, for the 28 model nodes.
NODE_TO_AREA = {
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "CH": "Switzerland",
    "CZ": "Czechia",
    "DE": "Germany",
    "DK": "Denmark",
    "EE": "Estonia",
    "EL": "Greece",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "HR": "Croatia",
    "HU": "Hungary",
    "IE": "Ireland",
    "IT": "Italy",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "NL": "Netherlands",
    "NO": "Norway",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SE": "Sweden",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "UK": "United Kingdom of Great Britain and Northern Ireland",
}


def production_by_node(item: str, year: int) -> dict[str, float]:
    """Read FAOSTAT "Production" (tonnes) of `item` for `year`, keyed by
    Crystal Ball node (ISO2). Nodes with no data for `item` get 0.0.
    """
    df = pd.read_csv(DATA_FILE, encoding="latin1", usecols=["Area", "Item", "Element", f"Y{year}"])
    rows = df[(df["Element"] == "Production") & (df["Item"] == item)].set_index("Area")[f"Y{year}"]

    return {
        node: float(rows[area]) if area in rows.index and pd.notna(rows[area]) else 0.0
        for node, area in NODE_TO_AREA.items()
    }


def feed_by_node(item: str, year: int) -> dict[str, float]:
    """Read the FAOSTAT Food Balance Sheet "Feed" use (1000 t) of `item` for
    `year`, keyed by Crystal Ball node (ISO2). Nodes with no data for `item`
    get 0.0.

    Some items (e.g. "Milk - Excluding Butter") appear twice per area under
    different (old- and new-system) item codes with identical values; rows
    are deduplicated by area before lookup.
    """
    df = pd.read_csv(FOOD_BALANCE_FILE, encoding="latin1", usecols=["Area", "Item", "Element", f"Y{year}"])
    rows = df[(df["Element"] == "Feed") & (df["Item"] == item)].drop_duplicates("Area").set_index("Area")[f"Y{year}"]

    return {
        node: float(rows[area]) if area in rows.index and pd.notna(rows[area]) else 0.0
        for node, area in NODE_TO_AREA.items()
    }
