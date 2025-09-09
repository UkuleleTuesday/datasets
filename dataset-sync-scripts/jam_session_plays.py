#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gspread",
#   "google-auth"
# ]
# ///

"""
Fetch jam session plays data from a Google Sheet and print it.
"""

import gspread
import google.auth


def main() -> None:
    # Authenticates via application default credentials
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(creds)

    spreadsheet_id = "1HeYf0OJHJorY10FIotvVlpdv-xGrmYroABRBxMYrNOQ"
    sh = gc.open_by_key(spreadsheet_id)

    # Process all worksheets except the first one (index 0)
    for worksheet in sh.worksheets()[1:]:
        print(f"--- Processing worksheet: {worksheet.title} ---")
        # Fetches all records from the sheet.
        # Assumes first row is header. Columns are Page, Song, Artist.
        try:
            list_of_hashes = worksheet.get_all_records()
            for row in list_of_hashes:
                print(row)
        except Exception as e:
            print(f"Error processing worksheet {worksheet.title}: {e}")


if __name__ == "__main__":
    main()
