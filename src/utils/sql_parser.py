import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()


# connect to local mariadb
def _get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD", ""),
        database="wikipedia"
    )

def get_page_title(page_id: int) -> str:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT page_title FROM page where page_id = %s
        """,
        (page_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0].decode('utf-8') if row else None

# from categorylinks get cl_target_id - input page id
# filter by hidden -> so we don't get the hidden categories
def get_categories_for_page(page_id: int) -> set[str]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT lt_title
        FROM categorylinks
        JOIN linktarget ON cl_target_id = lt_id
        LEFT JOIN page ON lt_title = page_title AND page_namespace = 14
        LEFT JOIN page_props ON page_id = pp_page AND pp_propname = 'hiddencat'
        WHERE cl_from = %s
        AND pp_page IS NULL
        """,
        (page_id,)
    )
    results = {row[0].decode('utf-8') for row in cursor.fetchall()} # set so we dont get double
    cursor.close()
    conn.close()
    return results

def get_intersection_cat_target(results_search: set, target_cats) -> bool:
    clean_results = {x.replace('_', ' ') for x in results_search}
    
    return clean_results & target_cats

def _find_lt_title_id(lt_title: str) -> int:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT page_id FROM page WHERE page_title = %s AND page_namespace = 14
        """,
        (lt_title,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None


def get_subcats_ids_for_cats(current_cats_titles: set) -> list:
    current_cats_id = [_find_lt_title_id(x) for x in current_cats_titles if x] # we could get non from _get_subcats_ids_for_cats 
    return [x for x in current_cats_id if x is not None]