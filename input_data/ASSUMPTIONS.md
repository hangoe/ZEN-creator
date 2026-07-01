# Assumptions made in the code

This file lists assumptions made in `src/industry_heat_eu/` and
`scripts/compute_params.py` when deriving parameters for the new industry
conversion technologies and carriers (glass, ceramic, paper, food) and the
shared `heat_low_temp_industry` carrier. It does not cover assumptions in
the input Excel files (`process_parametrization.xlsx`,
`industry_carriers.xlsx`, `heat_tech_parametrization.xlsx`) - those document 
their own sources in their `source`/`comment` columns.

## General

- **Temperature-level heat split** (`process_params.SectorParams`):
  Each sector's fuel heat demand is split into three ranges using the Rehfeldt
  temperature bins: `<100°C` → carrier `heat_industry_0_100`, `100–200°C` →
  carrier `heat_industry_100_200`, and the remaining bins (`200-500`, `500-1000`,
  `>1000`) stay as high-temperature `fuel` input to the production technology.
  The optimizer can then choose the cheapest supply technology per temperature
  level independently. Electricity is not split.

- **GJ/t -> GW/(tonproduct/h) conversion**
  (`process_params.GJ_per_t_to_conversion_factor`): conversion factors are
  computed as `energy_GJ_t / 3600`, since 1 tonproduct/h x 1 GJ/t = 1 GJ/h =
  1/3600 GW.

- **CAPEX and other table-driven defaults**: `build_conversion_tech`
  (`json_templates.py`) builds each new technology with a placeholder
  `capex_specific_conversion = 1.0 EUR/(tonproduct/h)`. `write_production_tech` 
  then overwrites this and other defaults (`opex_specific_fixed`, 
  `max_diffusion_rate`, ...) with the values from `process_parametrization.xlsx`.

- **Fuel mix shares for X_production**
  (`scripts/compute_params.py`, "FUEL MIX SHARES" section): each
  `X_production` technology takes its high-temperature fuel demand
  (`params.cf_fuel`) directly as a mix of primary energy carriers
  (`natural_gas`, `hard_coal`, `biomass`), split according to the sector's
  JRC-IDEES-2023 EU27 2023 thermal FEC shares. 

- **Fuel mix carrier cutoff** (`fuel_shares.renormalized_fuel_shares`,
  `MODEL_CARRIER_MAP`): of the JRC-IDEES thermal-FEC carriers, only natural
  gas, solid fuels (-> `hard_coal`) and biomass have a corresponding Crystal
  Ball carrier. All others (fuel oil, LPG, diesel, other liquids,
  derived/refinery gases, distributed steam) are excluded, either because
  they are below a 10% cutoff, or - for "Other liquids" and "Distributed
  steam" specifically - because no Crystal Ball carrier currently corresponds
  to them even where their share exceeds 10% (e.g. ceramics "Other liquids"
  ~15% of 2023 thermal FEC, paper "Distributed steam" ~8%). The remaining
  carriers are renormalised to sum to 1.

## Glass

- Three AIDRES sub-processes (container/flat/fibre glass), weighted by the
  AIDRES EU production mix (60/30/10%).
- Energy (fuel + electricity) taken from the AIDRES natural-gas-reference
  route (`AIDRES2023_GLASS`, key `ng_GJ_t`).
- Temperature distribution taken from Rehfeldt for the same three
  sub-processes, weighted with the same AIDRES 60/30/10 shares for
  consistency with the AIDRES energy data.
- Process (raw-material decomposition) emissions estimated as the AIDRES
  electricity-route direct emissions (`emit_elec`): the electricity route has
  zero combustion emissions, so its residual direct emissions are assumed to
  be entirely raw-material decomposition.
- **Cost and lifetime parameters** (`capex_specific_conversion`,
  `opex_specific_fixed`, `opex_specific_variable`, `lifetime`) from
  JRC-EU-TIMES 2019.11 (`SUBRES_10_TECHS_CHP_SUP_IND.xls`, IND sheet),
  activity-weighted across the three sub-processes using the same AIDRES
  60/30/10 shares: container→`IGHHOLLOW01` (INVCOST=250, FIXOM=20, LIFE=30),
  flat→`IGFFLATGL01` (INVCOST=150, FIXOM=10, LIFE=25), fibre→`IGFFLATGL01`
  as proxy (no dedicated fibre-glass technology in JRC-EU-TIMES; flat glass
  uses the same continuous-melt furnace design). Costs inflated from base year
  2006 to 2019 via EU27 GDP deflator (factor ≈1.187) and converted from
  EUR/(t/year) to EUR/(t/h) by multiplying by 8760 h/year. Resulting values:
  capex ≈ 2,183,366 EUR/(t/h), opex_fixed ≈ 166,352 EUR/(t/h)/yr,
  opex_variable ≈ 59.34 EUR/t (2019 prices), lifetime = 28 yr
  (0.6×30 + 0.3×25 + 0.1×25, rounded). Derivation block written to README
  sheet of `process_parametrization.xlsx` by `write_sector_cost_params`.
- **`carbon_intensity_technology = 0.1`** (orange cell in
  `process_parametrization.xlsx`): raw-material decomposition emissions
  (AIDRES electricity-route direct emissions), manually entered.

## Ceramic

- Three Rehfeldt sub-processes (tiles/technical/houseware), weighted by their
  EU28+3 activity (`activity_weights(REHFELDT2017_CERAMIC)`); AIDRES does not
  cover ceramics, so energy and temperature distribution come entirely from
  Rehfeldt.
- **Demand and capacity (v4.3)** (`ceramic_demand_from_fec_df`,
  `get_ceramic_demand_from_fec`, `get_ceramic_capacity_from_fec`): The
  JRC-IDEES physical output row "Ceramics & other NMM (kt bricks eq.)" is
  dominated by brick production (~1–2 GJ/t), which is not covered by Rehfeldt
  2017 (tiles 5.46 GJ/t, technical 12.11 GJ/t, houseware 24.24 GJ/t;
  activity-weighted average ≈ 8.04 GJ/t). Applying Rehfeldt's specific energy
  to the full bricks-equivalent volume inflated ceramic demand by ~4×. From
  v4.3, demand and capacity are instead derived from the JRC-IDEES thermal FEC
  of the ceramic kiln/furnace processes in the NMM_fec sheet (the same rows
  used for fuel shares: "Ceramics: Thermal drying and sintering", "Ceramics:
  Steam drying and sintering", "Ceramics: Thermal kiln", "Ceramics: Thermal
  furnace"), divided by Rehfeldt's activity-weighted specific fuel energy:

    demand [t/hr] = Σ thermal_FEC_ktoe × 41 868 GJ/ktoe
                    ÷ (rehfeldt_fuel_GJ_t × 1 000 t/kt)
                    ÷ 8 760 h/yr

    capacity_existing [t/hr] = same kt/yr ÷ 8 000 h/yr

  This is self-consistent: the thermal FEC represents energy consumed by
  high-fired ceramic kilns, and dividing by Rehfeldt's specific energy returns
  the equivalent production volume for the same sub-processes. CH/NO/UK nodes
  (without JRC-IDEES coverage) retain the same population-based scaling as
  glass: CH ← AT, NO ← FI, UK ← DE × (69.9/83.5).
- **Cost parameters** set manually in `process_parametrization.xlsx` (orange
  cells). JRC-EU-TIMES only contains generic "Other Non-Metallic Minerals"
  process-heat boiler technologies (`INMPRCxxx`, `INMSTMxxx`), which represent
  heat-supply equipment costs, not ceramic kiln / product-line capex — no
  appropriate JRC-EU-TIMES proxy available. Values used (same as glass, see
  glass section for derivation): capex = 2,183,366.39 EUR/(t/h),
  opex_fixed = 166,351.72 EUR/(t/h)/yr, opex_variable = 59.34 EUR/t,
  lifetime = 20 yr.
- **`carbon_intensity_technology = 0`** (orange cell): set to zero; ceramic
  process emissions (calcination CO2) are not included in this parametrization.

## Paper

- Only the top 3 Rehfeldt sub-processes by EU28+3 activity (paper, recovered
  fibres, chemical pulp) are used, covering 95.2% of the sector total.
  Mechanical pulp is excluded (see `industry_heat_eu/data/rehfeldt2017.py` for
  the rationale).
- `carbon_intensity_technology = 0`: there is no significant inorganic
  process CO2 for paper, and black-liquor combustion CO2 is treated as
  biogenic (not counted).
- **Cost and lifetime parameters** (`capex_specific_conversion`,
  `opex_specific_fixed`, `opex_specific_variable`, `lifetime`): `opex_specific_fixed`,
  `opex_specific_variable`, and `lifetime` are taken from JRC-EU-TIMES 2019.11,
  activity-weighted across the three sub-processes using Rehfeldt2017 EU28+3
  activity shares (paper 56.1%, recovered_fibres 28.9%, chemical_pulp 15.0%):
  `IPPHIGQUA01` (INVCOST=2500, FIXOM=125, LIFE=25), `IPPLOWQUA01` (INVCOST=1100,
  FIXOM=53, LIFE=25), `IPPPUPCHE01` (INVCOST=1355, FIXOM=40, VAROM=28, LIFE=25).
  Same 2006→2019 deflator and ×8760 unit conversion as glass. JRC-derived values:
  opex_fixed ≈ 950,445 EUR/(t/h)/yr, opex_variable ≈ 4.99 EUR/t (2019 prices),
  lifetime = 25 yr (all three IPP processes have LIFE=25).
- **`capex_specific_conversion` (literature-based override)**: the JRC-EU-TIMES
  activity-weighted CAPEX of ~19,996,000 EUR/(t/h) (~2,283 EUR/(t/yr)) is replaced
  by **700 EUR/(t/yr) → 6,132,000 EUR/(t/h)**. The JRC figure represents a fully
  integrated greenfield pulp-and-paper mill and is inconsistent with the scope used
  for glass and other sectors (furnace/process core only), overstating CAPEX relative
  to real-world investment announcements. Literature benchmarks for recent European
  paper mill conversions:
  - Stora Enso Oulu, Finland (newsprint→packaging board, brownfield, 2026):
    ~EUR 1 billion / 750,000 t/yr → ~1,333 EUR/(t/yr)
  - Stora Enso Langerbrugge, Belgium (newsprint→testliner/recycled fluting,
    brownfield, 2022): ~EUR 400 million / 700,000 t/yr → ~571 EUR/(t/yr)
  - Kotkamills BM2, Finland (newsprint/magazine→folding boxboard, brownfield, 2016):
    ~EUR 170–180 million / 400,000 t/yr → ~425–450 EUR/(t/yr)
  All three are brownfield conversions; a greenfield premium is expected. 700 EUR/(t/yr)
  is adopted as a conservative lower bound consistent with this evidence base.
- Note: Kraft pulp calcination CO2 (lime kiln, CaCO3→CaO+CO2) is a real
  process emission not captured by EMISSIONS~INDCO2P in JRC-EU-TIMES and
  therefore not included here.

## Food

- All 5 Rehfeldt food sub-processes (dairy, meat_processing, brewing,
  bread_bakery, sugar) are used, weighted by their EU28+3 activity. The top 3
  by activity (dairy, meat, brewing) ALL have 100% of heat demand below 200
  degC; restricting to the top 3 would incorrectly set the high-temperature
  fuel demand to zero and ignore the medium-temperature demand from
  bread-baking and sugar.
- **Cost and lifetime parameters** (`capex_specific_conversion`,
  `opex_specific_fixed`, `opex_specific_variable`, `lifetime`): JRC-EU-TIMES
  has no product-level food processing technology (only generic "Other
  Industries" process-heat boilers `IOIPRCxxx`/`IOISTMxxx`). Food processing
  sits at the low end of industrial capital intensity, comparable to glass and
  lime production. Cost parameters are based on the average of a capital-light
  JRC-EU-TIMES cluster — Glass Hollow (`IGHHOLLOW01`, INVCOST=250,
  FIXOM=20), Quick Lime (`ILMQLMPRO01`, INVCOST=300, FIXOM=10), and Copper
  Finishing (`ICUFINPRO01`, INVCOST=500, FIXOM=25, LIFE=20) — rounded to:
  INVCOST=300 EUR/(t/yr), FIXOM=15 EUR/(t/yr)/yr, VAROM=0, LIFE=20 yr (all
  in 2006 base-year EUR). Same 2006→2019 deflator and ×8760 unit conversion
  as glass/paper. Resulting values: capex ≈ 3,119,095 EUR/(t/h),
  opex_fixed ≈ 155,955 EUR/(t/h)/yr, opex_variable = 0 EUR/t (2019 prices),
  lifetime = 20 yr. Written to `process_parametrization.xlsx` by
  `write_direct_cost_params`.
- **Capacity (`capacity_and_demand.food_capacity_existing_df`)**: IDEES does
  not give a tonnage for food production (only a production index), so each
  Rehfeldt food sub-sector's EU-wide `activity_Mt` is split across nodes by
  that node's share of FAOSTAT `year` production of a proxy item
  (`FOOD_PRODUCTION_ITEMS`: dairy -> "Milk, Total", meat_processing -> "Meat,
  Total", brewing -> "Beer of barley, malted", bread_bakery -> "Wheat",
  sugar -> "Raw cane or beet sugar (centrifugal only)").
- **Demand (`capacity_and_demand.food_demand_df`)**: the "food" carrier's
  demand represents total national demands. For each Rehfeldt food
  sub-sector, the FAOSTAT Food Balance Sheet "Feed" use of a proxy item
  (`FOOD_FEED_ITEMS`: dairy -> "Milk - Excluding Butter", meat_processing ->
  "Meat", brewing -> "Barley and products", bread_bakery -> "Wheat and
  products", sugar -> "Sugar beet") is summed across sub-sectors per node.

## Capacity / demand units and node coverage
(`src/industry_heat_eu/capacity_and_demand.py`)

- **`OPERATING_HOURS = 8000` h/year** is used for `capacity_existing`
  (kt/year -> tonproduct/h), matching the convention already used (?). 
- **`HOURS_PER_YEAR = 8760` h/year** is used for `demand` (kt/year or
  1000 t/year -> tonproduct/h), matching the convention observed in Crystal
  Ball's `set_carriers/clinker/demand.csv` (AT clinker demand 336.7 t/h x
  8760 h ~ 2.95 Mt/year).
- **`MODEL_NODES`**: the 28 Crystal Ball model nodes - EU27 minus Cyprus and
  Malta, plus Switzerland, Norway, the UK and the Netherlands.
- **`NODES_WITHOUT_IDEES = (CH, NO, UK)`**: JRC-IDEES-2023 only covers EU27
  countries, so these three nodes get `capacity_existing = demand = 0` for
  glass/ceramic from IDEES. FAOSTAT covers all 28 nodes, so food
  capacity/demand is non-zero for CH/NO/UK.
- **Paper demand/capacity for CH, NO, UK** (JRC BAT Paper 2014, Table 1.2):
  since IDEES does not cover these nodes, paper consumption data is taken
  from JRC BAT Paper 2014 (Table 1.2, "Consumption of paper per capita and
  by country in 2008", source: RISI 2009 / CEPI 2009). The 2008 national
  consumption values (in 1000 t/year) are used: CH = 1,397 kt, NO = 831 kt,
  UK = 11,443 kt. Note: this is *consumption* (production + imports −
  exports), not production — a different metric than the IDEES "Physical
  output" used for the EU27 nodes. Demand is converted via
  `kt × 1000 / 8760`; `capacity_existing` is set assuming demand equals
  existing capacity (`kt × 1000 / 8000`). Glass and ceramic remain at 0 for
  these three nodes (no equivalent non-IDEES source available).
- **Glass/ceramic demand for CH, NO, UK** (population-scaled from reference
  countries): since JRC-IDEES does not cover these nodes and no equivalent
  source is available, glass and ceramic demand is derived from reference
  countries with comparable population:
  - **CH** (9.1M) → uses **AT** (9.2M) values directly (nearly identical
    population, same values assumed).
  - **NO** (5.6M) → uses **FI** (5.6M) values directly (identical population).
  - **UK** (69.9M) → scaled from **DE** (83.5M) by population ratio
    69.9/83.5 ≈ 0.837.
  Both demand and `capacity_existing` are scaled using the same
  reference-country logic so that existing capacity covers demand and the
  optimizer does not need to build additional capacity.
- **NL food demand/capacity** (FAOSTAT area name fix): FAOSTAT lists the
  Netherlands as "Netherlands (Kingdom of the)". The `NODE_TO_AREA` mapping
  uses this full name so that NL food demand and capacity are read directly
  from the FAOSTAT data.
- **`industry_demand_df` (glass/ceramic/paper demand)**: national demand is
  approximated by national JRC-IDEES-2023 "Physical output (kt)" for the
  given year, i.e. national production is assumed to equal national
  consumption (net trade is not modelled).
- **`FOOD_PRODUCTION_ITEMS` / `FOOD_FEED_ITEMS` country mapping**
  (`faostat.NODE_TO_AREA`): FAOSTAT area names are mapped to the 28 model
  node ISO2 codes; this mapping has full coverage of `MODEL_NODES` (unlike
  the IDEES-based data).
- **FAOSTAT Food Balance Sheet duplicate rows**
  (`faostat.feed_by_node`): some items (e.g. "Milk - Excluding Butter")
  appear twice per area under different old/new FBS item codes with
  identical values; duplicates are dropped via `.drop_duplicates("Area")`.

## JRC-IDEES sheet reading
(`src/industry_heat_eu/jrc_idees.py`, `capacity_and_demand.section_by_label`)

- **`FIRST_YEAR = 2000`**: JRC-IDEES-2023 Industry sheets (including "_fec"
  sheets) have one column per year starting at year 2000 in column index 1
  (0-based); `year_column(year) = year - FIRST_YEAR + 1`.
- **`section_by_label`**: the "Installed capacity (kt production)" and
  "Physical output (kt)" sections of the NMM/PPA sheets share identical row
  labels and both run until the next "... (kt production)" section header
  (verified for the NMM and PPA sheets).

## Heat pump (industry) capacity data

- **`input_data/David2017/David2017_heat_pumps.csv`**: transcribed verbatim
  from the table in David et al. (2017), "Heat Roadmap Europe: Large-Scale
  Electric Heat Pumps in District Heating Systems" (Supplementary Material),
  which lists 94 large-scale heat pump installations in European district
  heating systems (output capacity, number of units, COP, source/supply
  temperatures, commissioning year). Row order, country/location grouping and
  values match the source table; column totals (1580.0 MW, 149 units) were
  checked against the table's own "Total" row and match exactly. Empty cells
  in the source table (missing COP, temperatures, commissioning year, etc.)
  are left empty in the CSV. 
- **`capacity_and_demand.heat_pump_capacity_existing_df`**: aggregates
  `David2017_heat_pumps.csv` into `capacity_existing.csv` for
  `heat_pump_industry` (`node, year_construction, capacity_existing`,
  unit GW, matching `heat_pump_industry/attributes.json`), one row per node:
  - **Country -> node** (`DAVID2017_COUNTRY_TO_NODE`): each David2017 country
    maps 1:1 to its `MODEL_NODES` ISO2 code (AT, CZ, DK, FI, FR, IT, NL, NO,
    SK, SE, CH).
  - **MW -> GW**: `output_capacity_MW / 1000`.
  - **Missing `est_year`**: the 6 plants (out of 94) without a commissioning
    year are assigned `year_construction = 1998`
    (`DAVID2017_DEFAULT_YEAR`), the median `est_year` of the other 88 plants
    (range 1981-2016).
  - All plants of a node are summed into a single row;
    `year_construction` is the capacity-weighted average of the plants'
    `year_construction`, rounded to the nearest year. Nodes with no
    David2017 plants get no row (`capacity_existing` defaults to 0 in
    `attributes.json`).

## Boiler (industry) capacity data
(`biomass_boiler_industry`, `natural_gas_boiler_industry`,
`electrode_boiler_industry`)

- **`capacity_and_demand.boiler_capacity_existing_df(sheet, year)`**: builds
  `capacity_existing.csv` for a `*_boiler_industry` technology
  (`node, year_construction, capacity_existing`, unit GW), one row per
  `MODEL_NODES` node, `year_construction = FEC_YEAR` (2023).
- **Source**: `input_data/Eurostat/Eurostat_EB_GWh.xlsx` (the file's "Unit of
  measure" column is "Gigawatt-hour", i.e. the data is in **GWh**), "Gross
  heat production" by fuel:
  - `biomass_boiler_capacity_existing_df`: "Primary solid biofuels"
    (Sheet 74) - heat produced from solid biomass specifically, not from
    biogases, liquid biofuels or "Bioenergy" overall, matching
    `biomass_boiler_industry`'s `biomass` input carrier.
  - `natural_gas_boiler_capacity_existing_df`: "Natural gas" (Sheet 72),
    matching `natural_gas_boiler_industry`'s `natural_gas` input carrier.
  - `electrode_boiler_capacity_existing_df`: "Electricity" (Sheet 83),
    matching `electrode_boiler_industry`'s `electricity` input carrier (see
    below for the heat-pump correction).
- **GWh -> GW**: `capacity_existing = heat_GWh / OPERATING_HOURS`. Since the
  reference and output carrier of all three boiler technologies is
  `heat_low_temp_industry`, Eurostat's heat *output* maps directly to
  `capacity_existing` (no `conversion_factor` applied).
- **Switzerland ("CH")** has no entry in this Eurostat extract and gets
  `capacity_existing = 0` for all three boilers (e-boiler, biomass boiler,
  NG boiler). This means CH has no existing heating technology capacity in
  the model — all heat supply must be built by the optimizer. This is a data
  gap, not a modeling choice; CH is not the only country with 0 values for
  individual boiler types, but it is the only country with 0 across all
  three heating technologies.
- **United Kingdom**: this extract has no 2023 (or later) value for the UK
  in any of the three sheets (Eurostat coverage ends after 2019
  post-Brexit); the latest available year (2019) is used instead (Natural
  gas: 16321.438 GWh, Primary solid biofuels: 1168.056 GWh, Electricity:
  0.0 GWh).
- **Electrode boiler / heat pump overlap**: Eurostat's "Gross heat
  production" of "Electricity" includes heat from electric heat pumps as
  well as resistance ("electrode") boilers. To avoid double-counting with
  `heat_pump_industry`'s `capacity_existing` (David2017, see above),
  `electrode_boiler_capacity_existing_df` subtracts each node's
  `heat_pump_capacity_existing_df` capacity from the Eurostat "Electricity"
  value. For most nodes with David2017 heat pump data, this subtraction is
  negative (the heat pump capacity exceeds Eurostat's "Electricity" gross
  heat production for that node) - in these cases a warning is issued and
  `capacity_existing` is set to 0 (run `python scripts/compute_params.py` to
  see the full list of affected nodes: AT, CH, CZ, FI, FR, IT, SE).
- Note: these Eurostat balances cover all heat production by fuel (e.g.
  district heating plants), not only industrial boilers, so
  `capacity_existing` is likely an overestimate of installed industrial
  boiler capacity for `biomass_boiler_industry` and
  `natural_gas_boiler_industry`.

## Heat pump COP parametrization (v4.5+)

Six industry heat pump variants are modelled — two per temperature level — distinguished
by their heat source temperature:

- **Waste-heat source** (`_waste_heat`): T_cold = 50°C (323.15 K).
  Represents waste heat recovery from industrial processes at 50°C
  (Bever2024, Agora_IGE2023: waste heat at 20–80°C, mid ≈ 50°C assumed).
- **Water source** (`_water`): T_cold = 15°C (288.15 K).
  Represents rivers, groundwater, or seawater at 15°C (Agora_IGE2023).
  Unconstrained — ambient water bodies are assumed practically unlimited.

**Method**: COP = 0.50 × COP_Carnot (Agora_IGE2023), where
COP_Carnot = T_hot / (T_hot − T_cold), with T_hot = midpoint of the supply
temperature range (sink) and T_cold = source temperature as above.

**Waste-heat source (T_cold = 50°C = 323.15 K):**

| HP variant | T_hot (mid) | COP_Carnot | COP (50%) | conv. factor (1/COP) |
|---|---|---|---|---|
| `heat_pump_industry_0_100_waste_heat`   | 75°C = 348.15 K | 13.926 | **6.963** | 0.1436 |
| `heat_pump_industry_100_150_waste_heat` | 125°C = 398.15 K | 5.309  | **2.654** | 0.3768 |
| `heat_pump_industry_150_200_waste_heat` | 175°C = 448.15 K | 3.585  | **1.793** | 0.5578 |

**Water source (T_cold = 15°C = 288.15 K):**

| HP variant | T_hot (mid) | COP_Carnot | COP (50%) | conv. factor (1/COP) |
|---|---|---|---|---|
| `heat_pump_industry_0_100_water`   | 75°C = 348.15 K | 5.803 | **2.901** | 0.3447 |
| `heat_pump_industry_100_150_water` | 125°C = 398.15 K | 3.620 | **1.810** | 0.5525 |
| `heat_pump_industry_150_200_water` | 175°C = 448.15 K | 2.801 | **1.400** | 0.7143 |

**Costs**: identical for both source types — same `heat_pump_industry` row from
`heat_tech_parametrization.xlsx` (assumption: cost data not yet differentiated
by source type).

**Existing capacity**: David2017 capacity is split by temperature level
(demand-weighted shares) and then divided equally (50/50) between the two source
variants at each level.

Implemented via `HP_COP_WASTE_HEAT` and `HP_COP_WATER` dicts in
`heat_tech_parametrization.py` and the `cop_override` parameter of
`HeatTechParametrizationDataset.get_conversion_factor`.

### Waste-heat HP capacity limit (v4.5+)

The waste-heat HP variants (`_waste_heat`) are physically constrained by the amount of
high-temperature (>200°C) process exhaust heat available in the co-located industrial plants.
This is implemented via `capacity_addition_max` (GW of heat output, per node).

**Waste-heat availability per sector** (in GW thermal, per node):

    WH[s, n] = demand[s, n]  [tonproduct/hr]  ×  cf_fuel[s]  [GW / (tonproduct/hr)]

where `cf_fuel[s]` is the high-temperature fraction of the sector's fuel demand
(i.e. `SectorParams.fuel_GJ_t / 3600`), derived from Rehfeldt2017 temperature distributions
weighted by sub-process activity:

| Sector | High-temp fraction (>200°C) | Ratio to low-temp demand |
|---|---|---|
| Glass | ~79% | ≈ 4× |
| Ceramic | ~65–82% (sub-process weighted) | ≈ 2–5× |
| Paper | ~0–7% | negligible |
| Food | ~0–5% (weighted avg.) | negligible |

**Distribution to temperature levels**: the waste heat from each sector is apportioned
to each temperature level (0–100, 100–150, 150–200°C) proportionally to that sector's
low-temp heat demand share at that level:

    share[s, level] = cf_heat[s, level] / Σ_l cf_heat[s, l]

**Capacity limit** (`capacity_addition_max`, in GW of heat output):

    capacity_addition_max[level, n] = Σ_s  WH[s, n] × share[s, level]

This sets the waste heat input (GW) as the capacity limit. The physically correct bound
on HP heat output is `WH × COP/(COP-1)` (1.17–2.26× larger, depending on temperature
level), so this assumption is conservative by up to a factor of ~2.3 at the 150–200°C level.

Implemented in `ProcessParametrizationDataset.get_waste_heat_capacity_limit()` and
called via `_set_capacity_addition_max()` in each `WasteHeat` HP class.

### Previous parametrization (v4.2–v4.4, now superseded)

Used a single HP per temperature level with T_cold = 20°C (293.15 K):

| HP variant | T_hot (mid) | COP_Carnot | COP (50%) |
|---|---|---|---|
| `heat_pump_industry_0_100` | 75°C | 6.330 | 3.165 |
| `heat_pump_industry_100_150` | 125°C | 3.792 | 1.896 |
| `heat_pump_industry_150_200` | 175°C | 2.891 | 1.446 |

## Heat technology temperature-level structure (v3.0+)

Heat supply is modeled with three temperature levels (`heat_industry_0_100`,
`heat_industry_100_150`, `heat_industry_150_200`) and an asymmetric structure
reflecting the thermodynamic advantage of heat pumps at low temperatures:

- **Heat pumps** are split into six variants — two per temperature level,
  distinguished by heat source: waste heat at 50°C (`_waste_heat`) and
  water at 15°C (`_water`). The waste-heat variant achieves a higher COP
  at each level because its source temperature is closer to the sink
  temperature, but its buildable capacity is limited by the high-temp
  process heat available in co-located glass and ceramic plants (see
  "Waste-heat HP capacity limit" below). The water-source HPs are unconstrained.
- **Boilers** (`biomass_boiler_industry`, `electrode_boiler_industry`,
  `natural_gas_boiler_industry`) produce only `heat_industry_150_200`.
  Their full `capacity_existing` is assigned (no temperature split).
- **Temperature conversion cascade** — two conversion technologies allow
  higher-temperature heat to supply lower-temperature demand:
  - `heat_industry_temp_conversion_150_100`: converts
    `heat_industry_150_200` → `heat_industry_100_150` (conversion factor
    1.0, lossless; placeholder, to be calibrated).
  - `heat_industry_temp_conversion_100_0`: converts
    `heat_industry_100_150` → `heat_industry_0_100` (conversion factor
    1.0, lossless; placeholder, to be calibrated).
  No capex or existing capacity — the optimizer can freely build these
  bridge technologies.

### Heat pump capacity split

Heat pump `capacity_existing` (from David2017) is allocated between
the three HP variants proportionally to the **demand-weighted temperature
share** across all four production sectors at the three temperature levels.

### Previous structure (v2.3)

In v2.3, heat supply used two temperature levels (`heat_industry_0_100`,
`heat_industry_100_200`). Heat pumps were split into two variants, boilers
produced `heat_industry_100_200` only, and a single temperature conversion
(`heat_industry_100_200` → `heat_industry_0_100`) allowed boiler heat to
supply low-temp demand.

### Previous structure (v2.2)

In v2.2, all four heat supply technologies (heat pumps + 3 boilers) were each
split into two variants (`_0_100` and `_100_200`), totaling 8 technologies.
Capacity was split by the same demand-weighted temperature share for all techs.

## Industry thermal energy storage (v4.0+)

Two thermal energy storage (TES) technologies are added for industry heat,
parametrized from Mayer et al. (2024), Table 3:

- **`industry_TES_water`** (water tank): stores heat at the
  `heat_industry_0_100` temperature level. Water tanks are the lowest-cost
  TES option; Mayer2024 reports zero investment cost and low fixed O&M.
- **`industry_TES_steam`** (steam accumulator): stores heat at the
  `heat_industry_100_150` temperature level.

### Parametrization (from Mayer2024 Table 3)

| Parameter                       | Water tank        | Steam accumulator |
|---------------------------------|-------------------|-------------------|
| Round-trip efficiency           | 0.97              | 0.97              |
| → `efficiency_charge`           | √0.97 ≈ 0.985    | √0.97 ≈ 0.985    |
| → `efficiency_discharge`        | √0.97 ≈ 0.985    | √0.97 ≈ 0.985    |
| Investment cost (source)        | 0 EUR/kWh         | 117 EUR/kWh       |
| → `capex_specific_storage_energy` | 0 EUR/MWh       | 117,000 EUR/MWh   |
| Fixed O&M cost (source)         | 0.17 EUR/kWh      | 4.7 EUR/kWh       |
| → `opex_specific_fixed_energy`  | 170 EUR/MWh       | 4,700 EUR/MWh     |
| Lifetime                        | 40 years          | 25 years          |

- **Efficiency split**: the round-trip efficiency from the source is split
  symmetrically between charge and discharge: `η_charge = η_discharge =
  √η_roundtrip`.
- **Unit conversion**: costs in the CSV are in EUR/kWh (energy capacity);
  these are converted to EUR/MWh (×1000) to match the ZEN-garden storage
  technology unit convention (`power_unit = MW`).
- **`capacity_existing`**: set to 0 (default). There is essentially no
  deployed industrial TES capacity in Europe at present.
- **Reference carriers**: each TES variant is assigned to one temperature
  level. Water tanks serve 0–100 °C and 100–150 °C; steam accumulators
  serve 100–150 °C and 150–200 °C:
  - `industry_TES_water_0_100` → `heat_industry_0_100`
  - `industry_TES_water_100_150` → `heat_industry_100_150`
  - `industry_TES_steam_100_150` → `heat_industry_100_150`
  - `industry_TES_steam_150_200` → `heat_industry_150_200`

### Energy-to-power ratio bounds (v4.6+)

| Technology | `energy_to_power_ratio_min` (h) | `energy_to_power_ratio_max` (h) |
|---|---|---|
| Water tank (0–100 °C, 100–150 °C) | 1 | 24 |
| Steam accumulator (100–150 °C, 150–200 °C) | 0.25 | 4 |

- **Water tanks** are sized for intraday heat buffering; a minimum of 1 h ensures the
  tank has meaningful thermal mass relative to its charging rate. The 24 h cap reflects
  that industrial water tanks are not seasonal stores.
- **Steam accumulators** are pressurised vessels with inherently short storage horizons
  (minutes to a few hours); 0.25–4 h covers the practical range from industrial practice.

## Industry demand-side management (v4.0+)

Four demand-side management (DSM) storage technologies allow the optimizer
to shift production in time for each industry product carrier:

- **`glass_DSM`** — reference carrier: `glass`
- **`ceramic_DSM`** — reference carrier: `ceramic`
- **`paper_DSM`** — reference carrier: `paper`
- **`food_DSM`** — reference carrier: `food`

### Parametrization

DSM storages are modeled as perfect storages with no losses:

| Parameter                         | Value                       |
|-----------------------------------|-----------------------------|
| `efficiency_charge`               | 1.0 (default)               |
| `efficiency_discharge`            | 1.0 (default)               |
| `self_discharge`                  | 0.0 (default)               |
| `capex_specific_storage_energy`   | 0.01 EUR/(tonproduct/hour·h)|
| `lifetime`                        | 50 years                    |

- **Minimal capex**: a small but non-zero energy capex of 0.01 prevents the
  optimizer from building DSM capacity without economic justification.
- **No losses**: efficiency = 1.0 and self_discharge = 0.0, representing
  an idealized ability to reschedule production within a planning period.
- **Power unit**: `tonproduct/hour`, matching the production technology
  capacity units.

### Energy-to-power ratio bounds (v4.6+)

| Technology | `energy_to_power_ratio_max` (h) | Rationale |
|---|---|---|
| `glass_DSM` | 168 (1 week) | Stable inventory; aligns with Mayer2024 tsc |
| `ceramic_DSM` | 168 (1 week) | Thermally stable product; Mayer2024 tsc |
| `paper_DSM` | 168 (1 week) | Stable inventory; Mayer2024 tsc |
| `food_DSM` | 48 (2 days) | Perishability limits storage horizon |

- `energy_to_power_ratio_min` is left at 0 (default) for all DSM techs — no minimum
  inventory depth is physically required.
- Values follow the storage capacity time intervals (tsc) from Mayer et al. (2024).

## Existing capacity spread over vintage cohorts (v4.4+)

From v4.4 onwards, `capacity_existing` for all production and heat supply technologies
is spread uniformly across `lifetime` vintage cohorts instead of assigning all observed
capacity to a single `year_construction`.

**Motivation**: assigning all capacity to one year means all existing stock retires
simultaneously at `year_construction + lifetime`, creating an artificial investment
cliff. Spreading over the full lifetime distributes retirement gradually, one cohort
per year, which better reflects a real capital stock that was accumulated over decades.

**Method** (per node, per technology):

    cap_per_vintage_year = total_capacity_existing / lifetime
    year_construction ∈ {reference_year − lifetime + 1, …, reference_year}

Each vintage cohort contributes `cap_per_vintage_year` to the total and retires
`lifetime` years after its construction year, so at the reference year the cumulative
existing capacity equals the observed total.

**Reference year** = `CAPACITY_YEAR = 2022` (unchanged).
**Lifetimes used** (from `SECTOR_LIFETIMES` / `BOILER_LIFETIMES` in `_industry_heat_utils.py`):

| Technology              | Lifetime (yr) | Source                                  |
|-------------------------|---------------|-----------------------------------------|
| glass_production        | 28            | JRC-EU-TIMES, activity-weighted         |
| ceramic_production      | 20            | Manual (see Ceramic section above)      |
| paper_production        | 25            | JRC-EU-TIMES                            |
| food_production         | 20            | JRC-EU-TIMES cluster average            |
| biomass_boiler_industry | 20            | Crystal Ball / heat_tech_parametrization.xlsx |
| natural_gas_boiler_industry | 21        | Crystal Ball / heat_tech_parametrization.xlsx |
| electrode_boiler_industry | 30          | Crystal Ball / heat_tech_parametrization.xlsx |

Heat pumps retain their actual commissioning-year structure (David2017 data) and are
not affected by this change. TES and DSM technologies have `capacity_existing = 0`
and are also unaffected.

## Product carrier demand = capacity_existing (v4.2+)

From v4.2 onwards, the demand for all four product carriers (glass, ceramic,
paper, food) is set equal to the corresponding `capacity_existing` value,
rather than the previously used physical-output or feed-based proxies.
This change is implemented by patching the carrier `_set_demand` methods in
`my_scripts/my_model_v4_2.py` via `JrcIdeesIndustryDataset.get_demand_as_capacity_existing`
and `FaostatFoodDataset.get_food_demand_as_capacity_existing`.

**Rationale**: The mismatch between capacity and demand in v4.1 arose from
two sources: (1) `capacity_existing` used JRC-IDEES "Installed capacity (kt)"
divided by 8000 operating hours, while demand used "Physical output (kt)"
divided by 8760 total hours — effectively encoding a sector-specific
utilization rate that is better left to the optimizer; and (2) for food,
capacity was derived from FAOSTAT production activity while demand used
FAOSTAT feed quantities — two fundamentally different data series. Setting
demand = capacity_existing removes this inconsistency and ensures the
optimizer starts from a state where existing capacity exactly meets demand,
with no implicit overcapacity or underutilization assumption.

**Unit**: `tonproduct/hour` (unchanged).

**Per-sector detail**:

- **Glass, ceramic** (JRC-IDEES nodes): demand = installed capacity (kt) × 1000
  / 8000 h. CH/NO/UK nodes retain the same population-proxy logic as
  `capacity_existing` (AT values for CH, FI values for NO, DE×69.9/83.5 for UK).
- **Paper** (JRC-IDEES nodes): demand = installed capacity (kt) × 1000 / 8000 h.
  CH/NO/UK nodes use JRC-BAT 2014 consumption (kt) × 1000 / 8000 h (same as
  `capacity_existing`; previously demand used /8760 h for these nodes).
- **Food**: demand = FAOSTAT production-weighted Rehfeldt activity (Mt) × 1e6
  / 8000 h — identical to `food_capacity_existing_df`. The previous food demand
  (FAOSTAT feed quantities / 8760 h) is no longer used.

## Code restructuring (v5.0)

In v5.0, the industry heat codebase was restructured to follow the
zen-creator template pattern consistently across all element types:

- **Carriers** (`Glass`, `Ceramic`, `Paper`, `Food`, `HeatIndustry0100`,
  `HeatIndustry100150`, `HeatIndustry150200`) were moved from
  `zen_creator/elements/industry_heat/carriers.py` to
  `zen_creator/elements/carriers/industry_carriers.py`.
- **Production technologies** (`GlassProduction`, `CeramicProduction`,
  `PaperProduction`, `FoodProduction`) were moved from
  `zen_creator/elements/industry_heat/production_techs.py` to
  `zen_creator/elements/conversion_technologies/industry_production.py`.
- **Heat supply technologies** (6 heat pumps, 3 boilers, 2 temperature
  conversions) were moved from
  `zen_creator/elements/industry_heat/heat_techs.py` to
  `zen_creator/elements/conversion_technologies/industry_heat_supply.py`.
- **Storage technologies** (`IndustryTESWater`, `IndustryTESSteam`) remain
  in `zen_creator/elements/storage_technologies/industry_TES.py` (added in
  v4.0).

All data processing logic previously in `zen_creator/industry_heat_eu/` was
absorbed into Dataset classes under `zen_creator/datasets/datasets/`:

- `ProcessParametrizationDataset` — sector parameters, conversion factors,
  fuel shares, and cost data (from `process_parametrization.xlsx`,
  Rehfeldt2017, AIDRES2023, Wolf2017, JRC-EU-TIMES, and JRC-IDEES FEC).
- `HeatTechParametrizationDataset` — heat technology parameters (from
  `heat_tech_parametrization.xlsx`).
- `IndustryCarrierDataset` — carrier attributes (from
  `industry_carriers.xlsx`).
- `JrcIdeesIndustryDataset` — industry capacity and demand (from
  JRC-IDEES-2023).
- `FaostatFoodDataset` — food capacity and demand (from FAOSTAT).
- `EurostatBoilerDataset` — boiler capacity (from Eurostat).

The `IndustryHeat` sector class was moved from
`zen_creator/elements/industry_heat/sector.py` to
`zen_creator/sectors/industry_heat.py`. The legacy
`zen_creator/industry_heat_eu/` module and `scripts/compute_params.py` were
deleted — their logic now lives entirely within the Dataset classes.

Element classes no longer use `apply_attrs_dict()` in their constructors.
Instead, all attributes are set through `_set_<attribute>()` methods that
delegate to the appropriate Dataset's `get_<attribute>()` method, following
the zen-creator template pattern. This change is structural only — the
computed parameter values and model output are unchanged.
