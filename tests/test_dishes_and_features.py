import json
import unittest

import pandas as pd

from modeling.dishes import match_dish
from nlp.features import extract
from pricing.addon_prices import extract_addon_prices


def feats(name, desc=None):
    return {h["feature"] for h in extract(name, desc)}


class DishMatchTests(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(match_dish("murgh makhani"), "butter_chicken")
        self.assertEqual(match_dish("butter chicken boneless"), "butter_chicken")
        self.assertEqual(match_dish("paneer makhani"), "paneer_butter_masala")
        self.assertEqual(match_dish("hyderabadi chicken dum biryani"), "chicken_biryani")

    def test_combos_and_containers_are_excluded(self):
        self.assertIsNone(match_dish("butter chicken pizza"))
        self.assertIsNone(match_dish("butter chicken roll"))
        self.assertIsNone(match_dish("dal makhani with rice"))
        self.assertIsNone(match_dish("paneer tikka masala"))
        self.assertIsNone(match_dish("butter chicken biryani"))
        self.assertIsNone(match_dish("veg butter chicken"))

    def test_fries_variants(self):
        self.assertEqual(match_dish("french fries"), "french_fries")
        self.assertIsNone(match_dish("peri peri fries"))
        self.assertIsNone(match_dish("cheesy french fries"))


class FeatureTests(unittest.TestCase):
    def test_fried_rice_is_not_deep_fried(self):
        self.assertNotIn("DEEP_FRIED", feats("Veg Fried Rice"))
        self.assertIn("STIR_FRIED", feats("Veg Fried Rice", "stir-fried in a wok"))

    def test_cottage_cheese_is_paneer(self):
        found = feats("Kadai Paneer", "cubes of cottage cheese")
        self.assertIn("PANEER", found)
        self.assertNotIn("CHEESE", found)

    def test_negation(self):
        self.assertNotIn("ONION", feats("Chilli Paneer", "Prepared without onion and garlic"))
        self.assertIn("BONELESS", feats("Chicken Tikka Without Bone"))

    def test_name_beats_description_confidence(self):
        hits = {h["feature"]: h for h in extract("Tandoori Chicken", "cooked in a tandoor")}
        self.assertEqual(hits["TANDOOR"]["evidence"], "name")
        self.assertAlmostEqual(hits["TANDOOR"]["confidence"], 0.95)


class AddonTests(unittest.TestCase):
    def test_only_items_on_the_same_menu_count(self):
        record = {"menu": {"modifier_groups": [{"name": "Best paired with", "items": [
            {"name": "Butter Naan", "price": 60, "item_id": "x1"},
            {"name": "Extra Cheese", "price": 30, "item_id": "x2"},
            {"name": "Complimentary Ketchup", "price": 0, "item_id": "x3"},
        ]}]}}
        raw = pd.DataFrame({"res_id": ["1"], "json": [json.dumps(record)]})
        menu = pd.DataFrame({
            "restaurant_id": ["zomato:1", "zomato:1"], "normalized_dish_name": ["butter naan", "dal makhani"],
            "dish_id": ["d1", "d2"], "dish_name": ["Butter Naan", "Dal Makhani"],
            "item_role": ["accompaniment", "main"], "estimated_price": [32.0, 140.0],
        })
        out = extract_addon_prices(raw, menu)
        self.assertEqual(out["normalized_dish_name"].tolist(), ["butter naan"])
        self.assertEqual(out["observed_addon_price"].iloc[0], 60)


if __name__ == "__main__":
    unittest.main()
