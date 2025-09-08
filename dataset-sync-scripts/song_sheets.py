#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gcsfs"
# ]
# ///

"""
Aggregate per-song JSON files from a GCS source prefix into a single JSONL file,
and write to a destination prefix with both date-stamped and 'latest' paths.
Optionally also write a PR-local 'latest' under EXTRA_LATEST_PREFIX for previews.

Env vars:
  SRC_BUCKET            (default: songbook-generator-cache-europe-west1)
  SRC_PREFIX            (default: song-sheets/)
  DST_BUCKET            (default: ukulele-tuesday-datasets)
  DST_PREFIX            (default: song-sheets/aggregated)
  EXTRA_LATEST_PREFIX   (optional; e.g., song-sheets/aggregated/previews/pr-123)
  GCSFS_REQUESTER_PAYS  (optional; set to a billing project ID to enable requester pays)
"""

import os
import sys
import json
import datetime
import gcsfs
import io


def write_content(fs: gcsfs.GCSFileSystem, content: str, gcs_path: str):
    """Write string content to a GCS path."""
    with fs.open(gcs_path, "w") as f:
        f.write(content)
    print(f"Wrote {len(content.splitlines())} lines to gs://{gcs_path}")


def main() -> None:
    # Config via env
    src_bucket = os.getenv("SRC_BUCKET", "songbook-generator-cache-europe-west1")
    src_prefix = os.getenv("SRC_PREFIX", "song-sheets/").lstrip("/")
    dst_bucket = os.getenv("DST_BUCKET", "ukulele-tuesday-datasets")
    dst_prefix = os.environ.get("DST_PREFIX", "song-sheets/aggregated").lstrip("/")
    extra_latest_base = os.getenv("EXTRA_LATEST_PREFIX")  # optional

    requester_pays_project = os.getenv("GCSFS_REQUESTER_PAYS")  # optional
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
        print(f"No .json files found under gs://{src_base}; skipping writes.")
        return

    # Generate new dataset content in memory
    new_content_io = io.StringIO()
    written = 0
    for fp in json_files:
        try:
            with fs.open(fp, "r") as in_f:
                data = json.load(in_f)
        except Exception as exc:
            print(f"WARNING: skipping {fp} (invalid JSON): {exc}", file=sys.stderr)
            continue

        # Accept either dict or list-of-dicts; write one JSON object per line
        if isinstance(data, list):
            for item in data:
                new_content_io.write(json.dumps(item, separators=(",", ":")) + "\n")
                written += 1
        elif isinstance(data, dict):
            new_content_io.write(json.dumps(data, separators=(",", ":")) + "\n")
            written += 1
        else:
            # Fallback: wrap primitive under 'value'
            new_content_io.write(json.dumps({"value": data}, separators=(",", ":")) + "\n")
            written += 1
    new_content = new_content_io.getvalue()
    new_content_io.close()

    # Compare with existing 'latest' to see if an update is needed
    latest_path = f"{dst_prefix}/latest/data.jsonl"
    gcs_latest_full_path = f"{dst_bucket}/{latest_path.lstrip('/')}"
    if fs.exists(gcs_latest_full_path):
        try:
            with fs.open(gcs_latest_full_path, "r") as f:
                current_latest_content = f.read()
            if new_content == current_latest_content:
                print("Dataset content is unchanged. Skipping writes.")
                return
        except Exception as e:
            print(f"WARNING: Could not read existing latest file to compare: {e}", file=sys.stderr)

    # Write date-stamped and latest under DST_PREFIX
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    date_path = f"{dst_prefix}/{today}/data.jsonl"
    write_content(fs, new_content, f"{dst_bucket}/{date_path.lstrip('/')}")
    write_content(fs, new_content, gcs_latest_full_path)

    # Optional PR-local latest under EXTRA_LATEST_PREFIX
    if extra_latest_base:
        pr_latest_path = f"{extra_latest_base.strip('/')}/latest/data.jsonl"
        write_content(fs, new_content, f"{dst_bucket}/{pr_latest_path.lstrip('/')}")


if __name__ == "__main__":
    main()
