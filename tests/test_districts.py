import unittest

import pandas as pd
from shapely.geometry import Point

from map.districts import assign_district, district_profile, district_records


class DistrictTests(unittest.TestCase):
    def test_eleven_districts_match_the_government_map(self):
        names = [record["name"] for record in district_records()]
        self.assertEqual(
            names,
            [
                "North",
                "North West",
                "West",
                "South West",
                "Central",
                "New Delhi",
                "South",
                "South East",
                "East",
                "North East",
                "Shahdara",
            ],
        )

    def test_landmarks_fall_in_the_named_district(self):
        geoms = {record["name"]: record["geometry"] for record in district_records()}
        expect = {
            "New Delhi": (77.219, 28.632),
            "Central": (77.190, 28.652),
            "South West": (77.046, 28.592),
            "North West": (77.006, 28.736),
            "North": (77.102, 28.853),
            "South": (77.216, 28.524),
            "South East": (77.232, 28.573),
            "West": (77.122, 28.642),
            "East": (77.277, 28.631),
            "Shahdara": (77.290, 28.673),
            "North East": (77.267, 28.700),
        }
        for name, (lon, lat) in expect.items():
            self.assertTrue(geoms[name].covers(Point(lon, lat)), name)
        self.assertFalse(geoms["South West"].covers(Point(77.219, 28.632)))

    def test_assignment_and_empty_profile(self):
        restaurants = pd.DataFrame(
            {
                "restaurant_id": ["cp", "dwarka"],
                "name": ["Centre", "Edge"],
                "locality_name": ["Connaught Place", "Dwarka"],
                "rating": [4.1, 3.9],
                "cost_for_two": [500, 400],
                "canonical_cuisines": ["NORTH_INDIAN", "CHINESE"],
                "latitude": [28.632, 28.592],
                "longitude": [77.219, 77.046],
                "address": ["A", "B"],
            }
        )
        restaurants["district"] = assign_district(restaurants)
        self.assertEqual(restaurants.loc[0, "district"], "New Delhi")
        self.assertEqual(restaurants.loc[1, "district"], "South West")
        dishes = pd.DataFrame(
            {
                "restaurant_id": ["cp"],
                "dish_name": ["Dal Makhani"],
                "normalized_dish_name": ["dal makhani"],
                "item_role": ["main"],
                "estimated_price": [175],
            }
        )
        empty = district_profile(restaurants, dishes, "North")
        self.assertEqual(empty["restaurant_count"], 0)
        self.assertEqual(empty["restaurants_per_km2"], 0)
        self.assertGreater(empty["area_km2"], 0)
        self.assertIsNone(empty["median_cost_for_two"])
        filled = district_profile(restaurants, dishes, "New Delhi")
        self.assertEqual(filled["restaurant_count"], 1)
        self.assertGreater(filled["restaurants_per_km2"], 0)
        self.assertEqual(filled["median_main_estimate"], 175)


if __name__ == "__main__":
    unittest.main()
