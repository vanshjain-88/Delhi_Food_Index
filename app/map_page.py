"""Deliverable 2: Delhi's eleven districts on a white map."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ingestion.gap_fill import CURRENT_YEAR, combine_restaurants
from map.districts import UNTYPED, assign_district, district_profile, district_records, listing_profile
from ui import ACCENT, CHART, INK, SURFACE, load_gap_fill, load_listings, load_tables, pretty_token

HOVER = (
    "<b>%{customdata[0]}</b><br>"
    "%{customdata[1]} places listed<br>"
    "%{customdata[2]} per km²<br>"
    "%{customdata[3]}<br>"
    "Restaurants with prices: %{customdata[4]}<br>"
    "Median rating: %{customdata[5]}<br>"
    "Median cost for two: %{customdata[6]}<extra></extra>"
)


def render_map() -> None:
    restaurants, dishes, _localities = load_tables()
    listings = load_listings()
    placed = restaurants.copy()
    placed["district"] = assign_district(placed)
    placed, filled = combine_restaurants(placed, load_gap_fill())
    records = district_records()
    names = [record["name"] for record in records]
    if st.session_state.get("map_pick"):
        st.session_state.map_district = st.session_state.pop("map_pick")
    if "map_district" not in st.session_state or st.session_state.map_district not in names:
        st.session_state.map_district = "New Delhi"

    with st.sidebar:
        st.header("Explore")
        choice = st.selectbox("District", names, key="map_district")

    st.title("Food Map")
    st.caption(
        "The eleven revenue districts from the Delhi government district map, on a plain background. "
        "Boundaries are OpenStreetMap (June 2018; South uses the current OSM outline). "
        "Click a district to colour it by places per km² and open its profile."
    )

    figure = _figure(records, placed, listings, choice)
    event = st.plotly_chart(
        figure,
        width="stretch",
        on_select="rerun",
        selection_mode="points",
        key="delhi_food_map",
    )
    thin = placed.groupby("district")["restaurant_id"].nunique().reindex(names, fill_value=0)
    thin = thin[thin < 10].sort_values()
    listed_note = (
        f"Places listed are restaurants, cafes, bakeries and sweet shops from Overture Maps (open data, release "
        f"{listings['release'].iloc[0]}, existence confidence 0.5 or more): names, types and locations only. "
        if not listings.empty else
        "No Overture Maps listings are loaded (run scripts/build_overture_places.py), so density is from the "
        "restaurant listings only. "
    )
    filled_note = (
        f"Ratings and cost for two are from the 2026 delivery snapshot, except in {_names(filled)}, where that "
        f"snapshot has too few restaurants and 2021 listings are used instead (2021 rupees, no menus). "
        if filled else "Ratings, cost for two and menus come from the 2026 delivery snapshot. "
    )
    st.caption(
        listed_note
        + filled_note
        + "Districts with fewer than 10 restaurants with prices: "
        + (", ".join(f"{name} {int(count)}" for name, count in thin.items()) if not thin.empty else "none")
        + "."
    )
    clicked = _clicked_district(getattr(event, "selection", {}))
    if clicked and clicked != choice:
        st.session_state.map_pick = clicked
        st.rerun()

    _profile(placed, dishes, listings, choice, choice in filled)


def _figure(records: list[dict], restaurants: pd.DataFrame, listings: pd.DataFrame, selected_name: str) -> go.Figure:
    # Density comes from the Overture listings, which cover every district. The rated restaurants are far fewer
    # outside central Delhi, so a density from them alone would say North and South West are nearly empty.
    source = listings if not listings.empty else restaurants.rename(columns={"restaurant_id": "place_id"})
    counts = source.groupby("district")["place_id"].nunique().to_dict()
    densities = {
        record["name"]: (counts.get(record["name"], 0) / record["area_km2"] if record["area_km2"] else 0.0)
        for record in records
    }
    hottest = max(densities.values()) if densities else 0.0
    figure = go.Figure()
    ordered = sorted(records, key=lambda record: record["geometry"].area, reverse=True)
    for record in ordered:
        part = restaurants[restaurants["district"] == record["name"]]
        listed = listings[listings["district"] == record["name"]] if not listings.empty else listings
        selected = record["name"] == selected_name
        color = _density_color(record["color"], densities[record["name"]], hottest) if selected else record["color"]
        figure.add_trace(
            go.Choroplethmap(
                geojson={"type": "FeatureCollection", "features": [record["feature"]]},
                locations=[record["feature"]["properties"]["district_id"]],
                z=[1],
                featureidkey="properties.district_id",
                colorscale=[[0, color], [1, color]],
                showscale=False,
                marker_opacity=0.9 if selected else 0.78,
                marker_line_width=3.2 if selected else 1.4,
                marker_line_color=ACCENT if selected else "#3A3330",
                customdata=[_hover_row(record["name"], part, listed, record["area_km2"], counts.get(record["name"], 0))],
                hovertemplate=HOVER,
                name=record["name"],
            )
        )
    points = [(record["label"], record["geometry"].representative_point()) for record in records]
    figure.add_trace(
        go.Scattermap(
            lat=[point.y for _, point in points],
            lon=[point.x for _, point in points],
            mode="text",
            text=[label for label, _ in points],
            textfont={"size": 11, "color": INK},
            hoverinfo="skip",
            name="Labels",
        )
    )
    bounds = _bounds(records)
    figure.update_layout(
        map_style="white-bg",
        map_zoom=9.05,
        map_center={"lat": (bounds[1] + bounds[3]) / 2, "lon": (bounds[0] + bounds[2]) / 2},
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=680,
        paper_bgcolor=SURFACE,
        font_color=INK,
        showlegend=False,
    )
    return figure


def _density_color(base: str, density: float, hottest: float) -> str:
    """Shift the clicked district from its poster colour toward terracotta as density rises."""
    if hottest <= 0 or density <= 0:
        return base
    return _mix(base, ACCENT, density / hottest)


def _mix(start: str, end: str, amount: float) -> str:
    amount = min(1.0, max(0.0, amount))

    def channels(color: str) -> tuple[int, int, int]:
        color = color.lstrip("#")
        return tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))

    left, right = channels(start), channels(end)
    mixed = tuple(round(left[index] + (right[index] - left[index]) * amount) for index in range(3))
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def _hover_row(name: str, zomato: pd.DataFrame, listed: pd.DataFrame, area_km2: float, listed_count: int) -> list:
    """Hover text for one district: coverage from the Overture listings, ratings and cost from the restaurant listings."""
    density = f"{(listed_count / area_km2) if area_km2 else 0:.1f}"
    typed = listed[listed["label"] != UNTYPED] if not listed.empty else listed
    kinds = ", ".join(typed["label"].value_counts().head(3).index) if len(typed) else "No type information"
    zomato = zomato.dropna(subset=["cost_for_two"]) if not zomato.empty else zomato
    zomato_count = int(zomato["restaurant_id"].nunique()) if not zomato.empty else 0
    year = int(zomato["price_year"].max()) if zomato_count and "price_year" in zomato else CURRENT_YEAR
    return [
        name,
        f"{listed_count:,}",
        density,
        kinds,
        f"{zomato_count:,}",
        _number(_median(zomato["rating"]), "%.1f") if zomato_count else "—",
        (_rupee(_median(zomato["cost_for_two"])) + ("" if year == CURRENT_YEAR else f" ({year} prices)")) if zomato_count else "—",
    ]


def _bounds(records: list[dict]) -> tuple[float, float, float, float]:
    boxes = [record["geometry"].bounds for record in records]
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _clicked_district(selection) -> str | None:
    points = selection.get("points", []) if selection else []
    for point in points:
        custom = point.get("customdata")
        if isinstance(custom, (list, tuple)) and custom:
            return str(custom[0])
    return None


def _names(names: list[str]) -> str:
    return ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else (names[0] if names else "")


def _profile(restaurants: pd.DataFrame, dishes: pd.DataFrame, listings: pd.DataFrame, district_name: str,
             older: bool = False) -> None:
    zomato = district_profile(restaurants, dishes, district_name)
    listed = listing_profile(listings, district_name)
    zomato_count = zomato["restaurant_count"]
    st.subheader(district_name)

    one, two, three, four = st.columns(4)
    one.metric("Places listed", f"{listed['count']:,}", help="Restaurants, cafes, bakeries and sweet shops (Overture Maps).")
    two.metric("Per km²", f"{listed['per_km2']:.1f}")
    three.metric("Median rating", _number(zomato["median_rating"], "%.1f"),
                 help="Delivery rating of the restaurants listed below. Restaurants without a rating are left out.")
    four.metric("Median cost for two", _rupee(zomato["median_cost_for_two"]),
                help="2021 rupees." if older else "2026 rupees.")
    if zomato_count == 0:
        st.caption(
            f"Rating and cost are blank because no restaurant with a rating or price is listed in {district_name}. "
            "They are not estimated from other districts."
        )
    elif older:
        rated = int(zomato["places"]["rating"].notna().sum())
        st.caption(
            f"Rating and cost come from {zomato_count:,} restaurants in this district, {rated:,} of them rated"
            + (" (a small sample)" if zomato_count < 10 else "")
            + ". Prices are from 2021, so the rupee amounts are lower than the 2026 figures in other districts "
            "and should not be compared with them directly."
        )
    else:
        st.caption(f"Rating and cost come from {zomato_count:,} restaurants in this district"
                   + (" (a small sample)." if zomato_count < 10 else "."))

    st.subheader("What is listed here")
    if listed["count"] == 0:
        st.info(f"No Overture Maps listings fall in {district_name}.")
    else:
        left, right = st.columns([2, 3])
        with left:
            _bar(listed["types"], "Type", "Places")
            if listed["untyped_share"] > 0:
                st.caption(f"{listed['untyped_share']:.0%} of listings carry no type beyond \"restaurant\" and are not charted.")
        with right:
            table = listed["places"][["name", "label", "confidence"]].rename(
                columns={"name": "Name", "label": "Type", "confidence": "Confidence"}
            )
            st.dataframe(
                table,
                width="stretch",
                hide_index=True,
                height=360,
                column_config={"Confidence": st.column_config.ProgressColumn(format="%.2f", min_value=0.0, max_value=1.0,
                                                                              help="Overture's estimate that the place exists.")},
            )
            st.caption("Names, types and locations only. Overture has no ratings, prices or menus.")

    st.subheader("Restaurants, ratings and prices")
    if zomato_count == 0:
        st.info(
            f"No restaurant with a rating or price is listed in {district_name}, so there are no menus, ratings or "
            "prices here. The Price Index and What Drives Price? also have nothing for this district."
        )
        return
    if older:
        st.caption(
            "No menus are available for this district, so there are no dish prices or common mains here. The Price "
            "Index covers it from cost for two; What Drives Price? does not, because it needs menus."
        )
    else:
        st.caption(
            "Median estimated main-dish price: "
            + _rupee(zomato["median_main_estimate"])
            + ". Each estimate is 35% of that dish's own restaurant cost for two, not a listed menu price."
        )

    if older:
        st.markdown("**Cuisines**")
        cuisines = zomato["cuisines"].copy()
        cuisines["Cuisine"] = cuisines["Cuisine"].map(pretty_token)
        _bar(cuisines, "Cuisine", "Restaurants")
    else:
        left, right = st.columns(2)
        with left:
            st.markdown("**Cuisines**")
            cuisines = zomato["cuisines"].copy()
            cuisines["Cuisine"] = cuisines["Cuisine"].map(pretty_token)
            _bar(cuisines, "Cuisine", "Restaurants")
        with right:
            st.markdown("**Common mains**")
            if zomato["dishes"].empty:
                st.info("No main dishes in this district.")
            else:
                _bar(zomato["dishes"], "Dish", "Restaurants")
                st.caption("A main counts once per restaurant, however many times the menu repeats it.")

    st.markdown("**Restaurants**")
    places = zomato["places"][
        ["name", "locality_name", "rating", "cost_for_two", "canonical_cuisines", "address"]
    ].rename(
        columns={
            "name": "Restaurant",
            "locality_name": "Locality",
            "rating": "Rating",
            "cost_for_two": "Cost for two (₹, 2021)" if older else "Cost for two (₹)",
            "canonical_cuisines": "Cuisines",
            "address": "Address",
        }
    )
    places["Cuisines"] = places["Cuisines"].map(_pretty_list)
    st.dataframe(
        places,
        width="stretch",
        hide_index=True,
        height=360,
        column_config={
            "Rating": st.column_config.NumberColumn(format="%.1f"),
            ("Cost for two (₹, 2021)" if older else "Cost for two (₹)"): st.column_config.NumberColumn(format="₹%.0f"),
            "Restaurant": st.column_config.TextColumn(width="medium"),
            "Cuisines": st.column_config.TextColumn(width="large"),
        },
    )


def _bar(frame: pd.DataFrame, label: str, value: str) -> None:
    import plotly.express as px

    figure = px.bar(
        frame,
        x=value,
        y=label,
        orientation="h",
        color_discrete_sequence=[ACCENT],
    )
    figure.update_layout(
        yaxis={"categoryorder": "total ascending"},
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        height=360,
        showlegend=False,
        **CHART,
    )
    st.plotly_chart(figure, width="stretch")


def _pretty_list(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return ", ".join(pretty_token(token) for token in str(value).split(" | ") if token)


def _rupee(value: float | None) -> str:
    if value is None:
        return "—"
    return f"₹{value:,.0f}"


def _number(value: float | None, pattern: str) -> str:
    if value is None:
        return "—"
    return pattern % value


def _median(series: pd.Series) -> float | None:
    values = series.dropna()
    if values.empty:
        return None
    return float(values.median())
