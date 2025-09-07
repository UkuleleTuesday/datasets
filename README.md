# Ukulele Tuesday Statistics

This repository contains a Streamlit application that provides data visualizations and insights for [Ukulele Tuesday](https://www.ukuleletuesday.ie/) datasets. For now, it's providing some insights into our song books and song sheets.

## Live Application

The dashboard is deployed and can be viewed live at:

**https://ukuleletuesday-stats.streamlit.app/**

## Data Source

The application automatically loads song metadata from our public GCS bucket (`songbook-generator-cache-europe-west1`) where JSON metadata files are published. This eliminates the need for manual dataset syncing and ensures the dashboard always shows the latest song data.

If GCS access is unavailable, the app will fall back to a local dataset file for development purposes.

## Features

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
- `uv` package manager (or pip)

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
The app will automatically load data from GCS when running. For local development:

```bash
uv run streamlit run main.py
```

Or with pip:
```bash
streamlit run main.py
```

### Local Development with Manual Dataset (Optional)

For development when GCS access is not available, you can still build a local dataset from Google Drive:

```bash
export GDRIVE_SONG_SHEETS_FOLDER_IDS="<your_folder_ids_here>"
# Optional, for impersonation
export GDRIVE_TARGET_PRINCIPAL="<your_service_account_email>"
uv run python build_song_sheets_dataset.py data/song_sheets_dataset.json
```

The app will automatically use this local file as a fallback if GCS is unavailable.
