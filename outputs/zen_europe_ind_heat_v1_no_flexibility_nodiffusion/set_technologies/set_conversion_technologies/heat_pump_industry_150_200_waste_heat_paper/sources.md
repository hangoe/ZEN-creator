heat_pump_industry_150_200_waste_heat_paper
===========================================

lifetime
--------

Step 1
Technical lifetime for heat_pump_industry_100_200 from DEA sheet '2.b High temp. hp Up to 150'.

**Citation**

Danish Energy Agency (2026). Technology Data for Industrial Process Heat. Technology Data for Industrial Process Heat.

capacity_addition_unbounded
---------------------------

Step 1
heat_pump_industry_150_200_waste_heat_paper capacity_addition_unbounded: Crystal Ball heat_pump_DH installed capacity (1.875 GW EU) / 6 industry HP variants × paper share of band 150_200 heat demand (0.6660) / 28 nodes = 0.00743 GW per node, same value at every node, applied once per investment period. See ASSUMPTIONS.md, 'Technology diffusion'.

**Citation**

ZEN Creator (2024). Industry process technology parametrization. Internal parametrization workbook.

capacity_existing
-----------------

Step 1
Industrial heat pump capacity (zero — no deployed industrial HP capacity).

**Citation**

Eurostat (2024). Eurostat energy balance — gross heat production. Eurostat Energy Balance.

capacity_limit
--------------

Step 1
Waste-heat HP capacity limit for 150_200: sector high-temp fuel demand (paper) × sector-specific low-temp heat share at this level. Source: Rehfeldt2017 temperature distributions, AIDRES2023 (glass), FAOSTAT production data (food); cross-checked against Mathiesen2026 (Heat Roadmap Europe) as a sanity check (see ASSUMPTIONS.md).

**Citation**

ZEN Creator (2024). Industry process technology parametrization. Internal parametrization workbook.

opex_specific_variable
----------------------

Step 1
Variable O&M for heat_pump_industry_100_200 from DEA sheet '2.b High temp. hp Up to 150', interpolated over 2022-2050, expressed as a yearly-variation multiplier on the 2022 value.

**Citation**

Danish Energy Agency (2026). Technology Data for Industrial Process Heat. Technology Data for Industrial Process Heat.

opex_specific_fixed
-------------------

Step 1
Fixed O&M for heat_pump_industry_100_200 from DEA sheet '2.b High temp. hp Up to 150', interpolated over 2022-2050.

**Citation**

Danish Energy Agency (2026). Technology Data for Industrial Process Heat. Technology Data for Industrial Process Heat.

carbon_intensity_technology
---------------------------

Step 1
Carbon intensity for heat_pump_industry (combustion CO2 carried on fuel carrier).

**Citation**

ZEN Creator (2024). Industry heat technology parametrization. Internal parametrization workbook.

capex_specific_conversion
-------------------------

Step 1
Nominal investment for heat_pump_industry_100_200 from DEA sheet '2.b High temp. hp Up to 150', interpolated over 2022-2050. Plus a flat 1500 Euro/kW waste-heat recovery add-on (approximation within Stark et al. 2025, Joule 9, 102157, Table 2: ~1,234-1,645 Euro/kW).

**Citation**

Danish Energy Agency (2026). Technology Data for Industrial Process Heat. Technology Data for Industrial Process Heat.