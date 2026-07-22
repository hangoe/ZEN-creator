import shutil
from pathlib import Path

from zen_creator.model import Model
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
# extends carbon_emissions_budget to credit the new industry sectors, see
# carbon_budget_allocation.py and ASSUMPTIONS.md ("Carbon emissions budget")
from zen_creator.elements.energy_systems.crystal_ball_industry import (  # noqa: F401
    CrystalBallIndustryEnergySystem,
)

data_path = "/Users/hannegoericke/ZEN-models/data/Crystal_Ball"
output_path = Path(__file__).parent.parent / "outputs"
VERSION = "Crystal_Ball_HG_v6_0"

# Case-study scenarios from MT_report_HG/Sections/03_SI.tex (table:SIScenarios).
# industry_heat must come first in every combination: glass/ceramic/paper/food
# carriers are defined there and referenced by the DSM/TES/low-temp-heat technologies.
# DSM sectors use the optimistic demand-shiftability category assumptions by default
# (see input_data/DSM_parametrization/DSM_literature_review.md); "_DSM_pessimistic"
# reruns the full-flexibility case with the pessimistic assumptions instead.
SCENARIOS = [
    ("", ["industry_heat", "industry_low_temp_heat", "industry_tes", "industry_dsm_optimistic"]),  # full flexibility (main version)
    ("_no_flexibility", ["industry_heat", "industry_low_temp_heat"]),
    ("_DSM_only", ["industry_heat", "industry_low_temp_heat", "industry_dsm_optimistic"]),
    ("_TES_only", ["industry_heat", "industry_low_temp_heat", "industry_tes"]),
    # single temperature level: only the highest-band heat pumps (no industry_low_temp_heat),
    # everything else including full flexibility stays the same
    ("_single_temp", ["industry_heat", "industry_tes", "industry_dsm_optimistic"]),
    # full flexibility, but with pessimistic DSM demand-shiftability assumptions
    ("_DSM_pessimistic", ["industry_heat", "industry_low_temp_heat", "industry_tes", "industry_dsm_pessimistic"]),
]


def archive_existing_outputs(path: Path, keep_names: set[str]) -> None:
    """Move everything currently in `path` into `path / "archive"`.

    Run at the start of every model-generation run so that only the models
    written by the current run sit directly under `outputs/`. Entries whose
    name is in `keep_names` (i.e. this run is about to regenerate them under
    the same name) are left in place for `model.write()` to overwrite.
    """
    archive_path = path / "archive"
    archive_path.mkdir(parents=True, exist_ok=True)
    for entry in path.iterdir():
        if entry == archive_path or entry.name in keep_names:
            continue
        destination = archive_path / entry.name
        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        shutil.move(str(entry), str(destination))


archive_existing_outputs(
    output_path, keep_names={f"{VERSION}{suffix}" for suffix, _ in SCENARIOS}
)

for suffix, sectors in SCENARIOS:
    config = Config.load_from_existing_model(data_path)
    config.elements.insert.energy_system = "crystal_ball_industry_energy_system"
    model = Model.from_existing(data_path, config=config)
    for sector_name in sectors:
        model.add_sector_by_name(sector_name)
    model.build()
    model.name = f"{VERSION}{suffix}"
    model.output_folder = output_path
    model.write()
