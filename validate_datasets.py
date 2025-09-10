#!/usr/bin/env python3
"""
Dataset validation script for Ukulele Tuesday datasets.

Validates datasets against their corresponding JSON schemas.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List
import jsonschema
from jsonschema import validate, ValidationError


def load_schema(schema_path: Path) -> Dict[str, Any]:
    """Load a JSON schema from file."""
    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Schema file not found: {schema_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in schema file {schema_path}: {e}")
        sys.exit(1)


def load_dataset(dataset_path: Path) -> Any:
    """Load a dataset from file."""
    try:
        with open(dataset_path, 'r') as f:
            # Handle both JSON and JSONL formats
            if dataset_path.suffix == '.jsonl':
                data = []
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))
                return data
            else:
                return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Dataset file not found: {dataset_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in dataset file {dataset_path}: {e}")
        sys.exit(1)


def validate_dataset(data: Any, schema: Dict[str, Any], dataset_name: str) -> bool:
    """Validate a dataset against its schema."""
    try:
        validate(instance=data, schema=schema)
        print(f"✅ {dataset_name}: Dataset validation passed")
        return True
    except ValidationError as e:
        print(f"❌ {dataset_name}: Dataset validation failed")
        print(f"   Validation error: {e.message}")
        if e.absolute_path:
            print(f"   Path: {' -> '.join(str(p) for p in e.absolute_path)}")
        if e.instance is not None:
            # Show a snippet of the failing instance for context
            instance_str = str(e.instance)
            if len(instance_str) > 200:
                instance_str = instance_str[:200] + "..."
            print(f"   Instance: {instance_str}")
        return False
    except Exception as e:
        print(f"❌ {dataset_name}: Unexpected error during validation: {e}")
        return False


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Validate Ukulele Tuesday datasets against their schemas"
    )
    parser.add_argument(
        "--dataset",
        choices=["jam-sessions", "song-sheets", "all"],
        default="all",
        help="Which dataset to validate (default: all)"
    )
    parser.add_argument(
        "--schemas-dir",
        type=Path,
        default=Path(__file__).parent / "schemas",
        help="Directory containing schema files"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent / "data",
        help="Directory containing dataset files"
    )
    parser.add_argument(
        "--jam-sessions-file",
        type=Path,
        help="Custom path to jam sessions dataset file"
    )
    parser.add_argument(
        "--song-sheets-file",
        type=Path,
        help="Custom path to song sheets dataset file"
    )
    
    args = parser.parse_args()
    
    # Default file paths
    default_jam_sessions = args.data_dir / "jam-sessions-data.jsonl"
    default_song_sheets = args.data_dir / "song_sheets_dataset.json"
    
    validation_results = []
    
    if args.dataset in ["jam-sessions", "all"]:
        jam_sessions_file = args.jam_sessions_file or default_jam_sessions
        if jam_sessions_file.exists():
            print(f"Validating jam sessions dataset: {jam_sessions_file}")
            schema = load_schema(args.schemas_dir / "sessions.json")
            data = load_dataset(jam_sessions_file)
            
            # Jam sessions data is an array of session objects
            if isinstance(data, list):
                all_valid = True
                for i, session in enumerate(data):
                    if not validate_dataset(session, schema, f"jam-sessions[{i}]"):
                        all_valid = False
                        break  # Stop on first error for clarity
                validation_results.append(("jam-sessions", all_valid))
            else:
                validation_results.append(("jam-sessions", False))
                print("❌ jam-sessions: Expected array of sessions, got single object")
        else:
            print(f"⚠️  Jam sessions dataset file not found: {jam_sessions_file}")
    
    if args.dataset in ["song-sheets", "all"]:
        song_sheets_file = args.song_sheets_file or default_song_sheets
        if song_sheets_file.exists():
            print(f"Validating song sheets dataset: {song_sheets_file}")
            schema = load_schema(args.schemas_dir / "song-sheets.json")
            data = load_dataset(song_sheets_file)
            validation_results.append(("song-sheets", validate_dataset(data, schema, "song-sheets")))
        else:
            print(f"⚠️  Song sheets dataset file not found: {song_sheets_file}")
    
    # Report results
    print("\n" + "="*50)
    print("VALIDATION SUMMARY")
    print("="*50)
    
    all_passed = True
    for dataset_name, passed in validation_results:
        status = "PASSED" if passed else "FAILED"
        icon = "✅" if passed else "❌"
        print(f"{icon} {dataset_name}: {status}")
        if not passed:
            all_passed = False
    
    if not validation_results:
        print("⚠️  No datasets were validated")
        sys.exit(1)
    
    if all_passed:
        print("\n🎉 All validations passed!")
        sys.exit(0)
    else:
        print("\n💥 Some validations failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()