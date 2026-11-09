"""Build the showable Delhi menu dataset from the retained raw extract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ingestion.canonical import split_cuisines  # noqa: E402
from ingestion.price_weights import WEIGHTS, assign_role, estimated_price  # noqa: E402
from ingestion.zomato_menu import (  # noqa: E402
    find_lat_lon,
    find_text,
    iter_menu_items,
    normalize_name,
    parse_price,
)

RAW_PATH = ROOT / "data" / "raw" / "zomato" / "delhi_restaurants.parquet"
OUT_DIR = ROOT / "data" / "processed"
SOURCE_NAME = "kaggle:archangel0x01/zomato-india-delivery-menus"
COLLECTION_DATE = "2026-11-09"


def _record(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _menu(record: dict):
    for key in ("menu", "menus", "order_menu", "menu_data"):
        value = record.get(key)
        if value not in (None, [], {}, ""):
            return value
    return None


def locality_name(raw: str | None) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    text = str(raw).strip()
    for suffix in (", New Delhi", ", Delhi"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    return text or None


def locality_id(name: str | None) -> str | None:
    normalized = normalize_name(name)
    if not normalized:
        return None
    return "loc_" + normalized.replace(" ", "_")


def _restaurant_veg(series: pd.Series) -> str | None:
    known = series.dropna()
    if known.empty:
        return None
    if bool(known.all()):
        return "veg"
    if not bool(known.any()):
        return "nonveg"
    return "mixed"


def _prefer_category(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep one row when a dish is repeated under a menu tab and a food category."""
    if frame.empty:
        return frame
    useful = (
        "main",
        "starter",
        "bread",
        "drink",
        "dessert",
        "rice",
        "biryani",
        "soup",
        "snack",
        "beverage",
        "combo",
        "pizza",
        "pasta",
        "noodle",
        "dosa",
        "thali",
    )

    def rank(category: str | None) -> int:
        text = (category or "").lower()
        return 0 if any(word in text for word in useful) else 1

    ranked = frame.copy()
    ranked["_rank"] = ranked["category"].map(rank)
    with_id = ranked[ranked["source_id"].notna()].sort_values(["_rank", "category"])
    with_id = with_id.drop_duplicates(["restaurant_id", "source_id"], keep="first")
    no_id = ranked[ranked["source_id"].isna()].drop_duplicates(
        ["restaurant_id", "normalized_dish_name", "category"],
        keep="first",
    )
    kept = pd.concat([with_id, no_id], ignore_index=True).drop(columns="_rank")
    counts: dict[str, int] = {}
    unique_ids = []
    for dish_id in kept["dish_id"]:
        seen = counts.get(dish_id, 0)
        counts[dish_id] = seen + 1
        unique_ids.append(dish_id if seen == 0 else f"{dish_id}:{seen}")
    kept["dish_id"] = unique_ids
    return kept


def build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = pd.read_parquet(RAW_PATH)
    restaurants: list[dict] = []
    dishes: list[dict] = []
    for row in source.itertuples(index=False):
        res_id = str(row.res_id)
        record = _record(row.json)
        name = row.restaurant_name
        place = locality_name(row.locality_name)
        lat, lon = find_lat_lon(record)
        cost = row.cost_for_two
        if cost is None or (isinstance(cost, float) and pd.isna(cost)):
            cost = parse_price(find_text(record, ("cost_for_two", "average_cost_for_two", "cft")))
        else:
            cost = parse_price(cost)
        rating = row.delivery_rating
        try:
            rating = None if rating is None or (isinstance(rating, float) and pd.isna(rating)) else float(rating)
        except (TypeError, ValueError):
            rating = None
        rating_count_text = find_text(record, ("votes", "rating_count", "vote_count", "review_count"))
        try:
            rating_count = None if rating_count_text is None else int(float(str(rating_count_text).replace(",", "")))
        except (TypeError, ValueError):
            rating_count = None
        cuisine = row.cuisine_string
        if cuisine is None or (isinstance(cuisine, float) and pd.isna(cuisine)):
            cuisine = None
        else:
            cuisine = str(cuisine)
        canonical = split_cuisines(cuisine)
        menu_node = record.get("menu") if isinstance(record.get("menu"), dict) else {}
        blocked = menu_node.get("price_login_blocker")
        restaurants.append(
            {
                "restaurant_id": f"zomato:{res_id}",
                "name": None if name is None or (isinstance(name, float) and pd.isna(name)) else str(name),
                "normalized_name": normalize_name(None if pd.isna(name) else str(name)),
                "address": find_text(record, ("address", "locality_verbose")),
                "locality_id": locality_id(place),
                "locality_name": place,
                "locality_raw": None if pd.isna(row.locality_name) else str(row.locality_name),
                "city_name": "Delhi",
                "latitude": lat,
                "longitude": lon,
                "rating": rating,
                "rating_count": rating_count,
                "cost_for_two": cost,
                "cuisine": cuisine,
                "canonical_cuisines": " | ".join(canonical) if canonical else None,
                "url": find_text(record, ("restaurant_url", "url", "order_url")),
                "source": SOURCE_NAME,
                "source_id": res_id,
                "collection_date": COLLECTION_DATE,
                "dish_price_blocked": blocked if isinstance(blocked, bool) else None,
            }
        )
        payload = _menu(record)
        seen: set[tuple] = set()
        for index, item in enumerate(iter_menu_items(payload) if payload is not None else []):
            key = (item["normalized_dish_name"], item["category"], item["item_source_id"])
            if key in seen:
                continue
            seen.add(key)
            role = assign_role(item["category"], item["dish_name"])
            item_key = item["item_source_id"] or f"{item['normalized_dish_name'] or 'dish'}:{index}"
            dishes.append(
                {
                    "dish_id": f"zomato:{res_id}:{item_key}",
                    "restaurant_id": f"zomato:{res_id}",
                    "dish_name": item["dish_name"],
                    "normalized_dish_name": item["normalized_dish_name"],
                    "category": item["category"],
                    "cuisine": cuisine,
                    "canonical_cuisines": " | ".join(canonical) if canonical else None,
                    "item_role": role,
                    "price_weight": WEIGHTS.get(role),
                    "observed_price": item["price"],
                    "estimated_price": estimated_price(cost, role),
                    "description": item["description"],
                    "is_veg": item["is_veg"],
                    "image_url": item["image_url"],
                    "source": SOURCE_NAME,
                    "source_id": item["item_source_id"],
                    "collection_date": COLLECTION_DATE,
                }
            )
    restaurant_frame = pd.DataFrame(restaurants).sort_values("restaurant_id").reset_index(drop=True)
    dish_frame = _prefer_category(pd.DataFrame(dishes))
    if not dish_frame.empty:
        veg_summary = dish_frame.groupby("restaurant_id")["is_veg"].apply(_restaurant_veg).rename("veg_nonveg")
        restaurant_frame = restaurant_frame.merge(veg_summary, on="restaurant_id", how="left")
        dish_frame = dish_frame.sort_values(["restaurant_id", "dish_name"]).reset_index(drop=True)
    else:
        restaurant_frame["veg_nonveg"] = None
    locality_rows = (
        restaurant_frame.dropna(subset=["locality_id"])
        .groupby(["locality_id", "locality_name"], dropna=False)
        .agg(
            restaurant_count=("restaurant_id", "size"),
            latitude=("latitude", "mean"),
            longitude=("longitude", "mean"),
            median_cost_for_two=("cost_for_two", "median"),
        )
        .reset_index()
        .sort_values(["restaurant_count", "locality_name"], ascending=[False, True])
    )
    locality_rows.insert(2, "city_name", "Delhi")
    locality_rows["normalized_name"] = locality_rows["locality_name"].map(normalize_name)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    restaurant_frame.to_parquet(OUT_DIR / "restaurants.parquet", index=False)
    dish_frame.to_parquet(OUT_DIR / "menu_items.parquet", index=False)
    locality_rows.to_parquet(OUT_DIR / "localities.parquet", index=False)
    return restaurant_frame, dish_frame, locality_rows


def main() -> None:
    restaurants, dishes, localities = build()
    duplicate_restaurants = int(restaurants["restaurant_id"].duplicated().sum())
    duplicate_dishes = int(dishes["dish_id"].duplicated().sum()) if not dishes.empty else 0
    if duplicate_restaurants or duplicate_dishes:
        raise SystemExit(f"Duplicate ids: restaurants={duplicate_restaurants}, dishes={duplicate_dishes}")
    print(f"restaurants {len(restaurants)}")
    print(f"menu_items {len(dishes)}")
    print(f"localities {len(localities)}")
    print(f"with cost_for_two {int(restaurants['cost_for_two'].notna().sum())}")
    print(f"with coordinates {int((restaurants.latitude.notna() & restaurants.longitude.notna()).sum())}")
    print(f"estimated prices {int(dishes['estimated_price'].notna().sum())}")
    print("wrote", OUT_DIR)


if __name__ == "__main__":
    main()
