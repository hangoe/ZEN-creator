# Assumptions made in the code

This file lists assumptions made in `zen_creator/` when deriving parameters for the
industry conversion technologies and carriers (glass, ceramic, paper, food) and the
shared `heat_industry_*` carriers. It does not cover assumptions in the input Excel
files (`process_parametrization.xlsx`, `industry_carriers.xlsx`,
`heat_tech_parametrization.xlsx`) — those document their own sources in their
`source`/`comment` columns. This file describes only the current version's assumptions,
not the history of how they were derived.

## General

- **Temperature-level heat split**: each sector's fuel heat demand is split into three
  carriers using the Rehfeldt temperature bins: `<100°C` → `heat_industry_0_100`,
  `100–150°C` → `heat_industry_100_150`, `150–200°C` → `heat_industry_150_200`, and the
  remaining bins (`200-500`, `500-1000`, `>1000`) stay as high-temperature `fuel` input
  to the production technology. The optimizer can then choose the cheapest supply
  technology per temperature level independently. Electricity is not split.
- **GJ/t -> GW/(tonproduct/h) conversion**: conversion factors are computed as
  `energy_GJ_t / 3600`, since 1 tonproduct/h x 1 GJ/t = 1 GJ/h = 1/3600 GW.
- **CAPEX and other table-driven defaults**: each new technology is built with a
  placeholder `capex_specific_conversion = 1.0 EUR/(tonproduct/h)`, then overwritten
  (along with `opex_specific_fixed`, `max_diffusion_rate`, ...) with the values from
  `process_parametrization.xlsx`.
- **Fuel mix shares for X_production**: each `X_production` technology takes its
  high-temperature fuel demand (`cf_fuel`) as a mix of primary energy carriers
  (`natural_gas`, `hard_coal`, `biomass`), split according to the sector's
  JRC-IDEES-2023 EU27 2023 thermal FEC shares.
- **Fuel mix carrier cutoff**: of the JRC-IDEES thermal-FEC carriers, only natural gas,
  solid fuels (-> `hard_coal`) and biomass have a corresponding Crystal Ball carrier.
  All others (fuel oil, LPG, diesel, other liquids, derived/refinery gases, distributed
  steam) are excluded, either because they are below a 10% cutoff, or — for "Other
  liquids" and "Distributed steam" specifically — because no Crystal Ball carrier
  currently corresponds to them even where their share exceeds 10% (e.g. ceramics
  "Other liquids" ~15% of 2023 thermal FEC, paper "Distributed steam" ~8%). The
  remaining carriers are renormalised to sum to 1.

## Glass

- Three AIDRES sub-processes (container/flat/fibre glass), weighted by the AIDRES EU
  production mix (60/30/10%).
- Energy (fuel + electricity) taken from the AIDRES natural-gas-reference route
  (`AIDRES2023_GLASS`, key `ng_GJ_t`).
- Temperature distribution taken from Rehfeldt for the same three sub-processes,
  weighted with the same AIDRES 60/30/10 shares for consistency with the AIDRES energy
  data.
- Process (raw-material decomposition) emissions estimated as the AIDRES
  electricity-route direct emissions (`emit_elec`): the electricity route has zero
  combustion emissions, so its residual direct emissions are assumed to be entirely
  raw-material decomposition.
- **Cost and lifetime parameters** (`capex_specific_conversion`, `opex_specific_fixed`,
  `opex_specific_variable`, `lifetime`) from JRC-EU-TIMES 2019.11
  (`SUBRES_10_TECHS_CHP_SUP_IND.xls`, IND sheet), activity-weighted across the three
  sub-processes using the same AIDRES 60/30/10 shares: container→`IGHHOLLOW01`
  (INVCOST=250, FIXOM=20, LIFE=30), flat→`IGFFLATGL01` (INVCOST=150, FIXOM=10, LIFE=25),
  fibre→`IGFFLATGL01` as proxy (no dedicated fibre-glass technology in JRC-EU-TIMES;
  flat glass uses the same continuous-melt furnace design). Costs inflated from base
  year 2006 to 2019 via EU27 GDP deflator (factor ≈1.187) and converted from
  EUR/(t/year) to EUR/(t/h) by multiplying by 8760 h/year. Resulting values:
  capex ≈ 2,183,366 EUR/(t/h), opex_fixed ≈ 166,352 EUR/(t/h)/yr,
  opex_variable ≈ 59.34 EUR/t (2019 prices), lifetime = 28 yr
  (0.6×30 + 0.3×25 + 0.1×25, rounded).
- **`carbon_intensity_technology = 0.1`**: raw-material decomposition emissions
  (AIDRES electricity-route direct emissions), manually entered.

## Ceramic

- Three Rehfeldt sub-processes (tiles/technical/houseware), weighted by their EU28+3
  activity; AIDRES does not cover ceramics, so energy and temperature distribution come
  entirely from Rehfeldt.
- **Demand and capacity**: the JRC-IDEES physical output row "Ceramics & other NMM (kt
  bricks eq.)" is dominated by brick production (~1–2 GJ/t), which is not covered by
  Rehfeldt2017 (tiles 5.46 GJ/t, technical 12.11 GJ/t, houseware 24.24 GJ/t;
  activity-weighted average ≈ 8.04 GJ/t) — applying Rehfeldt's specific energy to the
  full bricks-equivalent volume would inflate ceramic demand by ~4×. Demand and
  capacity are instead derived from the JRC-IDEES thermal FEC of the ceramic
  kiln/furnace processes in the NMM_fec sheet (the same rows used for fuel shares:
  "Ceramics: Thermal drying and sintering", "Ceramics: Steam drying and sintering",
  "Ceramics: Thermal kiln", "Ceramics: Thermal furnace"), divided by Rehfeldt's
  activity-weighted specific fuel energy:

        capacity_existing [t/hr] = Σ thermal_FEC_ktoe × 41 868 GJ/ktoe
                                   ÷ (rehfeldt_fuel_GJ_t × 1 000 t/kt)
                                   ÷ 8 000 h/yr

        demand [t/hr] = capacity_existing

  This is self-consistent: the thermal FEC represents energy consumed by high-fired
  ceramic kilns, and dividing by Rehfeldt's specific energy returns the equivalent
  production volume for the same sub-processes. As with glass, paper and food, demand
  is set exactly equal to `capacity_existing` (see "Product carrier demand =
  capacity_existing" below). CH/NO/UK nodes (without JRC-IDEES coverage) retain the
  same population-based scaling as glass: CH ← AT, NO ← FI, UK ← DE × (69.9/83.5).
- **Waste-heat-capacity-limit and heat-pump-capacity-split inputs** (`ceramic` demand
  volume used in `ProcessParametrizationDataset.get_waste_heat_capacity_limit()` and
  `get_heat_capacity_split()`) use this same FEC-derived demand series — not the plain
  JRC-IDEES physical-output figure (`industry_demand_df("ceramic", ...)`), which is
  ~3.5–6.4× higher for the reason above and would otherwise substantially overstate
  ceramic's contribution to those calculations.
- **Cost parameters** set manually in `process_parametrization.xlsx`. JRC-EU-TIMES only
  contains generic "Other Non-Metallic Minerals" process-heat boiler technologies
  (`INMPRCxxx`, `INMSTMxxx`), which represent heat-supply equipment costs, not ceramic
  kiln / product-line capex — no appropriate JRC-EU-TIMES proxy available. Values used
  (same as glass, see glass section for derivation): capex = 2,183,366.39 EUR/(t/h),
  opex_fixed = 166,351.72 EUR/(t/h)/yr, opex_variable = 59.34 EUR/t, lifetime = 20 yr.
- **`carbon_intensity_technology = 0`**: ceramic process emissions (calcination CO2)
  are not included in this parametrization.

## Paper

- Only the top 3 Rehfeldt sub-processes by EU28+3 activity (paper, recovered fibres,
  chemical pulp) are used, covering 95.2% of the sector total. Mechanical pulp is
  excluded.
- `carbon_intensity_technology = 0`: there is no significant inorganic process CO2 for
  paper, and black-liquor combustion CO2 is treated as biogenic (not counted).
- **Cost and lifetime parameters**: `opex_specific_fixed`, `opex_specific_variable`,
  and `lifetime` are taken from JRC-EU-TIMES 2019.11, activity-weighted across the
  three sub-processes using Rehfeldt2017 EU28+3 activity shares (paper 56.1%,
  recovered_fibres 28.9%, chemical_pulp 15.0%): `IPPHIGQUA01` (INVCOST=2500, FIXOM=125,
  LIFE=25), `IPPLOWQUA01` (INVCOST=1100, FIXOM=53, LIFE=25), `IPPPUPCHE01`
  (INVCOST=1355, FIXOM=40, VAROM=28, LIFE=25). Same 2006→2019 deflator and ×8760 unit
  conversion as glass. JRC-derived values: opex_fixed ≈ 950,445 EUR/(t/h)/yr,
  opex_variable ≈ 4.99 EUR/t (2019 prices), lifetime = 25 yr.
- **`capex_specific_conversion` (literature-based override)**: the JRC-EU-TIMES
  activity-weighted CAPEX of ~19,996,000 EUR/(t/h) (~2,283 EUR/(t/yr)) represents a
  fully integrated greenfield pulp-and-paper mill and is inconsistent with the scope
  used for glass and other sectors (furnace/process core only), overstating CAPEX
  relative to real-world investment announcements. It is replaced by
  **700 EUR/(t/yr) → 6,132,000 EUR/(t/h)**, adopted as a conservative lower bound based
  on literature benchmarks for recent European paper mill conversions:
  - Stora Enso Oulu, Finland (newsprint→packaging board, brownfield, 2026):
    ~EUR 1 billion / 750,000 t/yr → ~1,333 EUR/(t/yr)
  - Stora Enso Langerbrugge, Belgium (newsprint→testliner/recycled fluting,
    brownfield, 2022): ~EUR 400 million / 700,000 t/yr → ~571 EUR/(t/yr)
  - Kotkamills BM2, Finland (newsprint/magazine→folding boxboard, brownfield, 2016):
    ~EUR 170–180 million / 400,000 t/yr → ~425–450 EUR/(t/yr)

  All three are brownfield conversions; a greenfield premium is expected.
- Note: Kraft pulp calcination CO2 (lime kiln, CaCO3→CaO+CO2) is a real process
  emission not captured by EMISSIONS~INDCO2P in JRC-EU-TIMES and therefore not
  included here.

## Food

- All 5 Rehfeldt food sub-processes (dairy, meat_processing, brewing, bread_bakery,
  sugar) are used, weighted by their EU28+3 activity. The top 3 by activity (dairy,
  meat, brewing) ALL have 100% of heat demand below 200°C; restricting to the top 3
  would incorrectly set the high-temperature fuel demand to zero and ignore the
  medium-temperature demand from bread-baking and sugar.
- **Cost and lifetime parameters**: JRC-EU-TIMES has no product-level food processing
  technology (only generic "Other Industries" process-heat boilers
  `IOIPRCxxx`/`IOISTMxxx`). Food processing sits at the low end of industrial capital
  intensity, comparable to glass and lime production. Cost parameters are based on the
  average of a capital-light JRC-EU-TIMES cluster — Glass Hollow (`IGHHOLLOW01`,
  INVCOST=250, FIXOM=20), Quick Lime (`ILMQLMPRO01`, INVCOST=300, FIXOM=10), and Copper
  Finishing (`ICUFINPRO01`, INVCOST=500, FIXOM=25, LIFE=20) — rounded to: INVCOST=300
  EUR/(t/yr), FIXOM=15 EUR/(t/yr)/yr, VAROM=0, LIFE=20 yr (all in 2006 base-year EUR).
  Same 2006→2019 deflator and ×8760 unit conversion as glass/paper. Resulting values:
  capex ≈ 3,119,095 EUR/(t/h), opex_fixed ≈ 155,955 EUR/(t/h)/yr, opex_variable = 0
  EUR/t (2019 prices), lifetime = 20 yr.
- **Capacity and demand**: IDEES does not give a tonnage for food production (only a
  production index), so each Rehfeldt food sub-sector's EU-wide `activity_Mt` is split
  across nodes by that node's share of FAOSTAT **Production** of a proxy item
  (`FOOD_PRODUCTION_ITEMS`: dairy -> "Milk, Total", meat_processing -> "Meat, Total",
  brewing -> "Beer of barley, malted", bread_bakery -> "Wheat", sugar -> "Raw cane or
  beet sugar (centrifugal only)"). Food carrier demand is set equal to this
  `capacity_existing` value (see "Product carrier demand = capacity_existing" below).
  This same production-based figure is also used as food's demand contribution to
  `get_waste_heat_capacity_limit()`, `get_heat_capacity_split()`, and
  `total_industry_heat_demand_gw()` (used for boiler capacity sizing), for consistency
  with the food carrier's own demand.

## Capacity / demand units and node coverage

- **`OPERATING_HOURS = 8000` h/year** is used for `capacity_existing`
  (kt/year -> tonproduct/h).
- **`HOURS_PER_YEAR = 8760` h/year** is used for `demand` (kt/year or 1000 t/year ->
  tonproduct/h).
- **`MODEL_NODES`**: the 28 Crystal Ball model nodes — EU27 minus Cyprus and Malta,
  plus Switzerland, Norway and the UK.
- **`NODES_WITHOUT_IDEES = (CH, NO, UK)`**: JRC-IDEES-2023 only covers EU27 countries,
  so these three nodes get `capacity_existing = demand = 0` for glass/ceramic from
  IDEES. FAOSTAT covers all 28 nodes, so food capacity/demand is non-zero for CH/NO/UK.
- **Paper demand/capacity for CH, NO, UK** (JRC BAT Paper 2014, Table 1.2): since IDEES
  does not cover these nodes, paper consumption data is taken from JRC BAT Paper 2014
  (Table 1.2, "Consumption of paper per capita and by country in 2008", source: RISI
  2009 / CEPI 2009). The 2008 national consumption values (in 1000 t/year) are used:
  CH = 1,397 kt, NO = 831 kt, UK = 11,443 kt. Note: this is *consumption* (production +
  imports − exports), not production — a different metric than the IDEES "Physical
  output" used for the EU27 nodes. `capacity_existing` and demand are both converted
  via `kt × 1000 / 8000` (demand equals `capacity_existing`, see below). Glass and
  ceramic remain at 0 for these three nodes (no equivalent non-IDEES source available).
- **Glass/ceramic demand for CH, NO, UK** (population-scaled from reference
  countries): since JRC-IDEES does not cover these nodes and no equivalent source is
  available, glass and ceramic demand is derived from reference countries with
  comparable population:
  - **CH** (9.1M) → uses **AT** (9.2M) values directly (nearly identical population,
    same values assumed).
  - **NO** (5.6M) → uses **FI** (5.6M) values directly (identical population).
  - **UK** (69.9M) → scaled from **DE** (83.5M) by population ratio 69.9/83.5 ≈ 0.837.

  Both demand and `capacity_existing` are scaled using the same reference-country logic
  so that existing capacity covers demand and the optimizer does not need to build
  additional capacity.
- **NL food demand/capacity** (FAOSTAT area name fix): FAOSTAT lists the Netherlands as
  "Netherlands (Kingdom of the)". The `NODE_TO_AREA` mapping uses this full name so
  that NL food demand and capacity are read directly from the FAOSTAT data.
- **`industry_demand_df` (glass/paper demand)**: national demand is approximated by
  national JRC-IDEES-2023 "Physical output (kt)" for the given year, i.e. national
  production is assumed to equal national consumption (net trade is not modelled).
  Ceramic uses the FEC-derived demand described above instead.
- **`FOOD_PRODUCTION_ITEMS` country mapping** (`faostat.NODE_TO_AREA`): FAOSTAT area
  names are mapped to the 28 model node ISO2 codes; this mapping has full coverage of
  `MODEL_NODES` (unlike the IDEES-based data).

## JRC-IDEES sheet reading

- **`FIRST_YEAR = 2000`**: JRC-IDEES-2023 Industry sheets (including "_fec" sheets)
  have one column per year starting at year 2000 in column index 1 (0-based);
  `year_column(year) = year - FIRST_YEAR + 1`.
- **`section_by_label`**: the "Installed capacity (kt production)" and "Physical
  output (kt)" sections of the NMM/PPA sheets share identical row labels and both run
  until the next "... (kt production)" section header (verified for the NMM and PPA
  sheets).

## Heat pump (industry) capacity

`capacity_existing = 0` for `heat_pump_industry` at every node, for all six
waste-heat/water × temperature-level variants — the optimizer must build all heat pump
capacity from scratch. `input_data/David2017/David2017_heat_pumps.csv` (94 large-scale
European heat pump installations, transcribed from David et al. 2017) exists in the
input data but is currently not used to compute any capacity value.

## Boiler (industry) capacity

(`biomass_boiler_industry`, `natural_gas_boiler_industry`, `electrode_boiler_industry`)

Each boiler technology's `capacity_existing` (GW, one row per node,
`year_construction = FEC_YEAR = 2023`) is computed in two steps:

1. **Fuel-mix shares per node**, from `input_data/Eurostat/Eurostat_EB_GWh.xlsx`
   "Gross heat production": "Primary solid biofuels" (Sheet 74, biomass), "Natural
   gas" (Sheet 72), "Electricity" (Sheet 83, electrode). Each is converted to GW via
   `/ OPERATING_HOURS`, and the three are normalized to shares
   (`share_bio + share_ng + share_elec = 1`). If a node has no Eurostat entry, it
   falls back to 100% natural gas — except Switzerland, which uses Austria's
   fuel-mix shares (see below).
2. **Total boiler capacity per node** = `total_industry_heat_demand_gw(node)` (summed
   heat-carrier demand across glass/ceramic/paper/food, all 3 temperature levels) ×
   that node's fuel-mix share. This sizes total existing boiler capacity to match
   modeled industry heat demand rather than reading an independent absolute value from
   Eurostat, ensuring enough boiler capacity exists to meet demand at every temperature
   level.

- **Switzerland ("CH")** has no entry in the Eurostat extract, so it falls back to
  Austria's fuel-mix shares instead of the generic 100%-natural-gas default —
  Austria is the closest neighboring energy system among the covered nodes, and
  unlike most of Europe it is not dominated by natural gas, so 100% NG was a poor
  proxy. Austria 2023 gross heat production: natural gas 6581.12 GWh, primary solid
  biofuels 11208.557 GWh, electricity 3.398 GWh, giving shares of
  biomass ≈ 63.0%, natural gas ≈ 37.0%, electrode ≈ 0.02%. These shares are applied
  to Switzerland's own modeled heat demand (`total_industry_heat_demand_gw("CH")`)
  to split its `capacity_existing` across the three boiler technologies.
- **United Kingdom**: the Eurostat extract has no 2023 (or later) value for the UK in
  any of the three sheets (coverage ends after 2019 post-Brexit); the latest available
  year (2019) is used instead for the fuel-mix shares (Natural gas: 16321.438 GWh,
  Primary solid biofuels: 1168.056 GWh, Electricity: 0.0 GWh).

## Heat pump COP parametrization

Six industry heat pump variants are modelled — two per temperature level — distinguished
by their heat source temperature:

- **Waste-heat source** (`_waste_heat`): T_cold = 50°C (323.15 K). Represents waste
  heat recovery from industrial processes at 50°C (Bever2024, Agora_IGE2023: waste
  heat at 20–80°C, mid ≈ 50°C assumed).
- **Water source** (`_water`): T_cold = 15°C (288.15 K). Represents rivers, groundwater,
  or seawater at 15°C (Agora_IGE2023). Unconstrained — ambient water bodies are assumed
  practically unlimited.

**Method**: COP = 0.50 × COP_Carnot (Agora_IGE2023), where
COP_Carnot = T_hot / (T_hot − T_cold), with T_hot = midpoint of the supply temperature
range (sink) and T_cold = source temperature as above.

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
`heat_tech_parametrization.xlsx` (cost data not differentiated by source type).

**Existing capacity**: `capacity_existing` is 0 for all six variants (see "Heat pump
(industry) capacity" above), so `get_heat_capacity_split()`'s demand-weighted
temperature-level split and the 50/50 division between source variants currently have
no effect on model output — 0 × any share is still 0.

Implemented via `HP_COP_WASTE_HEAT` and `HP_COP_WATER` dicts in
`heat_tech_parametrization.py` and the `cop_override` parameter of
`HeatTechParametrizationDataset.get_conversion_factor`.

## Waste-heat HP capacity limit

The waste-heat HP variants (`_waste_heat`) are physically constrained by the amount of
high-temperature (>200°C) process exhaust heat available in the co-located industrial
plants. This is implemented via `capacity_limit` (GW of heat output, per node).

**Waste-heat availability per sector** (in GW thermal, per node):

    WH[s, n] = demand[s, n]  [tonproduct/hr]  ×  cf_fuel[s]  [GW / (tonproduct/hr)]

where `cf_fuel[s]` is the high-temperature fraction of the sector's fuel demand
(i.e. `SectorParams.fuel_GJ_t / 3600`), derived from Rehfeldt2017 temperature
distributions weighted by sub-process activity:

| Sector | High-temp fraction (>200°C) | Ratio to low-temp demand |
|---|---|---|
| Glass | ~79% | ≈ 4× |
| Ceramic | ~65–82% (sub-process weighted) | ≈ 2–5× |
| Paper | ~0–7% | negligible |
| Food | ~0–5% (weighted avg.) | negligible |

`demand[s, n]` for glass and paper comes from `industry_demand_df()`. For ceramic it
comes from the FEC-derived series (see "Ceramic" above, not the ~3.5–6.4× higher plain
physical-output figure). For food it comes from `food_capacity_existing_df()` (FAOSTAT
production data), matching the food carrier's own demand.

**Distribution to temperature levels**: the waste heat from each sector is apportioned
to each temperature level (0–100, 100–150, 150–200°C) proportionally to that sector's
low-temp heat demand share at that level:

    share[s, level] = cf_heat[s, level] / Σ_l cf_heat[s, l]

**Capacity limit** (`capacity_limit`, in GW of heat output):

    capacity_limit[level, n] = Σ_s  WH[s, n] × share[s, level]

This sets the waste heat input (GW) as the capacity limit. The physically correct
bound on HP heat output is `WH × COP/(COP-1)` (1.17–2.26× larger, depending on
temperature level), so this remains a conservative bound.

Implemented in `ProcessParametrizationDataset.get_waste_heat_capacity_limit()` and
called via `_hp_waste_heat_limit()` in each `WasteHeat` HP class.

### Sanity check against Mathiesen2026

The Rehfeldt2017-based `WH[s, n]` estimate above was cross-checked against
`Mathiesen2026` (Heat Roadmap Europe, Ch. 2 "Waste heat potential and data for EU"),
which reports actual industrial waste-heat quantities by country and sub-sector
(Tables 9–12), independent of the Rehfeldt2017 fuel-demand method used here.

Mathiesen2026 splits industrial waste heat into three fixed source-temperature tiers
— 25°C (low), 55°C (medium), 95°C (high) — rather than a single value; this model's
single flat 50°C source-temperature assumption sits close to the "medium" tier.
Summing all three tiers per country and restricting to the sub-sectors comparable to
this model's scope ("Non-metallic minerals" ≈ glass + ceramic, "Paper and pulp" ≈
paper; food/beverage is not broken out separately in Mathiesen2026 and could not be
checked) gives, for the five countries with sub-sector detail (base year 2015, TJ →
average GW via `/(3.6 × 8760)`):

| Node | `WH[s, n]` proxy (GW) | Mathiesen2026 glass+ceramic+paper (GW) | Ratio |
|---|---|---|---|
| DE | 3.45 | 3.87 | 0.89× |
| FR | 1.82 | 2.42 | 0.75× |
| HU | 0.18 | 0.26 | 0.68× |
| PL | 1.36 | 1.58 | 0.86× |
| ES | 2.10 | 2.38 | 0.88× |

The proxy is within 0.68–0.89× (avg. ~0.81×) of Mathiesen2026's reported waste heat
across all five countries, and the proxy total above still excludes food (which
Mathiesen2026 could not validate). This is treated as a plausibility check, not a
calibration target — no correction factor is applied to `WH[s, n]`.

## Heat technology temperature-level structure

Heat supply is modeled with three temperature levels (`heat_industry_0_100`,
`heat_industry_100_150`, `heat_industry_150_200`) and an asymmetric structure
reflecting the thermodynamic advantage of heat pumps at low temperatures:

- **Heat pumps** are split into six variants — two per temperature level,
  distinguished by heat source: waste heat at 50°C (`_waste_heat`) and water at 15°C
  (`_water`). The waste-heat variant achieves a higher COP at each level because its
  source temperature is closer to the sink temperature, but its buildable capacity is
  limited by the high-temp process heat available in co-located plants (see
  "Waste-heat HP capacity limit" above). The water-source HPs are unconstrained.
- **Boilers** (`biomass_boiler_industry`, `electrode_boiler_industry`,
  `natural_gas_boiler_industry`) produce only `heat_industry_150_200`. Their full
  `capacity_existing` is assigned (no temperature split).
- **Temperature conversion cascade** — two conversion technologies allow
  higher-temperature heat to supply lower-temperature demand:
  - `heat_industry_temp_conversion_150_100`: converts `heat_industry_150_200` →
    `heat_industry_100_150` (conversion factor 1.0, lossless).
  - `heat_industry_temp_conversion_100_0`: converts `heat_industry_100_150` →
    `heat_industry_0_100` (conversion factor 1.0, lossless).

  No capex or existing capacity — the optimizer can freely build these bridge
  technologies.

## Case study scenarios

`my_scripts/my_model.py` generates the case-study scenarios from the SI (see
`MT_report_HG/Sections/03_SI.tex`, table:SIScenarios) as combinations of sectors:
`industry_heat` (+`industry_low_temp_heat`) for heat supply and production,
`industry_tes`/`industry_dsm_optimistic` for flexibility. No-flexibility, DSM-only and
TES-only simply omit the corresponding sector(s).

- **Single temperature level** (`_single_temp`) omits `industry_low_temp_heat`, so
  `heat_industry_0_100`/`heat_industry_100_150` demand is served only via the
  temperature-downgrade cascade from `heat_industry_150_200`, not by dedicated
  low/mid-band heat pumps. This means all industrial heat-pump electricity use is
  costed at the 150–200°C band's (lower) COP, even for demand that in reality would be
  met at a lower, more efficient temperature level — the COP penalty of always
  producing at the highest level is intentionally not avoided, so this scenario is a
  worst-case bound on heat-pump electricity demand relative to the temperature-resolved
  scenarios.
- **DSM pessimistic** (`_DSM_pessimistic`) reruns the full-flexibility case with
  `industry_dsm_pessimistic` instead of `industry_dsm_optimistic`, i.e. every DSM
  technology uses the pessimistic demand-shiftability category from
  `input_data/DSM_parametrization/DSM_literature_review.md` instead of the optimistic
  one (see "Industry demand-side management (DSM)" below).

## Industry thermal energy storage (TES)

Two thermal energy storage (TES) technologies are added for industry heat (in the
`industry_tes` sector), parametrized from Mayer et al. (2024), Table 3:

- **`industry_TES_water`** (water tank): stores heat at the `heat_industry_0_100` and
  `heat_industry_100_150` temperature levels.
- **`industry_TES_steam`** (steam accumulator): stores heat at the
  `heat_industry_100_150` and `heat_industry_150_200` temperature levels.

### Parametrization (from Mayer2024 Table 3)

| Parameter                       | Water tank        | Steam accumulator |
|---------------------------------|-------------------|-------------------|
| Round-trip efficiency           | 0.9               | 0.95              |
| → `efficiency_charge`           | √0.9 ≈ 0.949     | √0.95 ≈ 0.975    |
| → `efficiency_discharge`        | √0.9 ≈ 0.949     | √0.95 ≈ 0.975    |
| Investment cost (source)        | 10 EUR/kWh        | 114 EUR/kWh       |
| → `capex_specific_storage_energy` | 10,000 EUR/MWh  | 114,000 EUR/MWh   |
| Fixed O&M cost (source)         | 0.15 EUR/kWh      | 4.1 EUR/kWh       |
| → `opex_specific_fixed_energy`  | 150 EUR/MWh       | 4,100 EUR/MWh     |
| Lifetime                        | 30 years          | 25 years          |

- **Efficiency split**: the round-trip efficiency from the source is split
  symmetrically between charge and discharge: `η_charge = η_discharge = √η_roundtrip`.
- **Unit conversion**: costs in the source CSV are in EUR/kWh (energy capacity);
  these are converted to EUR/MWh (×1000) to match the ZEN-garden storage technology
  unit convention (`power_unit = MW`).
- **`capacity_existing`**: 0 (default) — there is essentially no deployed industrial
  TES capacity in Europe at present.
- **`opex_specific_variable` = 1 EUR/GWh** for all TES technologies — small friction
  cost to prevent spurious charge/discharge cycling. Mayer2024 does not report a
  variable O&M cost for heat storage cycling.
- **`self_discharge` = 0.95** for all TES technologies — standing thermal loss per
  time step. Mayer et al. (2024) does not report self-discharge rates for industrial
  TES; this value is an internal assumption.
- **Reference carriers**: each TES variant is assigned to one temperature level.
  - `industry_TES_water_0_100` → `heat_industry_0_100`
  - `industry_TES_water_100_150` → `heat_industry_100_150`
  - `industry_TES_steam_100_150` → `heat_industry_100_150`
  - `industry_TES_steam_150_200` → `heat_industry_150_200`

### Energy-to-power ratio bounds

| Technology | `energy_to_power_ratio_min` (h) | `energy_to_power_ratio_max` (h) |
|---|---|---|
| Water tank (0–100 °C, 100–150 °C) | 1 | 24 |
| Steam accumulator (100–150 °C, 150–200 °C) | 0.25 | 4 |

- **Water tanks** are sized for intraday heat buffering; a minimum of 1 h ensures the
  tank has meaningful thermal mass relative to its charging rate. The 24 h cap
  reflects that industrial water tanks are not seasonal stores.
- **Steam accumulators** are pressurised vessels with inherently short storage
  horizons (minutes to a few hours); 0.25–4 h covers the practical range from
  industrial practice.

## Industry demand-side management (DSM)

DSM storage technologies allow the optimizer to shift production in time for each
industry product carrier. Every DSM technology is parametrized from one of three
demand-shiftability categories (Cat 1/2/3), assigned per carrier and per
optimistic/pessimistic variant in
`input_data/DSM_parametrization/DSM_literature_review.md`. Two sectors —
`industry_dsm_optimistic` and `industry_dsm_pessimistic` — cover the same carriers
with the optimistic or pessimistic category assumption respectively; only one is
normally added to a given model. Both live in
`zen_creator/sectors/industry_dsm.py` / `zen_creator/elements/storage_technologies/industry_DSM.py`.

### Covered carriers

| Technology | Carrier | Sector origin |
|---|---|---|
| `glass_DSM` | `glass` | industry_heat |
| `ceramic_DSM` | `ceramic` | industry_heat |
| `paper_DSM` | `paper` | industry_heat |
| `food_DSM` | `food` | industry_heat |
| `ammonia_DSM` | `ammonia` | Crystal Ball base model |
| `clinker_DSM` | `clinker` | Crystal Ball base model |
| `methanol_DSM` | `methanol` | Crystal Ball base model |
| `primary_steel_DSM` | `primary_steel` | Crystal Ball base model |
| `secondary_steel_DSM` | `secondary_steel` | Crystal Ball base model |
| `olefin_DSM` | `olefin` | Crystal Ball base model |

The six carriers originating in the Crystal Ball base model (ammonia, clinker,
methanol, primary/secondary steel, olefin) already exist in the base Crystal Ball
dataset — no new carrier classes are needed in zen_creator.

### Demand-shiftability categories

- **Cat 1 = fully flexible**: low cost, long shifting horizon.
- **Cat 2 = partially flexible / short timescales**: moderate cost and horizon.
- **Cat 3 = not flexible at all**: very high cost (effectively priced out of the
  optimum) and a short horizon.

| Category | `capex_specific_storage_energy` / `opex_specific_variable` (EUR/(power_unit·h)) | `energy_to_power_ratio_max` (h) |
|---|---|---|
| Cat 1 | 1 | 336 (2 weeks) |
| Cat 2 | 20 | 48 (2 days) |
| Cat 3 | 1,000 | 2 |

These are internal placeholder assumptions (no literature-derived cost source per
category yet) chosen to give Cat 1 a near-free, long-horizon shape, Cat 3 a
priced-out, short-horizon shape, and Cat 2 something in between.

| Carrier | Pessimistic | Optimistic | Key source(s) |
|---|---|---|---|
| Glass | Cat 3 | Cat 3 | Hubert2015 [1]; Hongtai2024 [2] |
| Ceramic | Cat 3 (continuous kilns) | Cat 2 (batch kilns) | Tangram2026 [3] |
| Paper | Cat 2 | Cat 1 | Helin2017 [4] |
| Food | Cat 3 | Cat 2 | AnaInterview2026 [5] (primary source; placeholder citation, needs last name + date) |
| Methanol | Cat 2 | Cat 1 | Schneider2023 [6]; ChenYang2021 [7] |
| Primary steel | Cat 3 (BF-BOF, NG-DRI) | Cat 2 (H2-DRI-EAF) | Boldrini2024 [8]; Golmohamadi2021 [9] |
| Secondary steel | Cat 2 | Cat 1 | Boldrini2024 [8]; Golmohamadi2021 [9] |
| Olefin | Cat 3 (conventional cracker) | Cat 2 (electrified cracker) | Tiggeloven2023 [10] |
| Ammonia | Cat 3 | Cat 2 | Salmon2023 [11]; Fahr2025 [12] |
| Clinker | Cat 3 | Cat 3 | Golmohamadi2021 [9] (Table 5: cement/clinker classified "Uninterruptible") |

Numbered citations refer to `input_data/DSM_parametrization/DSM_literature_review.md`,
which carries full source verification notes and BibTeX for each entry. [5] (food) is a
placeholder citation pending Ana's last name and interview date.

### Shared parametrization

| Parameter                         | Value                                  |
|-----------------------------------|-----------------------------------------|
| `efficiency_charge`               | 1.0 (default)                          |
| `efficiency_discharge`            | 1.0 (default)                          |
| `self_discharge`                  | 0.0 (default)                          |
| `capex_specific_storage_energy`   | by category (see table above)          |
| `opex_specific_variable`          | by category (see table above)          |
| `lifetime`                        | 50 years                               |
| `energy_to_power_ratio_max`       | by category (see table above)          |
| `capacity_limit`                  | 2 × per-node carrier demand            |

- **No losses**: efficiency = 1.0 and self_discharge = 0.0, representing an idealized
  ability to reschedule production within a planning period.
- **Power unit**: `tonproduct/hour`, matching production technology capacity units
  (`GW` for `ammonia_DSM` and `methanol_DSM`).
- **`capacity_limit` = 2 × per-node carrier demand** (200% of the carrier's annual
  demand rate at each node), derived at model build time from the carrier element's
  demand attribute. Prevents unrealistically large DSM stocks while allowing full
  flexibility within the demand range.
- `energy_to_power_ratio_min` is left at 0 (default) for all DSM techs — no minimum
  inventory depth is physically required.
- `lifetime` does not vary by category — no literature basis yet to differentiate it.

## Existing capacity spread over vintage cohorts

`capacity_existing` for all production and heat supply technologies is spread
uniformly across `lifetime` vintage cohorts instead of assigning all observed capacity
to a single `year_construction`.

**Motivation**: assigning all capacity to one year means all existing stock retires
simultaneously at `year_construction + lifetime`, creating an artificial investment
cliff. Spreading over the full lifetime distributes retirement gradually, one cohort
per year, which better reflects a real capital stock that was accumulated over
decades.

**Method** (per node, per technology):

    cap_per_vintage_year = total_capacity_existing / lifetime
    year_construction ∈ {reference_year − lifetime + 1, …, reference_year}

Each vintage cohort contributes `cap_per_vintage_year` to the total and retires
`lifetime` years after its construction year, so at the reference year the cumulative
existing capacity equals the observed total.

**Reference year** = `CAPACITY_YEAR = 2022`.
**Lifetimes used** (`SECTOR_LIFETIMES` / `BOILER_LIFETIMES` in `_industry_heat_utils.py`):

| Technology              | Lifetime (yr) | Source                                  |
|-------------------------|---------------|-----------------------------------------|
| glass_production        | 28            | JRC-EU-TIMES, activity-weighted         |
| ceramic_production      | 20            | Manual (see Ceramic section above)      |
| paper_production        | 25            | JRC-EU-TIMES                            |
| food_production         | 20            | JRC-EU-TIMES cluster average            |
| biomass_boiler_industry | 20            | Crystal Ball / heat_tech_parametrization.xlsx |
| natural_gas_boiler_industry | 21        | Crystal Ball / heat_tech_parametrization.xlsx |
| electrode_boiler_industry | 30          | Crystal Ball / heat_tech_parametrization.xlsx |

Heat pumps have `capacity_existing = 0` (see "Heat pump (industry) capacity" above)
and are not affected by this vintaging. TES and DSM technologies also have
`capacity_existing = 0` and are also unaffected.

## Product carrier demand = capacity_existing

The demand for all four product carriers (glass, ceramic, paper, food) is set equal to
their corresponding `capacity_existing` value, via each carrier's `_set_demand` method
(`zen_creator/elements/carriers/industry_carriers.py`) calling
`JrcIdeesIndustryDataset.get_demand_as_capacity_existing` (glass, paper),
`JrcIdeesIndustryDataset.get_ceramic_demand_as_capacity_existing` (ceramic), or
`FaostatFoodDataset.get_food_demand_as_capacity_existing` (food).

**Rationale**: setting demand = capacity_existing ensures the optimizer starts from a
state where existing capacity exactly meets demand, with no implicit overcapacity or
underutilization assumption baked into two independently-sourced numbers.

**Unit**: `tonproduct/hour`.

**Per-sector detail**:

- **Glass** (JRC-IDEES nodes): demand = installed capacity (kt) × 1000 / 8000 h.
  CH/NO/UK nodes retain the same population-proxy logic as `capacity_existing` (AT
  values for CH, FI values for NO, DE×69.9/83.5 for UK).
- **Paper** (JRC-IDEES nodes): demand = installed capacity (kt) × 1000 / 8000 h.
  CH/NO/UK nodes use JRC-BAT 2014 consumption (kt) × 1000 / 8000 h (same as
  `capacity_existing`).
- **Food**: demand = FAOSTAT production-weighted Rehfeldt activity (Mt) × 1e6 / 8000 h
  — identical to `food_capacity_existing_df`.
- **Ceramic**: demand = JRC-IDEES thermal FEC ÷ Rehfeldt specific energy (kt/yr) ×
  1000 / 8000 h — identical to `capacity_existing`; see "Ceramic" above for the full
  derivation.
