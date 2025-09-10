# Ukulele Tuesday Statistics

This repository contains a Streamlit application that provides data visualizations and insights for [Ukulele Tuesday](https://www.ukuleletuesday.ie/) datasets. For now, it's providing some insights into our song books and song sheets.

## Live Application

The dashboard is deployed and can be viewed live at:

**https://ukuleletuesday-stats.streamlit.app/**

## Data Sources

* Public UT Song Sheets cache GCS bucket (`songbook-generator-cache-europe-west1/song-sheets/`) (using Streamlit's FilesConnection with GCS backend)

## Dashboards

**UT Song Sheets Dashboard**

The application provides various statistics about the songs, including:
- Distribution of songs by decade of release.
- Breakdown of songs by tabber.
- Gender distribution of original artists.
- Difficulty distribution.
- Cumulative growth of the songbook over time.
- Filtering to view stats for all songs or just the "Current edition".

## Development

### Prerequisites
- Python 3.10+
- `uv` package manager

### Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   uv sync
   ```

### Running the App

```bash
uv run streamlit run main.py
```

### Dataset Sync

The repository includes a unified `dataset-sync.py` script for syncing datasets to various destinations:

#### Usage Examples

```bash
# Sync jam sessions to local file
./dataset-sync.py --dataset jam-sessions -o /path/to/output.jsonl

# Sync song sheets to GCS
./dataset-sync.py --dataset song-sheets -o gs://bucket/path/data.jsonl

# Sync to multiple destinations (both local and GCS)
./dataset-sync.py --dataset jam-sessions \
  -o /local/backup.jsonl \
  -o gs://bucket/latest/data.jsonl \
  -o gs://bucket/$(date +%Y-%m-%d)/data.jsonl
```

#### Supported Datasets
- `jam-sessions`: Fetches jam session data from Google Sheets
- `song-sheets`: Aggregates song sheet data from GCS

#### Environment Variables
- `SRC_BUCKET`: Source GCS bucket for song-sheets dataset
- `DST_BUCKET`: Default destination GCS bucket
- `GCSFS_REQUESTER_PAYS`: GCP project ID for requester pays
- `SERVICE_ACCOUNT_EMAIL`: Service account for impersonation (local dev)


