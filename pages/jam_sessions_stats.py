import json
import pandas as pd
import streamlit as st
import urllib.request
import altair as alt
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

        # Create a unique song identifier (song only for conciseness)
        songs_df['song_title'] = songs_df['song']
        
        song_counts = songs_df['song_title'].value_counts().nlargest(20).reset_index()
        song_counts.columns = ['song_title', 'count']

        chart = alt.Chart(song_counts).mark_bar().encode(
            x=alt.X('count', title='Times Played'),
            y=alt.Y('song_title', sort='-x', title='Song'),
            tooltip=['song_title', 'count']
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
        
        # --- Rising Stars and Falls from Grace ---
        st.subheader("Song Popularity Trends")

        # Define recent and past periods (12 months)
        analysis_end_date = pd.to_datetime(end_date)
        period_midpoint = analysis_end_date - pd.DateOffset(months=12)
        period_start = analysis_end_date - pd.DateOffset(months=24)

        # Filter songs and sessions for each period
        recent_songs = songs_df[songs_df['date'] > period_midpoint]
        past_songs = songs_df[(songs_df['date'] > period_start) & (songs_df['date'] <= period_midpoint)]
        
        sessions_recent_count = df[df['date'] > period_midpoint]['session_id'].nunique()
        sessions_past_count = df[(df['date'] > period_start) & (df['date'] <= period_midpoint)]['session_id'].nunique()

        if sessions_recent_count > 0 and sessions_past_count > 0:
            # Calculate frequencies
            freq_recent = (recent_songs['song_title'].value_counts() / sessions_recent_count).reset_index()
            freq_recent.columns = ['song_title', 'recent_freq']
            
            freq_past = (past_songs['song_title'].value_counts() / sessions_past_count).reset_index()
            freq_past.columns = ['song_title', 'past_freq']

            # Merge and calculate change
            trends_df = pd.merge(freq_recent, freq_past, on='song_title', how='outer').fillna(0)
            trends_df['change'] = trends_df['recent_freq'] - trends_df['past_freq']
            
            # Rising Stars
            rising_stars = trends_df.nlargest(10, 'change')
            st.markdown("##### Biggest Rising Stars")
            st.caption(f"Songs played more frequently in the last 12 months compared to the 12 months prior.")

            rising_chart = alt.Chart(rising_stars).mark_bar().encode(
                x=alt.X('change', title='Increase in Plays per Session'),
                y=alt.Y('song_title', sort='-x', title='Song'),
                tooltip=['song_title', 'change']
            ).interactive()
            st.altair_chart(rising_chart, use_container_width=True)
            
            # Falls from Grace
            falling_stars = trends_df.nsmallest(10, 'change')
            st.markdown("##### Biggest Falls from Grace")
            st.caption(f"Songs played less frequently in the last 12 months compared to the 12 months prior.")

            falling_chart = alt.Chart(falling_stars).mark_bar(color='firebrick').encode(
                x=alt.X('change', title='Decrease in Plays per Session'),
                y=alt.Y('song_title', sort='x', title='Song'),
                tooltip=['song_title', 'change']
            ).interactive()
            st.altair_chart(falling_chart, use_container_width=True)
        else:
            st.info("Not enough data in the selected time range to calculate popularity trends (requires at least 24 months of data).")

main()
