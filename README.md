# Ukulele Tuesday Statistics

This repository contains a Streamlit application that provides data visualizations and insights for [Ukulele Tuesday](https://www.ukuleletuesday.ie/) datasets. For now, it's providing some insights into our song books and song sheets.

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
   uv sync
   ```

### Building the Dataset

**Note: Dataset synchronization is now automated!** The app fetches data directly from Google Drive using cached API calls. No manual dataset building is required for normal usage.

#### For Development and Manual Building

If you need to build the dataset manually (for development or testing), the data is sourced from Google Drive folders. To build the dataset manually, you need to have credentials configured to access the Google Drive API. Then, run the following command:

```bash
export GDRIVE_SONG_SHEETS_FOLDER_IDS="<your_folder_ids_here>"
# Optional, for impersonation
export GDRIVE_TARGET_PRINCIPAL="<your_service_account_email>"
python build_song_sheets_dataset.py data/song_sheets_dataset.json
```

#### Streamlit App Configuration

The Streamlit app uses automated data fetching with Google Drive API. To configure:

1. **Local Development**: 
   - Copy `secrets.toml.template` to `.streamlit/secrets.toml`
   - Configure your Google Drive folder IDs and optional service account
   - Set up Google Cloud credentials (see Authentication section below)

2. **Streamlit Cloud Deployment**:
   - Add the same configuration to your app's secrets in the Streamlit Cloud dashboard

For detailed setup instructions, see [GDRIVE_SETUP.md](GDRIVE_SETUP.md).

#### Authentication

For Google Drive API access, you need to set up authentication:

**Local Development Options:**
- Run `gcloud auth application-default login` (recommended for development)
- Set up a service account key file and set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

**Production/Streamlit Cloud:**
- Use a dedicated service account with appropriate Google Drive permissions
- For enhanced security, consider setting up impersonation with a dedicated service account

See [GDRIVE_SETUP.md](GDRIVE_SETUP.md) for complete setup instructions.

### Running the App
You can run the Streamlit app locally:

```bash
streamlit run main.py
```

The app will automatically fetch the latest data from Google Drive on first load and cache it for performance. Use the "🔄 Refresh Data" button in the app to manually reload data if needed.
