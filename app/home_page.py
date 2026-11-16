"""Home: what the project is, what is in it, and what to be careful about."""

from __future__ import annotations

from typing import Callable

import pandas as pd
import streamlit as st

from ingestion.gap_fill import combine_restaurants
from map.districts import assign_district, district_records
from ui import DATA, cuisine_counts, load_gap_fill, load_listings, load_tables

# page name (must match main.SECTIONS), label, card title, button text, description
CARDS = (
    ("Dataset", "Deliverable 1", "Delhi menu dataset", "Open the dataset",
     "Restaurants, menus, localities, ratings and prices for New Delhi. Filter by locality, cuisine, dish role "
     "and diet, and search any dish."),
    ("Food Map", "Deliverable 2", "Food Map", "Open the food map",
     "The eleven Delhi districts. Hover for restaurant counts, ratings and cost. Click a district to explore its "
     "cuisines, popular dishes and places."),
    ("Price Index", "Deliverable 3", "Gastronomic Price Index", "Open the price index",
     "How expensive each locality is compared with Delhi, after comparing restaurants of the same cuisine. "
     "100 is the Delhi benchmark."),
    ("What Drives Price?", "Deliverable 4", "What drives dish prices?", "Open price drivers",
     "Which features of a dish, its restaurant and its locality go with higher or lower prices, dish by dish. "
     "Associations, not causes."),
)


@st.cache_data(show_spinner=False)
def _facts() -> dict:
    restaurants, dishes, localities = load_tables()
    gpi = pd.read_parquet(DATA / "gpi_locality.parquet")
    selection = pd.read_parquet(DATA / "dish_selection.parquet")
    placed, filled = combine_restaurants(restaurants.assign(district=assign_district(restaurants)), load_gap_fill())
    counts = placed.groupby("district")["restaurant_id"].nunique()
    names = [record["name"] for record in district_records()]
    per_district = {name: int(counts.get(name, 0)) for name in names}
    listings = load_listings()
    listed = listings.groupby("district").size() if not listings.empty else pd.Series(dtype=int)
    return {
        "listed": int(listed.sum()),
        "listed_districts": int((listed > 0).sum()),
        "restaurants": int(restaurants["restaurant_id"].nunique()),
        "menu_items": int(len(dishes)),
        "localities": int(len(localities)),
        "cuisines": int(len(cuisine_counts(restaurants))),
        "indexed": int((gpi["reliability"] != "suppressed").sum()),
        "indexed_total": int(len(gpi)),
        "dishes": int(selection["selected"].sum()),
        "covered": sum(1 for n in per_district.values() if n >= 10),
        "districts": len(names),
        "filled": filled,
        "empty": sorted(name for name, n in per_district.items() if n == 0),
        "thin": sorted((name, n) for name, n in per_district.items() if 0 < n < 10),
    }


def _data_point(page: str, facts: dict) -> str:
    return {
        "Dataset": f"{facts['restaurants']:,} restaurants · {facts['menu_items']:,} menu items",
        "Food Map": (
            f"{facts['listed']:,} places listed, in {facts['listed_districts']} of {facts['districts']} districts"
            if facts["listed"] else
            f"{facts['covered']} of {facts['districts']} districts have 10 or more restaurants with prices"
        ),
        "Price Index": f"{facts['indexed']} of {facts['indexed_total']} localities have enough restaurants for an index",
        "What Drives Price?": f"{facts['dishes']} popular dishes, one model each",
    }[page]


def render_home(open_page: Callable[[str], None]) -> None:
    facts = _facts()

    st.title("Delhi Gastronomic Intelligence")
    st.caption(
        "What Delhi eats and what it costs. A computational gastronomy project built on a public snapshot of "
        "Zomato delivery menus (Kaggle, collected 9 November 2026), older restaurant listings for thinly covered "
        "districts, and Overture Maps place listings. The project did not scrape Zomato."
    )

    figures = st.columns(5)
    figures[0].metric("Restaurants with menus", f"{facts['restaurants']:,}")
    figures[1].metric("Menu items", f"{facts['menu_items']:,}")
    figures[2].metric("Localities", f"{facts['localities']:,}")
    figures[3].metric("Cuisine labels", f"{facts['cuisines']:,}")
    figures[4].metric("Places listed", f"{facts['listed']:,}", help="Overture Maps, all 11 districts. Names, types and locations only.")

    st.subheader("Explore")
    for row in (CARDS[:2], CARDS[2:]):
        columns = st.columns(2)
        for column, (page, label, title, button, text) in zip(columns, row):
            with column.container(key=f"card_{page.lower().replace(' ', '_').replace('?', '')}"):
                st.caption(label)
                st.markdown(f"#### {title}")
                st.write(text)
                st.caption(_data_point(page, facts))
                st.button(button, key=f"open_{page}", on_click=open_page, args=(page,), type="primary")

    st.subheader("Read this before using the numbers")
    thin = ", ".join(f"{name} {n}" for name, n in facts["thin"])
    filled = ", ".join(facts["filled"])
    reach = (
        f"Ratings and cost for two reach every district: from the 2026 snapshot where it has 10 or more restaurants, "
        f"and from 2021 listings in {filled}, where it does not. Those use 2021 rupees, so compare their price index, "
        f"not their rupee amounts."
        if facts["filled"] else
        "Ratings and cost for two come from the 2026 snapshot."
    )
    st.markdown(
        f"- **Menus do not cover all of Delhi.** Menus, dish prices and the price-driver models come from the 2026 "
        f"delivery snapshot, which has {facts['restaurants']:,} restaurants, mostly in central Delhi. {reach} "
        + (f"Still under 10 restaurants with prices: {thin}. " if thin else "")
        + f"The Food Map also lists {facts['listed']:,} restaurants, cafes and shops from Overture Maps in every "
        "district, but only names, types and locations.\n"
        "- **Dish prices are estimates.** The source hides item prices. Cost for two is observed; a dish price is "
        "its role's share of that (main 35%, drink 15%, starter 18%, dessert 12%).\n"
        "- **Associations, not causes.** The price-driver models describe what goes with higher prices. They do not "
        "show what makes a dish expensive.\n"
        "- **Delivery menus only.** Restaurants that do not deliver have no menu in the data."
    )
    st.caption(
        "Data: Kaggle `archangel0x01/zomato-india-delivery-menus`, Delhi extract. Place listings: Overture Maps "
        "Foundation (places theme, permissive licenses). District outlines: OpenStreetMap contributors (ODbL). "
        "Methods and limits are in METHODOLOGY.md and DATA_SOURCES.md."
    )
