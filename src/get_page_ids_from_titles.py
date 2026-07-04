import argparse
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import sql_parser

main_dir = Path(__file__).resolve().parent.parent

def get_list_page_titles(titles_csv_path: str, title_col = "title") -> list[str]:
    """
    take a csv and return the list of strings of the titles
    """
    df = pd.read_csv(titles_csv_path)
    titles_list = df[f'{title_col}'].to_list()
    return titles_list

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument("--output", required=True, help="Path to write output CSV")
    parser.add_argument("--title-col", default="page_title", help="Column name containing titles (default: page_title)")
    
    args = parser.parse_args()

    lst_titles = get_list_page_titles(args.input, title_col = args.title_col)
    print(f"titles extracted {len(lst_titles)}")
    result_dict = sql_parser.find_page_title_ids(lst_titles)
    df = pd.DataFrame(result_dict.items(), columns=['page_title', 'page_id'])
    df.to_csv(args.output, index=False)
    print("Saved file")

if __name__ == "__main__":
    main()
