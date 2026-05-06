import json
import argparse
from pathlib import Path
try:
    from src.utils import sql_parser  # when run from project root
except ImportError:
    from utils import sql_parser      # when run directly as src/BFS.py

main_dir = Path(__file__).resolve().parent.parent
TARGET_CATS_PATH = main_dir / "data/output/target_categories.json"

# algorithm to find the target categories
def BFS(page_id: int, target_cats) -> tuple[set, int]:
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
            for inter in new_intersection:
                intersection[inter] = intersection.get(inter, 0) + 1

        old_categories = new_categories - visited
        if not old_categories:
            break
        visited.update(new_categories)

        if intersection:
            max_count = max(intersection.values())
            top = {k for k, v in intersection.items() if v == max_count}
            if counter == 1 and len(top) == 1:           # 1st iteration: unique winner (the counter was increased before, so it's effectively the 1st)
                UNIQUE_TOP = True
            elif 2 <= counter <= 4 and len(top) <= 2:          # 2nd iteration and others: at most 2
                UNIQUE_TOP = True
            elif counter >= 5 and len(top) <= 2 and max_count > 1:  # 5th+ iteration: at most 2 with evidence
                UNIQUE_TOP = True

        counter += 1

    depth = counter - 1

    if not intersection:
        return {"Other"}, depth
    return top, depth


if __name__ == "__main__":

    with open(TARGET_CATS_PATH, "r") as f:
        target_cats = set(json.load(f))

    page_id = int(input("Enter a page_id: "))
    result, depth = BFS(page_id, target_cats)
    print(f"Result: {result} (depth: {depth})")