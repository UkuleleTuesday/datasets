# Ukulele Tuesday Songbook Statistics

This repository contains a Streamlit application that provides data visualizations and insights into the song sheets used by [Ukulele Tuesday](https://www.ukuleletuesday.com/).

## Live Application

The dashboard is deployed and can be viewed live at:

**https://ukuleletuesday-stats.streamlit.app/**

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
- `uv` package manager

### Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   uv pip install -e .
   ```

### Building the Dataset
The data is sourced from a Google Drive folder. To build the dataset, you need to have credentials configured to access the Google Drive API. Then, run the following command:

```bash
export GDRIVE_SONG_SHEETS_FOLDER_IDS="<your_folder_ids_here>"
# Optional, for impersonation
export GDRIVE_TARGET_PRINCIPAL="<your_service_account_email>"
python build_song_sheets_dataset.py data/song_sheets_dataset.json
```

### Running the App
Once the dataset is built, you can run the Streamlit app locally:

```bash
streamlit run main.py
```
