import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st
from st_files_connection import FilesConnection
import json


@st.cache_data(ttl=600)
def load_data_from_gcs():
    """Load and preprocess the song sheets dataset from GCS bucket."""
    try:
        # Connect to GCS using streamlit's connection
        conn = st.connection('gcs', type=FilesConnection)
        
        # List all files in the song-sheets folder
        bucket_path = "gs://songbook-generator-cache-europe-west1/song-sheets/"
        
        with st.spinner("Loading songs from GCS bucket..."):
            files = conn.fs.ls(bucket_path)
        
        # Filter for .metadata.json files only
        metadata_files = [f for f in files if f.endswith('.json')]
        
        if not metadata_files:
            st.error("No .metadata.json files found in the GCS bucket")
            return None
        
        # Load all metadata files
        all_data = []
        progress_bar = st.progress(0)
        total_files = len(metadata_files)
        
        for i, file_path in enumerate(metadata_files):
            try:
                # Read the JSON content - assuming it has the same format as Drive API returns
                with conn.fs.open(file_path, 'r') as f:
                    entry = json.load(f)
                
                # The .metadata.json files should already have the Drive API format
                # with "properties", "id", and "name" fields
                all_data.append(entry)
                
                # Update progress
                progress_bar.progress((i + 1) / total_files)
                
            except Exception as e:
                st.warning(f"Error loading {file_path}: {e}")
                continue
        
        progress_bar.empty()
        
        if not all_data:
            st.error("No valid metadata files could be loaded from GCS")
            return None
            
        # Create DataFrame from the loaded data
        df = pd.DataFrame(all_data)
        
        st.success(f"Successfully loaded {len(all_data)} songs from GCS bucket")
        return df
        
    except Exception as e:
        st.error(f"Error connecting to GCS bucket: {e}")
        st.info("🔄 Falling back to local dataset file if available...")
        return None


def load_data_from_local():
    """Load and preprocess the song sheets dataset from local file (fallback)."""
    filepath = "data/song_sheets_dataset.json"
    try:
        df = pd.read_json(filepath)
        st.info("📁 Using local dataset file as fallback")
    except ValueError as e:
        st.error(f"Error reading JSON file: {e}")
        return None
    except FileNotFoundError:
        st.error(f"Error: The file '{filepath}' was not found.")
        st.info(
            "Please run the build_song_sheets_dataset.py script to generate it first."
        )
        return None
    
    return process_dataframe(df)


def process_dataframe(df):
    """Process and clean the dataframe."""
    # Use json_normalize to flatten the 'properties' column
    properties_df = pd.json_normalize(df["properties"])
    # Concatenate the flattened properties with the original dataframe (id and name)
    df = pd.concat([df.drop("properties", axis=1), properties_df], axis=1)

    # Sort by song name
    df = df.sort_values(by="name").reset_index(drop=True)

    # Data cleaning and type conversion
    df["difficulty"] = pd.to_numeric(df["difficulty"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    df["specialbooks"] = df["specialbooks"].str.split(",")
    df["chords"] = df["chords"].str.split(",")

    return df


def load_data():
    """Load song sheets dataset, trying GCS first, then falling back to local file."""
    # Try loading from GCS first
    df = load_data_from_gcs()
    if df is not None:
        return process_dataframe(df)
    
    # Fall back to local file
    return load_data_from_local()

    # Use json_normalize to flatten the 'properties' column
    properties_df = pd.json_normalize(df["properties"])
    # Concatenate the flattened properties with the original dataframe (id and name)
    df = pd.concat([df.drop("properties", axis=1), properties_df], axis=1)

    # Sort by song name
    df = df.sort_values(by="name").reset_index(drop=True)

    # Data cleaning and type conversion
    df["difficulty"] = pd.to_numeric(df["difficulty"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    df["specialbooks"] = df["specialbooks"].str.split(",")
    df["chords"] = df["chords"].str.split(",")

    return df


def main():
    st.set_page_config(page_title="Ukulele Tuesday Song Stats", layout="wide")
    st.title("Ukulele Tuesday Song Sheets Dashboard")

    st.markdown(
        """
        This dashboard provides an interactive exploration of the songs tabbed for [Ukulele Tuesday](https://www.ukuleletuesday.ie/), a weekly ukulele jam session.
        It analyzes metadata from all song sheets, including artist information, release year, difficulty, and more.
        You can filter the data to see insights for all songs ever tabbed or just the songs in the current rotating songbook.
        For the songbooks themselves, visit [songbooks.ukuleletuesday.ie](https://songbooks.ukuleletuesday.ie/).
        """
    )

    df = load_data()

    if df is not None:
        # Map display options to query param values
        song_filter_options = {"All songs": "all", "Current edition": "current"}
        options_list = list(song_filter_options.keys())
        query_params = st.query_params

        # Determine index from query param, default to 0 ('All songs')
        current_selection_value = query_params.get("songs", "all")
        try:
            current_index = list(song_filter_options.values()).index(
                current_selection_value
            )
        except ValueError:
            current_index = 0

        song_filter = st.selectbox(
            "Included songs", options=options_list, index=current_index
        )
        # Update query param based on selection
        st.query_params["songs"] = song_filter_options[song_filter]

        if song_filter == "Current edition":
            df = df[
                df["specialbooks"].apply(
                    lambda x: isinstance(x, list) and "regular" in x
                )
            ]

        st.header("Dataset Overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Songs", len(df))
        col2.metric("Unique Artists", df["artist"].nunique())
        col3.metric("Number of Tabbers", df["tabber"].nunique())

        st.header("Analysis")

        # Songs per tabber
        st.subheader("Songs per Tabber")
        tabber_counts = df["tabber"].value_counts().sort_values(ascending=False)
        st.bar_chart(tabber_counts)

        # Total songs over time
        st.subheader("Total Songs Over Time")
        df_by_date = df.dropna(subset=["date"]).sort_values("date")
        # Create a column for cumulative song count
        df_by_date["cumulative_songs"] = range(1, len(df_by_date) + 1)
        st.line_chart(df_by_date.set_index("date")["cumulative_songs"])

        # Songs by decade of release
        st.subheader("Song Distribution by Decade of Release")
        df_with_year = df.dropna(subset=["year"]).copy()

        def map_year_to_decade(year):
            year = int(year)
            if year < 1950:
                return "<1950"
            return f"{(year // 10) * 10}s"

        df_with_year["decade"] = df_with_year["year"].apply(map_year_to_decade)
        
        # Define the chronological order of decades
        decade_order = sorted([d for d in df_with_year["decade"].unique() if d != '<1950'])
        if '<1950' in df_with_year["decade"].unique():
            decade_order.insert(0, '<1950')
        
        # Convert to categorical type to enforce order
        df_with_year["decade"] = pd.Categorical(df_with_year["decade"], categories=decade_order, ordered=True)
        
        decade_counts = df_with_year["decade"].value_counts().sort_index()
        st.bar_chart(decade_counts)

        # Difficulty distribution
        st.subheader("Difficulty Distribution")
        # Round difficulty to nearest integer for grouping, then count and sort.
        difficulty_groups = df["difficulty"].dropna().round(0).astype(int)
        st.bar_chart(difficulty_groups.value_counts().sort_index())

        # Most common chords
        st.subheader("Most Common Chords")
        all_chords = [
            chord for sublist in df["chords"].dropna() for chord in sublist
        ]
        chord_counts = pd.Series(all_chords).value_counts().reset_index()
        chord_counts.columns = ["chord", "count"]
        
        chart = (
            alt.Chart(chord_counts)
            .mark_bar()
            .encode(
                x=alt.X("count", title="Frequency"),
                y=alt.Y("chord", sort=None, title="Chord"),
                tooltip=["chord", "count"],
            )
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

        # Gender distribution
        st.subheader("Gender Distribution")
        gender_counts = df["gender"].value_counts().reset_index()
        gender_counts.columns = ["gender", "count"]
        fig = px.pie(
            gender_counts, values="count", names="gender", title="Gender Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.header("Raw Data")
        st.dataframe(df.drop("id", axis=1))

        st.subheader("Data Quality Check")
        # List of columns that are allowed to have missing values
        optional_cols = ["features", "song_title"]
        # Columns to check for missing values are all columns except the optional ones
        cols_to_check = [col for col in df.columns if col not in optional_cols]
        missing_data_df = df[df[cols_to_check].isna().any(axis=1)]
        st.write("Songs with one or more missing required fields:")
        st.dataframe(missing_data_df.drop("id", axis=1))

        st.markdown("---")
        st.markdown(
            "Found an issue or have a feature request? "
            "[Contribute on GitHub](https://github.com/UkuleleTuesday/stats)"
        )


main()
