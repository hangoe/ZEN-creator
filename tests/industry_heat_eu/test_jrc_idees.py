from zen_creator.industry_heat_eu.jrc_idees import workbook_path


def test_workbook_path():
    path = workbook_path("DE", "Industry")
    assert path.name == "JRC-IDEES-2023_Industry_DE.xlsx"
    assert path.parent.name == "DE"
