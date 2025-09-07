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

### Local Development with Manual Dataset (Fallback)

The app includes automatic fallback to a local dataset. If you need to manually build this dataset from Google Drive for development:

```bash
export GDRIVE_SONG_SHEETS_FOLDER_IDS="<your_folder_ids_here>"
# Optional, for impersonation
export GDRIVE_TARGET_PRINCIPAL="<your_service_account_email>"
uv run python build_song_sheets_dataset.py data/song_sheets_dataset.json
```

The generated `data/song_sheets_dataset.json` file will be automatically used as a fallback if GCS is unavailable.
