"""Plotting helpers to explore JRC-IDEES-2023 summary sheets.

Row numbers in the functions below are 1-based "Excel row numbers", i.e. the
row numbers shown when opening the workbook (matching what you see when
inspecting the sheet directly), not 0-based pandas/array indices.
"""

import colorsys

import numpy as np
import openpyxl
import matplotlib.pyplot as plt
import pandas as pd

from zen_creator.industry_heat_eu.jrc_idees import workbook_path


_GOLDEN_ANGLE = 0.618033988749895


def _sector_palette(n: int) -> list[tuple[float, float, float]]:
    """`n` perceptually well-spread base colors, one per top-level sector.

    Hues are stepped by the golden angle so that neighboring sectors don't
    end up with similar hues (which plain even-spacing can cause, e.g. two
    adjacent sectors both landing in the green range).
    """
    return [colorsys.hsv_to_rgb((i * _GOLDEN_ANGLE) % 1.0, 0.6, 0.85) for i in range(n)]


def _shades(base_color: tuple[float, float, float], n: int) -> list[tuple[float, float, float]]:
    """`n` shades of `base_color` (lightest to darkest), used for a sector's sub-sectors."""
    if n == 1:
        return [base_color]
    hue, lightness, saturation = colorsys.rgb_to_hls(*base_color)
    lightnesses = np.linspace(min(lightness + 0.28, 0.88), max(lightness - 0.12, 0.15), n)
    return [colorsys.hls_to_rgb(hue, l, saturation) for l in lightnesses]


def read_sheet_block(country: str, dataset: str, sheet: str, first_row: int, last_row: int) -> pd.DataFrame:
    """Read a block of rows from a summary sheet as a (label x year) table.

    `first_row`/`last_row` are 1-based Excel row numbers (inclusive), and the
    sheet is expected to have its row labels in column A and one year per
    column (as in the JRC-IDEES-2023 "_Summary" sheets).
    """
    df = pd.read_excel(workbook_path(country, dataset), sheet_name=sheet, header=None)
    years = df.iloc[0, 1:].astype(int)

    block = df.iloc[first_row - 1 : last_row, :].dropna(subset=[0])
    block = block.set_index(0)
    block.columns = years
    block.index.name = "label"
    return block


def _row_indents(country: str, dataset: str, sheet: str, first_row: int, last_row: int) -> pd.Series:
    """Return the cell indentation level of column A for each row in the block.

    The JRC-IDEES summary sheets use indentation to encode the label
    hierarchy (e.g. a sector total vs. its sub-sector breakdown), which lets
    us tell a section's total row apart from the entries that make it up.
    """
    workbook = openpyxl.load_workbook(workbook_path(country, dataset), data_only=True)
    worksheet = workbook[sheet]
    indents = {}
    for row in range(first_row, last_row + 1):
        cell = worksheet.cell(row=row, column=1)
        if cell.value is not None:
            indents[cell.value] = cell.alignment.indent
    return pd.Series(indents, name="indent")


def read_sector_breakdown(
    country: str,
    dataset: str = "Industry",
    sheet: str = "Ind_Summary",
    header_row: int = 51,
    last_row: int = 78,
    rtol: float = 1e-6,
) -> pd.DataFrame:
    """Read the "by sector" breakdown of final energy consumption (Ind_Summary).

    `header_row` (Excel row 51, "by sector") holds the section's total, and is
    used purely as a consistency check: the values of the top-level sectors
    (the least-indented entries below it) must sum up to it. That header/total
    row is excluded from the returned table, since it is not itself a sector
    and would otherwise dominate any plot of the breakdown.

    Returns a (sector x year) table of the top-level sectors only, i.e.
    without the per-sector sub-breakdowns (e.g. "Integrated steelworks" is
    omitted as it is already part of "Iron and steel").
    """
    table = read_sheet_block(country, dataset, sheet, first_row=header_row, last_row=last_row)
    indents = _row_indents(country, dataset, sheet, first_row=header_row, last_row=last_row)

    total = table.loc[indents.index[indents == indents.min()][0]]
    top_level_sectors = table.loc[indents[indents == sorted(indents.unique())[1]].index]

    if not top_level_sectors.sum().sub(total).abs().le(total.abs() * rtol).all():
        raise ValueError(
            f"Sector breakdown in {sheet!r} does not sum up to its total "
            f"('{total.name}'); the sheet layout may have changed."
        )

    return top_level_sectors


def read_sector_breakdown_with_subsectors(
    country: str,
    dataset: str = "Industry",
    sheet: str = "Ind_Summary",
    header_row: int = 51,
    last_row: int = 78,
) -> pd.DataFrame:
    """Read each top-level sector's direct sub-sector breakdown.

    Returns a (sector, subsector) x year table: sectors that have a further
    breakdown (e.g. "Iron and steel" -> "Integrated steelworks"/"Electric arc")
    contribute one row per direct sub-sector; sectors without one contribute a
    single row whose subsector is the sector itself.
    """
    table = read_sheet_block(country, dataset, sheet, first_row=header_row, last_row=last_row)
    indents = _row_indents(country, dataset, sheet, first_row=header_row, last_row=last_row)
    labels = list(indents.index)
    sector_indent = sorted(indents.unique())[1]

    pairs = []
    i = 1  # skip the total row (least indented, listed first)
    while i < len(labels):
        sector = labels[i]
        children = []
        j = i + 1
        while j < len(labels) and indents[labels[j]] > sector_indent:
            if indents[labels[j]] == sector_indent + 1:
                children.append(labels[j])
            j += 1
        pairs += [(sector, subsector) for subsector in (children or [sector])]
        i = j

    breakdown = table.loc[[subsector for _, subsector in pairs]]
    breakdown.index = pd.MultiIndex.from_tuples(pairs, names=["sector", "subsector"])
    return breakdown


def plot_values_for_year(table: pd.DataFrame, year: int, ylabel: str = "", title: str = "", ax=None):
    """Bar chart of one column (year) of a (label x year) table such as returned by `read_sheet_block`."""
    if year not in table.columns:
        raise ValueError(f"Year {year} not in data; available years: {sorted(table.columns)}")

    if ax is None:
        _, ax = plt.subplots(figsize=(12, 6))

    table[year].plot(kind="bar", ax=ax)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=75)
    return ax


def plot_energy_consumption_by_sector(country: str, year: int, ax=None):
    """Plot final energy consumption by industrial sector for one year.

    Reads the "by sector" breakdown from the Ind_Summary sheet (Excel rows
    51-78, in ktoe), checks it against its total, and plots the top-level
    sectors for the chosen year as a stacked bar chart, with each sector's
    direct sub-sectors (where available) shown as separate colored segments.
    """
    sectors = read_sector_breakdown(country, "Industry", "Ind_Summary", header_row=51, last_row=78)
    detail = read_sector_breakdown_with_subsectors(country, "Industry", "Ind_Summary", header_row=51, last_row=78)

    if year not in detail.columns:
        raise ValueError(f"Year {year} not in data; available years: {sorted(detail.columns)}")

    if ax is None:
        _, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(sectors.index))
    bottoms = np.zeros(len(sectors.index))
    base_colors = _sector_palette(len(sectors.index))

    for i, sector in enumerate(sectors.index):
        subsectors = detail.loc[sector]
        for shade, (subsector, row) in zip(_shades(base_colors[i], len(subsectors)), subsectors.iterrows()):
            ax.bar(x[i], row[year], bottom=bottoms[i], color=shade, label=subsector)
            bottoms[i] += row[year]

    ax.set_xticks(x)
    ax.set_xticklabels(sectors.index, rotation=75)
    ax.set_ylabel("Final energy consumption (ktoe)")
    ax.set_title(f"{country}: Final energy consumption by sector ({year})")
    ax.legend(title="Sub-sector", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize="small")
    return ax
