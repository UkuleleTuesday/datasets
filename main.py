import streamlit as st

pg = st.navigation(
    [
        st.Page(
            "pages/song_sheets_stats.py",
            title="Song Sheets Stats",
            icon=":material/analytics:",
            url_path="song-sheets-stats",
            default=True,
        ),
        st.Page(
            "pages/song_popularity.py",
            title="Song Popularity",
            icon="⭐",
            url_path="song-popularity",
        ),
        st.Page(
            "pages/dataset_explorer.py",
            title="Dataset Explorer",
            icon=":material/dataset:",
            url_path="dataset-explorer",
        )
    ]
)
pg.run()
