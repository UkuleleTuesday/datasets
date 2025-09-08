#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gcsfs",
#   "google-cloud-storage"
# ]
# ///

import json
import datetime
import gcsfs


def aggregate_song_sheets():
    # Configuration
    src_bucket = "songbook-generator-cache-europe-west1"
    src_prefix = "song-sheets/"
    dst_bucket = "ukulele-tuesday-datasets"
    dst_prefix = "song-sheets/aggregated"

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    date_path = f"{dst_prefix}/{today}/data.jsonl"
    latest_path = f"{dst_prefix}/latest/data.jsonl"

    fs = gcsfs.GCSFileSystem()

    # List all JSON files in source bucket
    files = fs.ls(f"{src_bucket}/{src_prefix}")
    json_files = [f for f in files if f.endswith(".json")]

    if not json_files:
        print("No JSON files found — skipping upload.")
        return

    def write_jsonl(gcs_path: str):
        with fs.open(f"{dst_bucket}/{gcs_path}", "w") as out_f:
            for file_path in json_files:
                with fs.open(file_path, "r") as in_f:
                    data = json.load(in_f)
                    out_f.write(json.dumps(data) + "\n")

    # Write to both date-stamped and latest paths
    for target in [date_path, latest_path]:
        write_jsonl(target)

    print(f"Wrote {len(json_files)} records to {date_path} and {latest_path}")


if __name__ == "__main__":
    aggregate_song_sheets()
