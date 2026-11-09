"""Delhi Gastronomic Intelligence."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st

from dataset_page import render_dataset
from map_page import render_map
from ui import apply_theme

st.set_page_config(
    page_title="Delhi Gastronomic Intelligence",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

st.markdown("**Delhi Gastronomic Intelligence**")
section = st.segmented_control(
    "Section",
    ["Dataset", "Food Map"],
    default="Dataset",
    required=True,
    label_visibility="collapsed",
)
if section == "Food Map":
    render_map()
else:
    render_dataset()
