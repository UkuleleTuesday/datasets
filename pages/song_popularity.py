import json
import pandas as pd
import streamlit as st
import urllib.request
import altair as alt
import difflib
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


def normalize_for_matching(text: str) -> str:
    """
    Normalize a string for comparison by trimming whitespace and converting to lowercase.

    This function is intentionally kept minimal but structured to allow future extensions
    (e.g., removing punctuation, handling 'feat.' artists, etc.).
    """
    return text.strip().lower()


@st.cache_data(ttl=600)
def load_song_sheets_data() -> Optional[List[Dict[str, Any]]]:
    """Load the canonical song sheets dataset from a public URL."""
    dataset_url = "https://ukulele-tuesday-datasets.storage.googleapis.com/song-sheets/aggregated/latest/data.jsonl"
    all_data: List[Dict[str, Any]] = []

    try:
        with urllib.request.urlopen(dataset_url) as response:
            if response.status != 200:
                return None
            for line in response:
                try:
                    song_data = json.loads(line)
                    # Extract the relevant fields for matching
                    all_data.append({
                        'id': song_data.get('id'),
                        'song': song_data.get('properties', {}).get('song'),
                        'artist': song_data.get('properties', {}).get('artist'),
                        'specialbooks': song_data.get('properties', {}).get('specialbooks'),
                    })
                except json.JSONDecodeError:
                    continue

        # Filter out any incomplete entries
        all_data = [s for s in all_data if s.get('id') and s.get('song') and s.get('artist')]
        return all_data if all_data else None

    except Exception as e:
        st.error(f"Error loading data from public URL: {e}")
        return None


def sanitize_jam_events(events_df, canonical_songs: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Sanitize jam session events by matching to canonical song sheets using difflib.
    Shows warnings for unmatched entries and removes invalid entries from the dataset.
    """
    if not canonical_songs:
        return events_df

    # Create a copy to avoid modifying the original
    sanitized_df = events_df.copy()

    # Ensure the 'specialbooks' column exists and can hold lists
    if 'specialbooks' not in sanitized_df.columns:
        sanitized_df['specialbooks'] = pd.Series(dtype='object')


    # Build canonical keys
    canonical_keys = []
    canonical_data = []
    for song_data in canonical_songs:
        key = f"{song_data['song']} - {song_data['artist']}"
        canonical_keys.append(normalize_for_matching(key))
        canonical_data.append(song_data)

    # Track indices to remove and unmatched songs
    indices_to_remove = []
    unmatched_songs = set()

    # Only process song events
    song_mask = sanitized_df['type'] == 'song'

    for idx in sanitized_df[song_mask].index:
        jam_song = sanitized_df.at[idx, 'song']
        jam_artist = sanitized_df.at[idx, 'artist']

        # Mark for removal if song or artist is None, NaN, empty, or just whitespace/dashes
        if pd.isna(jam_song) or pd.isna(jam_artist):
            indices_to_remove.append(idx)
            continue

        # Convert to strings and strip whitespace
        jam_song_str = str(jam_song).strip()
        jam_artist_str = str(jam_artist).strip()

        # Mark for removal if either is empty or just a dash
        if not jam_song_str or not jam_artist_str or jam_song_str == '-' or jam_artist_str == '-':
            indices_to_remove.append(idx)
            continue

        # Create search key
        jam_key = normalize_for_matching(f"{jam_song_str} - {jam_artist_str}")

        # Use difflib to find close matches
        matches = difflib.get_close_matches(jam_key, canonical_keys, n=1, cutoff=0.8)

        if matches:
            # Find the matched canonical data
            match_index = canonical_keys.index(matches[0])
            matched_data = canonical_data[match_index]

            # Replace with canonical names
            sanitized_df.at[idx, 'song'] = matched_data['song']
            sanitized_df.at[idx, 'artist'] = matched_data['artist']
            
            # Carry over specialbooks data
            specialbooks = matched_data.get('specialbooks')
            if isinstance(specialbooks, str):
                sanitized_df.at[idx, 'specialbooks'] = specialbooks.split(',')
            else:
                sanitized_df.at[idx, 'specialbooks'] = specialbooks
        else:
            # Mark for removal and record the unmatched entry
            unmatched_songs.add(f"{jam_song_str} - {jam_artist_str}")
            indices_to_remove.append(idx)

    # Remove invalid entries
    if indices_to_remove:
        sanitized_df = sanitized_df.drop(indices_to_remove)

    # Display a single warning for all unmatched songs
    if unmatched_songs:
        unmatched_list = "\n".join(f"- {song}" for song in sorted(list(unmatched_songs)))
        st.warning(f"Could not match the following songs, and they have been excluded:\n{unmatched_list}")

    return sanitized_df


def main():
    st.set_page_config(page_title="Ukulele Tuesday Song Popularity", layout="wide", page_icon="⭐")
    st.title("Ukulele Tuesday Song Popularity")

    st.markdown(
        """
        This dashboard provides an interactive exploration of historical jam session data from [Ukulele Tuesday](https://www.ukuleletuesday.ie/).
        It analyzes setlists from past events to show which songs are played most frequently.
        """
    )

    df = load_data_from_public_url()

    if df is not None:
        df["date"] = pd.to_datetime(df["date"])

        # Create year and year-month columns
        df["year"] = df["date"].dt.year
        df["year_month"] = df["date"].dt.to_period("M").astype(str)

        # Generate dropdown options
        years = sorted(df["year"].unique(), reverse=True)
        date_range_options = ["Last 12 months"] + [str(y) for y in years] + ["All time"]
        
        # Date range dropdown
        selected_range = st.selectbox(
            "Select date range",
            options=date_range_options,
            index=0  # Default to "Last 12 months"
        )
        
        # Filter dataframe based on selection
        end_date = df["date"].max().date()
        
        if selected_range == "Last 12 months":
            start_date = end_date - pd.DateOffset(months=12)
            df = df[df["date"] >= pd.to_datetime(start_date)]
        elif selected_range == "All time":
            pass  # No date filter needed
        else:
            # Filter by selected year
            selected_year = int(selected_range)
            df = df[df["year"] == selected_year]

        # Explode the 'events' column to get one row per event
        events_df = df.explode("events").reset_index(drop=True)
        # Normalize the 'events' column, which contains dicts
        events_df = pd.concat([events_df.drop(['events'], axis=1), events_df['events'].apply(pd.Series)], axis=1)

        # Sanitize song and artist names using canonical data
        canonical_songs = load_song_sheets_data()
        if canonical_songs:
            events_df = sanitize_jam_events(events_df, canonical_songs)

        # Filter for song events
        songs_df = events_df[events_df['type'] == 'song'].copy()

        # Add a column to indicate if a song is in the current songbook
        songs_df['in_current_songbook'] = songs_df["specialbooks"].apply(
            lambda x: isinstance(x, list) and "regular" in x
        )

        st.header("Overall Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Jam Sessions", df['session_id'].nunique())
        col2.metric("Total Songs Played", len(songs_df))
        col3.metric("Unique Songs Played", songs_df['song'].nunique())

        st.header("Most Played Songs")

        # Create a unique song identifier (song + artist)
        songs_df['song_artist'] = songs_df['song'] + " - " + songs_df['artist']

        # Group by song and get play count and songbook status
        song_counts = songs_df.groupby('song_artist').agg(
            Plays=('song_artist', 'size'),
            in_current_songbook=('in_current_songbook', 'first')
        ).sort_values(by='Plays', ascending=False).reset_index()
        
        # Rename column for display
        song_counts.rename(columns={'song_artist': 'Song'}, inplace=True)
        
        # Reorder columns
        song_counts = song_counts[['Song', 'Plays', 'in_current_songbook']]

        # Set index to start at 1 for ranking
        song_counts.index = song_counts.index + 1

        def highlight_in_songbook(row):
            return ['background-color: #e6ffed'] * len(row) if row.in_current_songbook else [''] * len(row)

        st.caption("Songs currently included in the songbook are highlighted in green.")

        # Display as a styled dataframe with a progress bar for plays
        st.dataframe(
            song_counts.style.apply(highlight_in_songbook, axis=1),
            use_container_width=True,
            height=(len(song_counts) + 1) * 35,
            column_config={
                "in_current_songbook": None,  # Hide the helper column
                "Plays": st.column_config.ProgressColumn(
                    "Plays",
                    format="%d",
                    min_value=0,
                    max_value=int(song_counts['Plays'].max()),
                ),
            },
        )

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
            freq_recent = (recent_songs['song_artist'].value_counts() / sessions_recent_count).reset_index()
            freq_recent.columns = ['song_artist', 'recent_freq']

            freq_past = (past_songs['song_artist'].value_counts() / sessions_past_count).reset_index()
            freq_past.columns = ['song_artist', 'past_freq']

            # Merge and calculate change
            trends_df = pd.merge(freq_recent, freq_past, on='song_artist', how='outer').fillna(0)
            trends_df['change'] = trends_df['recent_freq'] - trends_df['past_freq']

            # Rising Stars
            rising_stars = trends_df.nlargest(10, 'change')
            st.markdown("##### Biggest Rising Stars")
            st.caption(f"Songs played more frequently in the last 12 months compared to the 12 months prior.")

            rising_chart = alt.Chart(rising_stars).mark_bar().encode(
                x=alt.X('change', title='Increase in Plays per Session'),
                y=alt.Y('song_artist', sort='-x', title='Song'),
                tooltip=['song_artist', 'change']
            ).interactive()
            st.altair_chart(rising_chart, use_container_width=True)

            # Falls from Grace
            falling_stars = trends_df.nsmallest(10, 'change')
            st.markdown("##### Biggest Falls from Grace")
            st.caption(f"Songs played less frequently in the last 12 months compared to the 12 months prior.")

            falling_chart = alt.Chart(falling_stars).mark_bar(color='firebrick').encode(
                x=alt.X('change', title='Decrease in Plays per Session'),
                y=alt.Y('song_artist', sort='x', title='Song'),
                tooltip=['song_artist', 'change']
            ).interactive()
            st.altair_chart(falling_chart, use_container_width=True)
        else:
            st.info("Not enough data in the selected time range to calculate popularity trends (requires at least 24 months of data).")

main()
