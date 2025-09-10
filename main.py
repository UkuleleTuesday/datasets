import streamlit as st

pg = st.navigation(
    [
        st.Page(
            "pages/song_sheets_stats.py",
            title="Song Sheets Stats",
            icon=":material/analytics:",
            default=True,
        ),
        st.Page(
            "pages/dataset_explorer.py",
            title="Dataset Explorer",
            icon=":material/dataset:",
        )
    ]
)
pg.run()