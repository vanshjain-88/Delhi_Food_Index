"""Observed rupee prices recovered from menu add-on groups.

Dish records in the snapshot carry no price (``price_login_blocker``). Modifier
groups still do: "Best paired with", "Choose your sides", "Add on" and similar
groups list items with a price. Many of those items are ordinary dishes on the
same restaurant's menu (butter naan, boondi raita, cold coffee, gulab jamun).

A modifier item counts as an observed dish price only when

* its normalized name equals the normalized name of a dish on the *same*
  restaurant's menu,
* its price is positive, and
* the matched dish is food (not a non-food row).

The price is what the restaurant charges for that item as an add-on. It can
differ from the a-la-carte price (an add-on can be discounted), so it is kept
in its own table and labeled ``observed_addon_price``. When one item appears in
several groups at one restaurant, the median price is kept and the spread is
recorded.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

import pandas as pd

from ingestion.zomato_menu import normalize_name, parse_price


def _record(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def iter_modifier_items(record: dict) -> Iterable[dict]:
    menu = record.get("menu") if isinstance(record.get("menu"), dict) else {}
    for group in menu.get("modifier_groups") or []:
        if not isinstance(group, dict):
            continue
        for item in group.get("items") or []:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            price = None
            for key in ("price", "default_price", "display_price", "min_price"):
                price = parse_price(item.get(key))
                if price is not None:
                    break
            yield {
                "group_name": group.get("name"),
                "group_min": group.get("min"),
                "addon_name": name.strip(),
                "normalized_dish_name": normalize_name(name),
                "addon_price": price,
                "addon_item_id": item.get("item_id"),
            }


def extract_addon_prices(raw: pd.DataFrame, menu_items: pd.DataFrame) -> pd.DataFrame:
    """One row per restaurant and matched dish name, with the observed add-on price."""
    rows = []
    for res_id, payload in zip(raw["res_id"], raw["json"]):
        record = _record(payload)
        restaurant_id = f"zomato:{res_id}"
        for item in iter_modifier_items(record):
            item["restaurant_id"] = restaurant_id
            rows.append(item)
    addons = pd.DataFrame(rows)
    if addons.empty:
        return addons
    addons = addons[addons["addon_price"].notna() & (addons["addon_price"] > 0)]
    menu = (
        menu_items[menu_items["item_role"] != "non_food"]
        .sort_values("dish_id")
        .drop_duplicates(["restaurant_id", "normalized_dish_name"])
        [["restaurant_id", "normalized_dish_name", "dish_id", "dish_name", "item_role", "estimated_price"]]
    )
    matched = addons.merge(menu, on=["restaurant_id", "normalized_dish_name"], how="inner")
    summary = (
        matched.groupby(["restaurant_id", "normalized_dish_name"], as_index=False)
        .agg(
            dish_id=("dish_id", "first"),
            dish_name=("dish_name", "first"),
            item_role=("item_role", "first"),
            estimated_price=("estimated_price", "first"),
            observed_addon_price=("addon_price", "median"),
            addon_price_min=("addon_price", "min"),
            addon_price_max=("addon_price", "max"),
            addon_listings=("addon_price", "size"),
            addon_groups=("group_name", lambda s: " | ".join(sorted({str(x) for x in s if x}))[:300]),
        )
    )
    summary["price_source"] = "observed_addon"
    return summary.sort_values(["restaurant_id", "normalized_dish_name"]).reset_index(drop=True)
