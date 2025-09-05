import pandas as pd
import plotly.express as px
import streamlit as st


def load_data(filepath):
    """Load and preprocess the song sheets dataset."""
    try:
        df = pd.read_json(filepath)
    except ValueError as e:
        st.error(f"Error reading JSON file: {e}")
        return None
    except FileNotFoundError:
        st.error(f"Error: The file '{filepath}' was not found.")
        st.info(
            "Please run the build_song_sheets_dataset.py script to generate it first."
        )
        return None

    # Use json_normalize to flatten the 'properties' column
    properties_df = pd.json_normalize(df["properties"])
    # Concatenate the flattened properties with the original dataframe (id and name)
    df = pd.concat([df.drop("properties", axis=1), properties_df], axis=1)

    # Data cleaning and type conversion
    df["difficulty"] = pd.to_numeric(df["difficulty"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    df["specialbooks"] = df["specialbooks"].str.split(",")

    return df


def main():
    st.set_page_config(page_title="Ukulele Tuesday Song Stats", layout="wide")
    st.title("Ukulele Tuesday Song Sheets Dashboard")

    df = load_data("data/song_sheets_dataset.json")

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

        st.markdown("---")
        st.markdown(
            "Found an issue or have a feature request? "
            "[Contribute on GitHub](https://github.com/UkuleleTuesday/stats)"
        )


if __name__ == "__main__":
    main()
