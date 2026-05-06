# README

In this project we try to categorize all wikititles into a "technology" field

For this we use the wikipedia categories. 

We start from the wikipedia [Category Tree](https://en.wikipedia.org/wiki/Wikipedia:Contents/Categories). Not that this graph can have loops, and it's overall... a mess.

We define *Fields*: `Mathematics and logic`, 

I dropped Nature, and from General Technology i DROPPED marketing, design, health sciences, "Information science". Computing and society, "Surveillance", Formal sciences, "Firefighting", "Digital divide",  "Communication" Scientific method

two options 

1. Take the wikipedia categories and find the "closest path" to a one of our targets
2. Count the number of times each page reaches one of the targets and keep the one that it hits the most

The goal is to assign everything to the fields and subfields in "final_categories". We also keep track of the sub_subfileds. We can try to find the top-5

Breadth-first search (BFS) start at tree root and explore all nodes at the present depth prior to moving on to the nodes at the next depth level. Once in layer n+1 we find a "target" category, then that's our goal

actually Iterative deepening depth-first search

# Code

build from [this guy](https://stackoverflow.com/questions/65791801/get-more-general-category-from-the-category-of-a-wikipedia-page) 

```
# Source - https://stackoverflow.com/a/65859846
# Posted by logi-kal
# Retrieved 2026-05-03, License - CC BY-SA 4.0

import requests
import time
import wikipedia

def get_categories(title) :
    try : return set(wikipedia.page(title, auto_suggest=False).categories)
    except requests.exceptions.ConnectionError :
        time.sleep(10)
        return get_categories(title)

start_page = "Hamburger"
target_categories = {"Academic disciplines", "Business", "Concepts", "Culture", "Economy", "Education", "Energy", "Engineering", "Entertainment", "Entities", "Ethics", "Events", "Food and drink", "Geography", "Government", "Health", "History", "Human nature", "Humanities", "Knowledge", "Language", "Law", "Life", "Mass media", "Mathematics", "Military", "Music", "Nature", "Objects", "Organizations", "People", "Philosophy", "Policy", "Politics", "Religion", "Science and technology", "Society", "Sports", "Universe", "World"}
result_categories = {c:0 for c in target_categories}    # dictionary target category -> number of paths
cached_categories = set()       # monotonically encreasing
backlog = get_categories(start_page)
cached_categories.update(backlog)
while (len(backlog) != 0) :
    print("\nBacklog size: %d" % len(backlog))
    cat = backlog.pop()         # pick a category removing it from backlog
    print("Visiting category: " + cat)
    try:
        for parent in get_categories("Category:" + cat) :
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
```

Possible improvements

There are so many improvements for optimizing or approximating this algorithm. The first that come to my mind:

1. Consider keeping track of the path length and suppose that the target category with the shortest path is the most relevant one.
2. Reduce the execution time:
    - You can reduce the number of steps by stopping the script after the first target category occurrence (or at the N-th occurrence).
    - If you execute this algorithm starting from multiple articles, you can keep in memory the information which associates eventual target categories to every category that you met. For example, after your "Hamburger" run you will know that starting from "Category:Fast food" you will get to "Category:Economy", and this can be a precious information. This will be expensive in terms of space, but eventually will help you reducing the execution time.
3. Use as label only the target categories that are more frequent. E.g. if your result is {"Food and drinks" : 37, "Economy" : 4}, you may want to keep only "Food and drinks" as label. For doing this you can:
    - take the N most occurring target categories;
    - take the most relevant fraction (e.g. the first half, or third, or fourth);
    - take the categories which occurr at least N% of times w.r.t. the most frequent one;
    - use more sophisticated statistical tests for analyzing statistical significance of frequency.

I want to:

I'm going to build a network of the categories, so that i can fill in spaces and search for a parent that links me to one of the main categories without wasting time 

# issue: not necessarily hitting lal the categories

