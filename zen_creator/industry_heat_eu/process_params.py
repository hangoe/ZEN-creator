"""
Shared computations for deriving Crystal Ball conversion-technology
parameters from specific energy consumption (SEC) data such as
Rehfeldt et al. (2017) and AIDRES (2023).
"""

from dataclasses import dataclass

from zen_creator.industry_heat_eu.data.rehfeldt2017 import TEMP_BINS

# Bins below the 200 degC threshold become separate low-temperature heat
# carriers: heat_industry_0_100 and heat_industry_100_200.
LOW_TEMP_BINS = ("<100", "100-200")


def activity_weights(data: dict) -> dict:
    """Normalise the 'activity_Mt' field of each sub-process into shares summing to 1."""
    total = sum(entry["activity_Mt"] for entry in data.values())
    return {key: entry["activity_Mt"] / total for key, entry in data.items()}


def weighted_average(data: dict, weights: dict, key: str) -> float:
    """Compute sum(weight_i * data_i[key]) for matching keys."""
    return sum(weights[k] * data[k][key] for k in weights)


def weighted_avg_temp_dist(data: dict, weights: dict) -> dict:
    """Compute the weighted average temperature distribution (shares sum to 1)."""
    result = {b: sum(weights[k] * data[k]["temp_dist"][b] for k in weights) for b in TEMP_BINS}
    total = sum(result.values())
    assert abs(total - 1.0) < 1e-6, f"Temperature shares do not sum to 1: {total}"
    return result


def low_temp_fraction(temp_dist: dict) -> float:
    """Fraction of fuel heat demand at temperatures below 200 degC."""
    return sum(temp_dist[b] for b in LOW_TEMP_BINS)


def GJ_per_t_to_conversion_factor(energy_GJ_t: float) -> float:
    """
    Convert specific energy demand [GJ / t product] to Crystal Ball
    conversion_factor units [GW / (tonproduct / hour)].

    Derivation: 1 t/h x energy_GJ_t [GJ/t] / 3600 [s/h] = energy_GJ_t / 3600 [GW]
    """
    return energy_GJ_t / 3600.0


@dataclass
class SectorParams:
    """Derived per-tonne energy parameters for one conversion technology."""
    fuel_GJ_t: float
    lt_GJ_t_0_100: float    # heat demand in the <100°C bin → heat_industry_0_100
    lt_GJ_t_100_200: float  # heat demand in the 100-200°C bin → heat_industry_100_200
    elec_GJ_t: float
    temp_dist: dict

    @property
    def cf_fuel(self) -> float:
        return GJ_per_t_to_conversion_factor(self.fuel_GJ_t)

    @property
    def cf_lt_0_100(self) -> float:
        return GJ_per_t_to_conversion_factor(self.lt_GJ_t_0_100)

    @property
    def cf_lt_100_200(self) -> float:
        return GJ_per_t_to_conversion_factor(self.lt_GJ_t_100_200)

    @property
    def cf_elec(self) -> float:
        return GJ_per_t_to_conversion_factor(self.elec_GJ_t)

    # ── derived aggregates kept for convenience ───────────────────────────────
    @property
    def lt_GJ_t(self) -> float:
        return self.lt_GJ_t_0_100 + self.lt_GJ_t_100_200

    @property
    def lt_frac(self) -> float:
        total = self.fuel_GJ_t + self.lt_GJ_t
        return self.lt_GJ_t / total if total > 0 else 0.0

    @property
    def cf_lt(self) -> float:
        return GJ_per_t_to_conversion_factor(self.lt_GJ_t)


def compute_sector_params(
    energy_data: dict,
    temp_data: dict,
    weights: dict,
    fuel_key: str = "fuels_GJ_t",
) -> SectorParams:
    """
    Derive weighted-average energy demand and its high-/low-temperature fuel
    split for one sector.

    energy_data and temp_data may be the same dict (e.g. Rehfeldt for both)
    or different dicts (e.g. AIDRES for energy, Rehfeldt for temperature
    distribution), as long as both are keyed by the same sub-process names
    as `weights`.
    """
    fuel_total = weighted_average(energy_data, weights, fuel_key)
    elec = weighted_average(energy_data, weights, "elec_GJ_t")
    temp_dist = weighted_avg_temp_dist(temp_data, weights)
    frac_0_100   = temp_dist["<100"]
    frac_100_200 = temp_dist["100-200"]
    return SectorParams(
        fuel_GJ_t=fuel_total * (1.0 - frac_0_100 - frac_100_200),
        lt_GJ_t_0_100=fuel_total * frac_0_100,
        lt_GJ_t_100_200=fuel_total * frac_100_200,
        elec_GJ_t=elec,
        temp_dist=temp_dist,
    )


def print_summary(sectors: dict[str, SectorParams]) -> None:
    """Print a single consolidated summary table for all sectors."""
    names = list(sectors.keys())
    header = f"{'Parameter':<42}" + "".join(f"{n:>12}" for n in names) + "  Unit"
    print("\n" + "=" * len(header))
    print("SUMMARY")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    def row(label, values, fmt, unit=""):
        print(f"{label:<42}" + "".join(f"{v:>12{fmt}}" for v in values) + f"  {unit}")

    row("fuel (high-temp, >200°C)", [sectors[n].fuel_GJ_t for n in names], ".3f", "GJ/t")
    row("heat_industry_0_100 (<100°C)", [sectors[n].lt_GJ_t_0_100 for n in names], ".3f", "GJ/t")
    row("heat_industry_100_200 (100-200°C)", [sectors[n].lt_GJ_t_100_200 for n in names], ".3f", "GJ/t")
    row("electricity", [sectors[n].elec_GJ_t for n in names], ".3f", "GJ/t")
    row("low-temp fuel fraction", [sectors[n].lt_frac for n in names], ".1%")
    row("cf fuel [GW/(t/h)]", [sectors[n].cf_fuel for n in names], ".8f")
    row("cf heat_industry_0_100 [GW/(t/h)]", [sectors[n].cf_lt_0_100 for n in names], ".8f")
    row("cf heat_industry_100_200 [GW/(t/h)]", [sectors[n].cf_lt_100_200 for n in names], ".8f")
    row("cf electricity [GW/(t/h)]", [sectors[n].cf_elec for n in names], ".8f")
