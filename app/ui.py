"""Shared look and data loading for the Streamlit app."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

INK = "#1C1917"
MUTED = "#78716C"
SURFACE = "#FFFBF5"
RUST = "#9A3412"
TEAL = "#1F4E46"
NEUTRAL = "#E7E2DA"

CHART = {
    "template": "plotly_white",
    "paper_bgcolor": SURFACE,
    "plot_bgcolor": SURFACE,
    "font_color": INK,
}

# Diverging scale for indices around 100: green = cheaper than Delhi, terracotta = dearer.
DIVERGING = [[0.0, TEAL], [0.5, NEUTRAL], [1.0, RUST]]


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
    special = {"BBQ": "BBQ", "CAFE": "Cafe", "TEX_MEX": "Tex-Mex", "HOT_DOG": "Hot Dog", "OTHER": "Other"}
    if token in special:
        return special[token]
    return token.replace("_", " ").title()


def pretty_feature(column: str) -> str:
    """Readable label for a Deliverable 4 model feature column."""
    prefixes = {"ING_": "Ingredient: ", "TECH_": "Technique: ", "DESC_": "Descriptor: ", "LOC_": "Locality: ",
                "CUI_": "Lists cuisine: ", "DISH_": "Dish: "}
    for prefix, label in prefixes.items():
        if column.startswith(prefix):
            return label + pretty_token(column[len(prefix):]).replace("Portion ", "portion ")
    named = {
        "description_words": "Description length (words)",
        "pieces_listed": "Piece count in name",
        "variants": "Size/variant listings",
        "n_cuisines": "Number of cuisines listed",
        "log_menu_items": "Menu size",
        "description_share": "Share of menu with descriptions",
        "image_share": "Share of menu with photos",
        "is_chain": "Chain (2+ outlets in data)",
        "pure_veg": "Pure-veg restaurant",
        "rating": "Delivery rating",
        "rating_missing": "No rating",
        "log_rating_count": "Number of ratings",
    }
    return named.get(column, column)


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


@st.cache_data(show_spinner=False)
def district_layers() -> list[dict]:
    """District outlines as map layers, so point maps sit on the same plain base as the Food Map."""
    from map.districts import load_districts

    geo = load_districts()
    return [
        {"sourcetype": "geojson", "source": geo, "type": "fill", "color": "#F6EDE4", "opacity": 0.55, "below": "traces"},
        {"sourcetype": "geojson", "source": geo, "type": "line", "color": "#A8A29E", "line": {"width": 1}},
    ]
