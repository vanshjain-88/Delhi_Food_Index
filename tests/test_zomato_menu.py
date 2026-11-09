import unittest

from ingestion.zomato_menu import iter_menu_items, normalize_name, parse_price, veg_flag


class NormalizeTests(unittest.TestCase):
    def test_collapses_punctuation_and_case(self):
        self.assertEqual(normalize_name("Paneer Tikka (Half)"), "paneer tikka half")

    def test_blank_is_none(self):
        self.assertIsNone(normalize_name("   "))


class PriceTests(unittest.TestCase):
    def test_strips_rupee_and_commas(self):
        self.assertEqual(parse_price("₹1,250"), 1250.0)

    def test_zero_is_missing(self):
        self.assertIsNone(parse_price(0))


class VegTests(unittest.TestCase):
    def test_non_veg_is_not_read_as_veg(self):
        self.assertFalse(veg_flag({"tag_slugs": ["non-veg"]}))

    def test_egg_is_unknown(self):
        self.assertIsNone(veg_flag({"tag_slugs": ["egg"]}))


class MenuWalkTests(unittest.TestCase):
    def test_nested_zomato_shape(self):
        menu = {
            "menus": [
                {
                    "menu": {
                        "name": "Delivery",
                        "categories": [
                            {
                                "category": {
                                    "name": "Starters",
                                    "items": [
                                        {
                                            "item": {
                                                "id": "101",
                                                "name": "Paneer Tikka",
                                                "price": 320,
                                                "desc": "Tandoor paneer",
                                                "item_image_url": "https://example.test/paneer.jpg",
                                                "tag_slugs": ["veg", "bestseller"],
                                                "modifier_groups": [
                                                    {
                                                        "group": {
                                                            "name": "Extra",
                                                            "items": [
                                                                {"item": {"id": "m1", "name": "Extra cheese", "price": 40}}
                                                            ],
                                                        }
                                                    }
                                                ],
                                            }
                                        }
                                    ],
                                }
                            }
                        ],
                    }
                }
            ]
        }
        rows = list(iter_menu_items(menu))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["dish_name"], "Paneer Tikka")
        self.assertEqual(row["category"], "Starters")
        self.assertEqual(row["price"], 320.0)
        self.assertEqual(row["description"], "Tandoor paneer")
        self.assertTrue(row["is_veg"])
        self.assertTrue(row["is_bestseller"])
        self.assertEqual(row["image_url"], "https://example.test/paneer.jpg")
        self.assertEqual(row["item_source_id"], "101")

    def test_flat_item_without_wrapper(self):
        rows = list(iter_menu_items([{"name": "Dal Makhani", "display_price": "240", "desc": ""}]))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["price"], 240.0)
        self.assertIsNone(rows[0]["description"])

    def test_login_blocked_item_has_no_price(self):
        menu = {
            "price_login_blocker": True,
            "menus": [
                {
                    "name": "Full Menu",
                    "categories": [
                        {
                            "name": "Main Course",
                            "items": [
                                {
                                    "item_id": "999",
                                    "name": "Butter Chicken",
                                    "description": "Tomato gravy",
                                    "image_url": "https://example.test/bc.jpg",
                                    "dietary_slugs": ["non-veg"],
                                }
                            ],
                        }
                    ],
                }
            ],
            "modifier_groups": [
                {"name": "Add ons", "items": [{"item_id": "m1", "name": "Extra gravy", "price": 30}]}
            ],
        }
        rows = list(iter_menu_items(menu))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dish_name"], "Butter Chicken")
        self.assertEqual(rows[0]["category"], "Main Course")
        self.assertIsNone(rows[0]["price"])
        self.assertFalse(rows[0]["is_veg"])
        self.assertEqual(rows[0]["item_source_id"], "999")


if __name__ == "__main__":
    unittest.main()
