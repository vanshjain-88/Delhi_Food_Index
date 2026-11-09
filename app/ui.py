"""Shared look and data loading for the Streamlit app."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

CHART = {
    "template": "plotly_white",
    "paper_bgcolor": "#FFFBF5",
    "plot_bgcolor": "#FFFBF5",
    "font_color": "#1C1917",
}


def apply_theme() -> None:
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


def pretty_token(token: str) -> str:
    special = {"BBQ": "BBQ", "CAFE": "Cafe", "TEX_MEX": "Tex-Mex", "HOT_DOG": "Hot Dog"}
    if token in special:
        return special[token]
    return token.replace("_", " ").title()


def cuisine_counts(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for value in frame["canonical_cuisines"].dropna():
        for token in str(value).split(" | "):
            if token:
                rows.append(pretty_token(token))
    if not rows:
        return pd.DataFrame(columns=["Cuisine", "Restaurants"])
    return pd.Series(rows).value_counts().rename_axis("Cuisine").reset_index(name="Restaurants")


@st.cache_data(show_spinner=False)
def load_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    restaurants = pd.read_parquet(DATA / "restaurants.parquet")
    dishes = pd.read_parquet(DATA / "menu_items.parquet")
    localities = pd.read_parquet(DATA / "localities.parquet")
    show = dishes.merge(
        restaurants[
            [
                "restaurant_id",
                "name",
                "locality_name",
                "rating",
                "cost_for_two",
                "veg_nonveg",
            ]
        ],
        on="restaurant_id",
        how="left",
    )
    return restaurants, show.rename(columns={"name": "restaurant_name"}), localities
