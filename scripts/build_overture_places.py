"""Pull restaurant, cafe and eatery listings for Delhi from Overture Maps and write data/processed/overture_places.parquet.

Why: the Kaggle Zomato snapshot only covers central Delhi, so North and South West have no restaurants and South,
North East and Shahdara have very few. Overture Maps (open data, CDLA Permissive 2.0) lists places everywhere.

What it gives: name, category, coordinates, a 0-1 confidence that the place exists, and the source datasets.
What it does NOT give: ratings, cost for two, prices, menus. Those stay null and are never imputed. Rows are never
merged into the Zomato tables; this is a separate coverage layer.

Run (needs network, reads Overture's public S3 bucket through DuckDB):
    .venv/bin/python scripts/build_overture_places.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from map.districts import assign_district  # noqa: E402

OUT = ROOT / "data" / "processed" / "overture_places.parquet"
BBOX = (76.80, 28.38, 77.40, 28.90)  # lon_min, lat_min, lon_max, lat_max: Delhi plus margin; exact filter is by district polygon
EATERIES = ("restaurant", "casual_eatery", "fast_food_restaurant", "cafe", "coffee_shop")
NOT_FOOD = ("internet_cafe",)
MIN_CONFIDENCE = 0.5  # Overture's own estimate that the place exists; below this is mostly stale or duplicate records
FALLBACK_RELEASE = "2026-10-21.0"


def latest_release() -> str:
    try:
        with urllib.request.urlopen("https://stac.overturemaps.org/catalog.json", timeout=30) as response:
            return json.load(response)["latest"]
    except Exception:  # noqa: BLE001 - network or catalog layout problems fall back to the release used for the repo
        return FALLBACK_RELEASE


def label_for(category: str) -> str:
    special = {
        "restaurant": "Restaurant (type not listed)",
        "cafe": "Cafe",
        "coffee_shop": "Cafe",
        "fast_food_restaurant": "Fast food",
        "bakery": "Bakery",
        "dessert_shop": "Desserts",
        "ice_cream_shop": "Ice cream",
        "indian_sweets_shop": "Indian sweets",
        "candy_store": "Sweets and candy",
        "bar_and_grill_restaurant": "Bar and grill",
        "texmex_restaurant": "Tex-Mex",
        "barbecue_restaurant": "Barbecue",
    }
    if category in special:
        return special[category]
    for suffix in ("_restaurant", "_shop", "_store"):
        if category.endswith(suffix):
            category = category[: -len(suffix)]
            break
    return category.replace("_", " ").capitalize()


def main() -> None:
    release = latest_release()
    source = f"s3://overturemaps-us-west-2/release/{release}/theme=places/type=place/*"
    west, south, east, north = BBOX
    eateries = ", ".join(f"'{value}'" for value in EATERIES)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
    print(f"Reading Overture release {release} ...")
    frame = con.execute(
        f"""
        SELECT id AS place_id,
               names.primary AS name,
               basic_category AS kind,
               taxonomy.primary AS category,
               confidence,
               operating_status,
               addresses[1].postcode AS postcode,
               bbox.xmin AS longitude,
               bbox.ymin AS latitude,
               array_to_string(list_distinct(list_transform(sources, lambda s: s.dataset)), ' | ') AS source_datasets,
               array_to_string(list_distinct(list_transform(sources, lambda s: s.license)), ' | ') AS source_licenses
        FROM read_parquet('{source}', hive_partitioning=1)
        WHERE bbox.xmin BETWEEN {west} AND {east}
          AND bbox.ymin BETWEEN {south} AND {north}
          AND basic_category IN ({eateries})
          AND confidence >= {MIN_CONFIDENCE}
          AND names.primary IS NOT NULL
        """
    ).df()
    print(f"{len(frame):,} eatery records in the bounding box with confidence >= {MIN_CONFIDENCE}")

    frame["category"] = frame["category"].fillna(frame["kind"])  # a few places carry no detailed category
    frame = frame[~frame["category"].isin(NOT_FOOD)]
    frame = frame[frame["operating_status"].fillna("open") != "closed"].drop(columns="operating_status")
    frame["district"] = assign_district(frame)
    frame = frame[frame["district"].notna()].copy()  # drops Gurugram, Noida, Faridabad and other NCR points
    frame["label"] = frame["category"].map(label_for)
    frame["source"] = "overture_maps"
    frame["release"] = release
    frame = frame.sort_values(["district", "name"]).reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(OUT, index=False)

    print(f"Wrote {len(frame):,} places to {OUT.relative_to(ROOT)}")
    print(frame.groupby("district").size().sort_values(ascending=False).to_string())
    print("Licenses:", sorted(set(frame["source_licenses"].dropna().str.split(" | ", regex=False).explode())))


if __name__ == "__main__":
    pd.set_option("display.width", 120)
    main()
