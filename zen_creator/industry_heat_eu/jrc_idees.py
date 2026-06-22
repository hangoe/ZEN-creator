"""Helpers for reading JRC-IDEES-2023 Excel data."""

from pathlib import Path

import pandas as pd

DATA_ROOT = Path(__file__).resolve().parents[2] / "input_data" / "JRC-IDEES-2023"

# Industry sheets (incl. "_fec" sheets) have one column per year, starting at
# 2000 in column 1 (0-based).
FIRST_YEAR = 2000


def workbook_path(country: str, dataset: str) -> Path:
    """Return the path to a JRC-IDEES-2023 workbook for a country and dataset.

    E.g. workbook_path("DE", "Industry") -> .../JRC-IDEES-2023/DE/JRC-IDEES-2023_Industry_DE.xlsx
    """
    return DATA_ROOT / country / f"JRC-IDEES-2023_{dataset}_{country}.xlsx"


def read_sheet(country: str, dataset: str, sheet_name: str | int = 0) -> pd.DataFrame:
    """Read a single sheet from a JRC-IDEES-2023 workbook into a DataFrame."""
    return pd.read_excel(workbook_path(country, dataset), sheet_name=sheet_name)


def year_column(year: int) -> int:
    """0-based column index of `year` in a JRC-IDEES-2023 Industry sheet."""
    return year - FIRST_YEAR + 1
