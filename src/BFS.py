import json
from pathlib import Path
try:
    from src.utils import sql_parser  # when run from project root
except ImportError:
    from utils import sql_parser      # when run directly as src/BFS.py

main_dir = Path(__file__).resolve().parent.parent
TARGET_CATS_PATH    = main_dir / "data/output/target_categories.json"
CATEGORIES_JSON_PATH = main_dir / "data/input/final_categories.json"

# algorithm to find the target categories
def BFS(page_id: int, target_cats: set, subfield_lookup: dict, tech_subfields: set) -> tuple[set, int]:
    counter = 1
    intersection = dict()
    old_categories = set()
    visited = set()
    UNIQUE_TOP = False

    while counter <= 5 and not UNIQUE_TOP:
        if counter == 1:
            new_categories = sql_parser.get_categories_for_page(page_id)
        else:
            subcats_ids = sql_parser.get_subcats_ids_for_cats(old_categories)
            new_categories = set()
            for x in subcats_ids:
                new_categories.update(sql_parser.get_categories_for_page(x))

        new_intersection = sql_parser.get_intersection_cat_target(new_categories, target_cats)
        if new_intersection:
            weight = 1 / counter  # depth 1 = 1.0, depth 2 = 0.5, depth 3 = 0.33 ...
            for inter in new_intersection:
                intersection[inter] = intersection.get(inter, 0) + weight

        old_categories = new_categories - visited
        if not old_categories:
            break
        visited.update(new_categories)

        if intersection:
            max_count = max(intersection.values())
            top = {k for k, v in intersection.items() if v == max_count}

            # Rule 1: if tied, prefer tech-related subfields (techs_related=1 in JSON)
            if len(top) > 1:
                tech_top = {k for k in top if subfield_lookup.get(k) in tech_subfields}
                if tech_top:
                    top = tech_top

            # Rule 2: if still tied, all in same subfield -> done
            if len(top) > 1:
                top_subfields = {subfield_lookup.get(k) for k in top}
                if len(top_subfields) == 1:
                    UNIQUE_TOP = True #exits 

            if counter == 1 and len(top) == 1:                        # depth 1: unique winner
                UNIQUE_TOP = True
            elif 2 <= counter <= 3 and len(top) <= 2:               # depth 2–3: at most 2
                UNIQUE_TOP = True
            elif counter == 4 and len(top) == 1 and max_count > 1/3: # depth 4: unique + corroborated
                UNIQUE_TOP = True
            elif counter >= 5 and len(top) == 1 and max_count > 0.5: # depth 5+: unique + strong evidence
                UNIQUE_TOP = True

        counter += 1

    depth = counter - 1

    if not intersection:
        return {"Other"}, depth
    return top, depth


if __name__ == "__main__":

    with open(TARGET_CATS_PATH, "r") as f:
        target_cats = set(json.load(f))

    with open(CATEGORIES_JSON_PATH, "r") as f:
        categories_json = json.load(f)

    subfield_lookup = {
        sub: subfield['subfield_name']
        for field in categories_json if 'Info' not in field
        for subfield in field.get('subfields', [])
        for sub in subfield.get('subsubfields', [])
    }
    tech_subfields = {
        subfield['subfield_name']
        for field in categories_json if 'Info' not in field
        for subfield in field.get('subfields', [])
        if subfield.get('techs_related') == 1
    }

    page_id = int(input("Enter a page_id: "))
    result, depth = BFS(page_id, target_cats, subfield_lookup, tech_subfields)
    print(f"Result: {result} (depth: {depth})")
