#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gspread",
#   "google-auth",
#   "google-api-python-client", 
#   "tenacity",
#   "gcsfs",
#   "click"
# ]
# ///

"""
Unified dataset sync script for Ukulele Tuesday datasets.

Supports syncing different dataset types to various output destinations including GCS and local paths.

Usage:
  dataset-sync.py --dataset jam-sessions -o gs://bucket/path/data.jsonl
  dataset-sync.py --dataset song-sheets -o /local/path/data.jsonl -o gs://bucket/path/data.jsonl
"""

import datetime
import json
import os
import sys
import uuid
import io
import pathlib
from typing import List, Dict, Any, Optional

import click
import gspread
import google.auth
from google.auth import impersonated_credentials
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
import gcsfs

from gspread.exceptions import APIError


def is_rate_limit_error(exception):
    """Check if exception is a rate limit error that should be retried."""
    return isinstance(exception, APIError) and exception.response.status_code == 429


retry_on_rate_limit = retry(
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception(is_rate_limit_error),
)


class OutputWriter:
    """Handles writing content to various destinations (GCS, local files)."""
    
    def __init__(self):
        # Setup GCS filesystem if needed
        self.fs = None
        requester_pays_project = os.getenv("GCSFS_REQUESTER_PAYS")
        if requester_pays_project:
            fs_kwargs = {"requester_pays": True, "project": requester_pays_project}
        else:
            fs_kwargs = {}
        self._fs_kwargs = fs_kwargs
    
    def _get_gcs_fs(self):
        """Lazy initialize GCS filesystem."""
        if self.fs is None:
            self.fs = gcsfs.GCSFileSystem(**self._fs_kwargs)
        return self.fs
    
    def write_content(self, content: str, output_path: str) -> None:
        """Write content to the specified output path (GCS or local)."""
        if output_path.startswith("gs://"):
            # GCS path
            gcs_path = output_path[5:]  # Remove gs:// prefix
            fs = self._get_gcs_fs()
            with fs.open(gcs_path, "w") as f:
                f.write(content)
            print(f"Wrote {len(content.splitlines())} lines to {output_path}")
        else:
            # Local path
            path = pathlib.Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            print(f"Wrote {len(content.splitlines())} lines to {output_path}")
    
    def read_content(self, path: str) -> Optional[str]:
        """Read content from a path for comparison. Returns None if file doesn't exist."""
        try:
            if path.startswith("gs://"):
                gcs_path = path[5:]  # Remove gs:// prefix
                fs = self._get_gcs_fs()
                if not fs.exists(gcs_path):
                    return None
                with fs.open(gcs_path, "r") as f:
                    return f.read()
            else:
                if not os.path.exists(path):
                    return None
                with open(path, "r") as f:
                    return f.read()
        except Exception as e:
            print(f"WARNING: Could not read {path} for comparison: {e}", file=sys.stderr)
            return None


def transform_to_session(spreadsheet_name: str, worksheet_title: str, values: list) -> Optional[Dict[str, Any]]:
    """Transform spreadsheet data into a jam session object."""
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
    """Get all spreadsheets in a Google Drive folder."""
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    response = (
        drive_service.files()
        .list(q=query, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True)
        .execute()
    )
    return response.get("files", [])


@retry_on_rate_limit  
def get_worksheet_data(sh):
    """Get data from all worksheets except the first one."""
    worksheets_to_process = sh.worksheets()[1:]
    if not worksheets_to_process:
        return None, None

    ranges = [f"'{w.title}'!A:D" for w in worksheets_to_process]
    batch_get_result = sh.values_batch_get(ranges)
    value_ranges = batch_get_result.get("valueRanges", [])
    return worksheets_to_process, value_ranges


def fetch_jam_sessions_data() -> List[Dict[str, Any]]:
    """Fetch jam session data from Google Sheets."""
    # Setup Google authentication
    target_principal = os.getenv("SERVICE_ACCOUNT_EMAIL")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    creds, _ = google.auth.default(scopes=scopes)

    if target_principal:
        print(f"Impersonating service account: {target_principal}")
        creds = impersonated_credentials.Credentials(
            source_credentials=creds,
            target_principal=target_principal,
            target_scopes=scopes,
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

        # Map range data back to worksheets
        range_data_map = {item["range"]: item.get("values", []) for item in value_ranges}

        for i, worksheet in enumerate(worksheets_to_process):
            worksheet_values = range_data_map.get(value_ranges[i]["range"])

            if worksheet_values:
                session_data = transform_to_session(
                    spreadsheet["name"], worksheet.title, worksheet_values
                )
                if session_data:
                    all_sessions.append(session_data)

    return all_sessions


def fetch_song_sheets_data() -> List[Dict[str, Any]]:
    """Fetch and aggregate song sheets data from GCS."""
    # Config via env vars (backwards compatibility)
    src_bucket = os.getenv("SRC_BUCKET", "songbook-generator-cache-europe-west1")
    src_prefix = os.getenv("SRC_PREFIX", "song-sheets/").lstrip("/")

    requester_pays_project = os.getenv("GCSFS_REQUESTER_PAYS")
    fs_kwargs = {}
    if requester_pays_project:
        fs_kwargs = {"requester_pays": True, "project": requester_pays_project}

    fs = gcsfs.GCSFileSystem(**fs_kwargs)

    # List all .json files from source
    src_base = f"{src_bucket}/{src_prefix}".rstrip("/")
    try:
        paths = fs.ls(src_base)
    except Exception as e:
        print(f"ERROR: failed to list gs://{src_base}: {e}", file=sys.stderr)
        raise

    json_files = sorted(p for p in paths if p.endswith(".json"))
    if not json_files:
        print(f"No .json files found under gs://{src_base}")
        return []

    # Load and aggregate all JSON data
    all_data = []
    for fp in json_files:
        try:
            with fs.open(fp, "r") as in_f:
                data = json.load(in_f)
        except Exception as exc:
            print(f"WARNING: skipping {fp} (invalid JSON): {exc}", file=sys.stderr)
            continue

        # Accept either dict or list-of-dicts
        if isinstance(data, list):
            all_data.extend(data)
        elif isinstance(data, dict):
            all_data.append(data)
        else:
            # Fallback: wrap primitive under 'value'
            all_data.append({"value": data})

    return all_data


def generate_jsonl_content(data: List[Dict[str, Any]]) -> str:
    """Generate JSONL content from a list of data objects."""
    content_io = io.StringIO()
    for item in data:
        content_io.write(json.dumps(item, separators=(",", ":")) + "\n")
    content = content_io.getvalue()
    content_io.close()
    return content


@click.command()
@click.option(
    "--dataset", 
    required=True,
    type=click.Choice(["jam-sessions", "song-sheets"]),
    help="Dataset type to sync"
)
@click.option(
    "-o", "--output",
    multiple=True,
    required=True,
    help="Output path (can be repeated). Supports both local paths and GCS paths (gs://...)"
)
def main(dataset: str, output: tuple):
    """Sync dataset to specified output destinations."""
    output_paths = list(output)
    
    if not output_paths:
        click.echo("Error: At least one output path must be specified", err=True)
        sys.exit(1)
    
    # Fetch the appropriate dataset
    if dataset == "jam-sessions":
        print("Fetching jam sessions data...")
        data = fetch_jam_sessions_data()
        print(f"Fetched {len(data)} jam sessions")
    elif dataset == "song-sheets":
        print("Fetching song sheets data...")
        data = fetch_song_sheets_data()
        print(f"Fetched {len(data)} song sheet records")
    else:
        click.echo(f"Error: Unsupported dataset type: {dataset}", err=True)
        sys.exit(1)
    
    if not data:
        print("No data to sync. Exiting.")
        return
    
    # Generate JSONL content
    content = generate_jsonl_content(data)
    
    # Initialize output writer
    writer = OutputWriter()

    # Write to all specified outputs
    synced_count = 0
    for output_path in output_paths:
        # Check if we should skip writing for this path
        existing_content = writer.read_content(output_path)
        if existing_content is not None and content == existing_content:
            print(f"Content for {output_path} is unchanged. Skipping write.")
            continue

        try:
            writer.write_content(content, output_path)
            synced_count += 1
        except Exception as e:
            print(f"ERROR: Failed to write to {output_path}: {e}", file=sys.stderr)
            sys.exit(1)

    print(f"Successfully synced {dataset} dataset to {synced_count} of {len(output_paths)} destination(s)")


if __name__ == "__main__":
    main()
