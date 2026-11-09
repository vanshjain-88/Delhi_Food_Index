"""Eleven Delhi revenue districts and the restaurants that fall inside them.

Outlines live in data/geo/delhi_districts.geojson. They are OpenStreetMap
boundaries for the districts drawn on the Delhi government district map.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from map.regions import top_cuisines, top_mains

GEO_PATH = Path(__file__).resolve().parents[2] / "data" / "geo" / "delhi_districts.geojson"

# Pastel fills follow the government district poster: peach north, green west,
# blue south-west, yellow centre, pink New Delhi and east, lavender south-east,
# purple Shahdara.
DISTRICTS = (
    ("North", "NORTH", "#F6C89A"),
    ("North West", "NORTH WEST", "#C5DDB4"),
    ("West", "WEST", "#7EBF8A"),
    ("South West", "SOUTH WEST", "#A9CDE4"),
    ("Central", "CENTRAL", "#F3DC6E"),
    ("New Delhi", "NEW DELHI", "#F3A8BE"),
    ("South", "SOUTH", "#B7DDB4"),
    ("South East", "SOUTH EAST", "#C4B0D8"),
    ("East", "EAST", "#F09BBD"),
    ("North East", "NORTH EAST", "#F0DC78"),
    ("Shahdara", "SHAHDARA", "#C49AD8"),
)
COLORS = {name: color for name, _, color in DISTRICTS}
LABELS = {name: label for name, label, _ in DISTRICTS}


def load_districts() -> dict:
    return json.loads(GEO_PATH.read_text())


def district_records() -> list[dict]:
    by_name = {}
    for feature in load_districts()["features"]:
        name = feature["properties"]["name"]
        geometry = shape(feature["geometry"])
        by_name[name] = {
            "name": name,
            "label": feature["properties"].get("label", LABELS.get(name, name.upper())),
            "color": COLORS.get(name, "#E7D3C5"),
            "area_km2": _area_km2(geometry),
            "geometry": geometry,
            "feature": feature,
        }
    missing = [name for name, _, _ in DISTRICTS if name not in by_name]
    if missing:
        raise ValueError(f"District file is missing: {', '.join(missing)}")
    return [by_name[name] for name, _, _ in DISTRICTS]


def assign_district(restaurants: pd.DataFrame) -> pd.Series:
    """District name for each restaurant. A point on a shared edge uses the smaller district."""
    records = district_records()
    geoms = [record["geometry"] for record in records]
    tree = STRtree(geoms)
    names: list[str | None] = []
    for longitude, latitude in zip(restaurants["longitude"], restaurants["latitude"], strict=True):
        if pd.isna(longitude) or pd.isna(latitude):
            names.append(None)
            continue
        point = Point(float(longitude), float(latitude))
        hits = [
            index
            for index in tree.query(point, predicate="intersects")
            if geoms[int(index)].covers(point)
        ]
        if not hits:
            names.append(None)
            continue
        chosen = min(hits, key=lambda index: geoms[int(index)].area)
        names.append(records[int(chosen)]["name"])
    return pd.Series(names, index=restaurants.index, name="district")


def district_profile(restaurants: pd.DataFrame, dishes: pd.DataFrame, district_name: str) -> dict:
    places = restaurants[restaurants["district"] == district_name].copy()
    menu = dishes[dishes["restaurant_id"].isin(set(places["restaurant_id"]))]
    mains = menu[menu["item_role"] == "main"] if "item_role" in menu else menu.iloc[0:0]
    count = int(places["restaurant_id"].nunique()) if not places.empty else 0
    area = next(record["area_km2"] for record in district_records() if record["name"] == district_name)
    return {
        "restaurant_count": count,
        "area_km2": area,
        "restaurants_per_km2": count / area if area else 0.0,
        "median_rating": _median(places["rating"]) if not places.empty else None,
        "median_cost_for_two": _median(places["cost_for_two"]) if not places.empty else None,
        "cuisine_count": int(top_cuisines(places, limit=10_000).shape[0]) if not places.empty else 0,
        "median_main_estimate": _median(mains["estimated_price"]) if "estimated_price" in mains else None,
        "cuisines": top_cuisines(places),
        "dishes": top_mains(menu),
        "places": places.sort_values(["rating", "name"], ascending=[False, True], na_position="last"),
    }


def _area_km2(geometry) -> float:
    """Polygon area in square kilometres at Delhi's latitude."""
    return float(geometry.area) * (111.32**2) * math.cos(math.radians(28.6139))


def _median(series: pd.Series) -> float | None:
    values = series.dropna()
    if values.empty:
        return None
    return float(values.median())
