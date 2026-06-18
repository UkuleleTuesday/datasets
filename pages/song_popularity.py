import json
import pandas as pd
import numpy as np
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
                    props = song_data.get('properties', {})
                    all_data.append({
                        'id': song_data.get('id'),
                        'song': props.get('song'),
                        'artist': props.get('artist'),
                        'specialbooks': props.get('specialbooks'),
                        'ready_to_play_date': props.get('ready_to_play_date'),
                        'approved_date': props.get('approved_date'),
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


def parse_eligibility_date(song_data: Dict[str, Any]) -> Optional[pd.Timestamp]:
    """
    Determine when a song first became playable.

    Prefers ``ready_to_play_date`` (when it entered rotation), falling back to
    ``approved_date``. Returns a timezone-naive Timestamp (to compare against the
    timezone-naive session dates), or None if neither date is present/parseable.
    """
    for field in ("ready_to_play_date", "approved_date"):
        raw = song_data.get(field)
        if not raw:
            continue
        ts = pd.to_datetime(raw, errors="coerce", utc=True)
        if pd.notna(ts):
            return ts.tz_localize(None).normalize()
    return None


def wilson_interval(successes: pd.Series, totals: pd.Series, z: float = 1.96):
    """
    Wilson score interval for a binomial proportion.

    Used so windows backed by few sessions render with a wide (uncertain) band
    rather than spiking to a misleading 0% or 100%. Returns (low, high) Series.
    """
    n = totals.replace(0, np.nan)
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = (z / denom) * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (center - margin).clip(lower=0), (center + margin).clip(upper=1)


def compute_reach_timeseries(
    song_artist: str,
    full_songs_df: pd.DataFrame,
    all_sessions: pd.DataFrame,
    eligibility_date: Optional[pd.Timestamp],
    window: int,
) -> pd.DataFrame:
    """
    Build a smoothed "reach" time series for a single song.

    Reach = fraction of sessions (in a trailing window of ``window`` sessions)
    that included the song. The denominator is restricted to *eligible* sessions
    — those on or after the song became playable — so newly added songs are not
    unfairly flattened by counting sessions from before they existed.
    """
    sessions = all_sessions.drop_duplicates("session_id").sort_values("date")
    if eligibility_date is not None:
        sessions = sessions[sessions["date"] >= eligibility_date]

    if sessions.empty:
        return pd.DataFrame(columns=["date", "reach", "low", "high", "n", "played"])

    played_session_ids = set(
        full_songs_df.loc[full_songs_df["song_artist"] == song_artist, "session_id"]
    )
    sessions = sessions.copy()
    sessions["played"] = sessions["session_id"].isin(played_session_ids).astype(int)

    # Trailing window over sessions (not calendar time) so skipped Tuesdays /
    # holiday gaps don't distort the curve. min_periods lets the line start
    # before a full window has accumulated.
    min_periods = max(3, window // 2)
    successes = sessions["played"].rolling(window, min_periods=min_periods).sum()
    totals = sessions["played"].rolling(window, min_periods=min_periods).count()

    sessions["reach"] = successes / totals
    sessions["n"] = totals
    sessions["low"], sessions["high"] = wilson_interval(successes, totals)
    return sessions.dropna(subset=["reach"])[
        ["date", "reach", "low", "high", "n", "played"]
    ]


def render_song_popularity_graph(
    full_songs_df: pd.DataFrame,
    all_sessions: pd.DataFrame,
    eligibility_lookup: Dict[str, pd.Timestamp],
) -> None:
    """Render the per-song popularity-over-time section."""
    st.header("Single Song Popularity Over Time")
    st.caption(
        "Reach = the share of eligible sessions (those after the song entered "
        "rotation) that included this song — i.e. how likely you were to hear it "
        "on a given night. The shaded band is a 95% confidence interval; it widens "
        "when fewer sessions back the estimate."
    )

    # Order the song picker by total plays so popular songs surface first.
    play_order = (
        full_songs_df["song_artist"].value_counts().index.tolist()
    )
    if not play_order:
        st.info("No songs available to chart.")
        return

    col_sel, col_win = st.columns([3, 1])
    selected_song = col_sel.selectbox("Select a song", options=play_order)
    window = col_win.slider(
        "Smoothing window (sessions)", min_value=4, max_value=30, value=13
    )

    eligibility_date = eligibility_lookup.get(selected_song)
    ts = compute_reach_timeseries(
        selected_song, full_songs_df, all_sessions, eligibility_date, window
    )

    total_plays = int((full_songs_df["song_artist"] == selected_song).sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Plays", total_plays)
    c2.metric(
        "Peak Reach",
        f"{ts['reach'].max() * 100:.0f}%" if not ts.empty else "—",
    )
    c3.metric(
        "First Eligible",
        eligibility_date.date().isoformat() if eligibility_date is not None else "—",
    )

    if ts.empty:
        st.info("Not enough eligible sessions to chart a trend for this song yet.")
        return

    base = alt.Chart(ts).encode(
        x=alt.X("date:T", title="Date")
    )
    band = base.mark_area(opacity=0.2, color="#4c78a8").encode(
        y=alt.Y("low:Q", title="Reach (% of sessions)", axis=alt.Axis(format="%")),
        y2="high:Q",
    )
    line = base.mark_line(color="#4c78a8").encode(
        y=alt.Y("reach:Q"),
        tooltip=[
            alt.Tooltip("date:T", title="Date"),
            alt.Tooltip("reach:Q", title="Reach", format=".0%"),
            alt.Tooltip("n:Q", title="Sessions in window"),
        ],
    )
    # Tick marks along the bottom for the nights the song was actually played.
    plays = ts[ts["played"] == 1]
    ticks = alt.Chart(plays).mark_tick(color="#e45756", thickness=2, size=10).encode(
        x="date:T",
        tooltip=[alt.Tooltip("date:T", title="Played on")],
    )
    st.altair_chart((band + line + ticks).interactive(), use_container_width=True)


def main():
    st.set_page_config(page_title="Ukulele Tuesday Song Popularity", layout="wide", page_icon="⭐")
    st.title("Ukulele Tuesday Song Popularity")

    df = load_data_from_public_url()

    if df is not None:
        df["date"] = pd.to_datetime(df["date"])

        # Create year and year-month columns
        df["year"] = df["date"].dt.year
        df["year_month"] = df["date"].dt.to_period("M").astype(str)

        # --- Build the full, sanitized song-play table once ---
        # Done over the entire history (before any date filtering) so the
        # per-song popularity trend has the full record to work with, and so the
        # expensive fuzzy matching only runs a single time.
        canonical_songs = load_song_sheets_data()

        all_events_df = df.explode("events").reset_index(drop=True)
        all_events_df = pd.concat(
            [all_events_df.drop(['events'], axis=1), all_events_df['events'].apply(pd.Series)],
            axis=1,
        )
        if canonical_songs:
            all_events_df = sanitize_jam_events(all_events_df, canonical_songs)

        full_songs_df = all_events_df[all_events_df['type'] == 'song'].copy()
        full_songs_df['song_artist'] = full_songs_df['song'] + " - " + full_songs_df['artist']
        full_songs_df['in_current_songbook'] = full_songs_df["specialbooks"].apply(
            lambda x: isinstance(x, list) and "regular" in x
        )

        # Session list (one row per session) for reach denominators.
        all_sessions = df[['session_id', 'date']].copy()

        # Map each canonical song to when it first became playable.
        eligibility_lookup: Dict[str, pd.Timestamp] = {}
        for song_data in (canonical_songs or []):
            elig = parse_eligibility_date(song_data)
            if elig is not None:
                eligibility_lookup[f"{song_data['song']} - {song_data['artist']}"] = elig

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

        # Derive the date-filtered view from the already-sanitized full table.
        songs_df = full_songs_df[
            full_songs_df['session_id'].isin(df['session_id'])
        ].copy()

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
        
        # Create a new column with icons based on 'in_current_songbook'
        song_counts['In Rotation'] = song_counts['in_current_songbook'].apply(lambda x: '🟢' if x else '⚪')
        
        # Reorder columns for display
        song_counts = song_counts[['Song', 'Plays', 'In Rotation']]

        # Set index to start at 1 for ranking
        song_counts.index = song_counts.index + 1
        
        st.caption("In current sonbgook rotation: 🟢⠀⠀Not in: ⚪")

        # Display as a styled dataframe with a progress bar for plays
        st.dataframe(
            song_counts,
            use_container_width=True,
            height=(len(song_counts) + 1) * 35,
            column_config={
                "Plays": st.column_config.ProgressColumn(
                    "Plays",
                    format="%d",
                    min_value=0,
                    max_value=int(song_counts['Plays'].max()),
                ),
                "In Rotation": st.column_config.TextColumn(
                    width="small",
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

        # Per-song popularity over time always uses the full history (it is not
        # affected by the date-range selector above).
        render_song_popularity_graph(full_songs_df, all_sessions, eligibility_lookup)

main()
