"""Shared look and helpers for the app pages."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

INK = "#1C1917"
MUTED = "#78716C"
SURFACE = "#FFFBF5"
RUST = "#9A3412"
TEAL = "#0F766E"
NEUTRAL = "#E7E2DA"

CHART = {"template": "plotly_white", "paper_bgcolor": SURFACE, "plot_bgcolor": SURFACE, "font_color": INK}

# Diverging scale for indices around 100: teal = cheaper than Delhi, rust = dearer.
DIVERGING = [[0.0, TEAL], [0.5, NEUTRAL], [1.0, RUST]]


def pretty_token(token: str) -> str:
    special = {"BBQ": "BBQ", "CAFE": "Cafe", "TEX_MEX": "Tex-Mex", "HOT_DOG": "Hot Dog", "OTHER": "Other"}
    if token in special:
        return special[token]
    return token.replace("_", " ").title()


def pretty_feature(column: str) -> str:
    """Readable label for a model feature column."""
    prefixes = {"ING_": "Ingredient: ", "TECH_": "Technique: ", "DESC_": "Descriptor: ", "LOC_": "Locality: ",
                "CUI_": "Lists cuisine: ", "DISH_": "Dish: "}
    for prefix, label in prefixes.items():
        if column.startswith(prefix):
            return label + pretty_token(column[len(prefix):]).replace("Portion ", "portion ")
    named = {
        "description_words": "Description length (words)",
        "pieces_listed": "Piece count in name",
        "variants": "Size/variant listings",
        "n_cuisines": "Number of cuisines listed",
        "log_menu_items": "Menu size",
        "description_share": "Share of menu with descriptions",
        "image_share": "Share of menu with photos",
        "is_chain": "Chain (2+ outlets in data)",
        "pure_veg": "Pure-veg restaurant",
        "rating": "Delivery rating",
        "rating_missing": "No rating",
        "log_rating_count": "Number of ratings",
    }
    return named.get(column, column)
