Industry Heat & Sectors
========================

Overview
--------

``zen_creator`` ships a full working implementation of industrial process
heat modeling on top of the generic ``Sector``/``Element``/``Dataset``
architecture described elsewhere in this API reference. This page is a map
of that implementation -- which sectors exist, which elements they group,
and which datasets back them -- rather than a full class-by-class reference
(see the source modules listed below for detailed docstrings).

Sectors
-------

Four sectors live in ``zen_creator/sectors/``:

- ``industry_heat`` (``IndustryHeat``): the core sector -- glass/ceramic/
  paper/food product carriers and production technologies, the
  heat_industry_* energy carriers, boilers, the 150-200C heat pumps, the
  temperature downgrade cascade, kiln-fuel-switching technologies, and the
  ceramic/glass post-combustion carbon-capture retrofits.
- ``industry_low_temp_heat`` (``IndustryLowTempHeat``): the 0-100C and
  100-150C heat pumps, split out so a "single temperature level" model
  variant can omit them. Requires ``industry_heat`` to be added first.
- ``industry_tes`` (``IndustryTES``): thermal energy storage technologies for
  all three temperature bands. Requires ``industry_heat`` first.
- ``industry_dsm_optimistic`` / ``industry_dsm_pessimistic``
  (``IndustryDSMOptimistic``, ``IndustryDSMPessimistic``): demand-side
  management storage technologies for both the industry_heat product
  carriers and several pre-existing Crystal Ball carriers (ammonia, clinker,
  methanol, primary/secondary steel, olefin). Requires ``industry_heat``
  first.

See ``zen_creator/sectors/*.py`` for the exact element lists, and
``my_scripts/my_model.py`` for how these four sectors are combined into the
model's scenario variants.

Elements
--------

- ``zen_creator/elements/carriers/industry_carriers.py`` -- product carriers
  (Glass, Ceramic, Paper, Food) and energy carriers (HeatIndustry0100/
  100150/150200, FuelToKiln).
- ``zen_creator/elements/conversion_technologies/industry_production.py`` --
  the four production technologies (GlassProduction, CeramicProduction,
  PaperProduction, FoodProduction).
- ``zen_creator/elements/conversion_technologies/industry_heat_supply.py`` --
  heat pumps, boilers, the temperature downgrade cascade, and kiln-fuel-
  switching technologies.
- ``zen_creator/elements/conversion_technologies/industry_ccs.py`` --
  ceramic/glass post-combustion carbon-capture retrofits.
- ``zen_creator/elements/storage_technologies/industry_TES.py`` and
  ``industry_DSM.py`` -- thermal storage and demand-side-management
  technologies.
- ``zen_creator/elements/energy_systems/crystal_ball_industry.py`` --
  ``CrystalBallIndustryEnergySystem``, which extends the Crystal Ball base
  model's carbon emissions budget to credit the new sectors.

Datasets
--------

``zen_creator/datasets/datasets/`` holds one ``Dataset`` subclass per raw
data source: ``dea_industrial_heat.py`` (Danish Energy Agency heat pump/
boiler cost data), ``eurostat_boiler.py`` (Eurostat gross heat production),
``jrc_idees_industry.py`` and ``faostat_food.py`` (capacity/demand),
``heat_tech_parametrization.py`` and ``process_parametrization.py``
(internal parametrization workbooks), ``post_comb_cc.py`` and
``waste_boiler_dh_proxy.py`` (carbon capture and waste-boiler proxies),
``mayer2024.py`` and ``liu2025.py`` (thermal/ammonia storage literature
data), and ``carbon_budget_allocation.py`` (the carbon budget extension used
by ``CrystalBallIndustryEnergySystem``). ``_industry_heat_utils.py``
consolidates the shared unit-conversion, weighted-average, and per-node
capacity/demand helpers these datasets build on.

See ``input_data/ASSUMPTIONS.md`` for the full sourcing and methodology
writeup behind every dataset and parametrization choice referenced above.
