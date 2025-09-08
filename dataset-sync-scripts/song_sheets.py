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

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    date_path = f"{dst_prefix}/{today}/data.jsonl"
    latest_path = f"{dst_prefix}/latest/data.jsonl"

    def write_jsonl(target_rel_path: str) -> None:
        gcs_target = f"{dst_bucket}/{target_rel_path.lstrip('/')}"
        # GCS doesn't need pre-creating "dirs"
        written = 0
        with fs.open(gcs_target, "w") as out_f:
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
                        out_f.write(json.dumps(item, separators=(",", ":")) + "\n")
                        written += 1
                elif isinstance(data, dict):
                    out_f.write(json.dumps(data, separators=(",", ":")) + "\n")
                    written += 1
                else:
                    # Fallback: wrap primitive under 'value'
                    out_f.write(json.dumps({"value": data}, separators=(",", ":")) + "\n")
                    written += 1

        print(f"Wrote {written} lines to gs://{gcs_target}")

    # Write date-stamped and latest under DST_PREFIX
    write_jsonl(date_path)
    write_jsonl(latest_path)

    # Optional PR-local latest under EXTRA_LATEST_PREFIX
    if extra_latest_base:
        write_jsonl(f"{extra_latest_base.strip('/')}/latest/data.jsonl")


if __name__ == "__main__":
    main()
