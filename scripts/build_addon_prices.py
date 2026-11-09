"""Recover observed add-on prices for dishes from the raw menu JSON."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pricing.addon_prices import extract_addon_prices  # noqa: E402

RAW = ROOT / "data" / "raw" / "zomato" / "delhi_restaurants.parquet"
PROCESSED = ROOT / "data" / "processed"


def main() -> None:
    raw = pd.read_parquet(RAW, columns=["res_id", "json"])
    menu = pd.read_parquet(PROCESSED / "menu_items.parquet")
    prices = extract_addon_prices(raw, menu)
    prices.to_parquet(PROCESSED / "observed_addon_prices.parquet", index=False)
    ratio = (prices["observed_addon_price"] / prices["estimated_price"]).groupby(prices["item_role"]).median()
    print(f"observed add-on prices {len(prices)} rows, {prices['restaurant_id'].nunique()} restaurants")
    print("median observed / estimated by role")
    print(ratio.round(2).to_string())
    print("wrote", PROCESSED / "observed_addon_prices.parquet")


if __name__ == "__main__":
    main()
