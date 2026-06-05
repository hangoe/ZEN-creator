from pathlib import Path
from zen_creator.model import Model
from zen_creator import compare_trees

data_path = "/Users/hannegoericke/ZEN-models/data/Crystal_Ball" # the exiting model
output_path = Path("./outputs") # outputs will be saved here

# load the model
model = Model.from_existing(data_path)

# update the model here with any desired changes
model.name = "Crystal_Ball_HG_v1.0"
model.output_folder = output_path

# save the new model
model.write()

#compare with the previous version if desired
compare_trees(data_path, model.output_path)