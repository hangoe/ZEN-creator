"""
Loads process data from Rehfeldt et al. (2017), Table 1, from
input_data/Rehfeldt2017/Rehfeldt2017.csv.

Each sub-process entry provides:
  "fuels_GJ_t"   : specific fuel energy demand [GJ / t product]
  "elec_GJ_t"    : specific electricity demand  [GJ / t product]
  "activity_Mt"  : EU28+NO+IS+CH activity in 2012 [Mt / year]
  "temp_dist"    : fractional heat demand per temperature bin (sums to 1.0)
                   bins: "<100", "100-200", "200-500", "500-1000", ">1000"
  "source"       : literature reference
  "note"         : optional free-text note (only present if non-empty in the CSV)

doi: 10.1007/s12053-017-9571-y
"""

from pathlib import Path

import pandas as pd

INPUT_DATA = Path(__file__).resolve().parents[3] / "input_data" / "Rehfeldt2017"

# Temperature bins used by all "temp_dist" entries, and their corresponding
# columns in Rehfeldt2017.csv.
TEMP_BINS = ["<100", "100-200", "200-500", "500-1000", ">1000"]
_TEMP_COLUMNS = {
    "<100":     "temp_lt100",
    "100-200":  "temp_100_200",
    "200-500":  "temp_200_500",
    "500-1000": "temp_500_1000",
    ">1000":    "temp_gt1000",
}


def _load_sector(sector: str) -> dict:
    df = pd.read_csv(INPUT_DATA / "Rehfeldt2017.csv")
    df = df[df["sector"] == sector]

    sector_data = {}
    for _, row in df.iterrows():
        entry = {
            "fuels_GJ_t":  float(row["fuels_GJ_t"]),
            "elec_GJ_t":   float(row["elec_GJ_t"]),
            "activity_Mt": float(row["activity_Mt"]),
            "temp_dist":   {bin_: float(row[col]) for bin_, col in _TEMP_COLUMNS.items()},
            "source":      row["source"],
        }
        if pd.notna(row["note"]):
            entry["note"] = row["note"]
        sector_data[row["sub_process"]] = entry
    return sector_data


REHFELDT2017_GLASS = _load_sector("glass")
REHFELDT2017_CERAMIC = _load_sector("ceramic")

# Top 3 sub-processes by EU28+3 activity (covering 95.2 % of sector total).
# Mechanical pulp (9.85 Mt, 5.2 %) is excluded: TMP/CTMP refiners have a
# NEGATIVE fuel demand (-2.01 GJ/t) because they convert electricity to heat
# via friction, which does not fit the conversion-technology framework.
REHFELDT2017_PAPER = _load_sector("paper")

# All 5 Rehfeldt sub-processes are used. The top 3 by activity (dairy, meat,
# brewing) ALL have 100 % of heat demand below 200 degC; restricting to the
# top 3 would incorrectly set fuel_for_food to zero and ignore the
# medium-temperature demand from bread-baking and sugar.
REHFELDT2017_FOOD = _load_sector("food")
