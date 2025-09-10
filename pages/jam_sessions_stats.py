import json
import pandas as pd
import streamlit as st
import urllib.request
from typing import List, Dict, Any, Optional

@st.cache_data(ttl=600)
def load_data_from_public_url() -> Optional[pd.DataFrame]:
    """Load and preprocess the jam sessions dataset from a public URL."""
    dataset_url = "https://ukulele-tuesday-datasets.storage.googleapis.com/jam-sessions/latest/data.jsonl"
    all_data: List[Dict[str, Any]] = []

    try:
        with st.spinner("Loading jam sessions dataset..."):
            with urllib.request.urlopen(dataset_url) as response:
                if response.status != 200:
                    st.error(f"Failed to fetch data: HTTP {response.status}")
                    return None
                for line in response:
                    try:
                        all_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        st.warning(f"Skipping invalid JSON line: {line.strip()}")
                        continue

        if not all_data:
            st.error("No data found in the dataset file.")
            return None

        df = pd.DataFrame(all_data)
        st.success(f"Successfully loaded {len(all_data)} jam sessions")
        return df

    except Exception as e:
        st.error(f"Error loading data from public URL: {e}")
        return None

def main():
    st.set_page_config(page_title="Ukulele Tuesday Jam Session Stats", layout="wide")
    st.title("Ukulele Tuesday Jam Sessions Dashboard")
    
    st.markdown(
        """
        This dashboard provides an interactive exploration of historical jam session data from [Ukulele Tuesday](https://www.ukuleletuesday.ie/).
        It analyzes setlists from past events to show which songs are played most frequently.
        """
    )

    df = load_data_from_public_url()

    if df is not None:
        df["date"] = pd.to_datetime(df["date"])

        # Date range slider
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        
        start_date, end_date = st.slider(
            "Select date range",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="YYYY-MM-DD"
        )
        
        # Filter dataframe based on date range
        df = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]

        # Explode the 'events' column to get one row per event
        events_df = df.explode("events").reset_index(drop=True)
        # Normalize the 'events' column, which contains dicts
        events_df = pd.concat([events_df.drop(['events'], axis=1), events_df['events'].apply(pd.Series)], axis=1)
        
        # Filter for song events
        songs_df = events_df[events_df['type'] == 'song'].copy()
        
        st.header("Overall Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Jam Sessions", df['session_id'].nunique())
        col2.metric("Total Songs Played", len(songs_df))
        col3.metric("Unique Songs Played", songs_df['song'].nunique())
        
        st.header("Analysis")
        st.subheader("Top 20 Most Played Songs")

        # Create a unique song identifier (song + artist)
        songs_df['song_artist'] = songs_df['song'] + " - " + songs_df['artist']
        
        song_counts = songs_df['song_artist'].value_counts().nlargest(20)
        
        st.bar_chart(song_counts, horizontal=True)

main()
