#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gspread"
# ]
# ///

"""
Fetch jam session plays data from a Google Sheet and print it.
"""

import gspread


def main() -> None:
    # Authenticates via application default credentials
    gc = gspread.service_account()
    
    spreadsheet_id = "1HeYf0OJHJorY10FIotvVlpdv-xGrmYroABRBxMYrNOQ"
    sh = gc.open_by_key(spreadsheet_id)

    worksheet = sh.get_worksheet(0)  # First tab

    # Fetches all records from the sheet.
    # Assumes first row is header. Columns are Page, Song, Artist.
    list_of_hashes = worksheet.get_all_records()

    for row in list_of_hashes:
        print(row)


if __name__ == "__main__":
    main()
