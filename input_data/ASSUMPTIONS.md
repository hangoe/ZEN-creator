# Assumptions made in the code

This file lists assumptions made in `zen_creator/` when deriving parameters for the
industry conversion technologies and carriers (glass, ceramic, paper, food) and the
shared `heat_industry_*` carriers. It does not cover assumptions in the input Excel
files (`process_parametrization.xlsx`, `industry_carriers.xlsx`,
`heat_tech_parametrization.xlsx`) — those document their own sources in their
`source`/`comment` columns. This file describes only the current version's assumptions,
not the history of how they were derived.

## New in sector v7.0

- **`oil_boiler_industry`**: a fourth 150–200°C boiler technology, alongside
  `biomass_boiler_industry`, `natural_gas_boiler_industry`, and
  `electrode_boiler_industry`. `input_carrier` is `oil` instead of `natural_gas`;
  capex/opex/lifetime/efficiency are DEA-sourced like the other three boilers (see
  "Heat pump & boiler cost/efficiency parametrization (DEA)" below) — DEA's
  gas-and-oil boiler sheet covers both fuels with one set of techno-economics, so
  `natural_gas_boiler_industry` and `oil_boiler_industry` share identical
  capex/opex/lifetime/efficiency, differing only in `input_carrier`. No coal-fired
  boiler was added: coal is a minor EU industrial heating fuel and is already
  represented as a *process* fuel for glass/ceramic/paper/food (`Solids` →
  `hard_coal` in the JRC-IDEES thermal-FEC shares), not as boiler technology.
- **Oil data source**: `input_data/Eurostat/Eurostat_new.xlsx` is a second Eurostat
  `nrg_bal_c` extract (custom_22192472) that, unlike `Eurostat_EB_GWh.xlsx`
  (custom_21840385), includes oil products under "Gross heat production". Sheet 23,
  "Oil and petroleum products (excluding biofuel portion)" — the full oil
  aggregate — was chosen over the narrower "Fuel oil" (Sheet 39). Comparison of
  EU27 fuel-mix shares (natural_gas/biomass/electricity/oil only), 2023:

  | carrier | Eurostat, oil = full aggregate (Sheet 23) | Eurostat, oil = "Fuel oil" only (Sheet 39) | Fraunhofer2012, industry-specific (glass+ceramic+paper+food, <100/100–200°C) |
  |---|---|---|---|
  | natural_gas | 53.0% | 55.0% | 48.2% |
  | biomass | 41.5% | 43.0% | 43.2% |
  | electricity | 0.9% | 0.9% | 1.2% |
  | oil | **4.6%** | 1.0% | 7.4% (fuel oil) |

  The full aggregate (4.6%) is closer to Fraunhofer's industry-specific fuel-oil
  share (7.4%) than the narrow "Fuel oil" sheet (1.0%) — Eurostat's economy-wide
  "Gross heat production" statistic is dominated by district-heating/CHP plants
  rather than industrial boilers, and industrial oil use spans gas oil/diesel,
  LPG and refinery gas alongside heavy fuel oil, not just fuel oil narrowly. Using
  the full aggregate also keeps oil consistent with how biomass is already
  defined (`Primary solid biofuels`, itself a broad aggregate, not one narrow
  sub-product).

### Heat pump & boiler cost/efficiency parametrization (DEA)

`heat_pump_industry` (all 6 temperature-level/source variants),
`biomass_boiler_industry`, `natural_gas_boiler_industry`, `oil_boiler_industry`,
and `electrode_boiler_industry` previously borrowed `capex_specific_conversion`,
`opex_specific_fixed`, `opex_specific_variable`, and `lifetime` from the base
(non-industry) Crystal_Ball techs (`heat_pump`, `natural_gas_boiler`,
`biomass_boiler`, `electrode_boiler`) — a placeholder, since those numbers were
never industry-specific. They're now sourced from
`input_data/DanishEnergyAgency/technology_data_for_industrial_process_heat.xlsx`
(Danish Energy Agency, "Technology Data for Industrial Process Heat"), via the new
`zen_creator/datasets/datasets/dea_industrial_heat.py`.

- **Sheet-to-tech mapping** (central (`ctrl`) estimates only):

  | model tech | DEA sheet | capex (2025) | fixed O&M (2025) | variable O&M | lifetime | efficiency/COP |
  |---|---|---|---|---|---|---|
  | `heat_pump_industry_0_100` (both waste-heat/water variants) | 2.a, up to 125°C | 1,200 €/kW | 2.49 €/kW/yr | 3.6 €/MWh | 20 yr | Carnot formula (unchanged) |
  | `heat_pump_industry_100_150`, `heat_pump_industry_150_200` (4 remaining variants) | 2.b, up to 150°C | 1,550 €/kW | 2.49 €/kW/yr | 3.6 €/MWh | 20 yr | Carnot formula (unchanged) |
  | `electrode_boiler_industry` | 5.1a, electric boiler, steam, 2 MW | 250 €/kW | 1.44 €/kW/yr | 0.674 €/MWh | 25 yr | 99% |
  | `natural_gas_boiler_industry`, `oil_boiler_industry` | 6.1, boiler, gas and oil, 5 MW | 90 €/kW | 2.0 €/kW/yr | 1.23 €/MWh | 25 yr | 94% |
  | `biomass_boiler_industry` | 6.2, boiler, biomass, 6.5 MW | 878 €/kW | 39.5 €/kW/yr | 1.45 €/MWh | 25 yr | 89% |

- **Heat pump temperature tiering**: DEA has no tier above 150°C, so the 150°C
  sheet (2.b) is reused as the cost proxy for the 150–200°C band too (not just
  100–150°C). This only borrows *cost* — heat pump COP is untouched, still computed
  independently via the model's own Carnot-fraction formula
  (`HP_COP_WASTE_HEAT`/`HP_COP_WATER` in `heat_tech_parametrization.py`, see "Heat
  pump COP parametrization" below), so reusing 2.b's cost for the top band doesn't
  imply a 150°C-rated unit can literally reach 200°C output — only that its cost is
  the best available proxy.
- **Electric boiler size**: DEA gives two unit-size variants per electric-boiler
  sheet (2 MW vs 15 MW, materially different capex due to economies of scale); the
  2 MW variant (5.1a, 250 €/kW) was chosen over the 15 MW variant (5.1b, 110 €/kW)
  because the larger unit would price electricity-based heat *below* the fuel-fired
  gas/oil boiler (90 €/kW), which doesn't hold up against its peers. Gas/oil and
  biomass boilers only have one DEA size each, so no such choice was needed there.
- **Boiler efficiency**: `conversion_factor` (`1 / efficiency`) for all 4 boilers
  now comes from DEA's `Total efficiency, net [%], nominel load`, replacing the
  previous placeholder values (e.g. `natural_gas_boiler_industry`'s ~99.5%, copied
  from the base non-industry tech).
- **Time-varying costs**: DEA gives values at 5 sample years (2025, 2030, 2035,
  2040, 2050), all in real 2025€. Capex/opex are interpolated (linear) onto every
  calendar year 2022–2050. Years before 2025 (2022–2024) hold flat at the 2025
  value, since DEA has no earlier data. The gas/oil boiler (DEA sheet 6.1) is flat
  across all 5 DEA years (mature technology, no assumed learning curve), so its
  time series is a constant 1.0 multiplier/flat value throughout.
  - `capex_specific_conversion` and `opex_specific_fixed` use the same mechanism
    already used for `battery` in the base model (a `{attribute_name}.csv` file
    with a `year` index, alongside the scalar `attributes.json` default — see
    `Attribute.df`/`_load_time_series_data` in `zen_creator/utils/attribute.py`).
    ZEN-garden reads both of these with index sets `[node, year]` directly, so a
    year-indexed file (node omitted, broadcast to all nodes) is valid.
  - `opex_specific_variable` is different: ZEN-garden reads it with index sets
    `[node, time]` (intra-year dispatch resolution), not `[node, year]` — a bare
    `opex_specific_variable.csv` with only a `year` column has neither `time` nor
    `node`, which trips ZEN-garden's `extract_general_input_data` assertion
    ("More than one of the requested index sets are missing"). Year-to-year
    variation for this attribute instead has to go through ZEN-garden's separate
    yearly-variation mechanism — `opex_specific_variable_yearly_variation.csv`, a
    *multiplier* on the `attributes.json` default value, indexed by `year` (the
    same mechanism already used for e.g. the `oil` carrier's
    `price_import_yearly_variation.csv`) — via `Attribute.yearly_variations_df`,
    not `Attribute.df`.
- **Lifetime**: also switched to DEA's technical lifetime (heat pumps 20 yr, all
  boilers 25 yr) — a real change from the previous placeholders (heat pump 19,
  natural gas/oil 21, biomass 20, electrode 30). `BOILER_LIFETIMES` in
  `_industry_heat_utils.py` (used to spread *existing* capacity across
  construction-year vintage cohorts, independent of the optimization `lifetime`
  attribute) was updated to match (25 for all 4 boilers).
- **Out of scope**: `input_data/Parametrization/heat_tech_parametrization.xlsx`
  still holds the old placeholder numbers for `lifetime`/`capex_specific_conversion`/
  `opex_specific_fixed`/`opex_specific_variable` (and, for boilers,
  `conversion_factor`) in the 5 affected tech columns — they're no longer read for
  these params, kept only as a record of what used to be assumed. All other
  parameters for these techs (capacity bounds, load bounds, `construction_time`,
  `max_diffusion_rate`, carrier lists) are unaffected and still come from that
  file. DEA sheets 1.1/1.2 (traditional/combi heat pump, ≤60/80°C), 4 (mechanical
  vapor recompression, 5 K lift only), 6.3 (coal boiler), and 7.1–7.3 (direct
  firing) don't map onto the model's existing technologies and weren't used.

### Other v7.0 changes

- **`primary_steel_DSM` is Cat 3 in both the optimistic and pessimistic variant**
  (previously Cat 2 optimistic / Cat 3 pessimistic). This is a new evaluation, not
  a change in what the cited literature says — the sources
  (`Boldrini2024`/`Golmohamadi2021`) are unchanged; see
  `_CATEGORY_OVERRIDE_NOTES` in `zen_creator/elements/storage_technologies/industry_DSM.py`.
- **`heat_industry_temp_conversion_150`/`_100` now have `opex_specific_variable = 0`**
  (previously a nominal 0.1 EUR/GWh friction cost). These are lossless
  temperature-downgrade cascade technologies (see "Heat technology
  temperature-level structure" below); the small opex was not meaningful and made
  no difference to results, so it was removed.
- **`industry_TES_steam_100_150` (steam accumulator, 100–150°C) was removed** from
  the model and from `Mayer2024Dataset`'s `TECH_NAME_MAP` — it was never chosen by
  the optimizer and doesn't represent a sensible standalone technology once the
  100–150°C water tank (`industry_TES_water_100_150`) and the 150–200°C steam
  accumulator (`industry_TES_steam_150_200`) already cover that range. Only two
  TES technologies remain at the 100–150°C level's boundaries: the water tank
  (100–150°C) and the high-temperature steam accumulator (150–200°C).
- **DSM `capacity_limit` is now 1× per-node carrier demand** (previously 2×) — see
  `_dsm_capacity_limit` in `industry_DSM.py`. Halves the maximum DSM storage stock
  the optimizer can build per carrier per node relative to v6.1.
- **All TES technologies now have `efficiency_charge = efficiency_discharge = 1.0`**
  (previously `√round-trip-efficiency` from Mayer2024 Table 3, ≈0.949 for water
  tanks, ≈0.975 for the steam accumulator) — all TES losses are now represented
  purely via `self_discharge` instead of being split across charge/discharge.
  `self_discharge` itself **stays flat at 0.95 for all techs and all temperature
  levels, unchanged from v6.1** — a temperature-dependent self-discharge (higher
  standing loss at higher storage temperatures, following Newton's law of cooling)
  was considered but deliberately deferred: Mayer2024 has no heat-loss/insulation
  data to derive it from, and the right basis for "temperature-dependent" is itself
  unsettled (whether stored energy should be measured relative to ambient — in
  which case the fractional loss rate is roughly temperature-*independent* — or
  relative to the carrier's useful floor temperature, in which case it does grow
  with band). To be decided and implemented later; for now every TES tech uses the
  same uniform, temperature-independent 0.95.

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

(`biomass_boiler_industry`, `natural_gas_boiler_industry`, `electrode_boiler_industry`,
`oil_boiler_industry`)

Each boiler technology's `capacity_existing` (GW, one row per node,
`year_construction = FEC_YEAR = 2023`) is computed in two steps:

1. **Fuel-mix shares per node**, from `input_data/Eurostat/Eurostat_EB_GWh.xlsx`
   "Gross heat production": "Primary solid biofuels" (Sheet 74, biomass), "Natural
   gas" (Sheet 72), "Electricity" (Sheet 83, electrode), plus "Oil and petroleum
   products (excluding biofuel portion)" from the separate extract
   `input_data/Eurostat/Eurostat_new.xlsx` (Sheet 23, oil — see "New in sector
   v7.0" above for why this sheet/extract). Each is converted to GW via
   `/ OPERATING_HOURS`, and the four are normalized to shares
   (`share_bio + share_ng + share_elec + share_oil = 1`). If a node has no Eurostat
   entry, it falls back to 100% natural gas — except Switzerland, which uses
   Austria's fuel-mix shares (see below).
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
  biofuels 11208.557 GWh, electricity 3.398 GWh, oil 1121.159 GWh, giving shares of
  biomass ≈ 59.3%, natural gas ≈ 34.8%, electrode ≈ 0.02%, oil ≈ 5.9%. These shares
  are applied to Switzerland's own modeled heat demand
  (`total_industry_heat_demand_gw("CH")`) to split its `capacity_existing` across
  the four boiler technologies.
- **United Kingdom**: neither Eurostat extract has a 2023 (or later) value for the
  UK in any of the four sheets (coverage ends after 2019 post-Brexit); the latest
  available year (2019) is used instead for the fuel-mix shares (Natural gas:
  16321.438 GWh, Primary solid biofuels: 1168.056 GWh, Electricity: 0.0 GWh, Oil:
  307.701 GWh).

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
  `heat_industry_150_200` temperature level. A `heat_industry_100_150` steam variant
  also existed through v6.1 but was removed in v7.0 (see "New in sector v7.0"
  above) — never chosen by the optimizer, and redundant with the water tank already
  covering that level.

### Parametrization (from Mayer2024 Table 3)

| Parameter                       | Water tank        | Steam accumulator |
|---------------------------------|-------------------|-------------------|
| Investment cost (source)        | 10 EUR/kWh        | 114 EUR/kWh       |
| → `capex_specific_storage_energy` | 10,000 EUR/MWh  | 114,000 EUR/MWh   |
| Fixed O&M cost (source)         | 0.15 EUR/kWh      | 4.1 EUR/kWh       |
| → `opex_specific_fixed_energy`  | 150 EUR/MWh       | 4,100 EUR/MWh     |
| Lifetime                        | 30 years          | 25 years          |

- **Unit conversion**: costs in the source CSV are in EUR/kWh (energy capacity);
  these are converted to EUR/MWh (×1000) to match the ZEN-garden storage technology
  unit convention (`power_unit = MW`).
- **`capacity_existing`**: 0 (default) — there is essentially no deployed industrial
  TES capacity in Europe at present.
- **`opex_specific_variable` = 1 EUR/GWh** for all TES technologies — small friction
  cost to prevent spurious charge/discharge cycling. Mayer2024 does not report a
  variable O&M cost for heat storage cycling.
- **`efficiency_charge` = `efficiency_discharge` = 1.0** for all TES technologies
  (v7.0 onward; see "New in sector v7.0" above) — no charge/discharge losses. Mayer
  2024's round-trip efficiency (0.9 water tank, 0.95 steam accumulator) was
  previously split symmetrically (`η_charge = η_discharge = √η_roundtrip`) but is no
  longer used; all losses are represented via `self_discharge` instead.
- **`self_discharge` = 0.95** for all TES technologies, uniform across every
  temperature level — standing thermal loss per time step. Mayer et al. (2024) does
  not report self-discharge rates for industrial TES; this value is an internal
  assumption. A temperature-dependent self-discharge (higher loss at higher storage
  temperature) is a deliberate future extension, not yet implemented — see "New in
  sector v7.0" above for why it was deferred.
- **Reference carriers**: each TES variant is assigned to one temperature level.
  - `industry_TES_water_0_100` → `heat_industry_0_100`
  - `industry_TES_water_100_150` → `heat_industry_100_150`
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
| Primary steel | Cat 3 (BF-BOF, NG-DRI) | Cat 3 [†] | Boldrini2024 [8]; Golmohamadi2021 [9] |
| Secondary steel | Cat 2 | Cat 1 | Boldrini2024 [8]; Golmohamadi2021 [9] |
| Olefin | Cat 3 (conventional cracker) | Cat 2 (electrified cracker) | Tiggeloven2023 [10] |
| Ammonia | Cat 3 | Cat 2 | Salmon2023 [11]; Fahr2025 [12] |
| Clinker | Cat 3 | Cat 3 | Golmohamadi2021 [9] (Table 5: cement/clinker classified "Uninterruptible") |

Numbered citations refer to `input_data/DSM_parametrization/DSM_literature_review.md`,
which carries full source verification notes and BibTeX for each entry. [5] (food) is a
placeholder citation pending Ana's last name and interview date. [†] Primary steel
optimistic was re-evaluated to Cat 3 in v7.0 (from Cat 2 for the H2-DRI-EAF route) —
a new evaluation, not a change in what [8]/[9] say; see "New in sector v7.0" above.

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
| `capacity_limit`                  | 1 × per-node carrier demand            |

- **No losses**: efficiency = 1.0 and self_discharge = 0.0, representing an idealized
  ability to reschedule production within a planning period.
- **Power unit**: `tonproduct/hour`, matching production technology capacity units
  (`GW` for `ammonia_DSM` and `methanol_DSM`).
- **`capacity_limit` = 1 × per-node carrier demand** (100% of the carrier's annual
  demand rate at each node, reduced from 200% in v6.1 — see "New in sector v7.0"
  above), derived at model build time from the carrier element's demand attribute.
  Prevents unrealistically large DSM stocks while allowing full flexibility within
  the demand range.
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

## Carbon emissions budget

`carbon_emissions_budget` (`energy_system/attributes.json`) is `23.152036605496253`
gigatons in the base Crystal Ball dataset — Mannhardt (2026)'s Chapter 5/6 figure
(dissertation Appendix A.2, printed pp. 124-127): an IPCC AR6 remaining global carbon
budget, allocated per-capita to 28 European countries, then reduced to the ~90.0% share
of those countries' 2021 direct CO2 emissions attributable to her 11 modeled sectors
(electricity, res./comm. heat, passenger/truck transport, aviation, shipping, refining,
chemicals, steel, cement). That figure does not credit the glass/ceramic/paper/food
sectors added in this model (via `industry_heat`), since they were not part of her
case study.

`CrystalBallIndustryEnergySystem` (`zen_creator/elements/energy_systems/
crystal_ball_industry.py`, wired in via `my_scripts/my_model.py`) extends the budget:

```
new_budget = old_budget × (1 + E_new_sectors / E_old_sectors)
```

where `E_old_sectors`/`E_new_sectors` are 2022 direct CO2 emissions (EEA/UNFCCC CRF
data, 28 countries minus UK — UK is not covered by the available EEA extract) for
Mannhardt's 11 sectors and for the newly credited sectors respectively. This avoids
needing to recover the unrounded IPCC/per-capita constants, since
`old_budget = B_countries × f_old` is already known exactly.

**Finding**: Mannhardt's Table A.2 defines "Cement" as CRF `1.A.2.f + 2.A`, where `2.A`
("Mineral Industry") already includes glass (`2.A.3`) and ceramics (`2.A.4`) as
sub-categories, and `1.A.2.f` combustion is a bucket shared across cement/glass/
ceramics that EEA does not split further. So glass's and ceramics' emissions appear to
already be nested inside the existing "cement" budget line. Three variants for
crediting the new sectors were computed from `input_data/Mannhardt2026/
sector_emissions_2022.csv` (derived from `UNFCCC_v30.csv`, an EEA GHG-inventory export;
see `input_data/Mannhardt2026/extract_sector_emissions.py`), `E_old_sectors =
2,563,680.16` kt CO2:

| Variant | `E_new_sectors` composition | ΔB | new budget |
|---|---|---|---|
| A — zero increment | paper + food only | 0.4916 Gt | 23.6437 Gt |
| C — process-only | + glass/ceramic process (`2.A.3`, `2.A.4` as ceramics proxy) | 0.6194 Gt | 23.7715 Gt |
| **B — naive full-add (chosen)** | + the entire shared combustion bucket (`1.A.2.f`) added again | **1.3373 Gt** | **24.4893 Gt** |

**Decision**: Variant B is implemented (`DEFAULT_VARIANT = "B"` in
`carbon_budget_allocation.py`) — a +5.78% budget increase, judged a reasonable
estimate of additional European industry emissions for these sectors, while
acknowledging it is the least methodologically clean of the three (it re-adds
combustion emissions already implicit in cement's existing budget share). This
question was raised on the ZEN community forum and is unresolved as of writing (2026);
**the choice may need to be revisited** once a reply is received. All three variants
remain available via the `variant` argument to
`Mannhardt2026CarbonBudgetDataset.get_carbon_emissions_budget()`/
`get_new_sector_emissions()` — switching does not require recomputing the CSV.

Other caveats: UK is absent from the EEA extract (both numerator and denominator
consistently exclude it); ceramics-specific process emissions (CRF `2.A.4.a`) are not
broken out in `UNFCCC_v30.csv`, so the coarser `2.A.4` aggregate (which also includes
soda ash and magnesium production) is used as a proxy, slightly overstating ceramics
alone.
