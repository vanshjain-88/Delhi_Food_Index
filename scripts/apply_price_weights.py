"""Attach role weights to the Phase 1 pilot without changing raw files."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ingestion.price_weights import WEIGHTS, assign_role, estimated_price  # noqa: E402

RAW_ITEMS = ROOT / "data" / "raw" / "pilot" / "pilot_menu_items.parquet"
RAW_RESTAURANTS = ROOT / "data" / "raw" / "pilot" / "pilot_restaurants.parquet"
OUT_DIR = ROOT / "data" / "interim"


def build() -> None:
    restaurants = pd.read_parquet(RAW_RESTAURANTS)
    items = pd.read_parquet(RAW_ITEMS)
    costs = restaurants[["restaurant_id", "cost_for_two"]]
    priced = items.merge(costs, on="restaurant_id", how="left")
    priced["item_role"] = [
        assign_role(category, name)
        for category, name in zip(priced["category"], priced["dish_name"], strict=True)
    ]
    priced["price_weight"] = priced["item_role"].map(WEIGHTS)
    priced["estimated_price"] = [
        estimated_price(cost, role)
        for cost, role in zip(priced["cost_for_two"], priced["item_role"], strict=True)
    ]
    priced = priced.drop(columns=["cost_for_two"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    restaurants.to_parquet(OUT_DIR / "pilot_restaurants.parquet", index=False)
    priced.to_parquet(OUT_DIR / "pilot_menu_items.parquet", index=False)
    print(priced["item_role"].value_counts().to_string())
    print("estimated_price missing", int(priced["estimated_price"].isna().sum()), "of", len(priced))
    print("wrote", OUT_DIR)


if __name__ == "__main__":
    build()
