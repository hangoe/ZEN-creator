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
- **Cost and lifetime parameters (cement-plant proxy)**: JRC-EU-TIMES only contains generic
  "Other Non-Metallic Minerals" process-heat boiler technologies (`INMPRCxxx`, `INMSTMxxx`),
  which represent heat-supply equipment costs, not ceramic kiln/product-line capex — no
  appropriate JRC-EU-TIMES proxy available (same gap as `paper`'s CAPEX, see "Paper" below).
  No ceramic-specific techno-economic literature was found either. Instead, values are taken
  from **Gardarsdóttir et al. 2019**, "Comparison of Technologies for CO2 Capture from Cement
  Production — Part 2: Cost Analysis" (*Energies* 12, 542) — a techno-economic study of a
  reference European cement clinker plant (retrofit CO2-capture costs in that paper are not
  used; only the underlying reference-plant figures before capture).

  This is a **cement proxy, not a ceramic source** — but a better-justified one than mirroring
  glass: cement clinker production and ceramics are both non-metallic-mineral processes whose
  core step is high-temperature **kiln-firing of a mineral/clay-based feedstock** (cement:
  limestone/raw meal in a rotary kiln; ceramics: clay/kaolin/feldspar bodies in a tunnel/periodic
  kiln), and both are bulk, comparatively low-value-added mineral products. Glass's core step —
  continuous melting of a silica-soda-lime batch into a molten state — is a more different,
  typically more capital- and chemically-intensive process; the previous "same as glass, both use
  a kiln" justification was the weaker analogy on its own logic.

  Reference cement plant data (€2014, pre-capture): capacity 120.65 t clinker/h, capacity factor
  91.3%, Total Plant Cost (TPC) 204 M€, annual OPEX 41 M€/yr, economic life 25 yr. Fixed OPEX is
  built up per the paper's explicit formula (Section 3.1.2): maintenance (2.5% TPC/yr) +
  insurance/taxes (2% TPC/yr) + operating labor (100 persons × 60 k€/yr) + admin/support
  overhead (30% of operating + maintenance labor) = 17.592 M€/yr. Non-fuel variable OPEX is raw
  meal (5 €/t) + NOx reagent (0.60 t/h ammonia × 130 €/t ÷ 120.65 t/h ≈ 0.65 €/t) + miscellaneous
  variable O&M (1.1 €/t, an explicit Table 4 line item) = 6.75 €/t — **excluding fuel and
  electricity**, which the model prices separately via `conversion_factor` × carrier price
  (same convention as JRC-EU-TIMES VAROM for glass/paper/food). All figures deflated 2014→2019
  EUR via `gdp_deflator_ratio()` (factor ≈1.0765) for consistency with the JRC_COST_TARGET_YEAR
  used elsewhere. Resulting values (see `process_parametrization.py::_compute_jrc_cost_params()`,
  `"ceramic"` branch): capex = 1,820,124.59 EUR/(t/h), opex_fixed = 156,958.98 EUR/(t/h)/yr,
  opex_variable = 7.27 EUR/t, lifetime = 25 yr (replacing the previously documented, inconsistent
  20 yr — the Excel/output value actually in use before this change was 28 yr, copied from glass).

  Cross-check against glass's JRC-derived values: cement's CAPEX and fixed OPEX land within
  ~6–17% of glass's (ratios 0.83 and 0.94 respectively) — a similar order of magnitude, meaning
  the previous glass-mirroring wasn't unreasonable for these two parameters, just unconfirmed.
  Variable OPEX is where the two diverge sharply (cement's 7.27 EUR/t vs. glass's 59.34 EUR/t):
  glass's batch chemistry (silica sand, soda ash, cullet, refractory wear) is a materially
  different, pricier input mix than cement's raw meal (crushed limestone). Ceramics' true
  non-fuel variable cost likely sits between the two (cheaper feedstock than glass, but
  potentially pricier than cement's raw meal for glazed/technical product lines) — this remains
  the parameter with the most residual uncertainty pending real ceramic-specific literature.
- **`carbon_intensity_technology = 0.064234` t/t** (previously `0`, "assumed negligible"):
  back-calculated from a JRC BAT finding that process emissions are 15% of total ceramic
  emissions, with the remaining 85% being combustion emissions already captured
  automatically via the carriers `ceramic_production` consumes (no separate
  `carbon_intensity_technology` needed for those — same convention as the heat-supply
  boilers, whose own `carbon_intensity_technology = 0` because "combustion CO2 [is]
  carried on the fuel carrier").

  Method: take ceramic's total thermal energy per tonne (8.036 GJ/t — sum of the
  `hard_coal`/`natural_gas`/`biomass`/`heat_industry_0_100`/`heat_industry_100_200`
  `conversion_factor` rows in `process_parametrization.xlsx`, × 3600; matches the 8.04
  GJ/t Rehfeldt figure above almost exactly). Apply the sector's own
  hard_coal/natural_gas/biomass fuel-mix shares (the same JRC-IDEES-derived mix already
  used for `ceramic_production`'s direct high-temperature fuel demand — see "Fuel mix
  shares for X_production" above) uniformly across *all* of that thermal energy, as a
  "representative heating tech mix" standing in for whichever boiler/heat-pump mix the
  optimizer actually picks to supply `heat_industry_0_100`/`100_200`. Weight each fuel's
  carbon intensity from the Crystal Ball carrier attributes (`natural_gas`: 0.20196
  t/MWh; `hard_coal`: 0.3406 t/MWh; `biomass`: 0, biogenic — same treatment as paper's
  black liquor) to get a weighted-average emission factor of 0.0453 tCO2/GJ, hence
  combustion emissions = 8.036 × 0.0453 ≈ 0.364 tCO2/t (the 85% share). Process
  emissions = 0.364 × (0.15/0.85) ≈ **0.0642 tCO2/t**.

  As a robustness check, assuming the lower-temperature heat is instead supplied
  entirely by a natural-gas boiler (rather than the sector fuel mix) gives ≈0.068 tCO2/t
  — within ~5% of the primary estimate.

  For comparison, glass's `carbon_intensity_technology = 0.1` t/t (raw-material
  decomposition, AIDRES-derived, see "Glass" above) — ceramic's back-calculated value is
  about 64% of glass's, which is directionally sensible: glass batches typically contain
  more carbonate raw material (soda ash, limestone) than most ceramic feedstocks.

## Ceramic and glass post-combustion carbon capture

`ceramic_post_comb` and `glass_post_comb` retrofit `ceramic_production`/`glass_production`
the same way the (externally-defined, pre-existing) `cement_post_comb` retrofits
`cement_kiln` — see `zen_creator/elements/conversion_technologies/industry_ccs.py` and
`zen_creator/datasets/datasets/post_comb_cc.py`.

- **Source**: `input_data/CCS/technology_data_for_carbon_capture_transport_storage.xlsx`
  (Danish Energy Agency, "Technology Data for Carbon Capture, Transport and Storage",
  2020 EUR prices), sheet `401.c Post comb - Cement kiln` — the only post-combustion-capture
  sheet in the catalogue. There is no ceramic- or glass-specific sheet, and the capture-plant
  physics (heat/electricity duty, capex, opex per tCO2 captured) are properties of the
  generic amine-capture unit, not of the industry it's bolted onto, so the cement-kiln sheet
  is reused as-is for both sectors. This sheet is also, verifiably, the exact source of
  `cement_post_comb`'s own numbers: its 2020 "Est" values (heat input 0.833 MWh/tCO2,
  electricity input 0.025 MWh/tCO2, heat output 1.65 MWh/tCO2, 90% capture rate, 25 yr
  lifetime, specific investment/fixed/variable O&M) match `cement_post_comb`'s
  `attributes.json` exactly, other than a small (~0.25%) uniform scaling factor on the three
  cost figures that could not be traced to anything in this repo (not the JRC GDP-deflator
  convention used elsewhere in this file, not a recognizable currency adjustment) — consistent
  with `cement_post_comb` being static legacy data, not generated by any script in this repo.
- **No price-year deflator applied**: unlike the JRC-derived ceramic/glass/paper/food base
  production costs above (which are deflated to `JRC_COST_TARGET_YEAR`), the DEA figures are
  used as-is (only unit conversion), following the existing convention of
  `DeaIndustrialHeatDataset` (`zen_creator/datasets/datasets/dea_industrial_heat.py`, used for
  the industrial heat pumps/boilers) rather than inventing a new deflator choice to try to
  reproduce `cement_post_comb`'s untraceable ~0.25% factor.
- **`capex_specific_conversion`/`opex_specific_fixed`**: DEA gives these at five sample years
  (2020/2025/2030/2040/2050); interpolated onto every model year 2022–2050 exactly like
  `DeaIndustrialHeatDataset` does for the industrial boilers/heat pumps (`np.interp`, holding
  flat outside the sample range). `opex_specific_variable`, `lifetime`, and all
  `conversion_factor` entries are held constant at the DEA 2020 value, matching how
  `cement_post_comb` itself does not vary these over time (e.g. its `fuel_for_cement`
  conversion factor stays at 0.833 throughout, even though DEA's own heat-input figure
  declines to 0.66 MWh/tCO2 by 2030).
- **Fuel input**: the capture unit's own auxiliary heat demand (DEA's 0.833 MWh/tCO2 "Heat
  input") is supplied by `natural_gas`/`hard_coal` only (no oil/biomass), split
  proportionally to each sector's own existing natural_gas:hard_coal ratio (from
  `ProcessParametrizationDataset`'s fuel-mix shares, renormalized to just these two carriers):
  ceramic 80.9%/19.1%, glass 82.5%/17.5% (glass's own fuel mix is already exactly these two
  carriers, so no renormalization changes it). Electricity (0.025 MWh/tCO2) and district heat
  output (1.65 MWh/tCO2) are included unmodified, matching `cement_post_comb` exactly (which
  also draws both fuel and electricity, and exports district heat).
- **`retrofit_flow_coupling_factor`**: mirrors `cement_post_comb`'s own construction exactly —
  `base_technology`'s own `carbon_intensity_technology` × DEA's capture rate (90%, "A3] CO2
  capture rate, net"). This is confirmed by exact arithmetic: `cement_kiln`'s
  `carbon_intensity_technology` (0.54 t/tonproduct, calcination/process emissions only —
  combustion CO2 is tracked separately via the `fuel_for_cement` carrier's own carbon content)
  × 90% = 0.486 t/tonproduct, exactly `cement_post_comb.retrofit_flow_coupling_factor`
  (0.000486 kilotCO2eq/tonproduct). Ceramic's and glass's `carbon_intensity_technology`
  values (0.064234 and 0.1 t/tonproduct — see "Ceramic"/"Glass" above) are already
  process-only in the same sense, so the same formula applies directly:
  ceramic → 0.064234 × 0.90 = 0.057811 t/tonproduct (0.0000578106 kilotCO2eq/tonproduct);
  glass → 0.1 × 0.90 = 0.09 t/tonproduct (0.00009 kilotCO2eq/tonproduct). **Caveat**: like
  `cement_post_comb`, this means the retrofit only captures the (smaller) process-emission
  share of each sector's CO2, not the larger combustion-CO2 stream also present in the flue
  gas a real post-combustion capture unit would draw from — a modeling simplification
  inherited deliberately for consistency with cement's existing convention, not a claim that
  combustion CO2 is uncapturable.
- **`capacity_addition_unbounded` (0.0114155 kilotCO2eq/hour) and `max_diffusion_rate`
  (0.13)**: carried forward unchanged from `cement_post_comb`, since both retrofits share the
  same underlying DEA "typical plant" capture-unit spec — only the base technology they're
  attached to differs.

## Ceramic and glass kiln fuel switching (`fuel_to_kiln`)

`ceramic_production`/`glass_production` previously took their direct high-temperature
(`>200°C`) `natural_gas` input as a fixed, non-substitutable flow — whatever JRC-IDEES-2023
said the 2023 EU fuel mix was stays fixed for the whole model horizon (see "Fuel mix
shares for X_production" above). A new intermediate carrier, `fuel_to_kiln`, and three
zero-tech-cost conversion technologies (`natural_gas_to_kilnfuel`, `hydrogen_to_kilnfuel`,
`electricity_to_kilnfuel`) now let the optimizer shift kiln firing away from natural gas
over time, while the reference year still reproduces today's natural-gas-only kiln fuel
exactly. Implemented in
`zen_creator/elements/carriers/industry_carriers.py` (`FuelToKiln`),
`zen_creator/elements/conversion_technologies/industry_heat_supply.py`
(`NaturalGasToKilnfuel`/`HydrogenToKilnfuel`/`ElectricityToKilnfuel`), and
`zen_creator/datasets/datasets/process_parametrization.py`
(`_kiln_fuel_shares()`, `get_kiln_fuel_switch_capacity_existing()`).

- **Scope**: only the direct high-temp `natural_gas` input to `ceramic_production`/
  `glass_production` is affected. The `heat_industry_0_100`/`100_150`/`150_200` carriers
  (low-temperature heat, `<200°C`) are untouched — they're already served by
  independently fuel-competing boiler technologies (`natural_gas_boiler_industry`,
  `biomass_boiler_industry`, `electrode_boiler_industry`, etc., see "Boiler (industry)
  capacity" above), which already provide fuel-switching flexibility at that level.
  `hard_coal`/`biomass`/`oil` high-temp shares are also untouched — they stay direct,
  fixed inputs exactly as before this change.
- **`fuel_to_kiln` is a shared carrier**, drawn on by both `glass_production` and
  `ceramic_production` at each node, the same way `heat_industry_0_100/100_150/150_200`
  are already shared across all four industry sectors.
- **Glass: 100% switchable.** All of glass's high-temp `natural_gas` conversion factor
  (today split 82.5%/17.5% `natural_gas`/`hard_coal`, see "Ceramic and glass
  post-combustion carbon capture" above) is rerouted through `fuel_to_kiln`; `hard_coal`
  stays a separate, fixed 17.5% input.
- **Ceramic: 97.4% switchable, 2.6% locked.** `KILN_NG_SWITCHABLE_SHARE["ceramic"] =
  46.26 / 47.49 ≈ 0.9741`, taken directly from the "Ceramic NG fuel-switch feasibility
  split" section below (that section's `electrifiable_share`/`gas_only_share`, originally
  computed as an exploratory, not-implemented calculation, is now the real basis for this
  split — see that section for the full Rehfeldt2017/JRC-BAT-CER-2026 derivation and its
  caveats, notably that the 2.6% "locked" share is an electrification-only feasibility
  limit repurposed as a proxy for "can't convert to any alternative fuel," not a literal
  hydrogen limit). `hard_coal`/`biomass`/`oil` shares stay separate, fixed inputs.
- **`_kiln_fuel_shares(sector, shares)`** (`process_parametrization.py`) replaces the
  `natural_gas` entry in the sector's fuel-mix `shares` dict with a `fuel_to_kiln` entry
  (scaled by `KILN_NG_SWITCHABLE_SHARE[sector]`) plus, only where the remainder is
  nonzero (ceramic), a reduced `natural_gas` entry — applied inside
  `ProcessParametrizationDataset.get_production_tech_dict()` before `build_conversion_tech()`
  runs, so both the `input_carrier` list and `conversion_factor` values are built directly
  against the split shares. `process_parametrization.xlsx`'s `conversion_factor:natural_gas`
  override row for `glass_production`/`ceramic_production` (a static snapshot written by
  a previous version of `compute_params.py`) was cleared for both columns, since it would
  otherwise silently overwrite the code-computed `fuel_to_kiln`/reduced-`natural_gas`
  values back to the old pre-split full-NG figure.
- **Zero tech cost, non-1:1 conversion factors.** `capex_specific_conversion`,
  `opex_specific_fixed`, `opex_specific_variable`, and `carbon_intensity_technology` are
  all `0` for the three `*_to_kilnfuel` techs (base `Technology`/`ConversionTechnology`
  defaults, no overrides) — production-tech costs are unchanged versus before this
  change, since this only models the fuel-*choice* decision, not burner-conversion capex.
  Combustion CO2 stays attributed to the input fuel carrier, same convention as the
  boilers. The routes are **not** energy-equivalent, though: `conversion_factor` is
  AIDRES2023-derived (`KILN_FUEL_SWITCH_CF` in `process_parametrization.py`), from
  glass's own container/flat/fibre production-route energy tables (AIDRES2023 Tables
  19/21/23), comparing each route's own fuel GJ/t against the NG-reference route's
  `natural_gas` GJ/t (the electricity route netted against the ~constant baseline
  auxiliary electricity already captured separately in `glass_production`'s own
  `electricity` conversion factor), weighted by the same 60/30/10 container/flat/fibre
  AIDRES activity shares used elsewhere for glass:

  | sub-process (AIDRES weight) | NG (ref) GJ/t | H2 GJ/t | H2/NG | Electricity route GJ/t | − baseline elec | furnace-only elec | elec/NG |
  |---|---|---|---|---|---|---|---|
  | container (60%) | 4.73 | 5.04 | 1.0655 | 5.09 | 1.07 | 4.02 | 0.8499 |
  | flat (30%) | 5.43 | 5.78 | 1.0645 | 5.41 | 0.80 | 4.61 | 0.8490 |
  | fibre (10%) | 7.24 | 7.17 | 0.9903 | 7.89 | 2.16 | 5.73 | 0.7914 |
  | **weighted (60/30/10)** | | | **1.0577** | | | | **0.8438** |

  So `hydrogen_to_kilnfuel`'s conversion factor is `1.0577` GW hydrogen in per GW
  `fuel_to_kiln` out (hydrogen firing needs ~5.8% more fuel energy than natural gas), and
  `electricity_to_kilnfuel`'s is `0.8438` (electric melting needs ~15.6% less energy than
  natural gas) — consistent with AIDRES's own text noting electric glass furnaces run at
  93% efficiency versus lower combustion-furnace efficiency.
  `natural_gas_to_kilnfuel`'s conversion factor is `1.0` (it's the reference route
  itself). **Ceramic reuses these same glass-derived ratios as a documented cross-sector
  proxy** — JRC-BAT-CER-2026 has no quantitative electric/hydrogen-vs-gas kiln efficiency
  figure of its own (Chapter 6 explicitly lists "specific energy consumption for electric
  kilns and dryers" as a data gap for future BREF review), and both processes are
  high-temperature kiln/furnace firing where electric resistive/induction heating
  displaces flue-gas-loss-prone combustion — the same kind of proxy already used for
  ceramic's CAPEX (borrowed from a cement-plant study, see "Ceramic" above).
- **Reference-year `capacity_existing`**: `get_kiln_fuel_switch_capacity_existing()`
  sizes `natural_gas_to_kilnfuel`'s per-node capacity so its output exactly reproduces
  today's `fuel_to_kiln`-eligible `natural_gas` flow, summed across glass and ceramic:
  `Σ_sector demand[sector, node] × fuel_to_kiln_conversion_factor[sector]`, spread across
  `KILN_FUEL_TECH_LIFETIME` (20 years, matching the external cement fuel-mix hub's
  `*_to_cement_fuel` techs — no `fuel_to_kiln`-specific lifetime source available) vintage
  years ending at `CAPACITY_YEAR`, the same vintage-spreading convention already used for
  the boiler/production-tech capacities (`_boiler_capacity_df_from_node_caps`).
  `hydrogen_to_kilnfuel`/`electricity_to_kilnfuel` both start at `capacity_existing = 0`
  (built from scratch), matching the `heat_pump_industry` convention.
- **`max_diffusion_rate`**: `0.13` for `hydrogen_to_kilnfuel`/`electricity_to_kilnfuel`
  (matches `heat_pump_industry`, all industry boilers, and the external `*_to_cement_fuel`
  techs). `natural_gas_to_kilnfuel` is unconstrained (`inf`), consistent with how
  baseline/incumbent production techs already work in this sector
  (`ceramic_production`/`glass_production` themselves have `max_diffusion_rate = inf`,
  "baseline production tech — no diffusion bottleneck").

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
`oil_boiler_industry`, `coal_boiler_industry`, `waste_boiler_industry`)

Each boiler technology's `capacity_existing` (GW, one row per node,
`year_construction = FEC_YEAR = 2023`) is computed in two steps:

1. **Fuel-mix shares per node**, from `input_data/Eurostat/Eurostat_EB_GWh.xlsx`
   "Gross heat production": "Primary solid biofuels" (Sheet 74, biomass), "Natural
   gas" (Sheet 72), "Electricity" (Sheet 83, electrode), plus from the separate
   extract `input_data/Eurostat/Eurostat_new.xlsx` (custom_22192472 — see "New in
   sector v7.0" above for why this second extract exists): "Oil and petroleum
   products (excluding biofuel portion)" (Sheet 23, oil), "Solid fossil fuels"
   (Sheet 2, coal), "Biogases" (Sheet 63, folded into biomass), and "Industrial
   waste (non-renewable)" + "Renewable municipal waste" + "Non-renewable municipal
   waste" (Sheets 64/65/66, summed into waste). Each is converted to GW via
   `/ OPERATING_HOURS`, and all six are normalized to shares (sum to 1). If a node
   has no Eurostat entry, it falls back to 100% natural gas — except Switzerland,
   which uses its own BFE-survey-derived fuel-mix shares (see below).
2. **Total boiler capacity per node** = `total_industry_heat_demand_gw(node)` (summed
   heat-carrier demand across glass/ceramic/paper/food, all 3 temperature levels) ×
   that node's fuel-mix share. This sizes total existing boiler capacity to match
   modeled industry heat demand rather than reading an independent absolute value from
   Eurostat, ensuring enough boiler capacity exists to meet demand at every temperature
   level.

**Why coal and waste are now included (previously excluded).** The original
4-carrier version of this calculation (biomass/gas/electrode/oil only) silently
treated their sum as 100% of "Gross heat production", even though the same Eurostat
extract also carries coal and waste as separate SIEC categories. Checking the
2023 data directly: EU28-wide, "Solid fossil fuels" (coal) totals ~98.7 TWh — the
3rd-largest carrier in the whole dataset, larger than oil (~15.9 TWh) and
electricity (~3.8 TWh) *combined*, both of which already had dedicated boiler
technologies. Waste (industrial + municipal, all categories) totals ~75.5 TWh,
also larger than oil or electricity alone. Per country the gap is large where
coal-fired heat plants are common: Poland's coal figure (51.4 TWh) alone exceeds
what the model's entire 4-carrier total captured for Poland (18.5 TWh); Czechia,
Germany, and Slovenia show similarly large gaps. This is a materially different
situation from the Swiss case below, where the same kind of exclusion is
explicitly checked and found genuinely small (~2%) — no equivalent check
previously existed for the EU nodes, where the answer turns out to be the
opposite. Biogases (Sheet 63, ~7.4 TWh EU-wide) were folded into the biomass
total at the same time, since a biogas boiler is the same technology as a
biomass boiler.

A separate check compared this Eurostat "Gross heat production" statistic
against the model's own district-heating (DH) sector technologies
(`hard_coal_boiler_DH`, `waste_boiler_DH`, etc., inherited from the external base
"Crystal Ball" model): DH capacity, even under a conservative full-load-hours
assumption, already matches or exceeds the *entire* Eurostat "Gross heat
production" total in nearly every country (EU28-wide: DH-implied ~933 TWh vs.
Eurostat's reported ~595 TWh). This confirms the Eurostat statistic being used
here as an industry-boiler-fuel-mix proxy is, at its core, a district-heating/CHP
sector number — there is no separate "industrial-only" residual to cleanly
isolate by subtracting DH from it. Practically, this means including coal and
waste is a **consistency fix to an already-borrowed DH-sector proxy**, not an
attempt to independently estimate a new industrial coal/waste demand: since coal
and waste are demonstrably larger contributors to that same statistic than the
oil and electricity carriers the model already includes, dropping them without
justification systematically inflated gas/biomass/oil/electrode shares in coal-
and waste-heavy countries. Two other sizeable carriers in the same extract were
deliberately left out: "Manufactured gases" (coke-oven/blast-furnace gas, ~6.9
TWh, concentrated in Poland/Germany) is steel-industry-specific and steel isn't
one of this model's four sectors (glass/ceramic/paper/food); everything else
(peat, geothermal, solar thermal, nuclear heat, oil shale, ambient heat/heat
pumps) is small and/or concentrated in 1–2 countries.

**`waste_boiler_industry` cost/efficiency** has no Danish Energy Agency sheet
(unlike coal — DEA's "6.3 Boiler, coal" has full capex/opex/efficiency/lifetime
data structurally identical to the existing "6.1"/"6.2" sheets, and is used
directly). In its absence, `waste_boiler_industry` reuses the Crystal Ball base
model's own `waste_boiler_DH` technology as a district-heating proxy (capex ≈
1430 €/kW, opex_fixed ≈ 50 €/kW/yr, opex_variable ≈ 4.7 €/MWh, lifetime 30 yr,
efficiency ≈ 93.6%) — see `waste_boiler_dh_proxy.py`. This is a frozen snapshot
(read once from that technology's `attributes.json`, since zen_creator has no
live read access to the external base model's technology definitions during
sector-dataset construction), and, like the fuel-mix shares themselves, an
explicit DH-sourced approximation rather than an industry-specific cost source.

- **Switzerland ("CH")** has no entry in the Eurostat extract. It previously fell
  back to Austria's fuel-mix shares (closest neighboring energy system among the
  covered nodes) but now uses Switzerland-specific shares computed from
  `input_data/BFE2025/BFE2025.xlsx` — the underlying data table (2013–2025, one
  sheet per energy carrier × 19 NOGA branch groups) behind BFE's annual survey
  report **BFE2025** ("Energieverbrauch in der Industrie und im
  Dienstleistungssektor", Resultate 2024, an eidgenössische Erhebung of ~13'000
  establishments extrapolated by BFS). See `_bfe_ch_fuel_shares()` and
  `_bfe_ch_branch_total_tj()` in `_industry_heat_utils.py`.
  - **Branches summed**: 1 "Nahrungsmittel" (food), 3 "Papier und Druck" (paper),
    6 "Andere Nicht-Eisen-Mineralien" (glass/ceramics) — matching this model's
    process-heat scope. Cement (branch 5, "Zement und Beton") is reported
    separately by BFE and is out of scope here, so it is excluded.
  - **Carriers summed**: Erdgas (→ natural_gas), Heizöl extra-leicht + Heizöl
    mittel und schwer (→ oil), Holz (→ biomass), Kohle (→ coal), Industrieabfälle
    (→ waste). Electricity is excluded from the mix — in these branches it is
    dominated by drives/lighting rather than boilers — consistent with
    electrode/heat-pump `capacity_existing = 0` for Switzerland (see "Heat pump
    (industry) capacity" above, David2017). Kohle and Industrieabfälle were
    previously dropped entirely (Kohle: <3% of the combustion total, "the model
    has no boiler technology for it"); both are now included now that
    `coal_boiler_industry`/`waste_boiler_industry` exist. There is no equivalent
    "renewable vs. non-renewable" split in the BFE data the way Eurostat
    distinguishes for the EU nodes — `Industrieabfälle` is used as-is.
  - **2023 values** (the year passed as `FEC_YEAR`, summed across the three
    branches): Erdgas 8596.23 TJ, Heizöl extra-leicht 2353.01 TJ, Heizöl mittel
    und schwer 0 TJ, Holz 1107.70 TJ, Kohle 298.00 TJ, Industrieabfälle 939.16 TJ.
    Shares: natural gas ≈ 64.7%, oil ≈ 17.7%, biomass ≈ 8.3%, coal ≈ 2.2%, waste
    ≈ 7.1%, electrode = 0%. (For comparison, 2022: Erdgas 8666.76 TJ, Heizöl
    extra-leicht 2792.07 TJ, Holz 963.63 TJ, Kohle 371.41 TJ, Industrieabfälle
    926.03 TJ.) This is a substantially different mix from the Austria proxy it
    replaced (natural gas ≈ 34.8%, biomass ≈ 59.3%, oil ≈ 5.9% — Austria's heat
    production is comparatively biomass-heavy, e.g. district heating/CHP, which
    is not representative of Swiss industrial process heat).
  - These shares are applied to Switzerland's own modeled heat demand
    (`total_industry_heat_demand_gw("CH")`) to split its `capacity_existing`
    across the six boiler technologies, same as for Eurostat-covered nodes.
  - **Citation key**: `BFE2025` (BibTeX entry maintained in the paper's own
    `.bib` file, not in this repo — see chat/PR history for the full entry).
- **United Kingdom**: neither Eurostat extract has a 2023 (or later) value for the
  UK in any of the sheets used here (coverage ends after 2019 post-Brexit); the
  latest available year (2019) is used instead for the fuel-mix shares (Natural
  gas: 16321.438 GWh, Primary solid biofuels: 1168.056 GWh, Electricity: 0.0 GWh,
  Oil: 307.701 GWh, Solid fossil fuels/coal and waste: see the 2019 sheet values
  directly).

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
  `natural_gas_boiler_industry`, `oil_boiler_industry`, `coal_boiler_industry`,
  `waste_boiler_industry`) produce only `heat_industry_150_200`. Their full
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

| Category | `capex_specific_storage_energy` / `opex_specific_variable` (EUR/tonproduct) | `energy_to_power_ratio_max` (h) |
|---|---|---|
| Cat 1 | 1 | 336 (2 weeks) |
| Cat 2 | 20 | 48 (2 days) |
| Cat 3 | 1,000 | 2 |

These are internal placeholder assumptions (no literature-derived cost source per
category yet) chosen to give Cat 1 a near-free, long-horizon shape, Cat 3 a
priced-out, short-horizon shape, and Cat 2 something in between.

**Ammonia/methanol LHV conversion**: `ammonia_DSM` and `methanol_DSM` have
`power_unit = "GW"` (their reference carriers are modeled in GW/GWh, not
`tonproduct/hour` — see "Power unit" below), so `capex_specific_storage_energy` and
`opex_specific_variable` need a Euro/GWh value, not Euro/tonproduct. Applying the
table above's raw number directly as Euro/GWh would silently represent a very
different real cost per tonne than for the mass-based DSM technologies (1 GWh is
hundreds of tonnes of ammonia or methanol). Instead, the table value above is
divided by each carrier's lower heating value (LHV) — ammonia 18.6 GJ/t (=
0.005167 GWh/t), methanol 19.9 GJ/t (= 0.005528 GWh/t), both standard literature
figures (IEA-AMF fuel properties for ammonia; H2Tools/EngineeringToolbox calorific
value references for methanol) — to convert the per-tonne placeholder into an
equivalent per-GWh value, preserving the same real cost per tonne of product across
all ten DSM technologies. `energy_to_power_ratio_max` is left unconverted: as a
pure duration (energy/power = time), it is already dimensionally identical whether
power is in `tonproduct/hour` or `GW`.

Resulting Euro/GWh values (Cat value ÷ LHV in GWh/t):

| Category | Ammonia (Euro/GWh) | Methanol (Euro/GWh) |
|---|---|---|
| Cat 1 | ≈ 194 | ≈ 181 |
| Cat 2 | ≈ 3,871 | ≈ 3,618 |
| Cat 3 | ≈ 193,548 | ≈ 180,905 |

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
| `efficiency_charge`               | 0.999                                  |
| `efficiency_discharge`            | 0.999                                  |
| `self_discharge`                  | 0.0 (default)                          |
| `capex_specific_storage_energy`   | by category (see table above)          |
| `opex_specific_variable`          | by category (see table above)          |
| `lifetime`                        | 50 years                               |
| `energy_to_power_ratio_max`       | by category (see table above)          |
| `capacity_limit`                  | 1 × per-node carrier demand            |

- **Near-lossless, not lossless**: `efficiency_charge = efficiency_discharge = 0.999`
  (not the framework default of 1.0), representing an essentially idealized ability to
  reschedule production within a planning period while still closing off a modeling
  loophole: at exactly 1.0, simultaneously charging and discharging the same product
  stock is a free, physically meaningless cycle for the optimizer (net stock change
  zero, net cost zero), so nothing in the model penalizes it. A 0.1% round-trip loss
  makes any such cycling strictly costly without materially affecting real shifting
  behaviour. `self_discharge` is left at 0.0 (default) — unlike TES (see below),
  product stock held in a DSM technology is not physically decaying, only
  time-shifted.
- **Power unit**: `tonproduct/hour`, matching production technology capacity units
  (`GW` for `ammonia_DSM` and `methanol_DSM` — for these two, `capex_specific_storage_energy`
  and `opex_specific_variable` are LHV-converted from the category's per-tonne value
  to an equivalent per-GWh value; see "Ammonia/methanol LHV conversion" above).
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
| biomass_boiler_industry | 25            | DEA "6.2 Boiler, biomass"               |
| natural_gas_boiler_industry | 25        | DEA "6.1 Boiler, gas and oil"           |
| oil_boiler_industry     | 25            | DEA "6.1 Boiler, gas and oil"           |
| electrode_boiler_industry | 25          | DEA "5.1a Electric boiler steam"        |
| coal_boiler_industry    | 25            | DEA "6.3 Boiler, coal"                  |
| waste_boiler_industry   | 30            | Crystal Ball waste_boiler_DH (DH proxy, no DEA industrial sheet exists) |

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
data, 28 countries) for Mannhardt's 11 sectors and for the newly credited sectors
respectively — `E_new_sectors` additionally credits UK emissions for the four new
sectors, see "UK data" below. This avoids needing to recover the unrounded
IPCC/per-capita constants, since `old_budget = B_countries × f_old` is already known
exactly.

**Finding**: Mannhardt's Table A.2 defines "Cement" as CRF `1.A.2.f + 2.A`, where `2.A`
("Mineral Industry") already includes glass (`2.A.3`) and ceramics (`2.A.4`) as
sub-categories, and `1.A.2.f` combustion is a bucket shared across cement/glass/
ceramics that EEA does not split further. So glass's and ceramics' emissions appear to
already be nested inside the existing "cement" budget line. Three variants for
crediting the new sectors were computed from `input_data/Emissionbudget/
sector_emissions_2022.csv` (derived from `UNFCCC_v30.csv`, an EEA GHG-inventory
export, plus UK data — see below; see `input_data/Emissionbudget/
extract_sector_emissions.py`), `E_old_sectors = 2,563,680.16` kt CO2 (28 countries,
unchanged by the UK addition):

| Variant | `E_new_sectors` composition | ΔB | new budget |
|---|---|---|---|
| A — zero increment | paper + food only | 0.5831 Gt | 23.7352 Gt |
| C — process-only | + glass/ceramic process (`2.A.3`, `2.A.4` as ceramics proxy) | 0.7171 Gt | 23.8691 Gt |
| **B — naive full-add (chosen)** | + the entire shared combustion bucket (`1.A.2.f`) added again | **1.4349 Gt** | **24.5869 Gt** |

**Decision**: Variant B is implemented (`DEFAULT_VARIANT = "B"` in
`carbon_budget_allocation.py`) — a +6.20% budget increase, judged a reasonable
estimate of additional European industry emissions for these sectors, while
acknowledging it is the least methodologically clean of the three (it re-adds
combustion emissions already implicit in cement's existing budget share). This
question was raised on the ZEN community forum and is unresolved as of writing (2026);
**the choice may need to be revisited** once a reply is received. All three variants
remain available via the `variant` argument to
`Mannhardt2026CarbonBudgetDataset.get_carbon_emissions_budget()`/
`get_new_sector_emissions()` — switching does not require recomputing the CSV.

Other caveats: ceramics-specific process emissions (CRF `2.A.4.a`) are not broken out
in `UNFCCC_v30.csv`, so the coarser `2.A.4` aggregate (which also includes soda ash
and magnesium production) is used as a proxy for the 28-country figure, slightly
overstating ceramics alone (the UK component does not have this issue — see below).

### UK data

The EEA/UNFCCC extract above excludes the UK entirely. For the four *new* sectors
only — glass, ceramic, paper, food — UK emissions are added on top of the 28-country
total (`emissions_kt_co2_uk` column in `sector_emissions_2022.csv`); `E_old_sectors`
(Mannhardt's 11 original sectors) is deliberately left 28-country-only, so
`old_budget = B_countries × f_old` stays exactly reproducible from Mannhardt's
published numbers.

- **Glass/ceramic** — `BEIS2023`, sheet `1.2` ("Estimated territorial greenhouse gas
  emissions by source category, UK 1990-2021"), 2021 values, cross-checked against
  sheet `6.1`'s IPCC-code mapping. `Glass production` (IPCC `2A3`) is an exact match
  to CRF `2.A.3` → 340.25 kt CO2e. Ceramic sums `Bricks production` + `Fletton brick
  production` + `Other ceramics` (all IPCC `2A4a`) → 335.21 kt CO2e — this is cleaner
  than the 28-country `2.A.4` proxy above, since the UK table separates out soda ash
  (`2A4b`) into its own line instead of bundling it into ceramics.
- **Food/paper** — `ONS2026` ("Atmospheric emissions: greenhouse gases by industry and
  gas"), sheet `CO2`, 2022 values, CO2-only (matching the `Pollutant_name == "CO2"`
  filter used for the EEA extract). Paper = SIC `17` ("Paper and paper products"),
  matching CRF `1.A.2.d` → 3,035.70 kt CO2. Food = SIC `10.1`–`10.9` (food) + `11.01-
  06`/`11.07` (beverages) + `12` (tobacco) → 7,099.60 kt CO2, matching CRF `1.A.2.e`'s
  IPCC definition ("Food, Beverages and Tobacco") exactly.
- `glass_ceramic_shared_combustion` (the CRF `1.A.2.f` bucket variant B re-adds) has
  no clean UK equivalent — BEIS folds that combustion into a single aggregate row
  ("Industrial combustion and electricity (excl. iron and steel)") together with
  several other sub-sectors, so it is left 28-country-only.
- Caveats: BEIS figures are MtCO2e (GHG total) rather than CO2-only like the EEA/ONS
  figures — negligible in practice, since glass/ceramic process emissions are almost
  entirely CO2. ONS figures are on a UK *residence* basis rather than *territorial*
  like BEIS/EEA — immaterial for domestically produced-and-consumed goods like food
  and paper. The BEIS (2021) and ONS (2022) reference years differ slightly, each
  being the latest/closest year available from that source.

Sources:

```bibtex
@techreport{BEIS2023,
  author      = {{Department for Business, Energy and Industrial Strategy}},
  title       = {Final UK Greenhouse Gas Emissions National Statistics: 1990 to 2021},
  institution = {UK Government},
  year        = {2023},
  note        = {Accessed: 2023-06-19},
  url         = {https://www.gov.uk/government/statistics/final-uk-greenhouse-gas-emissions-national-statistics-1990-to-2021}
}
```

```bibtex
@techreport{ONS2026,
  author      = {{Office for National Statistics}},
  title       = {Atmospheric Emissions: Greenhouse Gases by Industry and Gas},
  institution = {Office for National Statistics (ONS), UK},
  year        = {2026},
  note        = {Released 5 June 2026; underlying data from the UK National Atmospheric Emissions Inventory (NAEI), apportioned to SIC 2007 industry codes on a residence basis; Crown copyright, Open Government Licence},
  url         = {https://www.ons.gov.uk/economy/environmentalaccounts/datasets/ukenvironmentalaccountsatmosphericemissionsgreenhousegasemissionsbyeconomicsectorandgasunitedkingdom}
}
```

## Ceramic NG fuel-switch feasibility split (electricity vs. gas)

Sources: `input_data/Rehfeldt2017/Rehfeldt2017.csv` (Rehfeldt2017) and
`input_data/JRC-BAT/JRC_BAT_Ceramic2026.pdf` (JRC-BAT-CER-2026, Final Draft, April 2026).

### How this is used

This split sets `KILN_NG_SWITCHABLE_SHARE["ceramic"]` (see "Ceramic and glass kiln fuel
switching" above): the 97.4% `electrifiable_share` computed below becomes the share of
`ceramic_production`'s direct high-temp `natural_gas` input that is rerouted through the
`fuel_to_kiln` carrier (switchable to `hydrogen_to_kilnfuel`/`electricity_to_kilnfuel`);
the 2.6% `gas_only_share` remainder stays a fixed, non-substitutable `natural_gas` input.

Important framing correction versus how this section originally read: the calculation
below (§4.2.1–4.2.3) derives a feasibility ceiling for **electrification** specifically —
kilns can't reliably run electric above ~1600°C. JRC-BAT-CER-2026 §4.2.4 (hydrogen) was
checked directly and documents **no equivalent temperature ceiling for hydrogen firing** —
only fossil-free-hydrogen-availability, burner-configuration and product-colour caveats,
none of them temperature-dependent. So the 2.6% "locked" `natural_gas` share is really a
conservative stand-in for "can't convert to *any* alternative fuel" (hydrogen included),
not a literal hydrogen limit — it likely overstates how much of ceramic's kiln NG is
genuinely non-substitutable, since hydrogen combustion (unlike electric resistive/
induction heating) is not obviously temperature-constrained in the same way. Applied here
to ceramic's `natural_gas` share specifically (not its total kiln fuel, which also
includes `hard_coal`/`biomass`/`oil`, untouched by `fuel_to_kiln`), since no NG-specific
temperature-bin breakdown exists — this assumes NG's own temperature distribution mirrors
the sector's overall one.

### Method

1. Rehfeldt2017 gives, per ceramic sub-process (tiles/technical/houseware), `fuels_GJ_t`,
   `activity_Mt` (EU28+3), and 5 temperature-bin shares (`<100`, `100–200`, `200–500`,
   `500–1000`, `>1000` °C) of that sub-process's total heat demand.
2. Total fuel demand per sub-process: `fuel_PJ = fuels_GJ_t × activity_Mt` (Mt × GJ/t =
   10⁶ GJ = PJ). Fuel demand per bin: `fuel_PJ × bin_share`.
3. JRC-BAT-CER-2026 §4.2.1–4.2.3 (electrification of intermittent/continuous/hybrid
   kilns) each list, under "Technical considerations relevant to applicability,"
   restricted applicability "above 1 600 °C" — taken here as the electrification
   feasibility cutoff (below: electrifiable; above: gas-only, since electric heating
   elements are stated as unable to reliably sustain these temperatures at the
   document's current technology-readiness level, Table 1-7: CCS/CCU and electrification
   both rated low/TRL 1–2).
4. Rehfeldt's top bin (`>1000°C`) is coarser than the 1600°C cutoff, so it is split
   qualitatively per sub-process using JRC-BAT-CER-2026's own firing-temperature tables
   (§2, Figure 2-4 and per-product tables):
   - **tiles, houseware** (sanitaryware/tableware proxy): typical firing 1000–1400°C
     (below 1600°C) → entire `>1000°C` bin assigned electrifiable.
   - **technical**: firing up to 1600–2500°C reported for some products (§2.3.8.8; e.g.
     SiC firing auxiliaries at 2000–2500°C, though most technical-ceramics examples in
     the document, e.g. electrical insulators at 1300°C, sit below the cutoff) → entire
     `>1000°C` bin conservatively assigned gas-only (worst case; see caveats).

### Formulas

For sub-process `s` with temperature-bin shares `b_i(s)`, `i ∈ {<100, 100–200, 200–500,
500–1000, >1000}`, and `gas_only_flag(s) ∈ {0,1}` (1 = technical, 0 = tiles/houseware):

```
fuel_PJ(s)          = fuels_GJ_t(s) × activity_Mt(s)
fuel_PJ(s, bin_i)   = fuel_PJ(s) × b_i(s)
electrifiable_PJ(s) = fuel_PJ(s) − fuel_PJ(s, ">1000") × gas_only_flag(s)
gas_only_PJ(s)      = fuel_PJ(s) × b_">1000"(s) × gas_only_flag(s)

electrifiable_share = Σ_s electrifiable_PJ(s) / Σ_s fuel_PJ(s)
gas_only_share      = Σ_s gas_only_PJ(s)      / Σ_s fuel_PJ(s)
```

### Computed numbers (Rehfeldt2017.csv, EU28+3 activity basis)

| sub_process | fuels_GJ/t | activity_Mt | fuel_PJ | <1000°C bins (PJ) | >1000°C bin (PJ) | gas_only_flag |
|---|---|---|---|---|---|---|
| tiles | 5.46 | 4.66 | 25.44 | 10.94 | 14.50 | 0 |
| technical | 12.11 | 0.68 | 8.23 | 7.00 | 1.23 | 1 |
| houseware | 24.24 | 0.57 | 13.82 | 4.84 | 8.98 | 0 |
| **total** | | | **47.49** | **22.78** | **24.71** | |

```
electrifiable_PJ = 22.78 (all <1000°C bins) + 14.50 (tiles >1000°C) + 8.98 (houseware >1000°C)
                  = 46.26 PJ
gas_only_PJ       = 1.23 PJ (technical >1000°C bin only)

electrifiable_share ≈ 46.26 / 47.49 ≈ 97.4 %
gas_only_share      ≈  1.23 / 47.49 ≈  2.6 %
```

### Caveats / open decisions before implementation

- Rehfeldt's `>1000°C` bin is not sub-divided at 1600°C; `gas_only_flag=1` for technical
  ceramics assigns its **entire** `>1000°C` bin (1.23 PJ) as non-electrifiable, a
  worst-case simplification — JRC-BAT-CER-2026's own examples suggest most technical-
  ceramics tonnage fires below 1600°C (e.g. electrical insulators at 1300°C using NG),
  with only niche products (SiC firing auxiliaries) needing 2000–2500°C. True gas-only
  share for technical ceramics, and hence for ceramics overall, is likely lower than 2.6%.
- No NG↔electricity/hydrogen efficiency or conversion factor is available from either
  source. JRC-BAT-CER-2026 Chapter 6 explicitly lists "specific energy consumption for
  electric kilns and dryers" as a data gap for future BREF review work. As implemented
  (see "Ceramic and glass kiln fuel switching" above), ceramic's `hydrogen_to_kilnfuel`/
  `electricity_to_kilnfuel` conversion factors reuse glass's own AIDRES-derived route
  ratios as a documented cross-sector proxy, rather than an unjustified 1:1 GJ
  substitution — glass has real per-route GJ/t data (AIDRES2023, see "Glass" above);
  ceramic does not.
- §4.1.6.3.5 (Fuel choice) notes product-driven exceptions independent of temperature:
  certain coloured facing bricks require coal/coal-dust co-firing (Hoffmann kilns) and
  cannot be produced on natural gas alone. This is a small, unquantified additional
  non-substitutable share not captured by the temperature-threshold calculation above.
- §4.2.4 (hydrogen) and §4.2.3 (hybrid kilns) define **partial**-substitution technique
  thresholds — H2 ≥30% of kiln fuel, hybrid ≥50% electric heat — i.e. even within the
  "electrifiable"/"gas-only" categories above, full 100% single-carrier swaps are not
  how these BAT techniques are actually defined. As implemented, `fuel_to_kiln` doesn't
  model these partial-substitution thresholds explicitly — the optimizer is free to mix
  `natural_gas_to_kilnfuel`/`hydrogen_to_kilnfuel`/`electricity_to_kilnfuel` in any
  proportion for the switchable 97.4% share, which can reproduce a ≥30%/≥50% blend as one
  point in its feasible range but isn't constrained to match the BAT techniques' own
  specific operational definitions.
- Real-world adoption is negligible for all these options today (BAT Table 3-201, n=199
  plants surveyed: electrification 6 plants, hydrogen 1 testing kiln, CCS/CCU 0 plants).
  The 97.4%/2.6% split above is a **technical-feasibility ceiling**, not an expected
  near-term deployment share.
