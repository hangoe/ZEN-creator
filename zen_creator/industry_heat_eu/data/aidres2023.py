"""
Loads process data from AIDRES (2023), Section 7 - glass production routes,
from input_data/AIDRES2023/AIDRES2023_glass.csv.

Energy values per tonne of product [GJ/t] for the natural-gas reference
route (NG REF: natural-gas furnace, no CCS).

Direct emissions [tCO2/t]:
  - emit_ng_ref : NG REF route, includes combustion + raw-material decomposition
  - emit_elec   : electricity route, raw-material decomposition only (no
                  combustion) -> used as the best estimate of PROCESS
                  EMISSIONS alone.

Ceramics are NOT covered by AIDRES.
"""

from pathlib import Path

import pandas as pd

INPUT_DATA = Path(__file__).resolve().parents[3] / "input_data" / "AIDRES2023"

_df = pd.read_csv(INPUT_DATA / "AIDRES2023_glass.csv").set_index("sub_process")

AIDRES2023_GLASS = {
    sub_process: {
        "ng_GJ_t":        float(row["ng_GJ_t"]),
        "elec_GJ_t":      float(row["elec_GJ_t"]),
        "capex_eur_t_yr": int(row["capex_eur_t_yr"]),
        "emit_ng_ref":    float(row["emit_ng_ref"]),
        "emit_elec":      float(row["emit_elec"]),
        "source":         row["source"],
    }
    for sub_process, row in _df.iterrows()
}

# AIDRES EU production mix (§7.1): container 60 %, flat 30 %, fibre 10 %.
AIDRES2023_GLASS_SHARES = {sub_process: float(share) for sub_process, share in _df["eu_production_share"].items()}
assert abs(sum(AIDRES2023_GLASS_SHARES.values()) - 1.0) < 1e-9
