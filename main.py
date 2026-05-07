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
TARGET_CATS_PATH     = main_dir / "data/output/target_categories.json"
CATEGORIES_JSON_PATH = main_dir / "data/input/final_categories.json"
DB_PATH              = main_dir / "data/output/results.db"


def build_lookups(categories_json: list) -> tuple[dict, dict, set]:
    """
    Returns three structures built from the categories JSON:
      - subsubfield_to_subfield : "Artificial intelligence" -> "Computing"
      - subsubfield_to_sector   : "Artificial intelligence" -> "Technology and applied sciences"
      - tech_subfields          : set of subfield names where techs_related=1
    """
    sub_to_subfield = {}
    sub_to_sector   = {}
    tech_subfields  = set()

    for field in categories_json:
        if 'Info' in field:
            continue
        sector = field['field_name']
        for subfield in field.get('subfields', []):
            sf_name = subfield['subfield_name']
            if subfield.get('techs_related') == 1:
                tech_subfields.add(sf_name)
            for subsubfield in subfield.get('subsubfields', []):
                sub_to_subfield[subsubfield] = sf_name
                sub_to_sector[subsubfield]   = sector

    return sub_to_subfield, sub_to_sector, tech_subfields

def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            page_id      INTEGER PRIMARY KEY,
            page_title   TEXT,
            subsubfields TEXT,
            subfields    TEXT,
            sectors      TEXT,
            depth        INTEGER
        )
    """)
    conn.commit()


def is_processed(conn: sqlite3.Connection, page_id: int) -> bool:
    return conn.execute(
        "SELECT 1 FROM results WHERE page_id = ?", (page_id,)
    ).fetchone() is not None


def save_result(conn, page_id, page_title, subsubfields, subfields, sectors, depth):
    conn.execute(
        """INSERT OR REPLACE INTO results
           (page_id, page_title, subsubfields, subfields, sectors, depth)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (page_id, page_title,
         json.dumps(sorted(subsubfields)),
         json.dumps(sorted(subfields)),
         json.dumps(sorted(sectors)),
         depth)
    )
    conn.commit()


def start_mariadb():
    mysqld_path = os.getenv("MYSQLD_PATH")
    if not mysqld_path:
        print("MYSQLD_PATH not set in .env, skipping DB start.")
        return
    print(f"Starting MariaDB from {mysqld_path}...")
    subprocess.Popen([mysqld_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import mysql.connector
    for _ in range(30):
        try:
            c = mysql.connector.connect(host="localhost", user="root",
                                        password=os.getenv("DB_PASSWORD", ""),
                                        database="wikipedia")
            c.close()
            print("MariaDB is ready.")
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("MariaDB did not start in time.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_path', help='Path to CSV file with page_id column')
    parser.add_argument('--id-col', default='page_id',
                        help='Column name for page IDs in the CSV (default: page_id)')
    parser.add_argument('--overwrite', action='store_true',
                        help='Delete existing results and start fresh')
    parser.add_argument('--start-db', action='store_true',
                        help='Start MariaDB server before running (Windows only)')
    args = parser.parse_args()

    if args.start_db:
        start_mariadb()

    if args.overwrite and DB_PATH.exists():
        DB_PATH.unlink()
        print("Existing results deleted.")

    with open(TARGET_CATS_PATH, 'r') as f:
        target_cats = set(json.load(f))

    with open(CATEGORIES_JSON_PATH, 'r') as f:
        categories_json = json.load(f)

    sub_to_subfield, sub_to_sector, tech_subfields = build_lookups(categories_json)

    # read page_ids — deduplicate while preserving order
    with open(args.csv_path, 'r') as f:
        reader = csv.DictReader(f)
        seen, page_ids = set(), []
        for row in reader:
            pid = int(row[args.id_col])
            if pid not in seen:
                seen.add(pid)
                page_ids.append(pid)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    already_done = sum(1 for pid in page_ids if is_processed(conn, pid))
    to_process   = [pid for pid in page_ids if not is_processed(conn, pid)]

    print(f"Total pages in CSV:       {len(page_ids)}")
    print(f"Already in DB (skipping): {already_done}")
    print(f"Remaining to process:     {len(to_process)}")

    write_lock = threading.Lock()

    def process_page(page_id):
        page_title  = sql_parser.get_page_title(page_id)
        subsubfields, depth = BFS(page_id, target_cats, sub_to_subfield, tech_subfields)
        subfields = {sub_to_subfield.get(s, "Other") for s in subsubfields}
        sectors   = {sub_to_sector.get(s,   "Other") for s in subsubfields}
        return page_id, page_title, subsubfields, subfields, sectors, depth

    if to_process:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(process_page, pid): pid for pid in to_process}
            for i, future in enumerate(tqdm(as_completed(futures),
                                            total=len(to_process),
                                            desc="Processing pages")):
                page_id, page_title, subsubfields, subfields, sectors, depth = future.result()
                with write_lock:
                    save_result(conn, page_id, page_title, subsubfields, subfields, sectors, depth)
                if i % 100 == 0:
                    tqdm.write(
                        f"[{i}] page_id={page_id} | title={page_title} "
                        f"| subfields={subfields} | sectors={sectors} | depth={depth}"
                    )
    else:
        print("All pages already in DB — skipping processing.")

    remaining = [pid for pid in page_ids if not is_processed(conn, pid)]

    if remaining:
        print(f"\n{len(remaining)} pages still unprocessed — run again to continue.")
    else:
        print("All pages processed. Building JSON output...")
        placeholders = ",".join("?" * len(page_ids))
        rows = conn.execute(
            f"""SELECT page_id, page_title, subsubfields, subfields, sectors
                FROM results WHERE page_id IN ({placeholders})""",
            page_ids
        ).fetchall()

        json_results = [
            {
                "page_id":      row[0],
                "page_title":   row[1],
                "subsubfields": json.loads(row[2]),
                "subfields":    json.loads(row[3]),
                "sectors":      json.loads(row[4]),
            }
            for row in rows
        ]

        input_stem = Path(args.csv_path).stem
        out_dir = main_dir / "data/user_outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_output_path = out_dir / f"{input_stem}.json"
        with open(json_output_path, "w") as f:
            json.dump(json_results, f, indent=2)
        print(f"JSON saved to {json_output_path}")

    conn.close()
    print(f"Results DB at {DB_PATH}")


if __name__ == "__main__":
    main()
