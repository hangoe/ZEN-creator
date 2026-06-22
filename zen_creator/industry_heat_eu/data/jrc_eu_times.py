"""Functions to read industry process cost data from the JRC-EU-TIMES model
(SubRES_TMPL/SUBRES_10_TECHS_CHP_SUP_IND.xls, IND sheet).

Source: JRC-EU-TIMES model v2019.11
File: input_data/JRC-EU-TIMES_2019_11/SubRES_TMPL/SUBRES_10_TECHS_CHP_SUP_IND.xls
Reference in file: "Prospects for Energy technologies in the Netherlands,
    ECN-C--095-039; MATTER and ICARUS-4, NWS-E-2001-02, base year 2006."

Units in JRC-EU-TIMES IND sheet:
    TechCapUnit = Mta (million tonnes per year of product)
    INVCOST     = M€/Mta = EUR/(t/year)           — investment cost per annual capacity
    FIXOM       = M€/Mta/year = EUR/(t/year)/year — annual fixed O&M per annual capacity
    VAROM       = EUR/t product                   — variable O&M per tonne output
    LIFE        = years                           — technical lifetime
    EMISSIONS~INDCO2P = Mt CO2 / Mta output       — direct (non-combustion) process CO2

To convert to Crystal Ball capacity units (tonproduct/h):
    INVCOST [EUR/(t/h)]      = INVCOST_JRC [EUR/(t/year)] × HOURS_PER_YEAR
    FIXOM   [EUR/(t/h)/year] = FIXOM_JRC   [EUR/(t/year)/year] × HOURS_PER_YEAR

Coverage by sector
------------------
Glass (IGF/IGH): JRC-EU-TIMES has technology-level data for flat glass (IGF) and
    hollow/container glass (IGH). Mapped to AIDRES2023 sub-processes container/flat/fibre.
    No fibre glass technology exists in JRC-EU-TIMES; flat glass (IGFFLATGL01) is used
    as a proxy for fibre glass (both are continuous-melt processes, similar equipment).

Paper (IPP): JRC-EU-TIMES has technology-level data for high-quality paper machines
    (IPPHIGQUA01), low-quality / recycled-fibre machines (IPPLOWQUA01), and chemical
    (Kraft) pulp lines (IPPPUPCHE01). Mapped to Rehfeldt2017 sub-processes.

Ceramics (INM): JRC-EU-TIMES only has generic "Other Non-Metallic Minerals" process-heat
    boiler technologies (INMPRCxxx, INMSTMxxx), which represent heat-supply equipment
    costs, NOT ceramic kiln / product-line capex. No appropriate proxy available.

Food (IOI): JRC-EU-TIMES only has generic "Other Industries" process-heat boiler
    technologies (IOIPRCxxx, IOISTMxxx) — same limitation as ceramics. No appropriate
    proxy available for food processing equipment capex.
"""

from pathlib import Path

import xlrd

JRC_DIR = Path(__file__).resolve().parents[3] / "input_data" / "JRC-EU-TIMES_2019_11"
SUBRES_IND_FILE = JRC_DIR / "SubRES_TMPL" / "SUBRES_10_TECHS_CHP_SUP_IND.xls"

# Base year of all cost data in the JRC-EU-TIMES file.
PARAM_BASE_YEAR = 2006

# Hours per year for unit conversion EUR/(t/year) → EUR/(t/h).
HOURS_PER_YEAR = 8760

# ── Glass ────────────────────────────────────────────────────────────────────
# AIDRES2023 sub-process → JRC-EU-TIMES technology code.
# IGF = flat glass; IGH = hollow (container) glass.
# "fibre" has no dedicated JRC-EU-TIMES technology; IGFFLATGL01 used as proxy
# (both flat and fibre glass use similar continuous-melt furnace technology).
GLASS_AIDRES_TO_JRC = {
    "container": "IGHHOLLOW01",   # IGH.Glass Hollow.01
    "flat":      "IGFFLATGL01",   # IGF.Glass Flat.01
    "fibre":     "IGFFLATGL01",   # proxy: no specific fibre tech, use flat
}

# ── Paper ─────────────────────────────────────────────────────────────────────
# Rehfeldt2017 sub-process → JRC-EU-TIMES technology code.
PAPER_REHFELDT_TO_JRC = {
    "paper":            "IPPHIGQUA01",   # IPP.High Quality Paper Production.01
    "recovered_fibres": "IPPLOWQUA01",   # IPP.Low Quality Paper Production.01
    "chemical_pulp":    "IPPPUPCHE01",   # IPP.Chemical Pulp Production.01
}


def read_ind_process_params(tech_name: str) -> dict:
    """Return INVCOST, FIXOM, VAROM, LIFE, EMISSIONS_INDCO2P for `tech_name`
    from the IND sheet.  All values in JRC-EU-TIMES base units
    (EUR/(t/year) for cost parameters).  Missing / empty cells → 0.0.
    """
    wb = xlrd.open_workbook(SUBRES_IND_FILE)
    ws = wb.sheet_by_name("IND")

    headers = {ws.cell_value(4, j): j for j in range(ws.ncols)}
    col = {
        "TechName": headers["TechName"],
        "INVCOST":  headers["INVCOST"],
        "FIXOM":    headers["FIXOM"],
        "VAROM":    headers["VAROM"],
        "LIFE":     headers["LIFE"],
        "CO2":      headers["EMISSIONS~INDCO2P"],
    }

    result = {k: 0.0 for k in ("INVCOST", "FIXOM", "VAROM", "LIFE", "EMISSIONS_INDCO2P")}
    current_tech = None
    for i in range(ws.nrows):
        name = ws.cell_value(i, col["TechName"])
        if name and name != "TechName":
            current_tech = name
        if current_tech != tech_name:
            continue
        for key, col_key in [
            ("INVCOST", "INVCOST"), ("FIXOM", "FIXOM"), ("VAROM", "VAROM"),
            ("LIFE", "LIFE"), ("EMISSIONS_INDCO2P", "CO2"),
        ]:
            v = ws.cell_value(i, col[col_key])
            if isinstance(v, (int, float)) and v != 0:
                result[key] = float(v)
            elif isinstance(v, str) and v.strip() not in ("", "0"):
                try:
                    result[key] = float(v)
                except ValueError:
                    pass

    return result


def gdp_deflator_ratio(from_year: int, to_year: int) -> float:
    """Return the EU GDP deflator ratio from_year→to_year.

    Uses the GDPdeflator sheet (EU27, price index 2000=100, Q4 observations
    2004–2012).  Years beyond 2012 are extrapolated at the CAGR observed
    over the available data range.
    """
    wb = xlrd.open_workbook(SUBRES_IND_FILE)
    ws = wb.sheet_by_name("GDPdeflator")

    obs: dict[int, float] = {}
    for i in range(3, 12):
        label = str(ws.cell_value(i, 0)).strip()
        val = ws.cell_value(i, 1)
        if label and isinstance(val, (int, float)):
            obs[int(label[:4])] = float(val)

    years_sorted = sorted(obs)
    first_y, last_y = years_sorted[0], years_sorted[-1]
    cagr = (obs[last_y] / obs[first_y]) ** (1 / (last_y - first_y)) - 1

    def _index(year: int) -> float:
        if year in obs:
            return obs[year]
        if year < first_y:
            return obs[first_y] / (1 + cagr) ** (first_y - year)
        return obs[last_y] * (1 + cagr) ** (year - last_y)

    return _index(to_year) / _index(from_year)


def sector_weighted_params(
    jrc_mapping: dict[str, str],
    activity_weights: dict[str, float],
    target_year: int,
) -> dict[str, float]:
    """Compute activity-weighted JRC-EU-TIMES cost parameters for any sector.

    Parameters
    ----------
    jrc_mapping:
        Maps sub-process name → JRC-EU-TIMES technology code.
        Every key must be present in `activity_weights`.
    activity_weights:
        Weight for each sub-process (must sum to 1 across the keys in
        jrc_mapping).
    target_year:
        Target price year; cost data are inflated from PARAM_BASE_YEAR using
        the EU GDP deflator.

    Returns
    -------
    dict with Crystal Ball-ready values:
        capex_specific_conversion   [Euro/(tonproduct/h)]
        opex_specific_fixed         [Euro/(tonproduct/h)/year]
        opex_specific_variable      [Euro/tonproduct]
        carbon_intensity_technology [tonCO2/tonproduct]
        lifetime                    [years, rounded]
    """
    deflator = gdp_deflator_ratio(PARAM_BASE_YEAR, target_year)

    capex = fixom = varom = co2 = life = 0.0
    for sub_key, jrc_code in jrc_mapping.items():
        w = activity_weights[sub_key]
        p = read_ind_process_params(jrc_code)
        capex += w * p["INVCOST"]
        fixom += w * p["FIXOM"]
        varom += w * p["VAROM"]
        co2   += w * p["EMISSIONS_INDCO2P"]
        life  += w * p["LIFE"]

    return {
        "capex_specific_conversion": capex * deflator * HOURS_PER_YEAR,
        "opex_specific_fixed":       fixom * deflator * HOURS_PER_YEAR,
        "opex_specific_variable":    varom * deflator,
        "carbon_intensity_technology": co2,
        "lifetime":                  round(life),
    }
