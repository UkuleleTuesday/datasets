import streamlit as st

pg = st.navigation(
    [
        st.Page(
            "pages/song_sheets_stats.py",
            title="Song Sheets Stats",
            icon=":material/analytics:",
            default=True,
        )
    ]
)
pg.run()