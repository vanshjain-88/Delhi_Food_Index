"""Flatten a Zomato restaurant record into restaurant and menu-item rows.

The Kaggle snapshot nests menus in more than one shape. This walker follows
the shapes that show up in Zomato order payloads and skips modifier groups,
which are add-ons rather than dishes.
"""

from __future__ import annotations

import re
from typing import Any, Iterator

SKIP_KEYS = {
    "modifier_groups",
    "modifiergroups",
    "modifiers",
    "modifier_group",
    "customisations",
    "customizations",
    "addons",
    "add_ons",
    "groups_of_modifiers",
}

PRICE_KEYS = ("price", "default_price", "min_price", "display_price", "item_price")
NAME_KEYS = ("name", "item_name", "dish_name")
DESC_KEYS = ("desc", "description", "item_desc", "subtitle")
IMAGE_KEYS = ("item_image_url", "image_url", "photo_url", "image", "item_image")
ID_KEYS = ("id", "item_id", "dish_id")
TAG_KEYS = ("tag_slugs", "dietary_slugs", "tags", "item_tags", "dietary_tag")


def normalize_name(name: str | None) -> str | None:
    if name is None:
        return None
    text = str(name).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _first_present(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return None


def parse_price(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if number > 0 else None
    if isinstance(value, str):
        match = re.search(r"\d+(?:\.\d+)?", value.replace(",", ""))
        if not match:
            return None
        number = float(match.group())
        return number if number > 0 else None
    if isinstance(value, dict):
        return parse_price(_first_present(value, PRICE_KEYS))
    return None


def _tag_blob(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in TAG_KEYS:
        value = item.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            for entry in value:
                if isinstance(entry, str):
                    parts.append(entry)
                elif isinstance(entry, dict):
                    label = entry.get("slug") or entry.get("name") or entry.get("text")
                    if label:
                        parts.append(str(label))
    return " ".join(parts).lower().replace("-", " ").replace("_", " ")


def veg_flag(item: dict[str, Any]) -> bool | None:
    blob = _tag_blob(item)
    if "non veg" in blob or "nonveg" in blob:
        return False
    if re.search(r"\begg\b", blob):
        return None
    if re.search(r"\bveg\b", blob):
        return True
    if "is_veg" in item and isinstance(item["is_veg"], bool):
        return item["is_veg"]
    return None


def bestseller_flag(item: dict[str, Any]) -> bool | None:
    blob = _tag_blob(item)
    if "bestseller" in blob or "best seller" in blob or "must try" in blob:
        return True
    for key in ("is_bestseller", "is_best_seller", "bestseller"):
        if isinstance(item.get(key), bool):
            return item[key]
    return None


def _image_url(item: dict[str, Any]) -> str | None:
    value = _first_present(item, IMAGE_KEYS)
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("url", "src", "image_url"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def item_from_dict(item: dict[str, Any], category: str | None) -> dict[str, Any] | None:
    name = _first_present(item, NAME_KEYS)
    if not isinstance(name, str) or not name.strip():
        return None
    price = None
    for key in PRICE_KEYS:
        if key in item:
            price = parse_price(item.get(key))
            if price is not None:
                break
    description = _first_present(item, DESC_KEYS)
    source_id = _first_present(item, ID_KEYS)
    return {
        "dish_name": name.strip(),
        "normalized_dish_name": normalize_name(name),
        "category": category.strip() if isinstance(category, str) and category.strip() else None,
        "price": price,
        "description": description.strip() if isinstance(description, str) and description.strip() else None,
        "is_veg": veg_flag(item),
        "is_bestseller": bestseller_flag(item),
        "image_url": _image_url(item),
        "item_source_id": str(source_id) if source_id is not None else None,
    }


def _looks_like_item(node: dict[str, Any]) -> bool:
    has_name = any(isinstance(node.get(key), str) and str(node.get(key)).strip() for key in NAME_KEYS)
    has_price = any(key in node for key in PRICE_KEYS)
    has_item_id = node.get("item_id") not in (None, "")
    is_container = any(key in node for key in ("categories", "items", "menus", "menu"))
    return has_name and (has_price or has_item_id) and not is_container


def iter_menu_items(menu: Any, category: str | None = None) -> Iterator[dict[str, Any]]:
    """Yield dish dicts from a nested Zomato menu payload."""
    if isinstance(menu, list):
        for entry in menu:
            yield from iter_menu_items(entry, category)
        return
    if not isinstance(menu, dict):
        return

    next_category = category
    category_node = menu.get("category")
    if isinstance(category_node, dict):
        label = category_node.get("name")
        if isinstance(label, str) and label.strip():
            next_category = label.strip()
    elif isinstance(menu.get("name"), str) and any(
        key in menu for key in ("categories", "items")
    ):
        next_category = menu["name"].strip() or next_category

    wrapped = menu.get("item")
    if isinstance(wrapped, dict):
        parsed = item_from_dict(wrapped, next_category)
        if parsed is not None:
            yield parsed
        for key, value in wrapped.items():
            if key in SKIP_KEYS:
                continue
            yield from iter_menu_items(value, next_category)
        for key, value in menu.items():
            if key == "item" or key in SKIP_KEYS:
                continue
            yield from iter_menu_items(value, next_category)
        return

    if _looks_like_item(menu):
        parsed = item_from_dict(menu, next_category)
        if parsed is not None:
            yield parsed
        return

    for key, value in menu.items():
        if key in SKIP_KEYS:
            continue
        yield from iter_menu_items(value, next_category)


def find_lat_lon(record: dict[str, Any], depth: int = 0) -> tuple[float | None, float | None]:
    """First latitude/longitude pair above the menu subtree."""
    if depth > 5 or not isinstance(record, dict):
        return None, None
    lat = record.get("latitude", record.get("lat"))
    lon = record.get("longitude", record.get("lng", record.get("lon")))
    if lat is not None and lon is not None:
        try:
            return float(lat), float(lon)
        except (TypeError, ValueError):
            pass
    for key, value in record.items():
        if key in {"menu", "menus"} or key in SKIP_KEYS:
            continue
        if isinstance(value, dict):
            found_lat, found_lon = find_lat_lon(value, depth + 1)
            if found_lat is not None and found_lon is not None:
                return found_lat, found_lon
    return None, None


def _as_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def find_text(record: Any, keys: tuple[str, ...], depth: int = 0) -> str | None:
    if depth > 5:
        return None
    if isinstance(record, dict):
        for key in keys:
            text = _as_text(record.get(key))
            if text:
                return text
        for key, value in record.items():
            if key in {"menu", "menus"} or key in SKIP_KEYS:
                continue
            found = find_text(value, keys, depth + 1)
            if found:
                return found
    elif isinstance(record, list):
        for entry in record[:20]:
            found = find_text(entry, keys, depth + 1)
            if found:
                return found
    return None
