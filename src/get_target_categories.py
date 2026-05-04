import json 
from pathlib import Path

# from the categorization in 'final_categories.json'
# define the target categories as all the subsubfields 
# or the subfields when it doesnt have subsubfields

# Get current script directory, go up twice, and join with file name
main_dir = Path(__file__).resolve().parent.parent 
file_path = main_dir / 'data/input' / 'final_categories.json'
output_path = main_dir / 'data/output' / 'target_categories.json'

# Read the file
with open(file_path, 'r') as f:
    cat_dict = json.load(f)

target_list = []

for field in cat_dict:
    if 'Info' in field.keys():
        continue
    else:
        for subfield in field['subfields']:
            if 'subsubfields' not in subfield.keys():
                target_list.append(subfield['subfield_name'])
            else:
                target_list += subfield['subsubfields']

print(f"Number of target categories {len(target_list)}")

with open(output_path, "w") as f:
    json.dump(target_list, f)
