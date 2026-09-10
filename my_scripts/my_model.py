import logging
import math
import os
import shutil
from pathlib import Path

from zen_creator.model import Model
from zen_creator.utils.attribute import Attribute
from zen_creator.utils.default_config import Config

# import sectors (triggers auto-registration via __init_subclass__)
from zen_creator.sectors.industry_heat import IndustryHeat  # noqa: F401
from zen_creator.sectors.industry_low_temp_heat import IndustryLowTempHeat  # noqa: F401
from zen_creator.sectors.industry_tes import IndustryTES  # noqa: F401
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
VERSION = "Crystal_Ball_ind_heat_v9_0"

# Case-study scenarios: which sectors are active for each run.
# industry_heat must come first in every combination: glass/ceramic/paper/food
# carriers are defined there and referenced by the DSM/TES/low-temp-heat technologies.
# DSM sectors use the optimistic demand-shiftability category assumptions by default
# (see input_data/DSM_parametrization/DSM_literature_review.md); "_DSM_pessimistic"
# reruns the full-flexibility case with the pessimistic assumptions instead.
MAIN_SECTORS = ["industry_heat", "industry_low_temp_heat", "industry_tes", "industry_dsm_optimistic"]

SCENARIOS = [
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
    # combines _no_flexibility and _single_temp: no TES/DSM flexibility, and
    # only the highest (150-200) temperature band (no industry_low_temp_heat)
    ("_no_flex_single_temp", ["industry_heat"]),
]

DIFFUSION_DISABLED_SUFFIXES = {"_nodiffusion", "_no_flexibility_nodiffusion"}


def disable_diffusion_limits(model: Model) -> None:
    """Set every technology's max_diffusion_rate to inf, in place.

    Must run after model.build() (attributes aren't populated before then) and
    before model.write().
    """
    for technology in model.technologies.values():
        technology.max_diffusion_rate = Attribute(
            "max_diffusion_rate", default_value=math.inf, unit="1", element=technology
        )


def delete_old_outputs(path: Path, keep_names: set[str]) -> None:
    """Delete everything in `path` except entries whose name is in `keep_names`."""
    if not path.exists():
        return
    for entry in path.iterdir():
        if entry.name in keep_names:
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
    output_path, keep_names={f"{VERSION}{suffix}" for suffix, _ in SCENARIOS}
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
    model.name = f"{VERSION}{suffix}"
    model.output_folder = output_path
    model.write()
    logger.info(f"Wrote scenario '{model.name}' ({len(model.elements)} elements).")
