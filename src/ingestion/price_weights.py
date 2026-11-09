"""Role weights that turn a restaurant cost-for-two into an estimated item price.

The reference meal for two is two main dishes and two drinks:

    2 * 0.35 + 2 * 0.15 = 1

Other menu roles get a smaller share of the same bill. Those shares are
assumptions, not observed menu prices.
"""

from __future__ import annotations

import re

WEIGHTS = {
    "main": 0.35,
    "beverage": 0.15,
    "starter": 0.18,
    "dessert": 0.12,
    "accompaniment": 0.08,
    "other": 0.20,
}

_NON_FOOD = (
    "party prop",
    "props",
    "cutlery",
    "merchandise",
)
_BEVERAGE = (
    "beverage",
    "drink",
    "drinks",
    "shake",
    "milkshake",
    "cooler",
    "coffee",
    "tea",
    "chai",
    "juice",
    "lassi",
    "mocktail",
    "cocktail",
    "soda",
    "cola",
    "buttermilk",
    "chaas",
    "lemonade",
    "frappe",
    "mojito",
    "smoothie",
    "soft drink",
    "mineral water",
    "cold drink",
    "matcha",
)
_MAIN = (
    "main course",
    "biryani",
    "fried rice",
    "thali",
    "pizza",
    "pasta",
    "noodle",
    "noodles",
    "dosa",
    "combo",
    "meal",
    "curry",
    "mains",
    "uttapam",
    "idli",
    "burger",
    "shawarma",
    "breakfast",
    "gravy",
    "chowmein",
    "taco",
    "thukpa",
    "sabji",
    "lunch",
    "dinner",
    "manchurian",
    "chopsuey",
    "platter",
)
_PROTEIN_MAIN = (
    "paneer",
    "dal",
    "chicken",
    "mutton",
    "chaap",
    "kathal",
    "fish",
    "prawn",
    "lamb",
    "gosht",
    "kofta",
    "korma",
    "makhani",
    "lababdar",
    "kadhai",
    "kadai",
    "palak",
    "malai",
    "keema",
    "nihari",
    "handi",
    "butter masala",
)
_DESSERT = (
    "dessert",
    "ice cream",
    "icecream",
    "cake",
    "pastry",
    "mithai",
    "brownie",
    "cookie",
    "waffle",
    "gulab jamun",
    "rasmalai",
    "jalebi",
    "kheer",
    "halwa",
    "pudding",
    "muffin",
    "doughnut",
    "donut",
    "kulfi",
    "cheesecake",
    "cupcake",
    "sweets",
    "sundae",
    "scoop",
    "laddu",
    "ladoo",
    "chocolate",
    "biscuit",
    "burfi",
    "barfi",
    "rasgulla",
)
_ACCOMPANIMENT = (
    "bread",
    "naan",
    "roti",
    "kulcha",
    "paratha",
    "rumali",
    "chapati",
    "phulka",
    "rice",
    "pulao",
    "raita",
    "salad",
    "papad",
    "pickle",
    "chutney",
    "accompaniment",
    "side",
    "sides",
    "dip",
)
_STARTER = (
    "starter",
    "appetizer",
    "appetiser",
    "snack",
    "soup",
    "momo",
    "momos",
    "roll",
    "rolls",
    "sandwich",
    "sandwiches",
    "chaat",
    "tikka",
    "kebab",
    "kabab",
    "wing",
    "wings",
    "pakora",
    "fries",
    "dimsum",
    "maggi",
    "wrap",
    "munchies",
    "namkeen",
    "spring roll",
    "chilli potato",
)


def _text(category: str | None, dish_name: str | None) -> str:
    raw = f"{category or ''} {dish_name or ''}".lower().replace("&", " and ")
    raw = re.sub(r"[^a-z0-9\s]", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def _matches(text: str, phrases: tuple[str, ...]) -> bool:
    for phrase in phrases:
        forms = {phrase, phrase + "s", phrase + "es"}
        if phrase.endswith("y") and not phrase.endswith(("ay", "ey", "oy", "uy")):
            forms.add(phrase[:-1] + "ies")
        for form in forms:
            if re.search(rf"\b{re.escape(form)}\b", text):
                return True
    return False


def _role_from(text: str) -> str | None:
    if not text:
        return None
    if _matches(text, _NON_FOOD):
        return "non_food"
    looks_like_baked_sweet = _matches(text, ("cake", "pastry", "brownie", "muffin", "cookie"))
    if _matches(text, _BEVERAGE) and not looks_like_baked_sweet:
        return "beverage"
    if _matches(text, _MAIN):
        return "main"
    if _matches(text, _DESSERT):
        return "dessert"
    if _matches(text, _ACCOMPANIMENT):
        return "accompaniment"
    if _matches(text, _STARTER):
        return "starter"
    if _matches(text, _PROTEIN_MAIN):
        return "main"
    return None


def assign_role(category: str | None, dish_name: str | None) -> str:
    """Classify a menu row. An explicit category wins over words in the dish name."""
    category_role = _role_from(_text(category, None))
    if category_role:
        return category_role
    return _role_from(_text(category, dish_name)) or "other"


def estimated_price(cost_for_two: float | None, role: str) -> float | None:
    if cost_for_two is None:
        return None
    try:
        cost = float(cost_for_two)
    except (TypeError, ValueError):
        return None
    if cost != cost or cost <= 0:
        return None
    weight = WEIGHTS.get(role)
    if weight is None:
        return None
    return round(cost * weight, 2)
