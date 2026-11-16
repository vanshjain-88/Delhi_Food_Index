"""Shared look and data loading for the Streamlit app."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

# Cream and terracotta theme.
INK = "#1C1917"        # text
MUTED = "#78716C"      # captions, axis text
SURFACE = "#FFFBF5"    # page background
PANEL = "#F6EDE4"      # sidebar, inputs, table headers
BORDER = "#E7E2DA"     # card and divider lines
ACCENT = "#9A3412"     # terracotta: buttons, metrics, bars
SECONDARY = "#1F4E46"  # green, second series next to ACCENT
NEUTRAL = "#E7E2DA"    # midpoint of the diverging scale
CHEAP = "#1F4E46"      # "cheaper than Delhi" end of the diverging scale
GREY = "#A8A29E"       # missing or suppressed

CHART = {
    "template": "plotly_white",
    "paper_bgcolor": SURFACE,
    "plot_bgcolor": SURFACE,
    "font_color": INK,
}

# Diverging scale for indices around 100: green = cheaper than Delhi, terracotta = dearer.
DIVERGING = [[0.0, CHEAP], [0.5, NEUTRAL], [1.0, ACCENT]]


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
        /* Home page cards. */
        [class*="st-key-card_"] {
            background: #FFFFFF;
            border: 1px solid #E7E2DA;
            border-radius: 14px;
            padding: 1.1rem 1.25rem 1.2rem;
        }
        [class*="st-key-card_"] h4 { margin: 0.1rem 0 0.35rem; padding: 0; }
        /* Cards in one row share the height of the tallest. */
        [data-testid="stColumn"]:has([class*="st-key-card_"]) > [data-testid="stVerticalBlock"] { height: 100%; }
        [data-testid="stColumn"]:has([class*="st-key-card_"]) [data-testid="stLayoutWrapper"] { flex: 1 1 auto; }
        [class*="st-key-card_"] { height: 100%; }
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
def load_gap_fill() -> pd.DataFrame:
    """Older restaurant listing (ratings and cost for two, no menus) for districts the 2026 snapshot barely covers.

    Empty if scripts/build_gap_fill.py has not been run, so the app still starts without it.
    """
    path = DATA / "restaurants_2021.parquet"
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


LISTING_COLUMNS = ["place_id", "name", "kind", "category", "label", "confidence", "latitude", "longitude",
                   "district", "source_datasets", "release"]


@st.cache_data(show_spinner=False)
def load_listings() -> pd.DataFrame:
    """Overture Maps restaurant, cafe and eatery listings (names and locations only, no ratings or prices).

    Empty if scripts/build_overture_places.py has not been run, so the app still starts without it.
    """
    path = DATA / "overture_places.parquet"
    if not path.exists():
        return pd.DataFrame(columns=LISTING_COLUMNS)
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def delhi_bounds() -> tuple[float, float, float, float]:
    """(min lon, min lat, max lon, max lat) of the eleven districts."""
    from map.districts import load_districts

    lons: list[float] = []
    lats: list[float] = []

    def walk(node) -> None:
        if isinstance(node[0], (int, float)):
            lons.append(node[0])
            lats.append(node[1])
        else:
            for child in node:
                walk(child)

    for feature in load_districts()["features"]:
        walk(feature["geometry"]["coordinates"])
    return min(lons), min(lats), max(lons), max(lats)


def map_view(bounds: tuple[float, float, float, float], width_px: int = 640, height_px: int = 560,
             pad: float = 1.12) -> dict:
    """Centre and zoom that fit a lon/lat box inside a map of the given pixel size."""
    from math import cos, log2, radians

    west, south, east, north = bounds
    mid_lat = (south + north) / 2
    lon_span = max(east - west, 1e-6) * pad
    lat_span = max(north - south, 1e-6) * pad / cos(radians(mid_lat))
    zoom = min(log2(width_px * 360 / (512 * lon_span)), log2(height_px * 360 / (512 * lat_span)))
    return {"center": {"lat": mid_lat, "lon": (west + east) / 2}, "zoom": round(zoom, 2)}


@st.cache_data(show_spinner=False)
def district_layers() -> list[dict]:
    """District outlines as map layers, so point maps sit on the same plain base as the Food Map."""
    from map.districts import load_districts

    geo = load_districts()
    return [
        {"sourcetype": "geojson", "source": geo, "type": "fill", "color": "#F6EDE4", "opacity": 0.55, "below": "traces"},
        {"sourcetype": "geojson", "source": geo, "type": "line", "color": "#A8A29E", "line": {"width": 1}},
    ]
