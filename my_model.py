from pathlib import Path
from zen_creator.model import Model
from zen_creator import compare_trees

data_path = "/Users/hannegoericke/ZEN-models/data/Crystal_Ball" # the exiting model
output_path = Path("./outputs") # outputs will be saved here

# load the model
model = Model.from_existing(data_path)

# add new elements to the model and overwrite them with the data from EUROSTAT
path_to_eurostat_data = Path("../ZEN-europe-process-heat")

# discover all carriers and conversion technologies present in the dataset
new_carriers = sorted(
    p.name for p in (path_to_eurostat_data / "set_carriers").iterdir() if p.is_dir()
)
new_conversion_technologies = sorted(
    p.name
    for p in (
        path_to_eurostat_data / "set_technologies" / "set_conversion_technologies"
    ).iterdir()
    if p.is_dir()
)

# add carriers first, since conversion technologies reference them on validation
for carrier_name in new_carriers:
    model.add_element_by_name(carrier_name, generic="carrier")
    model.elements[carrier_name].overwrite_from_existing_model(path_to_eurostat_data)

for tech_name in new_conversion_technologies:
    model.add_element_by_name(tech_name, generic="conversion_technology")
    model.elements[tech_name].overwrite_from_existing_model(path_to_eurostat_data)

print(f"Added carriers: {new_carriers}")
print(f"Added conversion technologies: {new_conversion_technologies}")

# update the model with desired changes
model.name = "Crystal_Ball_HG_v1.0"
model.output_folder = output_path

# save the new model
model.write()

#compare with the previous version if desired
#compare_trees(data_path, model.output_path)