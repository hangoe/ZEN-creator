import logging
import math
import os
import shutil
from pathlib import Path

from zen_creator.model import Model
from zen_creator.utils.attribute import Attribute
from zen_creator.utils.default_config import Config

# import sectors (triggers auto-registration via __init_subclass__)
from zen_creator.sectors.industry_heat import IndustryHeat, IndustryHeatPerSector  # noqa: F401
from zen_creator.sectors.industry_low_temp_heat import (  # noqa: F401
    IndustryLowTempHeat,
    IndustryLowTempHeatPerSector,
)
from zen_creator.sectors.industry_tes import IndustryTES, IndustryTESPerSector  # noqa: F401
from zen_creator.sectors.industry_dsm import (  # noqa: F401
    IndustryDSMOptimistic,
    IndustryDSMPessimistic,
)

# import energy system (triggers auto-registration via __init_subclass__);
# extends carbon_emissions_budget to credit the industry sectors, see
# carbon_budget_allocation.py and ASSUMPTIONS.md ("Carbon emissions budget")
from zen_creator.elements.energy_systems.crystal_ball_industry import (  # noqa: F401
    CrystalBallIndustryEnergySystem,
)

logger = logging.getLogger(__name__)

# Override with the ZEN_CRYSTAL_BALL_DATA_PATH env var to run this on another
# machine/checkout without editing the script.
data_path = Path(
    os.environ.get(
        "ZEN_CRYSTAL_BALL_DATA_PATH",
        "/Users/hannegoericke/ZEN-models/data/Crystal_Ball",
    )
)
if not data_path.exists():
    raise FileNotFoundError(
        f"Data path '{data_path}' does not exist. Set the ZEN_CRYSTAL_BALL_DATA_PATH "
        "env var to point at a valid ZEN-garden input folder."
    )
output_path = Path(__file__).parent.parent / "outputs"
# v10_0: temp-conversion/natural_gas_to_kilnfuel get capacity_existing + capacity_limit,
# heat-tech max_diffusion_rate 0.13 (see ASSUMPTIONS.md, "Technology diffusion"); run
# with interval_between_years = 2 (ZEN-models parameters.csv); industry HPs seeded via capacity_addition_unbounded.
# v11_0: per-sector industry heat - every heat carrier/heat tech/TES exists once per sector,
# boiler capacity_existing split by the sectors' own JRC-IDEES fuel mix (see ASSUMPTIONS.md,
# "Per-sector industry heat (V11)"). Set PER_SECTOR_HEAT = False and VERSION = v10_0 for V10.
PER_SECTOR_HEAT = True
VERSION = "Crystal_Ball_ind_heat_v11_0" if PER_SECTOR_HEAT else "Crystal_Ball_ind_heat_v10_0"
# Only these scenario suffixes are written (None = all of ALL_SCENARIOS).
RUN_SUFFIXES: set[str] | None = {
    "_no_flexibility",
    "_no_flexibility_nodiffusion",
    "_no_flexibility_diff_debug",
}

# Case-study scenarios: which sectors are active for each run.
# industry_heat must come first in every combination: glass/ceramic/paper/food
# carriers are defined there and referenced by the DSM/TES/low-temp-heat technologies.
# DSM sectors use the optimistic demand-shiftability category assumptions by default
# (see input_data/DSM_parametrization/DSM_literature_review.md); "_DSM_pessimistic"
# reruns the full-flexibility case with the pessimistic assumptions instead.
MAIN_SECTORS = ["industry_heat", "industry_low_temp_heat", "industry_tes", "industry_dsm_optimistic"]

ALL_SCENARIOS = [
    ("", MAIN_SECTORS),  # full flexibility (main version)
    ("_no_flexibility", ["industry_heat", "industry_low_temp_heat"]),
    ("_DSM_only", ["industry_heat", "industry_low_temp_heat", "industry_dsm_optimistic"]),
    ("_TES_only", ["industry_heat", "industry_low_temp_heat", "industry_tes"]),
    # single temperature level: only the highest-band heat pumps (no industry_low_temp_heat),
    # everything else including full flexibility stays the same
    ("_single_temp", ["industry_heat", "industry_tes", "industry_dsm_optimistic"]),
    # full flexibility, but with pessimistic DSM demand-shiftability assumptions
    ("_DSM_pessimistic", ["industry_heat", "industry_low_temp_heat", "industry_tes", "industry_dsm_pessimistic"]),
    # same sectors as the main version, but every technology's max_diffusion_rate
    # is overridden to inf (disable_diffusion_limits below) - isolates how much of
    # the main version's trajectory is diffusion-constrained vs. cost-constrained
    ("_nodiffusion", MAIN_SECTORS),
    # combines _no_flexibility and _nodiffusion: no_flexibility sectors, with
    # every technology's max_diffusion_rate also overridden to inf
    ("_no_flexibility_nodiffusion", ["industry_heat", "industry_low_temp_heat"]),
    # v11 debug (run 45): _no_flexibility with capacity_addition_unbounded scaled up
    # for the industry heat pumps/boilers (scale_heat_capacity_addition_unbounded
    # below), to test whether more diffusion headroom fixes the 2a-interval infeasibility
    ("_no_flexibility_diff_debug", ["industry_heat", "industry_low_temp_heat"]),
    # combines _no_flexibility and _single_temp: no TES/DSM flexibility, and
    # only the highest (150-200) temperature band (no industry_low_temp_heat)
    ("_no_flex_single_temp", ["industry_heat"]),
]

DIFFUSION_DISABLED_SUFFIXES = {"_nodiffusion", "_no_flexibility_nodiffusion"}
DIFFUSION_DEBUG_SUFFIXES = {"_no_flexibility_diff_debug"}
DIFFUSION_DEBUG_UNBOUNDED_FACTOR = 5.0

# pooled industry heat sector -> its per-sector (V11) variant; DSM sectors are shared
PER_SECTOR_HEAT_SECTORS = {
    "industry_heat": "industry_heat_per_sector",
    "industry_low_temp_heat": "industry_low_temp_heat_per_sector",
    "industry_tes": "industry_tes_per_sector",
}

SCENARIOS = [
    (suffix, [PER_SECTOR_HEAT_SECTORS.get(s, s) for s in sectors] if PER_SECTOR_HEAT else sectors)
    for suffix, sectors in ALL_SCENARIOS
    if RUN_SUFFIXES is None or suffix in RUN_SUFFIXES
]


def disable_diffusion_limits(model: Model) -> None:
    """Set every technology's max_diffusion_rate to inf, in place.

    Must run after model.build() (attributes aren't populated before then) and
    before model.write().
    """
    for technology in model.technologies.values():
        technology.max_diffusion_rate = Attribute(
            "max_diffusion_rate", default_value=math.inf, unit="1", element=technology
        )


def scale_heat_capacity_addition_unbounded(model: Model, factor: float) -> None:
    """Multiply capacity_addition_unbounded by `factor`, in place, for the
    per-sector industry heat pumps (heat_pump_industry_*_{sector}) and boilers
    (*_boiler_industry_{sector}).

    market_share_unbounded is one system-wide scalar (energy_system attribute),
    so this per-technology attribute is the only heating-only lever. Boilers are
    seeded with 0, so scaling leaves them at 0; only the heat pumps change.
    Must run after model.build() and before model.write().
    """
    sectors = ("paper", "glass", "ceramic", "food")
    for name, technology in model.technologies.items():
        if not name.endswith(tuple(f"_{sector}" for sector in sectors)):
            continue
        if not (name.startswith("heat_pump_industry_") or "_boiler_industry_" in name):
            continue
        attribute = technology.capacity_addition_unbounded
        attribute.default_value = attribute.default_value * factor


def delete_old_outputs(path: Path, keep_names: set[str], prefix: str) -> None:
    """Delete entries in `path` whose name starts with `prefix` (the current VERSION)
    but isn't in `keep_names` - i.e. stale scenarios of this version only. Other
    versions' outputs (e.g. v9_0 while writing v10_0) are never touched."""
    if not path.exists():
        return
    for entry in path.iterdir():
        if not entry.name.startswith(prefix) or entry.name in keep_names:
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()


if not SCENARIOS:
    raise ValueError(
        "SCENARIOS is empty — refusing to run (would delete existing outputs and "
        "write nothing)."
    )

delete_old_outputs(
    output_path, keep_names={f"{VERSION}{suffix}" for suffix, _ in SCENARIOS}, prefix=VERSION
)

# Loaded once and copied per scenario below: reading the existing model's
# system.json and inferring carriers per technology is real disk I/O, and
# every scenario needs it with only `elements.insert.energy_system` differing.
base_config = Config.load_from_existing_model(data_path)
base_config.elements.insert.energy_system = "crystal_ball_industry_energy_system"

for suffix, sectors in SCENARIOS:
    config = base_config.model_copy(deep=True)
    model = Model.from_existing(data_path, config=config)
    n_elements_before = len(model.elements)
    for sector_name in sectors:
        try:
            model.add_sector_by_name(sector_name)
        except ValueError as e:
            raise ValueError(f"Scenario '{VERSION}{suffix}': {e}") from e
    if sectors and len(model.elements) == n_elements_before:
        raise ValueError(
            f"Scenario '{VERSION}{suffix}': sectors {sectors} were added but "
            "contributed no elements to the model."
        )
    model.build()
    if suffix in DIFFUSION_DISABLED_SUFFIXES:
        disable_diffusion_limits(model)
    if suffix in DIFFUSION_DEBUG_SUFFIXES:
        scale_heat_capacity_addition_unbounded(model, DIFFUSION_DEBUG_UNBOUNDED_FACTOR)
    model.name = f"{VERSION}{suffix}"
    model.output_folder = output_path
    model.write()
    logger.info(f"Wrote scenario '{model.name}' ({len(model.elements)} elements).")
