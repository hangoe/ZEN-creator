"""One-off extraction script: produces sector_emissions_2022.csv from UNFCCC_v30.csv.

Not part of the zen_creator package - run manually if UNFCCC_v30.csv is updated
(e.g. a new EEA submission year). See ASSUMPTIONS.md ("Carbon emissions budget")
and the plan this was generated from for the full methodology.

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
"""

import csv
from pathlib import Path

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


def main() -> None:
    source_dir = Path(__file__).parent
    values = load_values(source_dir / "UNFCCC_v30.csv")

    out_path = source_dir / "sector_emissions_2022.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "sector", "crf_category", "component", "bucket",
            "emissions_kt_co2_28countries", "variant_tags",
        ])
        for sector, crf_category, component, bucket, variant_tags in ROWS:
            emissions = total_28_countries(values, crf_category)
            writer.writerow([sector, crf_category, component, bucket, f"{emissions:.6f}", variant_tags])

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
