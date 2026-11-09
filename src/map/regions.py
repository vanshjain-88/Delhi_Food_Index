"""Locality regions and food profiles for the Delhi map.

A region is the set of points closer to one locality's restaurant centroid than
to any other. It is a display partition of this snapshot, not an official
Delhi boundary.
"""

from __future__ import annotations

import pandas as pd


def _bounds(points: list[tuple[float, float]], pad_ratio: float = 0.18) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    pad_x = max((max_x - min_x) * pad_ratio, 0.01)
    pad_y = max((max_y - min_y) * pad_ratio, 0.01)
    return min_x - pad_x, min_y - pad_y, max_x + pad_x, max_y + pad_y


def _rectangle(bounds: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    min_x, min_y, max_x, max_y = bounds
    return [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]


def _closer(point: tuple[float, float], origin: tuple[float, float], other: tuple[float, float]) -> bool:
    px, py = point
    ax, ay = origin
    bx, by = other
    return (px - ax) ** 2 + (py - ay) ** 2 <= (px - bx) ** 2 + (py - by) ** 2 + 1e-15


def _cross(start: tuple[float, float], end: tuple[float, float], origin: tuple[float, float], other: tuple[float, float]) -> tuple[float, float]:
    """Point on the segment where distance to the two sites is equal."""
    ax, ay = origin
    bx, by = other
    dx, dy = bx - ax, by - ay
    px, py = start
    vx, vy = end[0] - px, end[1] - py
    rhs = (bx * bx + by * by) - (ax * ax + ay * ay)
    denom = 2 * (dx * vx + dy * vy)
    numer = rhs - 2 * (dx * px + dy * py)
    if abs(denom) < 1e-18:
        t = 0.0
    else:
        t = numer / denom
    t = min(1.0, max(0.0, t))
    return (px + t * vx, py + t * vy)


def _clip(polygon: list[tuple[float, float]], origin: tuple[float, float], other: tuple[float, float]) -> list[tuple[float, float]]:
    if len(polygon) < 3:
        return []
    kept: list[tuple[float, float]] = []
    previous = polygon[-1]
    previous_inside = _closer(previous, origin, other)
    for current in polygon:
        current_inside = _closer(current, origin, other)
        if current_inside:
            if not previous_inside:
                kept.append(_cross(previous, current, origin, other))
            kept.append(current)
        elif previous_inside:
            kept.append(_cross(previous, current, origin, other))
        previous = current
        previous_inside = current_inside
    return _dedupe(kept)


def _dedupe(polygon: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not polygon:
        return []
    cleaned = [polygon[0]]
    for point in polygon[1:]:
        if abs(point[0] - cleaned[-1][0]) > 1e-12 or abs(point[1] - cleaned[-1][1]) > 1e-12:
            cleaned.append(point)
    if len(cleaned) > 1 and abs(cleaned[0][0] - cleaned[-1][0]) < 1e-12 and abs(cleaned[0][1] - cleaned[-1][1]) < 1e-12:
        cleaned.pop()
    return cleaned


def _fallback_box(point: tuple[float, float], size: float = 0.004) -> list[tuple[float, float]]:
    x, y = point
    return [(x - size, y - size), (x + size, y - size), (x + size, y + size), (x - size, y + size)]


def contains(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        crosses = (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-18) + xi
        if crosses:
            inside = not inside
        j = i
    return inside


def locality_polygons(frame: pd.DataFrame) -> list[dict]:
    """One polygon per locality. Coordinates are (longitude, latitude)."""
    rows = frame.dropna(subset=["locality_id", "locality_name", "longitude", "latitude"])
    sites = [
        (str(row.locality_id), str(row.locality_name), (float(row.longitude), float(row.latitude)))
        for row in rows.itertuples(index=False)
    ]
    if not sites:
        return []
    bounds = _bounds([site[2] for site in sites])
    box = _rectangle(bounds)
    polygons = []
    for locality_id, name, origin in sites:
        polygon = list(box)
        for _, _, other in sites:
            if other == origin:
                continue
            polygon = _clip(polygon, origin, other)
            if len(polygon) < 3:
                break
        if len(polygon) < 3 or not contains(origin, polygon):
            polygon = _fallback_box(origin)
        ring = [[x, y] for x, y in polygon]
        ring.append(ring[0])
        polygons.append(
            {
                "type": "Feature",
                "properties": {"locality_id": locality_id, "locality_name": name},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        )
    return polygons


def top_cuisines(restaurants: pd.DataFrame, limit: int = 8) -> pd.DataFrame:
    rows = []
    for value in restaurants["canonical_cuisines"].dropna():
        for token in str(value).split(" | "):
            if token:
                rows.append(token)
    if not rows:
        return pd.DataFrame(columns=["Cuisine", "Restaurants"])
    counts = pd.Series(rows).value_counts().rename_axis("Cuisine").reset_index(name="Restaurants")
    return counts.head(limit)


def top_mains(dishes: pd.DataFrame, limit: int = 8) -> pd.DataFrame:
    mains = dishes[dishes["item_role"] == "main"].dropna(subset=["normalized_dish_name"])
    if mains.empty:
        return pd.DataFrame(columns=["Dish", "Restaurants"])
    counts = (
        mains.groupby("normalized_dish_name")["restaurant_id"]
        .nunique()
        .sort_values(ascending=False)
        .head(limit)
    )
    labels = mains.groupby("normalized_dish_name")["dish_name"].agg(lambda names: names.value_counts().index[0])
    return pd.DataFrame({"Dish": [labels[key] for key in counts.index], "Restaurants": counts.to_numpy()})


def locality_profile(restaurants: pd.DataFrame, dishes: pd.DataFrame, locality_name: str) -> dict:
    places = restaurants[restaurants["locality_name"] == locality_name].copy()
    menu = dishes[dishes["restaurant_id"].isin(set(places["restaurant_id"]))]
    mains = menu[menu["item_role"] == "main"]
    return {
        "restaurant_count": int(places["restaurant_id"].nunique()),
        "median_rating": _median(places["rating"]),
        "median_cost_for_two": _median(places["cost_for_two"]),
        "cuisine_count": int(top_cuisines(places, limit=10_000).shape[0]),
        "median_main_estimate": _median(mains["estimated_price"]) if "estimated_price" in mains else None,
        "cuisines": top_cuisines(places),
        "dishes": top_mains(menu),
        "places": places.sort_values(["rating", "name"], ascending=[False, True], na_position="last"),
    }


def _median(series: pd.Series) -> float | None:
    values = series.dropna()
    if values.empty:
        return None
    return float(values.median())
