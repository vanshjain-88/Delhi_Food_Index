"""Deliverable 1: a browsable preview of the Delhi menu dataset."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

st.set_page_config(
    page_title="Delhi Gastronomic Dataset",
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

CHART = {"template": "plotly_white", "paper_bgcolor": "#FFFBF5", "plot_bgcolor": "#FFFBF5", "font_color": "#1C1917"}


def pretty_token(token: str) -> str:
    special = {"BBQ": "BBQ", "CAFE": "Cafe", "TEX_MEX": "Tex-Mex", "HOT_DOG": "Hot Dog"}
    if token in special:
        return special[token]
    return token.replace("_", " ").title()


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
    show = show.rename(columns={"name": "restaurant_name"})
    return restaurants, show, localities


def cuisine_counts(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for value in frame["canonical_cuisines"].dropna():
        for token in str(value).split(" | "):
            if token:
                rows.append(pretty_token(token))
    if not rows:
        return pd.DataFrame(columns=["Cuisine", "Restaurants"])
    counts = pd.Series(rows).value_counts().rename_axis("Cuisine").reset_index(name="Restaurants")
    return counts


restaurants, dishes, localities = load_tables()

st.title("Delhi Gastronomic Dataset")
st.caption(
    "Deliverable 1. Restaurants, menus, localities, ratings, and prices for New Delhi. "
    "Collected 9 November 2026 from the Kaggle Zomato delivery-menu snapshot. "
    "Cost for two is observed. Dish prices are estimated from it: a main dish is 35% of the bill and a drink is 15%."
)

locality_options = ["All localities"] + sorted(restaurants["locality_name"].dropna().unique())
cuisine_options = ["All cuisines"] + cuisine_counts(restaurants)["Cuisine"].tolist()
role_options = ["All roles", "main", "starter", "beverage", "dessert", "accompaniment", "other"]

with st.sidebar:
    st.header("Explore")
    locality = st.selectbox("Locality", locality_options)
    cuisine = st.selectbox("Cuisine", cuisine_options)
    role = st.selectbox("Dish role", role_options)
    veg = st.selectbox("Diet", ["All", "Veg items", "Non-veg items"])
    query = st.text_input("Dish name", placeholder="paneer tikka")

filtered_restaurants = restaurants
if locality != "All localities":
    filtered_restaurants = filtered_restaurants[filtered_restaurants["locality_name"] == locality]
if cuisine != "All cuisines":
    token = cuisine.upper().replace("-", "_").replace(" ", "_")
    filtered_restaurants = filtered_restaurants[
        filtered_restaurants["canonical_cuisines"].fillna("").str.contains(token, regex=False)
    ]

restaurant_ids = set(filtered_restaurants["restaurant_id"])
filtered_dishes = dishes[dishes["restaurant_id"].isin(restaurant_ids)]
if role != "All roles":
    filtered_dishes = filtered_dishes[filtered_dishes["item_role"] == role]
if veg == "Veg items":
    filtered_dishes = filtered_dishes[filtered_dishes["is_veg"] == True]  # noqa: E712
elif veg == "Non-veg items":
    filtered_dishes = filtered_dishes[filtered_dishes["is_veg"] == False]  # noqa: E712
if query.strip():
    needle = query.strip().lower()
    filtered_dishes = filtered_dishes[
        filtered_dishes["dish_name"].fillna("").str.lower().str.contains(needle, regex=False)
    ]
if role != "All roles" or veg != "All" or query.strip():
    filtered_restaurants = filtered_restaurants[
        filtered_restaurants["restaurant_id"].isin(set(filtered_dishes["restaurant_id"]))
    ]

left, middle, right, far = st.columns(4)
left.metric("Restaurants", f"{filtered_restaurants['restaurant_id'].nunique():,}")
middle.metric("Menu items", f"{len(filtered_dishes):,}")
right.metric("Localities", f"{filtered_restaurants['locality_name'].nunique():,}")
far.metric("Cuisine labels", f"{len(cuisine_counts(filtered_restaurants)):,}")
st.caption(
    f"Full dataset: {len(restaurants):,} restaurants, {dishes['dish_id'].nunique():,} menu items, "
    f"{len(localities):,} localities. "
    f"{int(restaurants['cost_for_two'].notna().sum()):,} restaurants have a cost for two."
)

chart_left, chart_right = st.columns(2)
cuisine_chart = cuisine_counts(filtered_restaurants).head(12)
with chart_left:
    st.subheader("Cuisines")
    if cuisine_chart.empty:
        st.info("No cuisines in this filter.")
    else:
        figure = px.bar(
            cuisine_chart,
            x="Restaurants",
            y="Cuisine",
            orientation="h",
            color_discrete_sequence=["#9A3412"],
        )
        figure.update_layout(
            yaxis={"categoryorder": "total ascending"},
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            height=420,
            showlegend=False,
            **CHART,
        )
        st.plotly_chart(figure, width="stretch")

with chart_right:
    st.subheader("Cost for two")
    costs = filtered_restaurants["cost_for_two"].dropna()
    if costs.empty:
        st.info("No cost for two in this filter.")
    else:
        figure = px.histogram(
            costs,
            nbins=20,
            labels={"value": "Cost for two (₹)"},
            color_discrete_sequence=["#1F4E46"],
        )
        figure.update_layout(
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            height=420,
            showlegend=False,
            yaxis_title="Restaurants",
            **CHART,
        )
        st.plotly_chart(figure, width="stretch")

st.subheader("Localities")
locality_chart = (
    filtered_restaurants.groupby("locality_name", dropna=False)
    .size()
    .reset_index(name="Restaurants")
    .sort_values("Restaurants", ascending=False)
    .head(15)
)
if locality_chart.empty:
    st.info("No localities in this filter.")
else:
    figure = px.bar(
        locality_chart,
        x="locality_name",
        y="Restaurants",
        labels={"locality_name": "Locality"},
        color_discrete_sequence=["#9A3412"],
    )
    figure.update_layout(
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        height=360,
        xaxis_tickangle=-35,
        showlegend=False,
        **CHART,
    )
    st.plotly_chart(figure, width="stretch")

st.subheader("Menu")
st.caption(
    "Estimated price is that dish's share of the restaurant's cost for two: "
    "main 35%, starter 18%, other food 20%, drink 15%, dessert 12%, bread or side 8%. "
    "It is not a listed menu price. This snapshot has no observed item prices."
)
preview = filtered_dishes[
    [
        "restaurant_name",
        "locality_name",
        "dish_name",
        "category",
        "item_role",
        "is_veg",
        "estimated_price",
        "cost_for_two",
        "rating",
        "restaurant_id",
    ]
].rename(
    columns={
        "restaurant_name": "Restaurant",
        "locality_name": "Locality",
        "dish_name": "Dish",
        "category": "Category",
        "item_role": "Role",
        "is_veg": "Veg",
        "estimated_price": "Estimated price (₹)",
        "cost_for_two": "Cost for two (₹)",
        "rating": "Rating",
    }
)
if query.strip():
    shown = preview.head(400)
else:
    shown = preview.groupby("restaurant_id", sort=False).head(3).head(400)
st.dataframe(
    shown.drop(columns=["restaurant_id"]),
    width="stretch",
    hide_index=True,
    height=460,
    column_order=[
        "Restaurant",
        "Locality",
        "Dish",
        "Role",
        "Estimated price (₹)",
        "Cost for two (₹)",
        "Category",
        "Veg",
        "Rating",
    ],
    column_config={
        "Restaurant": st.column_config.TextColumn(width="medium"),
        "Dish": st.column_config.TextColumn(width="large"),
        "Estimated price (₹)": st.column_config.NumberColumn(format="₹%.0f"),
        "Cost for two (₹)": st.column_config.NumberColumn(format="₹%.0f"),
        "Rating": st.column_config.NumberColumn(format="%.1f"),
        "Veg": st.column_config.CheckboxColumn(),
    },
)
st.caption(
    f"Showing {len(shown):,} of {len(preview):,} menu rows "
    f"for {filtered_restaurants['restaurant_id'].nunique():,} restaurants."
)
