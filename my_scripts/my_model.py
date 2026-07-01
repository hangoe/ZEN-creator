from pathlib import Path

from zen_creator.model import Model

# import sectors (triggers auto-registration via __init_subclass__)
from zen_creator.sectors.industry_heat import IndustryHeat  # noqa: F401
from zen_creator.sectors.industry_flexibility import IndustryFlexibility  # noqa: F401

data_path = "/Users/hannegoericke/ZEN-models/data/Crystal_Ball"
output_path = Path(__file__).parent.parent / "outputs"

model = Model.from_existing(data_path)

# industry_heat must come first: glass/ceramic/paper/food carriers are
# defined here and referenced by the DSM techs in industry_flexibility.
model.add_sector_by_name("industry_heat")
model.add_sector_by_name("industry_flexibility")

model.build()

model.name = "Crystal_Ball_HG_v5_0"
model.output_folder = output_path

model.write()
