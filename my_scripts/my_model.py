from pathlib import Path

from zen_creator.model import Model

# import the industry heat sector (registers all elements and the sector)
import zen_creator.elements.industry_heat  # noqa: F401

data_path = "/Users/hannegoericke/ZEN-models/data/Crystal_Ball"
output_path = Path(__file__).parent.parent / "outputs"

model = Model.from_existing(data_path)

model.add_sector_by_name("industry_heat")
model.build()

model.name = "Crystal_Ball_HG_v2_3"
model.output_folder = output_path

model.write()
