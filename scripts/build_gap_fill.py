"""Build data/processed/restaurants_2021.parquet: ratings and cost for two where the 2026 snapshot is thin.

Input: data/raw/zomato_2021/DelhiNCR Restaurants.csv (not committed; it carries restaurant phone numbers).
Download it with

    kaggle datasets download -d aestheteaman01/zomato-restaurants-in-delhi-ncr -p data/raw/zomato_2021 --unzip

Run after build_delhi_dataset.py. Rules and limits are in src/ingestion/gap_fill.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ingestion.gap_fill import (  # noqa: E402
    MIN_DISTRICT_RESTAURANTS,
    SNAPSHOT_YEAR,
    clean_listing,
    gap_districts,
)
from map.districts import DISTRICTS, assign_district  # noqa: E402

RAW = ROOT / "data" / "raw" / "zomato_2021" / "DelhiNCR Restaurants.csv"
CURRENT = ROOT / "data" / "processed" / "restaurants.parquet"
OUT = ROOT / "data" / "processed" / "restaurants_2021.parquet"
MANIFEST = ROOT / "data" / "raw" / "zomato_2021" / "SOURCE_MANIFEST.json"


def main() -> None:
    if not RAW.exists():
        raise SystemExit(
            f"Missing {RAW.relative_to(ROOT)}.\nDownload it with:\n  kaggle datasets download "
            "-d aestheteaman01/zomato-restaurants-in-delhi-ncr -p data/raw/zomato_2021 --unzip"
        )
    names = [name for name, _, _ in DISTRICTS]
    raw = pd.read_csv(RAW)
    district = assign_district(raw.rename(columns={"Latitude": "latitude", "Longitude": "longitude"}))
    listing = clean_listing(raw, district)
    current = pd.read_parquet(CURRENT)
    current = current.assign(district=assign_district(current))
    gaps = gap_districts(current, names)
    listing["fills_gap"] = listing["district"].isin(gaps)
    listing.to_parquet(OUT, index=False)

    table = pd.DataFrame(
        {
            "2026 snapshot": current.groupby("district")["restaurant_id"].nunique().reindex(names, fill_value=0),
            f"{SNAPSHOT_YEAR} listing": listing.groupby("district")["restaurant_id"].nunique().reindex(names, fill_value=0),
        }
    )
    table["filled"] = ["yes" if name in gaps else "" for name in table.index]
    print(f"{len(raw)} rows in the file; {len(listing)} inside the eleven districts with a cost for two")
    print(table.to_string())
    print(f"districts filled (2026 snapshot under {MIN_DISTRICT_RESTAURANTS}): {', '.join(gaps) or 'none'}")
    used = listing[listing["fills_gap"]]
    print(f"restaurants used to fill: {len(used)}; with a rating: {int(used['rating'].notna().sum())}")
    print("wrote", OUT.relative_to(ROOT))

    MANIFEST.write_text(
        json.dumps(
            {
                "dataset": "aestheteaman01/zomato-restaurants-in-delhi-ncr",
                "url": "https://www.kaggle.com/datasets/aestheteaman01/zomato-restaurants-in-delhi-ncr",
                "license": "CC0-1.0",
                "kaggle_last_updated": "2021-08-30",
                "snapshot_year": SNAPSHOT_YEAR,
                "rows_in_file": int(len(raw)),
                "rows_in_delhi_districts": int(len(listing)),
                "districts_filled": gaps,
                "not_committed": "DelhiNCR Restaurants.csv (carries restaurant phone numbers)",
                "fields_used": [
                    "Restaurant_Name", "Category", "Pricing_for_2", "Locality", "Delivery_Rating",
                    "Delivery_Rating_Count", "Website", "Address", "Latitude", "Longitude",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
