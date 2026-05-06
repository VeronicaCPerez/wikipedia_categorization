# Wikipedia Categorization

Assigns Wikipedia pages to a set of predefined fields and subfields by traversing the Wikipedia category graph upward using BFS.

**Output fields:** `Mathematics and logic`, `Natural and physical sciences`, `Computing`, `Electronics`, `Engineering`, `Transport`, and individual General Technology subfields (e.g. `Robotics`, `Agriculture`). Pages that don't match any field are assigned `Other`.

---

## How it works

Starting from a `page_id`, the algorithm walks up the Wikipedia category graph layer by layer, counting how many paths reach each target category. It exits early when a confident winner emerges, or runs up to 6 layers.

Hidden categories (maintenance, stub, cleanup) are filtered out. Cycles in the category graph are handled via a visited set.

---

## Developer Setup

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

### Generate target categories
```bash
uv run src/create_target_categories.py
```
This writes `data/output/target_categories.json` which the BFS uses.

## User Setup

### Requirements
- Python 3.13+
- `uv` for dependency management

### Install dependencies
```bash
uv sync
```

---

## Usage

For windows server 

```bash
uv run main.py path/to/your_pages.csv --start-db
```

Your CSV must have a `page_id` column.

### Options
| Flag | Description |
|------|-------------|
| `--overwrite` | Delete `results.db` and start fresh |
| `--start-db` | Start MariaDB before running (Windows server only) |

### Example
```bash
# normal run (Veronica)
uv run main.py data/input/tech_pages_v3.0.csv

# start fresh
uv run main.py data/input/tech_pages_v3.0.csv --overwrite

# windows server
python main.py data/input/tech_pages_v3.0.csv --start-db
```

---

## Output

Results are saved to two places:

**`data/output/results.db`** — SQLite database, persists across runs. Each row:
| column | description |
|--------|-------------|
| `page_id` | Wikipedia page ID |
| `page_title` | Page title |
| `subfields` | JSON list of matched subfields |
| `fields` | JSON list of matched fields |
| `depth` | Number of BFS layers used |

**`data/output/<input_stem>.json`** — Only written once **all** page_ids in the CSV have been processed. Schema:
```json
[
  {
    "page_id": 167079,
    "page_title": "Smartphone",
    "subfields": ["Consumer electronics", "Telecommunications"],
    "fields": ["Electronics"]
  }
]
```

---

## Stopping and restarting

You can stop the run at any time and restart — it will pick up exactly where it left off. The JSON is only written when all pages in the CSV are done.

```
Total pages in CSV:       50000
Already in DB (skipping): 12300
Remaining to process:     37700
```

---

## Collaboration / avoiding conflicts on results.db

`results.db` uses `INSERT OR REPLACE` — if two people process the same `page_id`, the last write wins. To avoid conflicts:

- **Do not run `--overwrite`** unless you intend to reprocess everything

---

## Project structure

```
wikipedia_categorization/
├── main.py                         # entry point
├── src/
│   ├── BFS.py                      # BFS algorithm
│   ├── create_target_categories.py # builds target_categories.json
│   └── utils/
│       └── sql_parser.py           # MariaDB query functions
├── data/
│   ├── input/
│   │   └── final_categories_filtered.json
│   └── output/
│       ├── target_categories.json
│       ├── results.db
│       └── <input_stem>.json
└── .env                            # not committed — add your own
```
