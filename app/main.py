"""Delhi Gastronomic Intelligence."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st

from dataset_page import render_dataset
from map_page import render_map
from price_drivers_page import render_price_drivers
from price_index_page import render_price_index
from ui import apply_theme

st.set_page_config(
    page_title="Delhi Gastronomic Intelligence",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

SECTIONS = {
    "Dataset": render_dataset,
    "Food Map": render_map,
    "Price Index": render_price_index,
    "What Drives Price?": render_price_drivers,
}

st.markdown("**Delhi Gastronomic Intelligence**")
section = st.segmented_control(
    "Section",
    list(SECTIONS),
    default="Dataset",
    required=True,
    label_visibility="collapsed",
)
SECTIONS.get(section, render_dataset)()
