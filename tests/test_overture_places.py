"""The Overture Maps listings fill the districts the Zomato snapshot does not cover, without inventing prices."""

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from map.districts import DISTRICTS, UNTYPED, listing_profile  # noqa: E402

PATH = ROOT / "data" / "processed" / "overture_places.parquet"


@unittest.skipUnless(PATH.exists(), "run scripts/build_overture_places.py first")
class OverturePlacesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.places = pd.read_parquet(PATH)

    def test_every_district_has_listings(self):
        counts = self.places.groupby("district").size()
        for name, _label, _color in DISTRICTS:
            self.assertGreaterEqual(int(counts.get(name, 0)), 50, name)

    def test_no_prices_or_ratings_are_invented(self):
        for column in ("rating", "cost_for_two", "price", "estimated_price"):
            self.assertNotIn(column, self.places.columns)

    def test_quality_filters_held(self):
        self.assertTrue((self.places["confidence"] >= 0.5).all())
        self.assertTrue(self.places["name"].notna().all())
        self.assertFalse(self.places["place_id"].duplicated().any())
        self.assertFalse((self.places["category"] == "internet_cafe").any())

    def test_listings_are_inside_delhi(self):
        self.assertTrue(self.places["latitude"].between(28.3, 28.95).all())
        self.assertTrue(self.places["longitude"].between(76.7, 77.5).all())

    def test_source_and_release_are_recorded(self):
        self.assertEqual(set(self.places["source"]), {"overture_maps"})
        self.assertEqual(self.places["release"].nunique(), 1)

    def test_listing_profile_for_a_district_with_no_zomato_restaurants(self):
        profile = listing_profile(self.places, "North")
        self.assertGreater(profile["count"], 0)
        self.assertGreater(profile["per_km2"], 0)
        self.assertNotIn(UNTYPED, set(profile["types"]["Type"]))
        self.assertTrue(profile["places"]["confidence"].is_monotonic_decreasing)

    def test_listing_profile_of_empty_frame_does_not_fail(self):
        profile = listing_profile(self.places.iloc[0:0], "North")
        self.assertEqual(profile["count"], 0)
        self.assertEqual(profile["per_km2"], 0.0)


if __name__ == "__main__":
    unittest.main()
