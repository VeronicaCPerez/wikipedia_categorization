import json
import csv
import sqlite3
import argparse
import threading
import subprocess
import time
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from src.BFS import BFS
from src.utils import sql_parser

main_dir = Path(__file__).resolve().parent
TARGET_CATS_PATH = main_dir / "data/output/target_categories.json"
CATEGORIES_JSON_PATH = main_dir / "data/input/final_categories_filtered.json"
DB_PATH = main_dir / "data/output/results.db"



# fields where we collapse everything into the top-level field name
COLLAPSE_TO_FIELD = {"Mathematics and logic", "Natural and physical sciences"}
# subfields where we keep the subfield name as the final label
KEEP_AS_SUBFIELD = {"Computing", "Electronics", "Engineering", "Transport"}
# for General Technology we keep the subsubfield itself as the label


def build_subfield_lookup(categories_json: list) -> dict[str, str]:
    """
    Build a reverse lookup: subsubfield -> final field label.
    - Mathematics and logic / Natural and physical sciences -> field name
    - Computing, Electronics, Engineering, Transport -> subfield name
    - General Technology -> subsubfield name (keep as-is)
    """
    lookup = {}
    for field in categories_json:
        if 'Info' in field:
            continue
        field_name = field.get('field_name', '')
        for subfield in field.get('subfields', []):
            subfield_name = subfield['subfield_name']
            for subsubfield in subfield.get('subsubfields', []):
                if field_name in COLLAPSE_TO_FIELD:
                    lookup[subsubfield] = field_name
                elif subfield_name in KEEP_AS_SUBFIELD:
                    lookup[subsubfield] = subfield_name
                elif subfield_name == "General Technology":
                    lookup[subsubfield] = subsubfield  # keep as-is
            if 'subsubfields' not in subfield:
                if field_name in COLLAPSE_TO_FIELD:
                    lookup[subfield_name] = field_name
                else:
                    lookup[subfield_name] = subfield_name
        
    return lookup


def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            page_id    INTEGER PRIMARY KEY,
            page_title TEXT,
            subfields  TEXT,
            fields     TEXT,
            depth      INTEGER
        )
    """)
    conn.commit()


def is_processed(conn: sqlite3.Connection, page_id: int) -> bool:
    row = conn.execute("SELECT 1 FROM results WHERE page_id = ?", (page_id,)).fetchone()
    return row is not None


def save_result(conn: sqlite3.Connection, page_id: int, page_title: str, subfields: set, fields: set, depth: int):
    conn.execute(
        "INSERT OR REPLACE INTO results (page_id, page_title, subfields, fields, depth) VALUES (?, ?, ?, ?, ?)",
        (page_id, page_title, json.dumps(list(subfields)), json.dumps(list(fields)), depth)
    )
    conn.commit()


def start_mariadb():
    mysqld_path = os.getenv("MYSQLD_PATH")
    if not mysqld_path:
        print("MYSQLD_PATH not set in .env, skipping DB start.")
        return
    print(f"Starting MariaDB from {mysqld_path}...")
    subprocess.Popen([mysqld_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # wait until the server is ready
    import mysql.connector
    for _ in range(30):
        try:
            conn = mysql.connector.connect(host="localhost", user="root", password=os.getenv("DB_PASSWORD", ""), database="wikipedia")
            conn.close()
            print("MariaDB is ready.")
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("MariaDB did not start in time.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_path', help='Path to CSV file with page_id column')
    parser.add_argument('--overwrite', action='store_true', help='Delete existing results and start fresh')
    parser.add_argument('--start-db', action='store_true', help='Start MariaDB server before running (Windows server only)')
    args = parser.parse_args()

    if args.start_db:
        start_mariadb()

    # handle overwrite
    if args.overwrite and DB_PATH.exists():
        DB_PATH.unlink()
        print("Existing results deleted.")

    # load target categories
    with open(TARGET_CATS_PATH, 'r') as f:
        target_cats = set(json.load(f))

    # load reverse lookup
    with open(CATEGORIES_JSON_PATH, 'r') as f:
        categories_json = json.load(f)
    subfield_lookup = build_subfield_lookup(categories_json)

    # read page_ids from csv
    with open(args.csv_path, 'r') as f:
        reader = csv.DictReader(f)
        page_ids = [int(row['page_id']) for row in reader]

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    already_processed = [pid for pid in page_ids if is_processed(conn, pid)]
    to_process = [pid for pid in page_ids if not is_processed(conn, pid)]

    print(f"Total pages in CSV:       {len(page_ids)}")
    print(f"Already in DB (skipping): {len(already_processed)}")
    print(f"Remaining to process:     {len(to_process)}")

    write_lock = threading.Lock()

    def process_page(page_id):
        page_title = sql_parser.get_page_title(page_id)
        subfields, depth = BFS(page_id, target_cats)
        fields = {subfield_lookup[s] for s in subfields if s in subfield_lookup} or {"Other"}
        return page_id, page_title, subfields, fields, depth

    if to_process:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(process_page, pid): pid for pid in to_process}
            for i, future in enumerate(tqdm(as_completed(futures), total=len(to_process), desc="Processing pages")):
                page_id, page_title, subfields, fields, depth = future.result()
                with write_lock:
                    save_result(conn, page_id, page_title, subfields, fields, depth)
                if i % 100 == 0:
                    tqdm.write(f"[{i}] page_id={page_id} | title={page_title} | fields={fields} | depth={depth}")
    else:
        print("All pages already in DB — skipping processing.")

    # check if everything is now in the db
    remaining = [pid for pid in page_ids if not is_processed(conn, pid)]

    if remaining:
        print(f"\n{len(remaining)} pages still unprocessed — JSON will be written on the next run when all are done.")
    else:
        print("All pages processed. Building JSON from DB...")
        placeholders = ",".join("?" * len(page_ids))
        rows = conn.execute(
            f"SELECT page_id, page_title, subfields, fields FROM results WHERE page_id IN ({placeholders})",
            page_ids
        ).fetchall()

        json_results = [
            {
                "page_id": row[0],
                "page_title": row[1],
                "subfields": json.loads(row[2]),
                "fields": json.loads(row[3])
            }
            for row in rows
        ]

        input_stem = Path(args.csv_path).stem
        json_output_path = main_dir / "data/output" / f"{input_stem}.json"
        with open(json_output_path, "w") as f:
            json.dump(json_results, f, indent=2)
        print(f"JSON saved to {json_output_path}")

    conn.close()
    print(f"Results DB at {DB_PATH}")


if __name__ == "__main__":
    main()
