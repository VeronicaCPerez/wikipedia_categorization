import json
import argparse
from pathlib import Path

main_dir = Path(__file__).resolve().parent.parent
file_path = main_dir / 'data/input' / 'final_categories.json'
output_path = main_dir / 'data/output' / 'target_categories.json'

with open(file_path, 'r') as f:
    cat_dict = json.load(f)


def get_all_categories() -> list[str]:
    """Return all subsubfields, or subfields when no subsubfields exist."""
    target_list = []
    for field in cat_dict:
        if 'Info' in field.keys():
            continue
        for subfield in field['subfields']:
            if 'subsubfields' not in subfield.keys():
                target_list.append(subfield['subfield_name'])
            else:
                target_list += subfield['subsubfields']
    return target_list

if __name__ == "__main__":

    target_list = get_all_categories()

    print(f"Number of target categories: {len(target_list)}")
    print(target_list)

    with open(output_path, "w") as f:
        json.dump(target_list, f)
