# Ukulele Tuesday Statistics

This repository contains a Streamlit application that provides data visualizations and insights for [Ukulele Tuesday](https://www.ukuleletuesday.ie/) datasets. For now, it's providing some insights into our song books and song sheets.

## Live Application

The dashboard is deployed and can be viewed live at:

**https://ukuleletuesday-stats.streamlit.app/**

## Data Source

The application automatically loads song metadata from our public GCS bucket (`songbook-generator-cache-europe-west1/song-sheets/`) using Streamlit's FilesConnection. The system:

- **Automatically discovers** all `.json` metadata files in the GCS bucket
- **Loads data in real-time** with 10-minute caching for optimal performance
- **Assumes metadata format** matches Google Drive API response structure (with `properties`, `id`, and `name` fields)
- **Provides automatic fallback** to local dataset file (`data/song_sheets_dataset.json`) if GCS is unavailable

This architecture eliminates manual dataset syncing and ensures the dashboard always displays the latest song data from the publishing pipeline.

## Features

The application provides various statistics about the songs, including:
- Distribution of songs by decade of release.
- Breakdown of songs by tabber.
- Gender distribution of original artists.
- Difficulty distribution.
- Cumulative growth of the songbook over time.
- Filtering to view stats for all songs or just the "Current edition".

## Technical Architecture

The application uses a modern, automated data pipeline:

1. **GCS Integration**: Direct connection to Google Cloud Storage bucket using `st-files-connection`
2. **Automatic Discovery**: Dynamically finds all `.json` metadata files in the bucket
3. **Real-time Loading**: Loads fresh data on each session with 10-minute caching
4. **Progress Tracking**: Visual progress bars for data loading operations
5. **Intelligent Fallback**: Seamless fallback to local dataset for development
6. **Data Processing**: Automatic flattening and cleaning of Drive API response format

## Development

### Prerequisites
- Python 3.10+
- `uv` package manager (or pip)

### Dependencies
The application uses several key dependencies for GCS integration:
- `streamlit` - Main web framework
- `st-files-connection` - Streamlit connector for cloud storage
- `gcsfs` - Google Cloud Storage filesystem interface
- `altair` & `plotly` - Data visualization libraries
- `pandas` - Data manipulation and analysis

### Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   uv sync
   ```
   
   Or with pip:
   ```bash
   pip install -e .
   ```

### Running the App

The app automatically loads data from the GCS bucket on startup with intelligent fallback:

1. **Primary**: Loads from GCS bucket (`songbook-generator-cache-europe-west1/song-sheets/`)
2. **Fallback**: Uses local dataset file if GCS is unavailable

```bash
uv run streamlit run main.py
```

Or with pip:
```bash
streamlit run main.py
```

The app will display loading progress and automatically handle any connection issues.

### Local Development with Manual Dataset (Fallback)

The app includes automatic fallback to a local dataset. If you need to manually build this dataset from Google Drive for development:

```bash
export GDRIVE_SONG_SHEETS_FOLDER_IDS="<your_folder_ids_here>"
# Optional, for impersonation
export GDRIVE_TARGET_PRINCIPAL="<your_service_account_email>"
uv run python build_song_sheets_dataset.py data/song_sheets_dataset.json
```

The generated `data/song_sheets_dataset.json` file will be automatically used as a fallback if GCS is unavailable.
