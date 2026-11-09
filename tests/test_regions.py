import unittest

import pandas as pd

from map.regions import contains, locality_polygons, locality_profile


class RegionTests(unittest.TestCase):
    def test_each_centroid_falls_in_its_own_region(self):
        frame = pd.DataFrame(
            {
                "locality_id": ["loc_a", "loc_b", "loc_c"],
                "locality_name": ["A", "B", "C"],
                "longitude": [77.20, 77.24, 77.18],
                "latitude": [28.63, 28.66, 28.60],
            }
        )
        features = locality_polygons(frame)
        self.assertEqual(len(features), 3)
        for feature, lon, lat in zip(features, frame.longitude, frame.latitude, strict=True):
            ring = [(x, y) for x, y in feature["geometry"]["coordinates"][0][:-1]]
            self.assertTrue(contains((lon, lat), ring))

    def test_two_sites_split_the_box(self):
        frame = pd.DataFrame(
            {
                "locality_id": ["loc_west", "loc_east"],
                "locality_name": ["West", "East"],
                "longitude": [77.15, 77.25],
                "latitude": [28.63, 28.63],
            }
        )
        features = {item["properties"]["locality_id"]: item for item in locality_polygons(frame)}
        west = [(x, y) for x, y in features["loc_west"]["geometry"]["coordinates"][0][:-1]]
        east = [(x, y) for x, y in features["loc_east"]["geometry"]["coordinates"][0][:-1]]
        self.assertTrue(contains((77.15, 28.63), west))
        self.assertFalse(contains((77.25, 28.63), west))
        self.assertTrue(contains((77.25, 28.63), east))


class ProfileTests(unittest.TestCase):
    def test_profile_counts_restaurants_cuisines_and_mains(self):
        restaurants = pd.DataFrame(
            {
                "restaurant_id": ["a", "b"],
                "name": ["Alpha", "Beta"],
                "locality_name": ["Saket", "Saket"],
                "rating": [4.2, 3.8],
                "cost_for_two": [500, 700],
                "canonical_cuisines": ["NORTH_INDIAN | CHINESE", "NORTH_INDIAN"],
                "latitude": [28.5, 28.51],
                "longitude": [77.2, 77.21],
            }
        )
        dishes = pd.DataFrame(
            {
                "restaurant_id": ["a", "a", "b"],
                "dish_name": ["Dal Makhani", "Butter Chicken", "Dal Makhani"],
                "normalized_dish_name": ["dal makhani", "butter chicken", "dal makhani"],
                "item_role": ["main", "main", "main"],
                "estimated_price": [175, 175, 245],
            }
        )
        profile = locality_profile(restaurants, dishes, "Saket")
        self.assertEqual(profile["restaurant_count"], 2)
        self.assertEqual(profile["median_cost_for_two"], 600)
        self.assertEqual(profile["cuisine_count"], 2)
        self.assertEqual(profile["cuisines"].iloc[0]["Cuisine"], "NORTH_INDIAN")
        self.assertEqual(profile["cuisines"].iloc[0]["Restaurants"], 2)
        self.assertEqual(profile["dishes"].iloc[0]["Dish"], "Dal Makhani")
        self.assertEqual(profile["dishes"].iloc[0]["Restaurants"], 2)
        self.assertEqual(profile["median_main_estimate"], 175)


if __name__ == "__main__":
    unittest.main()
