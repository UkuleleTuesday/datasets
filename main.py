import pandas as pd
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
    # df["specialbooks"] is not used in the app, so we can remove its processing.
    # df["specialbooks"] = df["specialbooks"].str.split(",")

    return df


def main():
    st.set_page_config(page_title="Ukulele Tuesday Song Stats", layout="wide")
    st.title("Ukulele Tuesday Song Sheets Dashboard")

    df = load_data("data/song_sheets_dataset.json")

    if df is not None:
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

        # Songs by decade of release
        st.subheader("Song Distribution by Decade of Release")
        df_with_year = df.dropna(subset=["year"])
        decade = (df_with_year["year"].astype(int) // 10) * 10
        decade_counts = decade.value_counts().sort_index()
        st.bar_chart(decade_counts)

        # Difficulty distribution
        st.subheader("Difficulty Distribution")
        # Round difficulty to nearest integer for grouping, then count and sort.
        difficulty_groups = df["difficulty"].dropna().round(0).astype(int)
        st.bar_chart(difficulty_groups.value_counts().sort_index())

        # Gender distribution
        st.subheader("Gender Distribution")
        gender_counts = df["gender"].value_counts()
        st.bar_chart(gender_counts)

        st.header("Raw Data")
        st.dataframe(df)


if __name__ == "__main__":
    main()
