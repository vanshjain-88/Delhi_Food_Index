"""Fill districts the 2026 delivery snapshot barely covers with an older restaurant listing.

The 2026 snapshot (``restaurants.parquet``) has menus, but almost no restaurants in four districts. An older
listing (Zomato restaurants in Delhi NCR, 2021, CC0) has a rating and a cost for two for restaurants in every
district. It has no menus.

Rules, so the two never blur together:

* A district is filled when the 2026 snapshot has fewer than ``MIN_DISTRICT_RESTAURANTS`` restaurants in it.
  In a filled district every figure comes from the older listing. Nothing is averaged across the two.
* Rupee levels are 2021 rupees. The Gastronomic Price Index compares every restaurant with the Delhi median of
  its own snapshot, so an index from 2021 prices is comparable with one from 2026 prices; rupee levels are not.
* A missing rating stays missing. Menus, dish prices and price drivers stay 2026-only.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from ingestion.canonical import split_cuisines
from ingestion.zomato_menu import normalize_name

SOURCE_NAME = "kaggle:aestheteaman01/zomato-restaurants-in-delhi-ncr"
SNAPSHOT_YEAR = 2021
CURRENT_YEAR = 2026
MIN_DISTRICT_RESTAURANTS = 10

# Same columns as restaurants.parquet, plus the district and the snapshot year.
COLUMNS = [
    "restaurant_id", "name", "normalized_name", "address", "locality_id", "locality_name", "locality_raw",
    "city_name", "latitude", "longitude", "rating", "rating_count", "cost_for_two", "cuisine",
    "canonical_cuisines", "url", "source", "source_id", "collection_date", "dish_price_blocked",
    "veg_nonveg", "district", "price_year",
]


def locality_label(raw: str | None) -> str | None:
    """Locality as the 2026 dataset writes it: ', New Delhi' / ', Delhi' dropped (see build_delhi_dataset)."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    text = str(raw).strip()
    for suffix in (", New Delhi", ", Delhi"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    return text or None


def locality_slug(name: str | None) -> str | None:
    normalized = normalize_name(name)
    if not normalized:
        return None
    return "loc_" + normalized.replace(" ", "_")


def _url_slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(url).lower().split("zomato.com/")[-1]).strip("-")


def clean_listing(raw: pd.DataFrame, district: pd.Series) -> pd.DataFrame:
    """Map the 2021 file onto the restaurants schema. Rows outside the eleven districts are dropped.

    ``district`` is aligned to ``raw`` and comes from map.districts.assign_district.
    """
    frame = raw.copy()
    frame["district"] = district
    frame = frame[frame["district"].notna()]
    frame = frame[frame["Pricing_for_2"].notna() & (frame["Pricing_for_2"] > 0)]
    frame = frame.drop_duplicates("Website")

    rating = frame["Delivery_Rating"]
    count = frame["Delivery_Rating_Count"].where(rating.notna())
    labels = frame["Locality"].map(locality_label)
    canonical = frame["Category"].map(split_cuisines)
    slug = frame["Website"].map(_url_slug)
    out = pd.DataFrame(
        {
            "restaurant_id": "zomato2021:" + slug,
            "name": frame["Restaurant_Name"].str.strip(),
            "normalized_name": frame["Restaurant_Name"].map(normalize_name),
            "address": frame["Address"],
            "locality_id": labels.map(locality_slug),
            "locality_name": labels,
            "locality_raw": frame["Locality"].str.strip(),
            "city_name": "Delhi",
            "latitude": frame["Latitude"],
            "longitude": frame["Longitude"],
            "rating": rating,
            "rating_count": count,
            "cost_for_two": frame["Pricing_for_2"].astype(float),
            "cuisine": frame["Category"],
            "canonical_cuisines": canonical.map(lambda tokens: " | ".join(tokens) if tokens else None),
            "url": frame["Website"],
            "source": SOURCE_NAME,
            "source_id": slug,
            "collection_date": str(SNAPSHOT_YEAR),
            "dish_price_blocked": None,
            "veg_nonveg": None,
            "district": frame["district"],
            "price_year": SNAPSHOT_YEAR,
        },
        index=frame.index,
    )
    return out.reset_index(drop=True)[COLUMNS]


def _url_key(url) -> str:
    text = re.sub(r"/(order|info|reviews)$", "", str(url).lower().rstrip("/"))
    return text.split("zomato.com")[-1]


def same_restaurant_costs(current: pd.DataFrame, listing: pd.DataFrame) -> pd.DataFrame:
    """Cost for two in both snapshots for restaurants that appear in both, matched on the Zomato URL (never the name)."""
    left = current.dropna(subset=["url", "cost_for_two"]).assign(key=lambda f: f["url"].map(_url_key))
    right = listing.dropna(subset=["url", "cost_for_two"]).assign(key=lambda f: f["url"].map(_url_key))
    both = left[["key", "cost_for_two"]].merge(right[["key", "cost_for_two"]], on="key", suffixes=("_2026", "_2021"))
    return both.drop_duplicates("key")


def gap_districts(current: pd.DataFrame, district_names: list[str]) -> list[str]:
    """Districts where the 2026 snapshot has fewer than MIN_DISTRICT_RESTAURANTS restaurants."""
    counts = current.groupby("district")["restaurant_id"].nunique()
    return [name for name in district_names if int(counts.get(name, 0)) < MIN_DISTRICT_RESTAURANTS]


def unique_localities(listing: pd.DataFrame, current_names: set[str]) -> pd.DataFrame:
    """Give each 2021 locality a name that cannot be mistaken for another locality or a 2026 one.

    A Zomato locality label such as "Rohini" can sit in two districts. The label stays when it belongs to one
    district only and is not used by the 2026 table; otherwise the district is added: "Rohini (North)".
    """
    frame = listing.copy()
    spread = frame.groupby("locality_name")["district"].nunique()
    ambiguous = frame["locality_name"].isin(set(spread[spread > 1].index) | set(current_names))
    frame["locality_name"] = np.where(
        ambiguous, frame["locality_name"] + " (" + frame["district"] + ")", frame["locality_name"]
    )
    frame["locality_id"] = frame["locality_name"].map(locality_slug)
    return frame


def combine_restaurants(current: pd.DataFrame, supplement: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Restaurants for district-level numbers: 2026 where it is well covered, 2021 in the filled districts.

    ``current`` needs a ``district`` column. Returns the combined frame and the filled district names.
    """
    if supplement.empty or "fills_gap" not in supplement:
        return current.assign(price_year=CURRENT_YEAR), []
    use = supplement[supplement["fills_gap"]]
    filled = sorted(use["district"].unique())
    kept = current[~current["district"].isin(filled)].assign(price_year=CURRENT_YEAR)
    combined = pd.concat([kept, use.drop(columns=["fills_gap"], errors="ignore")], ignore_index=True)
    return combined, filled
