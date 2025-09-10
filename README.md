# Ukulele Tuesday Statistics

This repository contains a comprehensive data platform for [Ukulele Tuesday](https://www.ukuleletuesday.ie/), including a Streamlit dashboard for data visualization and tools for dataset synchronization and validation. The platform handles both song sheets metadata and jam session data.

## Live Application

The dashboard is deployed and can be viewed live at:

**https://ukuleletuesday-stats.streamlit.app/**

## Project Structure

```
├── main.py                    # Streamlit application entry point
├── pages/
│   └── song_sheets_stats.py   # Main dashboard implementation
├── dataset-sync.py            # Dataset synchronization script
├── validate_datasets.py       # Dataset validation script
├── test_validation.py         # Validation system tests
├── schemas/                   # JSON schemas for data validation
│   ├── README.md             # Schema documentation
│   ├── song-sheets.json      # Song sheets schema
│   └── sessions.json         # Jam sessions schema
├── .github/workflows/         # CI/CD automation
│   └── build-dataset.yaml    # Daily dataset sync workflow
├── .devcontainer/            # Development container configuration
├── pyproject.toml           # Python project configuration
└── uv.lock                  # Dependency lock file
```

## Data Sources

The platform processes two main dataset types:

* **Song Sheets**: Aggregated from the public UT datasets at `https://ukulele-tuesday-datasets.storage.googleapis.com/song-sheets/aggregated/latest/data.jsonl`
* **Jam Sessions**: Fetched from Google Sheets containing session setlists and transformed into structured session objects

## Dashboards

**UT Song Sheets Dashboard**

The Streamlit application provides comprehensive statistics and visualizations about the songs, including:
- Dataset overview (total songs, unique artists, number of tabbers)
- Distribution of songs by tabber contribution
- Cumulative growth of the songbook over time
- Song distribution by decade of release
- Difficulty level distribution
- Most common chords analysis
- Gender distribution of original artists
- Data quality checks and missing field analysis
- Filtering to view stats for all songs or just the "Current edition" (songs in regular rotation)

The dashboard loads data from the public datasets and provides interactive visualizations using Plotly, Altair, and Streamlit's built-in charting.

## Development

### Prerequisites
- Python 3.10+ (tested with 3.11 and 3.12)
- `uv` package manager (recommended) or pip

### Setup

#### Option 1: Using uv (Recommended)
1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```

#### Option 2: Using pip
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install streamlit click google-api-python-client google-auth-httplib2 google-auth-oauthlib pandas plotly altair st-files-connection gcsfs jsonschema
   ```

#### Option 3: Development Container
This repository includes a devcontainer configuration for VS Code and GitHub Codespaces:
- Open in VS Code with the Dev Containers extension
- Or use GitHub Codespaces for instant development environment
- The container automatically installs dependencies and starts the Streamlit app

### Running the App

With uv:
```bash
uv run streamlit run main.py
```

With pip:
```bash
streamlit run main.py
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

