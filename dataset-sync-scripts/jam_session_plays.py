#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gspread",
#   "google-auth",
#   "google-api-python-client"
# ]
# ///

"""
Fetch jam session plays data from a Google Sheet and print it.
"""

import datetime
import json
import uuid

import gspread
import google.auth
from googleapiclient.discovery import build


def transform_to_session(spreadsheet_name: str, worksheet) -> dict:
    try:
        session_date_str = worksheet.title
        session_date = datetime.datetime.strptime(session_date_str, "%Y/%m/%d").date()
    except ValueError:
        print(f"Skipping worksheet with invalid date format title: {worksheet.title}")
        return None

    session = {
        "session_id": str(uuid.uuid4()),
        "date": session_date.isoformat(),
        "venue": None,
        "source_sheet": spreadsheet_name,
        "ingested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "events": [],
        "requests": [],  # Per schema, but no source data for this yet
    }

    values = worksheet.get("A:D")
    if not values or len(values) < 2:
        return None  # No data or header only

    header = values[0]
    position = 1
    break_found = False

    for row_values in values[1:]:
        padded_row = row_values + [""] * (len(header) - len(row_values))
        row_dict = dict(zip(header, padded_row))

        page = row_dict.get("Page", "").strip()
        song = row_dict.get("Song", "").strip()
        artist = row_dict.get("Artist", "").strip()

        if not page and not song and not artist:
            if not break_found:
                session["events"].append({"position": position, "type": "break"})
                break_found = True
                position += 1
            else:
                # After a break, an empty row signifies the end of songs for the session
                break
            continue

        requested_by = row_dict.get("Requested By", "").strip() or None
        if requested_by not in ["A", "G", "O"]:
            requested_by = None

        event = {
            "position": position,
            "type": "song",
            "page": page,
            "song": song,
            "artist": artist,
            "requested_by_code": requested_by,
        }
        session["events"].append(event)
        position += 1

    return session


def main() -> None:
    # Authenticates via application default credentials
    creds, _ = google.auth.default(
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
    )
    gc = gspread.authorize(creds)
    drive_service = build("drive", "v3", credentials=creds)

    folder_id = "1TY4KCBrbHODyCKCtWXgtNlCHs2-8Svpd"
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    response = (
        drive_service.files()
        .list(q=query, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True)
        .execute()
    )
    spreadsheets = response.get("files", [])

    for spreadsheet in spreadsheets:
        print(f"Processing spreadsheet: {spreadsheet['name']}")
        sh = gc.open_by_key(spreadsheet["id"])

        # Process all worksheets except the first one (index 0)
        for worksheet in sh.worksheets()[1:]:
            print(f"--- Processing worksheet: {worksheet.title} ---")
            # Fetches all records from columns A-D of the sheet.
            # Assumes first row is header.
            try:
                values = worksheet.get("A:D")
                if not values:
                    continue

                header = values[0]
                for row_values in values[1:]:
                    # Pad row with empty strings if it's shorter than the header
                    padded_row = row_values + [""] * (len(header) - len(row_values))
                    row_dict = dict(zip(header, padded_row))
                    print(row_dict)
            except Exception as e:
                print(f"Error processing worksheet {worksheet.title}: {e}")


if __name__ == "__main__":
    main()
