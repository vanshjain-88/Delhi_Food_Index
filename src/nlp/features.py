"""Rule-based ingredient, technique and descriptor extraction.

Only words that appear in the dish name or the menu description count as
explicit evidence. Ingredients implied by the canonical recipe (butter chicken
contains chicken, butter, cream, tomato) are recorded separately with
``source_type = "inferred"`` and lower confidence. Nothing is extracted from
images or from outside knowledge about a particular restaurant.

Confidence levels:

* 0.95 explicit, in the dish name
* 0.85 explicit, in the description (descriptions are longer and occasionally
  mention an ingredient in a "served with" or "without" clause)
* 0.60 inferred from the canonical recipe
"""

from __future__ import annotations

import re

import pandas as pd

INGREDIENTS: dict[str, tuple[str, ...]] = {
    "CHICKEN": ("chicken", "murgh", "murg"),
    "MUTTON": ("mutton", "lamb", "gosht", "goat"),
    "FISH": ("fish", "basa", "sole", "salmon", "tuna"),
    "PRAWN": ("prawn", "shrimp", "jhinga"),
    "EGG": ("egg", "anda"),
    "PANEER": ("paneer", "cottage cheese"),
    "CHEESE": ("cheese", "cheesy", "mozzarella", "cheddar", "parmesan", "goatcheese", "feta"),
    "BUTTER": ("butter", "makhan", "makhani", "amul"),
    "CREAM": ("cream", "creamy", "malai"),
    "GHEE": ("ghee",),
    "NUTS": ("cashew", "kaju", "almond", "badam", "pista", "pistachio", "walnut", "nut", "nuts"),
    "SAFFRON": ("saffron", "kesar"),
    "MUSHROOM": ("mushroom",),
    "CORN": ("corn", "babycorn"),
    "TOMATO": ("tomato",),
    "ONION": ("onion", "pyaz"),
    "GARLIC": ("garlic", "lasooni", "lehsun"),
    "CAPSICUM": ("capsicum", "bell pepper", "shimla mirch"),
    "POTATO": ("potato", "aloo"),
    "CHILLI": ("chilli", "chili", "mirch", "jalapeno", "peri peri", "piri piri"),
    "YOGURT": ("yogurt", "yoghurt", "curd", "dahi"),
    "CHOCOLATE": ("chocolate", "choco", "cocoa", "nutella", "mocha"),
    "PREMIUM_IMPORT": ("truffle", "parmesan", "olive oil", "avocado", "goatcheese", "feta", "belgian", "nutella", "pesto",
                       "jalapeno", "sourdough", "mascarpone", "burrata"),
}

TECHNIQUES: dict[str, tuple[str, ...]] = {
    "TANDOOR": ("tandoor", "tandoori", "clay oven", "angithi"),
    "GRILLED": ("grill", "grilled", "seekh", "barbeque", "bbq"),
    "CHARCOAL_SMOKED": ("charcoal", "coal", "smoked", "smoky", "smokey", "dhungar", "angara"),
    "SLOW_COOKED": ("slow cooked", "slow-cooked", "overnight", "simmered", "dum", "handi", "dum pukht"),
    "DEEP_FRIED": ("fried", "crispy", "crunchy", "kurkure"),
    "STEAMED": ("steamed", "steam"),
    "BAKED": ("baked", "oven", "wood fired", "woodfired"),
    "STIR_FRIED": ("wok", "tossed", "stirfried", "panfried"),
    "HANDMADE": ("handmade", "hand made", "homemade", "home made", "hand stretched", "hand-stretched"),
}

DESCRIPTORS: dict[str, tuple[str, ...]] = {
    "SIGNATURE": ("signature", "special", "spl", "chef", "house", "premium", "royal", "shahi", "must try"),
    "BONELESS": ("boneless", "without bone"),
    "HALAL": ("halal",),
    "HEALTH": ("healthy", "keto", "gluten free", "protein", "jain", "low fat", "diet", "vegan"),
    "REGIONAL_STYLE": ("punjabi", "amritsari", "hyderabadi", "lucknowi", "lucknawi", "awadhi", "dhaba",
                       "kolkata", "mughlai", "peshawari", "old delhi", "delhi"),
}

PORTION_PATTERNS = {
    "PORTION_HALF": r"\b(half|mini|small|regular|quarter|qtr)\b",
    "PORTION_FULL": r"\b(full|large|jumbo|family|serves 2|serves 3|serves 4)\b",
}
PIECES = re.compile(r"\b(\d{1,2})\s*(?:pcs|pc|pieces|piece|nos)\b")


def _normalize(text: str | None) -> str:
    if not isinstance(text, str):
        return ""
    lowered = text.lower().replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    # Fixed phrases whose words would otherwise trigger the wrong feature:
    # "fried rice" is not deep-fried, "ice cream" is not cream, "cottage cheese" is paneer.
    for phrase, joined in PHRASES.items():
        lowered = re.sub(rf"\b{phrase}\b", joined, lowered)
    # Simple negation: "without onion and garlic", "no onion" are not mentions.
    lowered = re.sub(r"\b(?:without|no|minus)\s+\w+(?:\s+(?:and|or)\s+\w+)?", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


PHRASES = {
    "without bone": "boneless",
    "stir fried": "stirfried",
    "stir fry": "stirfried",
    "pan fried": "panfried",
    "fried rice": "friedrice",
    "ice cream": "icecream",
    "butter milk": "buttermilk",
    "cream of": "creamof",
    "cottage cheese": "paneer",
    "indian cheese": "paneer",
    "indian cottage cheese": "paneer",
    "goat cheese": "goatcheese",
}


def _has(text: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}s?\b", text) for word in words)


def extract(name: str | None, description: str | None) -> list[dict]:
    """All explicit mentions in one menu row."""
    name_text = _normalize(name)
    desc_text = _normalize(description)
    found = []
    for family, vocabulary in (("ingredient", INGREDIENTS), ("technique", TECHNIQUES), ("descriptor", DESCRIPTORS)):
        for label, words in vocabulary.items():
            if _has(name_text, words):
                found.append({"family": family, "feature": label, "evidence": "name", "confidence": 0.95})
            elif _has(desc_text, words):
                found.append({"family": family, "feature": label, "evidence": "description", "confidence": 0.85})
    for label, pattern in PORTION_PATTERNS.items():
        if re.search(pattern, name_text):
            found.append({"family": "descriptor", "feature": label, "evidence": "name", "confidence": 0.95})
    return found


def piece_count(name: str | None) -> float | None:
    match = PIECES.search(_normalize(name))
    return float(match.group(1)) if match else None


def feature_columns() -> dict[str, list[str]]:
    return {
        "ingredient": [f"ING_{k}" for k in INGREDIENTS],
        "technique": [f"TECH_{k}" for k in TECHNIQUES],
        "descriptor": [f"DESC_{k}" for k in DESCRIPTORS] + [f"DESC_{k}" for k in PORTION_PATTERNS],
    }


PREFIX = {"ingredient": "ING_", "technique": "TECH_", "descriptor": "DESC_"}


def wide_flags(rows: pd.DataFrame, key: str = "observation_id") -> pd.DataFrame:
    """Binary feature columns per observation from long extraction rows."""
    columns = [c for group in feature_columns().values() for c in group]
    if rows.empty:
        return pd.DataFrame(columns=[key] + columns)
    explicit = rows[rows["source_type"] == "explicit"].copy()
    explicit["column"] = explicit["family"].map(PREFIX) + explicit["feature"]
    wide = pd.crosstab(explicit[key], explicit["column"]).clip(upper=1)
    return wide.reindex(columns=columns, fill_value=0).reset_index()
