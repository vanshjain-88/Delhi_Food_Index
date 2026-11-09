"""Delhi Gastronomic Intelligence: app entry point.

Run with ``streamlit run app/main.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

st.set_page_config(
    page_title="Delhi Gastronomic Intelligence",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background: #FFFBF5;
        color: #1C1917;
    }
    [data-testid="stSidebar"] { background: #F6EDE4; }
    [data-testid="stMetricValue"] { color: #9A3412; }
    </style>
    """,
    unsafe_allow_html=True,
)

pages = [
    st.Page("pages/dataset.py", title="Dataset", icon="🗂️", default=True),
    st.Page("pages/price_index.py", title="Price Index", icon="📊"),
    st.Page("pages/price_drivers.py", title="What Drives Price?", icon="🔎"),
]
st.navigation(pages, position="top").run()
