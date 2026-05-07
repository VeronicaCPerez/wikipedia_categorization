# Wikipedia Categorization

Assigns Wikipedia pages to a structured taxonomy of fields and subfields by traversing the Wikipedia category graph upward using BFS. Each page gets placed into up to three levels: **subsubfield** (specific match), **subfield** (parent group), and **sector** (top-level domain). A `technical_subfield` flag marks pages in science, engineering, medicine, and related disciplines.

---

## How it works

Starting from a `page_id`, the algorithm walks **up** the Wikipedia category graph layer by layer — from the page's own categories, then their parent categories, and so on. At each layer it checks how many paths reach one of the ~270 predefined target categories, accumulating a depth-weighted score (`weight = 1 / depth`). It exits early when a confident winner emerges, or stops after 5 layers.

Hidden categories (maintenance, stubs, cleanup tags) are filtered out. Cycles in the Wikipedia category graph are handled via a visited set.

### Tiebreaking rules

When multiple categories are tied in score:
1. **Tech preference** — if any tied category belongs to a subfield marked `techs_related=1`, non-tech categories are dropped.
2. **Same subfield** — if all tied categories belong to the same subfield, the result is accepted immediately.

### Exit conditions (by depth)

| Depth | Condition |
|-------|-----------|
| 1 | Unique winner |
| 2–3 | At most 2 tied winners |
| 4 | Unique winner + score > 0.33 (must have evidence from shallower depths) |
| 5 | Unique winner + score > 0.5 (strong corroboration required) |

Depth 4–5 results require corroboration from earlier layers, preventing noisy deep-graph hits from dominating.

---

## Category taxonomy

The taxonomy follows [Wikipedia:Contents/Categories](https://en.wikipedia.org/wiki/Wikipedia:Contents/Categories) and is defined in `data/input/final_categories.json`.

There are three levels:

### Sectors (top level)
The 10 broadest domains:

| Sector | Examples |
|--------|---------|
| Mathematics and logic | |
| Natural and physical sciences | |
| Health and fitness | |
| Technology and applied sciences | |
| Human activities | |
| Culture and the arts | |
| Society and social sciences | |
| Geography and places | |
| History and events | |
| Philosophy and thinking | |

### Subfields (middle level)
Each sector contains 1–7 subfields. Examples:
- **Technology and applied sciences** → Computing, Electronics, Engineering, Transport, Energy technology, Robotics and automation, Nanotechnology
- **Health and fitness** → Medicine, Medical technology, Psychology, Public health
- **Natural and physical sciences** → Biology, Chemistry, Physics, Earth sciences, Astronomy

### Subsubfields (leaf level, ~270 categories)
Each subfield contains specific Wikipedia category names used as BFS targets. Examples:
- **Computing** → Artificial intelligence, Machine learning, Computer networks, Programming languages, Application software, Databases, ...
- **Biology** → Genetics, Microbiology, Evolutionary biology, Neuroscience, Biotechnology, ...
- **Medicine** → Pharmacology, Oncology, Cardiology, Epidemiology, Surgery, ...

These are the actual Wikipedia category names the BFS tries to reach. The full list is in `data/output/target_categories.json`.

---

## The `technical_subfield` flag

`technical_subfield = 1` means at least one of the page's matched subfields is marked `techs_related = 1` in the JSON.

This flag covers subfields in science, engineering, medicine, and related applied domains:

| Sector | Technical subfields |
|--------|-------------------|
| Mathematics and logic | Mathematics, Applied mathematics, Statistics, Logic |
| Natural and physical sciences | Biology, Chemistry, Physics, Earth sciences, Astronomy |
| Health and fitness | Medicine, Medical technology |
| Technology and applied sciences | Computing, Electronics, Engineering, Transport, Energy technology, Robotics and automation, Nanotechnology |
| Human activities | Industry and manufacturing, Military and defense, Aviation and spaceflight |

Non-technical subfields (Culture and the arts, Law and government, Economics, Education, etc.) get `technical_subfield = 0`.

Use this flag to filter for pages that are substantively technical/scientific vs. general-interest topics.

---

## Developer setup

### Requirements
- Python 3.13+
- `uv` for dependency management
- MariaDB running locally with the Wikipedia dump loaded

### Configure environment
Create a `.env` file in the project root:
```
DB_PASSWORD=your_password_here
MYSQLD_PATH=E:\mariadb-12.2.2-winx64\bin\mysqld.exe   # Windows server only
```

### MariaDB tables required
The following Wikipedia dump tables must be loaded into a database named `wikipedia`:
- `categorylinks`
- `linktarget`
- `page`
- `page_props`
- `category`

### Install dependencies
```bash
uv sync
```

### Generate target categories
```bash
uv run src/create_target_categories.py
```
Writes `data/output/target_categories.json` — the flat list of ~270 Wikipedia category names the BFS matches against. Re-run this any time `final_categories.json` changes.

---

## Usage

```bash
# Standard run (Mac/Linux)
uv run main.py path/to/your_pages.csv

# Windows server (starts MariaDB automatically)
python main.py path/to/your_pages.csv --start-db

# Start fresh (deletes existing results.db)
uv run main.py path/to/your_pages.csv --overwrite

# Custom page_id column name
uv run main.py path/to/your_pages.csv --id-col primary_page_id
```

Your CSV must have a column containing Wikipedia `page_id` values. The column is `page_id` by default; use `--id-col` to specify a different name. Duplicate IDs are deduplicated automatically.

### Options
| Flag | Description |
|------|-------------|
| `--id-col NAME` | Column name for page IDs (default: `page_id`) |
| `--overwrite` | Delete `results.db` and reprocess everything |
| `--start-db` | Start MariaDB before running (Windows server only) |

---

## Output

### `data/output/results.db`
SQLite database — persists across runs, safe to stop and resume.

| Column | Type | Description |
|--------|------|-------------|
| `page_id` | INTEGER | Wikipedia page ID |
| `page_title` | TEXT | Page title |
| `subsubfields` | JSON list | Matched Wikipedia category names (leaf level) |
| `subfields` | JSON list | Parent subfields of the matches |
| `sectors` | JSON list | Top-level sectors of the matches |
| `depth` | INTEGER | BFS layers used (1 = direct match, 5 = deep traversal) |
| `technical_subfield` | INTEGER | 1 if any matched subfield is technical, else 0 |

### `data/user_outputs/<input_stem>.json`
Written once **all** pages in the CSV are processed. One object per page:

```json
[
  {
    "page_id": 167079,
    "page_title": "Smartphone",
    "subsubfields": ["Consumer electronics", "Telecommunications"],
    "subfields": ["Electronics"],
    "sectors": ["Technology and applied sciences"],
    "technical_subfield": true
  },
  {
    "page_id": 10913,
    "page_title": "Fractal",
    "subsubfields": ["Mathematics"],
    "subfields": ["Mathematics"],
    "sectors": ["Mathematics and logic"],
    "technical_subfield": true
  }
]
```

### `data/output/technical_subfields.json`
Reference file listing all subfields where `techs_related = 1`, with their sector and full list of subsubfields.

---

## Stopping and restarting

Stop the run at any time — it will pick up exactly where it left off.

```
Total pages in CSV:       50000
Already in DB (skipping): 12300
Remaining to process:     37700
```

The JSON output is only written once all pages are done. Partial runs are safe.

---

## Collaboration

`results.db` uses `INSERT OR REPLACE` — safe for multiple people to process different pages. To avoid conflicts:
- Split your CSV into non-overlapping chunks per person
- Do not run `--overwrite` unless you intend to reprocess everything

---

## Project structure

```
wikipedia_categorization/
├── main.py                          # Entry point and orchestration
├── src/
│   ├── BFS.py                       # BFS traversal algorithm
│   ├── create_target_categories.py  # Builds target_categories.json from final_categories.json
│   └── utils/
│       └── sql_parser.py            # MariaDB query functions
├── data/
│   ├── input/
│   │   └── final_categories.json    # Category taxonomy definition
│   └── output/
│       ├── target_categories.json   # Flat list of ~270 BFS target categories
│       ├── technical_subfields.json # All tech subfields with their items
│       ├── results.db               # SQLite results (persists across runs)
│       └── user_outputs/
│           └── <input_stem>.json    # Final JSON output per CSV input
├── wiki_categories_tree.html        # Interactive graph of the category taxonomy
└── .env                             # Not committed — add your own
```
