import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st
from gdrive_data import load_song_sheets_data_from_secrets, clear_data_cache, test_configuration


def load_data():
    """Load and preprocess the song sheets dataset from Google Drive."""
    try:
        # Fetch data from Google Drive using cached function
        data = load_song_sheets_data_from_secrets()
        df = pd.DataFrame(data)
        
        if df.empty:
            st.error("No data retrieved from Google Drive.")
            return None
            
    except Exception as e:
        st.error(f"Failed to load data from Google Drive: {e}")
        
        # Try to fall back to local JSON file if it exists
        fallback_path = "data/song_sheets_dataset.json"
        try:
            st.info(f"Attempting to load from fallback file: {fallback_path}")
            df = pd.read_json(fallback_path)
            st.warning("Using cached local data. Consider refreshing when Google Drive access is restored.")
        except (FileNotFoundError, ValueError):
            st.info(
                "Please check your Google Drive credentials and folder IDs in the secrets configuration. "
                "For local development, copy secrets.toml.template to .streamlit/secrets.toml and configure your values."
            )
            return None

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

    # Add data refresh button and config test
    col1, col2, col3 = st.columns([1, 1, 8])
    with col1:
        if st.button("🔄 Refresh Data", help="Clear cache and reload data from Google Drive"):
            clear_data_cache()
            st.rerun()
    
    with col2:
        if st.button("🔧 Test Config", help="Test Google Drive configuration"):
            with st.expander("Configuration Test Results", expanded=True):
                test_configuration()

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
