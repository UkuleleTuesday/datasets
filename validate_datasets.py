#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "jsonschema",
#   "click",
#   "pandas"
# ]
# ///

"""
Dataset validation script for Ukulele Tuesday datasets.

Validates datasets against their corresponding JSON schemas.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any
import click
import pandas as pd
from jsonschema import validate, ValidationError


def load_schema(dataset_type: str) -> Dict[str, Any]:
    """Load a JSON schema from file."""
    schema_files = {
        "jam-sessions": "sessions.json",
        "song-sheets": "song-sheets.json"
    }
    
    schema_path = Path(__file__).parent / "schemas" / schema_files[dataset_type]
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
        if dataset_path.suffix == '.jsonl':
            # For JSONL, read line by line to preserve exact JSON values
            data = []
            with open(dataset_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))
            return data
        else:
            # Use pandas for regular JSON files (for performance with large datasets)
            try:
                data = pd.read_json(dataset_path)
                if isinstance(data, pd.DataFrame):
                    # Convert back to original JSON structure, handling NaN values
                    return json.loads(data.to_json(orient='records'))
                else:
                    return data
            except Exception:
                # Fallback to regular JSON loading if pandas fails
                with open(dataset_path, 'r') as f:
                    return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Dataset file not found: {dataset_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in dataset file {dataset_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load dataset file {dataset_path}: {e}")
        sys.exit(1)


def validate_dataset_content(data: Any, schema: Dict[str, Any], dataset_type: str) -> bool:
    """Validate a dataset against its schema."""
    try:
        if dataset_type == "jam-sessions":
            # Jam sessions data is an array of session objects
            if isinstance(data, list):
                for i, session in enumerate(data):
                    validate(instance=session, schema=schema)
                print(f"✅ {dataset_type}: Dataset validation passed ({len(data)} sessions)")
            else:
                print("❌ jam-sessions: Expected array of sessions, got single object")
                return False
        else:
            # Song sheets - validate the entire dataset
            validate(instance=data, schema=schema)
            count = len(data) if isinstance(data, list) else 1
            print(f"✅ {dataset_type}: Dataset validation passed ({count} records)")
        
        return True
    except ValidationError as e:
        print(f"❌ {dataset_type}: Dataset validation failed")
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
        print(f"❌ {dataset_type}: Unexpected error during validation: {e}")
        return False


@click.command()
@click.option(
    "--dataset",
    required=True,
    type=click.Choice(["jam-sessions", "song-sheets"]),
    help="Dataset type to validate"
)
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
def main(dataset: str, file_path: Path):
    """Validate a dataset against its schema."""
    print(f"Validating {dataset} dataset: {file_path}")
    
    # Load schema
    schema = load_schema(dataset)
    
    # Load dataset
    data = load_dataset(file_path)
    
    # Validate
    if validate_dataset_content(data, schema, dataset):
        print("🎉 Validation passed!")
        sys.exit(0)
    else:
        print("💥 Validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()