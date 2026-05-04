# Source - https://stackoverflow.com/a/65859846
# Posted by logi-kal
# Retrieved 2026-05-03, License - CC BY-SA 4.0

import requests
import time
import wikipedia
import json 
from pathlib import Path


# DIR
main_dir = Path(__file__).resolve().parent.parent 


print("Loading Target categories")

# Load data
target_cat_path = main_dir / 'data/output' / 'target_categories.json'

with open(target_cat_path, "r") as f:
    target_categories = set(json.load(f))

print(f"Number of target categories {len(target_categories)}")
print(type(target_categories))

def get_categories(title):
    try:
        page = wikipedia.page(title, auto_suggest=False)
        all_categories = page.categories
        
        # Filter out common hidden category prefixes/keywords
        # Most hidden categories start with 'All ', 'Articles ', or 'Webarchive '
        visible_categories = [
            cat for cat in all_categories 
            if not any(hidden in cat for hidden in [
                "Hidden categories", 
                "Articles with", 
                "All articles", 
                "CS1 ", 
                "Commons category link"
            ])
        ]
        return set(visible_categories)

    except requests.exceptions.ConnectionError:
        time.sleep(10)
        return get_categories(title)
    except wikipedia.exceptions.PageError:
        return set()

start_page = "Smartphone"
## get page categories from my wikipedia text
## load it from the sql
page_categories = {"Smartphones", "Cloud clients", "Consumer electronics", "Information appliances",
                   "Personal digital assistants"}
print(type(target_categories))
result_categories = {c:0 for c in target_categories}    # dictionary target category -> number of paths
cached_categories = set()       # monotonically encreasing
backlog = page_categories
print(backlog)
cached_categories.update(backlog)
while (len(backlog) != 0) :
    time.sleep(0.3)
    print("\nBacklog size: %d" % len(backlog))
    cat = backlog.pop()         # pick a category removing it from backlog
    print("Visiting category: " + cat)
    try:
        for parent in get_categories("Category:" + cat) :
            time.sleep(0.3)
            if parent in target_categories :
                print("Found target category: " + parent)
                result_categories[parent] += 1
            elif parent not in cached_categories :
                backlog.add(parent)
                cached_categories.add(parent)
    except KeyError: pass       # current cat may not have "categories" attribute
result_categories = {k:v for (k,v) in result_categories.items() if v>0} # filter not-found categories
print("\nVisited categories: %d" % len(cached_categories))
print("Result: " + str(result_categories))