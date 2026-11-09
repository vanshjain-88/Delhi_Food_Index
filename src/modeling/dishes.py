"""Canonical dish matching for the price-driver analysis.

Each canonical dish is a set of name patterns plus exclusions. A menu row
matches when its normalized name contains one pattern and none of the
exclusions. Exclusions remove combos, platters and dishes that only *contain*
the target (butter chicken pizza, paneer tikka roll, dal makhani with rice).

Aliases were checked against the menu before they were added:

* "murgh makhani" and "chicken makhani" are butter chicken.
* "butter chicken masala" is butter chicken.
* "paneer makhani" / "paneer makhanwala" are paneer butter masala.
* "chicken dum biryani" is chicken biryani; "hyderabadi" is kept and recorded
  as a style feature, not a different dish.
* "hakka noodles" and "chowmein" are kept apart: chowmein is a street-food
  dish in Delhi with a different price point, so it is its own canonical dish.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

COMBO_WORDS = (
    "combo", "thali", "meal", "platter", "with", "and", "box", "bowl", "family",
    "party", "pack", "feast", "kit", "bucket", "pizza", "roll", "wrap", "burger",
    "sandwich", "momo", "momos", "frankie", "paratha", "naan", "kulcha", "rice",
    "biryani", "pasta", "noodles", "fried rice", "salad", "soup", "dosa", "bun",
    "drink", "coke", "pepsi", "fries", "chawal", "khichdi", "raita", "samosa", "patty",
    "bread", "shawarma", "poppers", "lunchbox", "sampler", "lasagna", "tikka", "kulcha",
    "chilla", "puff", "bites", "nuggets", "sizzler", "toast", "maggi",
    "omelette", "parantha", "seekh", "corn dog", "naanza", "pocket",
)


@dataclass(frozen=True)
class CanonicalDish:
    key: str
    label: str
    patterns: tuple[str, ...]
    exclude: tuple[str, ...] = ()
    # words from COMBO_WORDS that belong to this dish and must not exclude it
    allow: tuple[str, ...] = ()
    recipe: tuple[str, ...] = field(default_factory=tuple)


CANONICAL_DISHES: tuple[CanonicalDish, ...] = (
    CanonicalDish("butter_chicken", "Butter Chicken",
                  ("butter chicken", "murgh makhani", "chicken makhani"),
                  exclude=("veg", "lasagna", "slider", "bao", "taco", "sushi", "quesadilla", "nachos", "pie", "puff"),
                  recipe=("chicken", "butter", "cream", "tomato")),
    CanonicalDish("dal_makhani", "Dal Makhani", ("dal makhani", "daal makhani", "dal makhni", "daal makhni"),
                  recipe=("black lentil", "butter", "cream")),
    CanonicalDish("paneer_butter_masala", "Paneer Butter Masala",
                  ("paneer butter masala", "paneer makhani", "paneer makhanwala"),
                  recipe=("paneer", "butter", "cream", "tomato")),
    CanonicalDish("shahi_paneer", "Shahi Paneer", ("shahi paneer",), exclude=("tikka",), recipe=("paneer", "cream", "cashew")),
    CanonicalDish("kadai_paneer", "Kadai Paneer", ("kadai paneer", "kadhai paneer", "karahi paneer"),
                  recipe=("paneer", "capsicum", "tomato")),
    CanonicalDish("dal_tadka", "Dal Tadka", ("dal tadka", "daal tadka", "dal fry", "daal fry", "yellow dal tadka"),
                  exclude=("anda", "egg", "chicken", "keema"),
                  recipe=("yellow lentil", "ghee")),
    CanonicalDish("chicken_biryani", "Chicken Biryani", ("chicken biryani", "chicken dum biryani", "murgh biryani"),
                  exclude=("butter", "tikka", "chilli", "65"),
                  allow=("biryani", "rice"), recipe=("chicken", "rice")),
    CanonicalDish("veg_biryani", "Veg Biryani", ("veg biryani", "vegetable biryani", "veg dum biryani"),
                  exclude=("paneer", "non veg", "soya", "chicken", "egg"), allow=("biryani", "rice"), recipe=("rice", "vegetables")),
    CanonicalDish("paneer_tikka", "Paneer Tikka", ("paneer tikka",), exclude=("masala", "butter"), allow=("tikka",),
                  recipe=("paneer", "yogurt")),
    CanonicalDish("chicken_tikka", "Chicken Tikka", ("chicken tikka",), exclude=("masala", "butter", "veg", "soya", "gravy", "lababdar", "kabab", "kebab"),
                  allow=("tikka",),
                  recipe=("chicken", "yogurt")),
    CanonicalDish("tandoori_chicken", "Tandoori Chicken", ("tandoori chicken",), recipe=("chicken", "yogurt")),
    CanonicalDish("chilli_paneer", "Chilli Paneer", ("chilli paneer", "chili paneer"), exclude=("roll", "noodle", "rice"), recipe=("paneer", "capsicum", "soy sauce")),
    CanonicalDish("chilli_chicken", "Chilli Chicken", ("chilli chicken", "chili chicken"), recipe=("chicken", "capsicum", "soy sauce")),
    CanonicalDish("veg_manchurian", "Veg Manchurian", ("veg manchurian", "vegetable manchurian"),
                  recipe=("vegetables", "soy sauce")),
    CanonicalDish("veg_fried_rice", "Veg Fried Rice", ("veg fried rice", "vegetable fried rice"),
                  allow=("rice", "fried rice"), recipe=("rice", "vegetables", "soy sauce")),
    CanonicalDish("hakka_noodles", "Veg Hakka Noodles", ("veg hakka noodle", "vegetable hakka noodle", "hakka noodle"),
                  exclude=("chicken", "egg", "prawn", "paneer", "non veg", "pork", "mixed", "mix", "chilli garlic", "schezwan"),
                  allow=("noodles",), recipe=("noodles", "vegetables", "soy sauce")),
    CanonicalDish("veg_momos", "Veg Momos", ("veg momo", "veg steamed momo", "vegetable momo"),
                  allow=("momo", "momos"), exclude=("fried", "tandoori", "kurkure", "pan fried", "chilli", "chilly", "afghani", "gravy", "pepper", "cheese",
                           "paneer", "schezwan", "jhol", "malai"),
                  recipe=("flour", "vegetables")),
    CanonicalDish("margherita_pizza", "Margherita Pizza", ("margherita pizza", "margarita pizza", "margherita"),
                  allow=("pizza",), exclude=("makhani", "paneer", "chicken", "tandoori"), recipe=("flour", "cheese", "tomato")),
    CanonicalDish(key="french_fries", label="French Fries", allow=("fries",), patterns=("french fries", "salted fries", "classic fries", "plain fries", "classic salted fries", "salted french fries"),
                  exclude=("peri", "cheese", "cheesy", "masala", "loaded", "piri", "chicken", "sweet potato", "truffle",
                           "tandoori", "chilli", "schezwan", "mexican", "cajun", "garlic", "spicy", "herb", "chatpata"),
                  recipe=("potato",)),
    CanonicalDish("cold_coffee", "Cold Coffee", ("cold coffee",), recipe=("coffee", "milk", "sugar")),
    CanonicalDish("masala_dosa", "Masala Dosa", ("masala dosa",), allow=("dosa",),
                  exclude=("mysore", "paneer", "cheese", "rava", "onion", "butter", "ghee", "spring", "schezwan"),
                  recipe=("rice", "lentil", "potato")),
    CanonicalDish("chole_bhature", "Chole Bhature", ("chole bhature", "chole bhatura", "chhole bhature", "chole bhatoore"),
                  recipe=("chickpea", "flour")),
    CanonicalDish("gulab_jamun", "Gulab Jamun", ("gulab jamun",), exclude=("ice cream", "cheesecake", "shake", "rabri"),
                  recipe=("khoya", "sugar")),
)

DISH_BY_KEY = {dish.key: dish for dish in CANONICAL_DISHES}


def _contains(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}s?\b", text) is not None


def match_dish(normalized_name: str | None) -> str | None:
    """Return the canonical dish key for a normalized dish name, or None."""
    if not normalized_name:
        return None
    text = normalized_name
    for dish in CANONICAL_DISHES:
        hit = next((p for p in dish.patterns if _contains(text, p)), None)
        if hit is None:
            continue
        if any(_contains(text, word) for word in dish.exclude):
            continue
        # Combo words outside the matched phrase rule the row out.
        rest = text.replace(hit, " ")
        blocked = [w for w in COMBO_WORDS if w not in dish.allow and _contains(rest, w)]
        if blocked:
            continue
        return dish.key
    return None


def match_menu(menu_items: pd.DataFrame) -> pd.DataFrame:
    """Add ``canonical_dish`` to menu rows and keep the matching ones."""
    frame = menu_items.copy()
    frame["canonical_dish"] = frame["normalized_dish_name"].map(match_dish)
    return frame[frame["canonical_dish"].notna()].copy()
