import pytest

from zen_creator.industry_heat_eu.plotting import (
    plot_energy_consumption_by_sector,
    read_sector_breakdown,
    read_sheet_block,
)


def test_read_sheet_block_returns_label_by_year_table():
    table = read_sheet_block("EU27", "Industry", "Ind_Summary", first_row=51, last_row=78)
    assert "Iron and steel" in table.index
    assert 2023 in table.columns
    assert 2025 not in table.columns


def test_read_sector_breakdown_excludes_total_and_subsectors():
    table = read_sector_breakdown("EU27")
    assert "by sector" not in table.index
    assert "Iron and steel" in table.index
    assert "Integrated steelworks" not in table.index


def test_plot_energy_consumption_by_sector():
    ax = plot_energy_consumption_by_sector("EU27", year=2023)
    assert ax.get_title() == "EU27: Final energy consumption by sector (2023)"
    assert "by sector" not in [label.get_text() for label in ax.get_xticklabels()]


def test_plot_energy_consumption_by_sector_unavailable_year_raises():
    with pytest.raises(ValueError, match="2025"):
        plot_energy_consumption_by_sector("EU27", year=2025)
