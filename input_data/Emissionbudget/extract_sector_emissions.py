"""One-off extraction script: produces sector_emissions_2022.csv from UNFCCC_v30.csv,
plus UK-specific glass/ceramic/paper/food emissions from two UK national sources.

Not part of the zen_creator package - run manually if UNFCCC_v30.csv (or either UK
source file) is updated. See ASSUMPTIONS.md ("Carbon emissions budget") and the plan
this was generated from for the full methodology.

CRF category -> sector/component/bucket/variant mapping follows Mannhardt (2026)
dissertation, Appendix A.2, Table A.2, extended for glass/ceramics/paper/food:

- "old" rows are Mannhardt's 11 modeled sectors (Chapters 5/6), always counted.
- "new" rows are the four added sectors. `variant_tags` marks which of the three
  compared variants (A: zero increment, B: naive full-add [chosen], C: process-only)
  include that row when summing `E_new_sectors`.
- Paper/food have no CRF overlap with any existing sector -> counted in all variants.
- Glass (2.A.3 process) and ceramics (2.A.4 process, used as a proxy since this
  UNFCCC extract does not break out 2.A.4.a specifically) are excluded from Variant A,
  included from Variant C onward.
- 1.A.2.f ("Non-metallic minerals" combustion) is a shared EEA bucket already fully
  counted under the existing "cement" old-sector row (1.A.2.f + 2.A per Table A.2) -
  only Variant B re-adds it in full, accepting the resulting double-count.

UK data (`emissions_kt_co2_uk`, added on top of `emissions_kt_co2_28countries` for the
new sectors only - see ASSUMPTIONS.md for why "old" sectors are left 28-country-only):

- glass/ceramic: BEIS `UK-final-greenhouse-gas-emissions-tables-2021.xlsx`
  (`BEIS2023`), sheet 1.2, 2021 values. "Glass production" (IPCC 2A3) matches CRF
  2.A.3 exactly. Ceramic sums "Bricks production" + "Fletton brick production" +
  "Other ceramics" (all IPCC 2A4a per sheet 6.1) - cleaner than the EU27 2.A.4 proxy,
  since the UK table separates out soda ash (2A4b) instead of bundling it in.
- food/paper: ONS `ONS_atmospheric_emissions_ghg.xlsx` (`ONS2026`), sheet "CO2",
  2022 values, CO2-only (matches the EU27 Pollutant_name == "CO2" filter below).
  Paper = SIC 17 ("Paper and paper products"), matching CRF 1.A.2.d. Food = SIC
  10.1-10.9 + 11.01-06 + 11.07 + 12 (food + beverages + tobacco), matching CRF
  1.A.2.e's "Food, Beverages and Tobacco" IPCC definition exactly.
- `glass_ceramic_shared_combustion` (variant B's shared 1.A.2.f re-add) has no clean
  UK equivalent - the UK combustion for this bucket is folded into BEIS's single
  aggregate "Industrial combustion and electricity (excl. iron and steel)" row along
  with several other sub-sectors, so it is left 28-country-only.
- Caveats: BEIS values are MtCO2e (GHG total, not CO2-only like the EEA/ONS figures) -
  negligible in practice since glass/ceramic process emissions are almost entirely
  CO2. ONS figures are on a UK residence basis, not territorial like BEIS/EEA -
  immaterial for domestically-produced-and-consumed goods like food/paper. The BEIS
  (2021) and ONS (2022) reference years differ slightly, each being the latest/closest
  year available from that source.
"""

import csv
from pathlib import Path

import openpyxl

YEAR = "2022"
COUNTRIES = ["EUA", "CH", "NO", "MT", "CY"]  # 28-country total = EUA - MT - CY + CH + NO

# (sector, crf_category, component, bucket, variant_tags)
ROWS = [
    ("electricity", "1.A.1.a", "combustion", "old", "A,B,C"),
    ("refining", "1.A.1.b", "combustion", "old", "A,B,C"),
    ("steel", "1.A.2.a", "combustion", "old", "A,B,C"),
    ("steel", "2.C.1", "process", "old", "A,B,C"),
    ("chemicals", "1.A.2.c", "combustion", "old", "A,B,C"),
    ("chemicals", "2.B", "process", "old", "A,B,C"),
    ("cement", "1.A.2.f", "combustion", "old", "A,B,C"),
    ("cement", "2.A", "process", "old", "A,B,C"),
    ("aviation", "1.A.3.a", "combustion", "old", "A,B,C"),
    ("aviation", "1.D.1.a", "combustion", "old", "A,B,C"),
    ("passenger_road", "1.A.3.b.i", "combustion", "old", "A,B,C"),
    ("truck", "1.A.3.b.iii", "combustion", "old", "A,B,C"),
    ("shipping", "1.A.3.d", "combustion", "old", "A,B,C"),
    ("shipping", "1.D.1.b", "combustion", "old", "A,B,C"),
    ("residential_heat", "1.A.4.b", "combustion", "old", "A,B,C"),
    ("commercial_heat", "1.A.4.a", "combustion", "old", "A,B,C"),
    ("paper", "1.A.2.d", "combustion", "new", "A,B,C"),
    ("food", "1.A.2.e", "combustion", "new", "A,B,C"),
    ("glass", "2.A.3", "process", "new", "B,C"),
    ("ceramic", "2.A.4", "process", "new", "B,C"),
    ("glass_ceramic_shared_combustion", "1.A.2.f", "combustion", "new", "B"),
]

BEIS_FILE = "UK-final-greenhouse-gas-emissions-tables-2021.xlsx"
ONS_FILE = "ONS_atmospheric_emissions_ghg.xlsx"
ONS_FOOD_SIC_CODES = ["10.1", "10.2-3", "10.4", "10.5", "10.6", "10.7", "10.8", "10.9",
                       "11.01-06", "11.07", "12"]
ONS_PAPER_SIC_CODE = "17"
ONS_YEAR = 2022


def load_values(csv_path: Path) -> dict[tuple[str, str], float]:
    """Map (Sector_code, Country_code) -> CO2 emissions [kt] for the target year."""
    values: dict[tuple[str, str], float] = {}
    needed_codes = {crf for _, crf, _, _, _ in ROWS}
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Year"] != YEAR or row["Pollutant_name"] != "CO2":
                continue
            if row["Country_code"] not in COUNTRIES or row["Sector_code"] not in needed_codes:
                continue
            try:
                values[(row["Sector_code"], row["Country_code"])] = float(row["emissions"])
            except ValueError:
                continue
    return values


def total_28_countries(values: dict[tuple[str, str], float], crf_category: str) -> float:
    get = lambda country: values.get((crf_category, country), 0.0)
    return get("EUA") - get("MT") - get("CY") + get("CH") + get("NO")


def load_uk_glass_ceramic(xlsx_path: Path) -> dict[str, float]:
    """UK glass/ceramic 2021 emissions [kt CO2e] from BEIS table 1.2 (MtCO2e -> kt)."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb["1.2"]
    ceramic_categories = {"Bricks production", "Fletton brick production", "Other ceramics"}
    glass_mt = 0.0
    ceramic_mt = 0.0
    for row in ws.iter_rows(min_row=8, values_only=True):
        category = row[1]
        value_2021 = row[-1]
        if value_2021 is None:
            continue
        if category == "Glass production":
            glass_mt = value_2021
        elif category in ceramic_categories:
            ceramic_mt += value_2021
    return {"glass": glass_mt * 1000, "ceramic": ceramic_mt * 1000}


def load_uk_food_paper(xlsx_path: Path) -> dict[str, float]:
    """UK food/paper 2022 emissions [kt CO2] from the ONS by-industry CO2 sheet."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb["CO2"]
    rows = list(ws.iter_rows(values_only=True))
    header_codes = rows[6]
    food_cols = [i for i, code in enumerate(header_codes) if code in ONS_FOOD_SIC_CODES]
    paper_cols = [i for i, code in enumerate(header_codes) if code == ONS_PAPER_SIC_CODE]

    year_row = next(r for r in rows[8:] if isinstance(r[0], (int, float)) and int(r[0]) == ONS_YEAR)
    food_kt = sum(year_row[i] for i in food_cols if year_row[i] is not None)
    paper_kt = sum(year_row[i] for i in paper_cols if year_row[i] is not None)
    return {"food": food_kt, "paper": paper_kt}


def main() -> None:
    source_dir = Path(__file__).parent
    values = load_values(source_dir / "UNFCCC_v30.csv")

    uk_values: dict[str, float] = {}
    uk_values.update(load_uk_glass_ceramic(source_dir / BEIS_FILE))
    uk_values.update(load_uk_food_paper(source_dir / ONS_FILE))

    out_path = source_dir / "sector_emissions_2022.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "sector", "crf_category", "component", "bucket",
            "emissions_kt_co2_28countries", "emissions_kt_co2_uk", "variant_tags",
        ])
        for sector, crf_category, component, bucket, variant_tags in ROWS:
            emissions = total_28_countries(values, crf_category)
            uk_emissions = uk_values.get(sector, 0.0)
            writer.writerow([
                sector, crf_category, component, bucket,
                f"{emissions:.6f}", f"{uk_emissions:.6f}", variant_tags,
            ])

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
