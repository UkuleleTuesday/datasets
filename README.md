# Ukulele Tuesday Statistics

Datasets and streamlit dashboards for [Ukulele Tuesday](https://www.ukuleletuesday.ie/).

## Live Application

The dashboard is deployed and can be viewed live at:

**https://ukuleletuesday.streamlit.app/**
## Datasets

The platform currently provides two main datasets, both stored in the `ukulele-tuesday-datasets` GCS bucket:

* **Song Sheets**: Comprehensive dataset of Ukulele Tuesday song sheets with metadata including artist, chords, difficulty, and contributor information
* **Jam Sessions**: Historical jam session data with setlists, venue information, and song requests from live Ukulele Tuesday events

## Development

### Prerequisites
- Python 3.10+ (tested with 3.11 and 3.12)
- `uv` package manager

### Setup

#### Option 1: Using uv
1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```

#### Option 2: Development Container
This repository includes a devcontainer configuration for VS Code and GitHub Codespaces:
- Open in VS Code with the Dev Containers extension
- Or use GitHub Codespaces for instant development environment
- The container automatically installs dependencies and starts the Streamlit app

### Running the App

```bash
uv run streamlit run main.py
```

### Testing

Run the validation tests to ensure the schemas and validation system are working:
```bash
python test_validation.py
```

This tests both song-sheets and jam-sessions dataset validation with sample data.

### Dataset Sync

The repository includes a unified `dataset-sync.py` script for syncing datasets from their sources to various destinations including local files and Google Cloud Storage.

#### Supported Datasets

- **`song-sheets`**: Aggregates song sheet metadata from GCS sources
- **`jam-sessions`**: Fetches jam session data from Google Sheets and transforms it into structured session objects with events and metadata

#### Usage Examples

```bash
# Sync song sheets to local file
./dataset-sync.py --dataset song-sheets -o /path/to/output.jsonl

# Sync jam sessions to local file  
./dataset-sync.py --dataset jam-sessions -o /path/to/output.jsonl

# Sync to Google Cloud Storage
./dataset-sync.py --dataset song-sheets -o gs://bucket/path/data.jsonl

# Sync to multiple destinations (both local and GCS with date-stamped backup)
./dataset-sync.py --dataset jam-sessions \
  -o /local/backup.jsonl \
  -o gs://bucket/latest/data.jsonl \
  -o gs://bucket/$(date +%Y-%m-%d)/data.jsonl
```

#### Environment Variables
- `SRC_BUCKET`: Source GCS bucket for song-sheets dataset
- `DST_BUCKET`: Default destination GCS bucket
- `GCSFS_REQUESTER_PAYS`: GCP project ID for requester pays
- `SERVICE_ACCOUNT_EMAIL`: Service account for impersonation (local dev)

### Dataset Validation

The repository includes a comprehensive schema validation system for ensuring data quality and consistency.

#### Schemas

Located in the `schemas/` directory:
- **`song-sheets.json`**: JSON Schema for song sheets dataset validation
- **`sessions.json`**: JSON Schema for jam sessions dataset validation
- **`README.md`**: Detailed schema documentation

#### Validation Usage

```bash
# Validate song sheets dataset
./validate_datasets.py --dataset song-sheets /path/to/data.jsonl

# Validate jam sessions dataset  
./validate_datasets.py --dataset jam-sessions /path/to/data.jsonl

# The validation is automatically run in CI/CD pipeline
```

### Continuous Integration

The repository uses GitHub Actions for automated dataset synchronization and validation:

- **Daily Schedule**: Automatically syncs datasets every day at midnight UTC
- **Pull Request Validation**: Runs on every PR to validate changes
- **Manual Trigger**: Can be triggered manually via workflow dispatch

The workflow (`.github/workflows/build-dataset.yaml`):
1. Syncs both song-sheets and jam-sessions datasets
2. Validates each dataset against its schema
3. Uploads datasets as artifacts with 30-day retention
4. Supports preview deployments for pull requests

## Contributing

Found an issue or have a feature request? 
- [Open an issue](https://github.com/UkuleleTuesday/stats/issues) to report bugs or suggest features
- [Submit a pull request](https://github.com/UkuleleTuesday/stats/pulls) to contribute code improvements
- Check out the live dashboard at [ukuleletuesday-stats.streamlit.app](https://ukuleletuesday-stats.streamlit.app/)
- Visit the songbooks at [songbooks.ukuleletuesday.ie](https://songbooks.ukuleletuesday.ie/)

## License

This project is part of the Ukulele Tuesday ecosystem. For more information about Ukulele Tuesday, visit [ukuleletuesday.ie](https://www.ukuleletuesday.ie/).

