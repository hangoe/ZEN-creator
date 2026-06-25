from pathlib import Path

from zen_creator.model import Model

# import the industry heat sector (registers all elements and the sector)
from zen_creator.sectors.industry_heat import IndustryHeat  # noqa: F401

# import TES storage technologies (registers them in the Element registry)
from zen_creator.elements.storage_technologies.industry_TES import (  # noqa: F401
    IndustryTESSteam,
    IndustryTESWater,
)

data_path = "/Users/hannegoericke/ZEN-models/data/Crystal_Ball"
output_path = Path(__file__).parent.parent / "outputs"

model = Model.from_existing(data_path)

model.add_sector_by_name("industry_heat")

# v5_0: add industry thermal energy storage technologies
model.add_element(IndustryTESWater)
model.add_element(IndustryTESSteam)

model.build()

model.name = "Crystal_Ball_HG_v4_0"
model.output_folder = output_path

model.write()
