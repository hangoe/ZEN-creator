"""
Derives per-node `capacity_existing.csv` (for the X_production conversion
technologies, X in glass, ceramic, paper, food) and per-node `demand.csv`
(for the glass, ceramic, paper and food carriers), in the same format as
Crystal Ball's set_technologies/.../<tech>/capacity_existing.csv and
set_carriers/<carrier>/demand.csv.

Data sources
------------
- Glass, ceramic, paper: JRC-IDEES-2023 "Installed capacity (kt production)"
  (-> capacity_existing) and "Physical output (kt)" (-> demand).
- Food: FAOSTAT crop/livestock production combined with Rehfeldt's EU-wide
  subsector activity shares (-> capacity_existing, see
  food_capacity_existing_df), and FAOSTAT Food Balance Sheet "Feed" use of
  the same subsectors (-> demand, see food_demand_df). IDEES is not used for
  food: it only reports a production index, not a tonnage.

Node coverage
-------------
The industry_heat_eu model uses Crystal Ball's 28 nodes (EU27 minus Cyprus
and Malta, plus Switzerland, Norway, the UK and the Netherlands), `MODEL_NODES`.
JRC-IDEES-2023 only covers EU27 countries (so has Cyprus/Malta data, which is
unused here, but no Switzerland/Norway/UK data) - CH, NO and UK get
capacity_existing = demand = 0 for glass/ceramic/paper. FAOSTAT covers all 28
nodes.

Unit conversions
-----------------
IDEES reports "Installed capacity" and "Physical output" in kt product/year.

    capacity_existing [tonproduct/h] = installed_capacity [kt/y] * 1000 [t/kt] / OPERATING_HOURS

OPERATING_HOURS (8000 h/year) matches the convention already used for
opex_specific_fixed in process_parametrization.xlsx, "AIDRES2023 'opex cst'
... x 8000h".

    demand [tonproduct/h] = physical_output [kt/y] * 1000 [t/kt] / HOURS_PER_YEAR

HOURS_PER_YEAR (8760 h/year) matches the convention observed in Crystal
Ball's set_carriers/clinker/demand.csv (AT clinker demand 336.7 t/h x 8760 h
~ 2.95 Mt/year).
"""

import warnings
from pathlib import Path

import pandas as pd

from zen_creator.industry_heat_eu.data.rehfeldt2017 import REHFELDT2017_FOOD
from zen_creator.industry_heat_eu.faostat import feed_by_node, production_by_node
from zen_creator.industry_heat_eu.jrc_idees import workbook_path, year_column

INPUT_DATA = Path(__file__).resolve().parents[2] / "input_data"

# Crystal Ball model nodes: EU27 minus Cyprus (CY) and Malta (MT), plus
# Switzerland (CH), Norway (NO), the UK and the Netherlands (NL).
MODEL_NODES = (
    "AT", "BE", "BG", "CH", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU",
    "IE", "IT", "LT", "LU", "LV", "NL", "NO", "PL", "PT", "RO", "SE", "SI", "SK", "UK",
)

# Nodes with no JRC-IDEES-2023 country workbook -> capacity_existing = demand = 0.
NODES_WITHOUT_IDEES = ("CH", "NO", "UK")

OPERATING_HOURS = 8000  # h/year
HOURS_PER_YEAR = 8760  # h/year

# "Installed capacity (kt production)" and "Physical output (kt)" sections
# share row labels and run until the next "... (kt production)" header.
INSTALLED_CAPACITY_HEADER = "Installed capacity (kt production)"
PHYSICAL_OUTPUT_HEADER = "Physical output (kt)"

# sector -> (sheet, [row labels under "Installed capacity (kt production)" /
# "Physical output (kt)" to sum]).
SECTOR_CAPACITY_ROWS = {
    "glass": ("NMM", ["Glass production  (kt)"]),
    "ceramic": ("NMM", ["Ceramics & other NMM (kt bricks eq.)"]),
    "paper": ("PPA", ["Pulp production (kt)", "Paper production  (kt)", "Printing and media reproduction (kt paper eq.)"]),
}

# Rehfeldt food subsector -> FAOSTAT "Production" item used as a proxy for
# its output tonnage, for splitting Rehfeldt's EU-wide activity_Mt across
# nodes by each node's share of that item's production.
FOOD_PRODUCTION_ITEMS = {
    "dairy": "Milk, Total",
    "meat_processing": "Meat, Total",
    "brewing": "Beer of barley, malted",
    "bread_bakery": "Wheat",
    "sugar": "Raw cane or beet sugar (centrifugal only)",
}

# Rehfeldt food subsector -> FAOSTAT Food Balance Sheet "Feed" item used as a
# proxy for that subsector's contribution to national animal-feed demand.
FOOD_FEED_ITEMS = {
    "dairy": "Milk - Excluding Butter",
    "meat_processing": "Meat",
    "brewing": "Barley and products",
    "bread_bakery": "Wheat and products",
    "sugar": "Sugar beet",
}

# input_data/David2017/David2017_heat_pumps.csv "country" -> MODEL_NODES.
DAVID2017_COUNTRY_TO_NODE = {
    "Austria": "AT",
    "Czech Republic": "CZ",
    "Denmark": "DK",
    "Finland": "FI",
    "France": "FR",
    "Italy": "IT",
    "Netherlands": "NL",
    "Norway": "NO",
    "Slovakia": "SK",
    "Sweden": "SE",
    "Switzerland": "CH",
}

# Rows in David2017_heat_pumps.csv with no commissioning year ("est_year")
# are assigned this year_construction, the median est_year of the rows that
# do have one (1981-2016, median 1998).
DAVID2017_DEFAULT_YEAR = 1998

# input_data/Eurostat/Eurostat_EB_GWh.xlsx "GEO (Labels)" -> MODEL_NODES.
# Switzerland ("CH") has no entry in this dataset -> capacity_existing = 0.
EUROSTAT_COUNTRY_TO_NODE = {
    "Belgium": "BE",
    "Bulgaria": "BG",
    "Czechia": "CZ",
    "Denmark": "DK",
    "Germany": "DE",
    "Estonia": "EE",
    "Ireland": "IE",
    "Greece": "EL",
    "Spain": "ES",
    "France": "FR",
    "Croatia": "HR",
    "Italy": "IT",
    "Latvia": "LV",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Hungary": "HU",
    "Netherlands": "NL",
    "Austria": "AT",
    "Poland": "PL",
    "Portugal": "PT",
    "Romania": "RO",
    "Slovenia": "SI",
    "Slovakia": "SK",
    "Finland": "FI",
    "Sweden": "SE",
    "Norway": "NO",
    "United Kingdom": "UK",
}
NODE_TO_EUROSTAT_COUNTRY = {node: country for country, node in EUROSTAT_COUNTRY_TO_NODE.items()}

# Sheets of input_data/Eurostat/Eurostat_EB_GWh.xlsx ("Unit of measure" =
# Gigawatt-hour) for "Gross heat production" by SIEC, used as the basis for
# capacity_existing of the *_boiler_industry technologies (each technology's
# input_carrier). Sheets 72/74/83 = Natural gas / Primary solid biofuels / Electricity.
EUROSTAT_EB_XLSX = "Eurostat_EB_GWh.xlsx"
EUROSTAT_NATURAL_GAS_HEAT_SHEET = "Sheet 72"  # Natural gas -> natural_gas_boiler_industry
EUROSTAT_BIOMASS_HEAT_SHEET = "Sheet 74"  # Primary solid biofuels -> biomass_boiler_industry
EUROSTAT_ELECTRICITY_HEAT_SHEET = "Sheet 83"  # Electricity -> electrode_boiler_industry
EUROSTAT_HEAT_FIRST_YEAR = 2015


def section_by_label(df: pd.DataFrame, year: int, header: str) -> dict[str, float]:
    """Read the `header` section of `df` for `year`.

    Returns {row_label: value} for every row between the `header` row and
    the next "... (kt production)" section header.
    """
    col = year_column(year)
    labels = df[0]
    [header_idx] = df.index[labels == header]

    values: dict[str, float] = {}
    for i in range(header_idx + 1, len(df)):
        label = labels[i]
        if not isinstance(label, str):
            continue
        if label.endswith("(kt production)"):
            break
        values[label] = float(df.iat[i, col])
    return values


def _sector_kt(country: str, sector: str, year: int, header: str) -> float:
    """Sum a `header` section's `SECTOR_CAPACITY_ROWS` rows for `sector` and `year`."""
    sheet, row_labels = SECTOR_CAPACITY_ROWS[sector]
    df = pd.read_excel(workbook_path(country, "Industry"), sheet_name=sheet, header=None)
    values = section_by_label(df, year, header)
    return sum(values[label] for label in row_labels)


def installed_capacity_kt(country: str, sector: str, year: int) -> float:
    """Sum the IDEES "Installed capacity (kt production)" rows for `sector` and `year`."""
    return _sector_kt(country, sector, year, INSTALLED_CAPACITY_HEADER)


def physical_output_kt(country: str, sector: str, year: int) -> float:
    """Sum the IDEES "Physical output (kt)" rows for `sector` and `year`."""
    return _sector_kt(country, sector, year, PHYSICAL_OUTPUT_HEADER)


def capacity_existing_df(sector: str, year: int, year_construction: int | None = None) -> pd.DataFrame:
    """Build a capacity_existing.csv DataFrame (columns node, year_construction,
    capacity_existing) for `sector` (glass, ceramic or paper), one row per
    `MODEL_NODES`.

    Nodes in `NODES_WITHOUT_IDEES` get capacity_existing = 0. All other nodes
    get their `year`-installed capacity converted from kt/year to
    tonproduct/hour via `OPERATING_HOURS`.
    """
    rows = []
    for node in MODEL_NODES:
        if node in NODES_WITHOUT_IDEES:
            capacity = 0.0
        else:
            capacity = installed_capacity_kt(node, sector, year) * 1000 / OPERATING_HOURS
        rows.append({"node": node, "year_construction": year_construction or year, "capacity_existing": capacity})
    return pd.DataFrame(rows)


def industry_demand_df(sector: str, year: int) -> pd.DataFrame:
    """Build a demand.csv DataFrame (columns node, demand) for `sector`'s
    carrier (glass, ceramic or paper), one row per `MODEL_NODES`.

    ASSUMPTION: demand is approximated by `sector`'s JRC-IDEES-2023
    "Physical output (kt)" for `year` (i.e. national production is assumed to
    equal national consumption - net trade is not modelled).

    Nodes in `NODES_WITHOUT_IDEES` get demand = 0. All other nodes get their
    `year` physical output converted from kt/year to tonproduct/hour via
    `HOURS_PER_YEAR`.
    """
    rows = []
    for node in MODEL_NODES:
        if node in NODES_WITHOUT_IDEES:
            demand = 0.0
        else:
            demand = physical_output_kt(node, sector, year) * 1000 / HOURS_PER_YEAR
        rows.append({"node": node, "demand": demand})
    return pd.DataFrame(rows)


def food_capacity_existing_df(year: int, year_construction: int | None = None) -> pd.DataFrame:
    """Build a capacity_existing.csv DataFrame (columns node, year_construction,
    capacity_existing) for food_production, one row per `MODEL_NODES`.

    For each Rehfeldt food subsector, each node's share of FAOSTAT `year`
    production of the subsector's `FOOD_PRODUCTION_ITEMS` proxy is used to
    split that subsector's EU-wide `activity_Mt` across nodes. A node's
    activities are summed across subsectors, then converted from Mt/year to
    tonproduct/hour via `OPERATING_HOURS`.
    """
    activity_mt = {node: 0.0 for node in MODEL_NODES}
    for subsector, item in FOOD_PRODUCTION_ITEMS.items():
        production = production_by_node(item, year)
        total = sum(production[node] for node in MODEL_NODES)
        for node in MODEL_NODES:
            share = production[node] / total if total else 0.0
            activity_mt[node] += share * REHFELDT2017_FOOD[subsector]["activity_Mt"]

    rows = [
        {"node": node, "year_construction": year_construction or year, "capacity_existing": activity_mt[node] * 1e6 / OPERATING_HOURS}
        for node in MODEL_NODES
    ]
    return pd.DataFrame(rows)


def food_demand_df(year: int) -> pd.DataFrame:
    """Build a demand.csv DataFrame (columns node, demand) for the "food"
    carrier, one row per `MODEL_NODES`.

    For each node, sums the FAOSTAT `year` Food Balance Sheet "Feed" use of
    `FOOD_FEED_ITEMS` across all Rehfeldt food subsectors, then converts from
    1000 t/year to tonproduct/hour via `HOURS_PER_YEAR`.
    """
    feed_kt = {node: 0.0 for node in MODEL_NODES}
    for item in FOOD_FEED_ITEMS.values():
        feed = feed_by_node(item, year)
        for node in MODEL_NODES:
            feed_kt[node] += feed[node]

    rows = [
        {"node": node, "demand": feed_kt[node] * 1000 / HOURS_PER_YEAR}
        for node in MODEL_NODES
    ]
    return pd.DataFrame(rows)


def heat_pump_capacity_existing_df() -> pd.DataFrame:
    """Build a capacity_existing.csv DataFrame (columns node, year_construction,
    capacity_existing) for heat_pump_industry from
    `input_data/David2017/David2017_heat_pumps.csv`, one row per node with
    heat pump plants.

    Each plant's `output_capacity_MW` is mapped to a `MODEL_NODES` node via
    `DAVID2017_COUNTRY_TO_NODE` (the Netherlands entry is dropped - "NL" is
    not in MODEL_NODES) and converted from MW to GW (capacity_existing's unit
    for heat_pump_industry). All plants of a node are summed into a single
    row, with `year_construction` set to the capacity-weighted average of
    the plants' `est_year` (or `DAVID2017_DEFAULT_YEAR` if missing), rounded
    to the nearest year. Nodes without any heat pump plants get no row
    (capacity_existing defaults to 0 in attributes.json).
    """
    plants = pd.read_csv(INPUT_DATA / "David2017" / "David2017_heat_pumps.csv")
    plants = plants[plants["country"].isin(DAVID2017_COUNTRY_TO_NODE)]

    node = plants["country"].map(DAVID2017_COUNTRY_TO_NODE)
    year_construction = plants["est_year"].fillna(DAVID2017_DEFAULT_YEAR).astype(int)
    capacity_existing = plants["output_capacity_MW"] / 1000

    df = pd.DataFrame({"node": node, "year_construction": year_construction, "capacity_existing": capacity_existing})

    def aggregate(group: pd.DataFrame) -> pd.Series:
        total_capacity = group["capacity_existing"].sum()
        weighted_year = (group["year_construction"] * group["capacity_existing"]).sum() / total_capacity
        return pd.Series({"year_construction": int(round(weighted_year)), "capacity_existing": total_capacity})

    result = df.groupby("node", as_index=False).apply(aggregate)
    result["year_construction"] = result["year_construction"].astype(int)
    return result


def eurostat_gross_heat_gwh(sheet: str, year: int) -> dict[str, float]:
    """Read a "Gross heat production" sheet of Eurostat_EB_GWh.xlsx (in GWh)
    for `year`, returning {Eurostat country label: GWh}.

    If `year` is ":" (not available) for a country, the latest earlier year
    (back to `EUROSTAT_HEAT_FIRST_YEAR`) with a value is used instead (these
    extracts have no data after 2019 for the United Kingdom).
    """
    df = pd.read_excel(INPUT_DATA / "Eurostat" / EUROSTAT_EB_XLSX, sheet_name=sheet, header=None)
    [header_row] = df.index[df[0] == "TIME"]

    values: dict[str, float] = {}
    for i in range(header_row + 1, len(df)):
        label = df.iat[i, 0]
        if label not in EUROSTAT_COUNTRY_TO_NODE:
            continue
        for y in range(year, EUROSTAT_HEAT_FIRST_YEAR - 1, -1):
            cell = df.iat[i, 1 + 2 * (y - EUROSTAT_HEAT_FIRST_YEAR)]
            if cell != ":":
                values[label] = float(cell)
                break
    return values


def boiler_capacity_existing_df(sheet: str, year: int, year_construction: int | None = None) -> pd.DataFrame:
    """Build a capacity_existing.csv DataFrame (columns node, year_construction,
    capacity_existing) for a *_boiler_industry technology, one row per
    `MODEL_NODES`.

    Eurostat's `year` "Gross heat production" of `sheet` (GWh/year) is
    converted to GW (capacity_existing's unit for the *_boiler_industry
    technologies, whose reference and output carrier is
    heat_low_temp_industry) via `OPERATING_HOURS`. Switzerland ("CH"), which
    has no entry in this Eurostat extract, gets capacity_existing = 0.
    """
    heat_gwh = eurostat_gross_heat_gwh(sheet, year)

    rows = []
    for node in MODEL_NODES:
        country = NODE_TO_EUROSTAT_COUNTRY.get(node)
        gwh = heat_gwh.get(country, 0.0) if country else 0.0
        capacity = gwh / OPERATING_HOURS
        rows.append({"node": node, "year_construction": year_construction or year, "capacity_existing": capacity})
    return pd.DataFrame(rows)


def biomass_boiler_capacity_existing_df(year: int, year_construction: int | None = None) -> pd.DataFrame:
    """capacity_existing.csv DataFrame for biomass_boiler_industry, from
    Eurostat's "Gross heat production" of "Primary solid biofuels"
    (see `boiler_capacity_existing_df`)."""
    return boiler_capacity_existing_df(EUROSTAT_BIOMASS_HEAT_SHEET, year, year_construction)


def natural_gas_boiler_capacity_existing_df(year: int, year_construction: int | None = None) -> pd.DataFrame:
    """capacity_existing.csv DataFrame for natural_gas_boiler_industry, from
    Eurostat's "Gross heat production" of "Natural gas"
    (see `boiler_capacity_existing_df`)."""
    return boiler_capacity_existing_df(EUROSTAT_NATURAL_GAS_HEAT_SHEET, year, year_construction)


def electrode_boiler_capacity_existing_df(year: int, year_construction: int | None = None) -> pd.DataFrame:
    """capacity_existing.csv DataFrame for electrode_boiler_industry, from
    Eurostat's "Gross heat production" of "Electricity"
    (see `boiler_capacity_existing_df`), minus each node's
    `heat_pump_capacity_existing_df` capacity.

    ASSUMPTION: Eurostat's "Electricity" gross heat production includes heat
    from electric heat pumps as well as electrode (resistance) boilers; the
    David2017-based heat pump capacity (`heat_pump_capacity_existing_df`,
    converted to the same `year_construction`) is subtracted out per node to
    avoid double-counting. If this would make a node's capacity_existing
    negative, a warning is issued and it is set to 0 instead.
    """
    df = boiler_capacity_existing_df(EUROSTAT_ELECTRICITY_HEAT_SHEET, year, year_construction)
    heat_pump_capacity = heat_pump_capacity_existing_df().set_index("node")["capacity_existing"]

    def subtract_heat_pump(row):
        capacity = row["capacity_existing"] - heat_pump_capacity.get(row["node"], 0.0)
        if capacity < 0:
            warnings.warn(
                f"electrode_boiler_capacity_existing_df: node {row['node']} capacity_existing "
                f"({row['capacity_existing']}) minus heat pump capacity_existing "
                f"({heat_pump_capacity.get(row['node'], 0.0)}) is negative; setting to 0."
            )
            return 0.0
        return capacity

    df["capacity_existing"] = df.apply(subtract_heat_pump, axis=1)
    return df
