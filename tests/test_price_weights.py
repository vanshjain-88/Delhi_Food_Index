import unittest

from ingestion.price_weights import WEIGHTS, assign_role, estimated_price


class WeightIdentityTests(unittest.TestCase):
    def test_two_mains_and_two_drinks_use_the_whole_bill(self):
        self.assertAlmostEqual(2 * WEIGHTS["main"] + 2 * WEIGHTS["beverage"], 1.0)
        self.assertAlmostEqual(WEIGHTS["main"], 0.35)
        self.assertAlmostEqual(WEIGHTS["beverage"], 0.15)


class RoleTests(unittest.TestCase):
    def test_main_starter_bread_drink_and_dessert(self):
        self.assertEqual(assign_role("Veg Main Course", "Butter Chicken"), "main")
        self.assertEqual(assign_role("Veg Starters", "Paneer Tikka"), "starter")
        self.assertEqual(assign_role("Breads", "Butter Naan"), "accompaniment")
        self.assertEqual(assign_role("Drinks (Beverages)", "Masala Chaas"), "beverage")
        self.assertEqual(assign_role("Desserts", "Gulab Jamun"), "dessert")

    def test_fried_rice_is_a_main_and_plain_rice_is_a_side(self):
        self.assertEqual(assign_role("Fried Rice", "Veg Fried Rice"), "main")
        self.assertEqual(assign_role("Rice", "Jeera Rice"), "accompaniment")

    def test_milkshake_is_a_drink(self):
        self.assertEqual(assign_role("Milkshakes", "Oreo Shake"), "beverage")

    def test_common_delhi_mains_are_not_left_as_other(self):
        self.assertEqual(assign_role("North Indian", "Dal Makhani"), "main")
        self.assertEqual(assign_role("Veg", "Paneer Butter Masala"), "main")
        self.assertEqual(assign_role("Chaap", "Malai Chaap"), "main")
        self.assertEqual(assign_role("Veg Starters", "Paneer Tikka"), "starter")
        self.assertEqual(assign_role("Soups", "Chicken Soup"), "starter")
        self.assertEqual(assign_role("Breads", "Butter Naan"), "accompaniment")
        self.assertEqual(assign_role("Shakes", "Chocolate Shake"), "beverage")
        self.assertEqual(assign_role("Sweets", "Motichoor Laddu"), "dessert")

    def test_a_combo_that_mentions_a_drink_stays_a_main(self):
        self.assertEqual(
            assign_role("Match Day Combos", "3 Stuffed Naan With Dal Makhani & Cold Drink"),
            "main",
        )
        self.assertEqual(assign_role("Veg Starters", "Corn Pepper"), "starter")
        self.assertEqual(assign_role("Breads", "Tandoori Roti"), "accompaniment")
        self.assertEqual(assign_role("Mocktails", "Blue Lagoon"), "beverage")
        self.assertEqual(assign_role("Party Props", "Hat"), "non_food")
        self.assertIsNone(estimated_price(500, "non_food"))


class PriceTests(unittest.TestCase):
    def test_rupee_examples_at_500(self):
        self.assertEqual(estimated_price(500, "main"), 175.0)
        self.assertEqual(estimated_price(500, "beverage"), 75.0)
        self.assertEqual(estimated_price(500, "accompaniment"), 40.0)

    def test_missing_cost_stays_missing(self):
        self.assertIsNone(estimated_price(None, "main"))
        self.assertIsNone(estimated_price(float("nan"), "main"))


if __name__ == "__main__":
    unittest.main()
