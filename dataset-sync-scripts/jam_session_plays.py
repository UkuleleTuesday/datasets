#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gspread",
#   "google-auth",
#   "google-api-python-client",
#   "tenacity"
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
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from gspread.exceptions import APIError


# Define a retry condition to only retry on 429 Too Many Requests errors
def is_rate_limit_error(exception):
    return isinstance(exception, APIError) and exception.response.status_code == 429


retry_on_rate_limit = retry(
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception(is_rate_limit_error),
)


def transform_to_session(spreadsheet_name: str, worksheet_title: str, values: list) -> dict:
    try:
        session_date = datetime.datetime.strptime(worksheet_title, "%Y/%m/%d").date()
    except ValueError:
        print(f"Skipping worksheet with invalid date format title: {worksheet_title}")
        return None

    if not values or len(values) < 2:
        return None  # No data or header only

    header = values[0]

    session = {
        "session_id": str(uuid.uuid4()),
        "date": session_date.isoformat(),
        "venue": None,
        "source_sheet": spreadsheet_name,
        "ingested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "events": [],
        "requests": [],  # Per schema, but no source data for this yet
    }
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


@retry_on_rate_limit
def get_spreadsheets(drive_service, folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    response = (
        drive_service.files()
        .list(q=query, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True)
        .execute()
    )
    return response.get("files", [])


@retry_on_rate_limit
def get_worksheet_data(sh):
    worksheets_to_process = sh.worksheets()[1:]
    if not worksheets_to_process:
        return None, None

    ranges = [f"'{w.title}'!A:D" for w in worksheets_to_process]
    batch_get_result = sh.values_batch_get(ranges)
    value_ranges = batch_get_result.get("valueRanges", [])
    return worksheets_to_process, value_ranges


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
    spreadsheets = get_spreadsheets(drive_service, folder_id)

    all_sessions = []
    for spreadsheet in spreadsheets:
        sh = gc.open_by_key(spreadsheet["id"])

        # Process all worksheets except the first one (index 0)
        worksheets_to_process, value_ranges = get_worksheet_data(sh)
        if not worksheets_to_process:
            continue

        # The API does not guarantee the order of responses, so map them back
        # to worksheets by the returned range string.
        range_data_map = {item["range"]: item.get("values", []) for item in value_ranges}

        for i, worksheet in enumerate(worksheets_to_process):
            # The range string in the response may have sheet name quoting differences
            # compared to what we sent, so we check both.
            # e.g., "'Sheet'1'!A:D" vs "Sheet'1!A:D"
            # We use the index `i` from our worksheet list to get the corresponding
            # range we requested.
            worksheet_values = range_data_map.get(value_ranges[i]["range"])

            if worksheet_values:
                session_data = transform_to_session(
                    spreadsheet["name"], worksheet.title, worksheet_values
                )
                if session_data:
                    all_sessions.append(session_data)

    print(json.dumps(all_sessions, indent=2))


if __name__ == "__main__":
    main()
