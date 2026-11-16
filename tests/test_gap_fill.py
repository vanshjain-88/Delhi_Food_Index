"""The 2021 listing fills thinly covered districts without mixing years or inventing values."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ingestion.gap_fill import (  # noqa: E402
    CURRENT_YEAR,
    MIN_DISTRICT_RESTAURANTS,
    SNAPSHOT_YEAR,
    combine_restaurants,
    gap_districts,
    locality_label,
    locality_slug,
    unique_localities,
)
from map.districts import DISTRICTS, assign_district  # noqa: E402
from pricing.gpi import add_cuisine_group  # noqa: E402

PROCESSED = ROOT / "data" / "processed"
LISTING = PROCESSED / "restaurants_2021.parquet"
NAMES = [name for name, _label, _color in DISTRICTS]


class LocalityNamingTests(unittest.TestCase):
    @unittest.skipUnless((PROCESSED / "restaurants.parquet").exists(), "restaurants table missing")
    def test_same_locality_rule_as_the_2026_dataset(self):
        current = pd.read_parquet(PROCESSED / "restaurants.parquet").dropna(subset=["locality_raw"])
        self.assertTrue((current["locality_raw"].map(locality_label) == current["locality_name"]).all())
        self.assertTrue((current["locality_name"].map(locality_slug) == current["locality_id"]).all())

    def test_unique_localities_splits_a_label_used_in_two_districts(self):
        frame = pd.DataFrame(
            {
                "locality_name": ["Rohini", "Rohini", "Saket", "Hauz Khas"],
                "district": ["North", "North West", "South", "South"],
            }
        )
        out = unique_localities(frame, {"Hauz Khas"})
        self.assertEqual(
            out["locality_name"].tolist(),
            ["Rohini (North)", "Rohini (North West)", "Saket", "Hauz Khas (South)"],
        )
        self.assertEqual(out["locality_id"].iloc[0], "loc_rohini_north")


class CombineTests(unittest.TestCase):
    def test_a_filled_district_uses_only_the_older_listing(self):
        current = pd.DataFrame(
            {"restaurant_id": ["a", "b", "c"], "district": ["Central", "South", "South"], "cost_for_two": [1.0, 2.0, 3.0]}
        )
        listing = pd.DataFrame(
            {
                "restaurant_id": ["x", "y", "z"],
                "district": ["South", "South", "Central"],
                "cost_for_two": [4.0, 5.0, 6.0],
                "price_year": SNAPSHOT_YEAR,
                "fills_gap": [True, True, False],
            }
        )
        combined, filled = combine_restaurants(current, listing)
        self.assertEqual(filled, ["South"])
        self.assertEqual(sorted(combined["restaurant_id"]), ["a", "x", "y"])
        south = combined[combined["district"] == "South"]
        self.assertEqual(set(south["price_year"]), {SNAPSHOT_YEAR})
        self.assertEqual(set(combined[combined["district"] == "Central"]["price_year"]), {CURRENT_YEAR})

    def test_without_a_listing_nothing_changes(self):
        current = pd.DataFrame({"restaurant_id": ["a"], "district": ["Central"]})
        combined, filled = combine_restaurants(current, pd.DataFrame())
        self.assertEqual(filled, [])
        self.assertEqual(combined["restaurant_id"].tolist(), ["a"])


@unittest.skipUnless(LISTING.exists(), "run scripts/build_gap_fill.py first")
class ListingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.listing = pd.read_parquet(LISTING)
        cls.current = pd.read_parquet(PROCESSED / "restaurants.parquet")
        cls.current["district"] = assign_district(cls.current)

    def test_filled_districts_are_exactly_the_thin_ones(self):
        thin = gap_districts(self.current, NAMES)
        filled = sorted(self.listing.loc[self.listing["fills_gap"], "district"].unique())
        self.assertEqual(filled, sorted(thin))
        counts = self.current.groupby("district")["restaurant_id"].nunique()
        for name in filled:
            self.assertLess(int(counts.get(name, 0)), MIN_DISTRICT_RESTAURANTS, name)

    def test_every_filled_district_has_restaurants_with_a_price(self):
        used = self.listing[self.listing["fills_gap"]]
        for name in used["district"].unique():
            self.assertGreaterEqual(int((used["district"] == name).sum()), 5, name)

    def test_rows_are_inside_the_districts_and_priced(self):
        self.assertTrue(self.listing["district"].isin(NAMES).all())
        self.assertTrue((self.listing["cost_for_two"] > 0).all())
        self.assertTrue(self.listing["latitude"].between(28.3, 28.95).all())
        self.assertEqual(set(self.listing["price_year"]), {SNAPSHOT_YEAR})

    def test_missing_ratings_stay_missing(self):
        unrated = self.listing[self.listing["rating"].isna()]
        self.assertGreater(len(unrated), 0)
        self.assertTrue(unrated["rating_count"].isna().all())
        self.assertTrue((self.listing["rating"].dropna() > 0).all())

    def test_ids_are_unique_and_do_not_collide_with_2026(self):
        self.assertTrue(self.listing["restaurant_id"].is_unique)
        self.assertFalse(set(self.listing["restaurant_id"]) & set(self.current["restaurant_id"]))

    def test_no_menus_or_phone_numbers_are_carried(self):
        for column in self.listing.columns:
            self.assertNotIn("phone", column.lower())
            self.assertNotIn("menu", column.lower())


@unittest.skipUnless(LISTING.exists() and (PROCESSED / "gpi_locality.parquet").exists(), "tables missing")
class IndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overall = pd.read_parquet(PROCESSED / "gpi_locality.parquet")
        cls.cells = pd.read_parquet(PROCESSED / "gpi_cells.parquet")
        cls.priced = pd.read_parquet(PROCESSED / "gpi_restaurants.parquet")
        cls.listing = pd.read_parquet(LISTING)

    def test_both_years_present_and_localities_are_unique(self):
        self.assertEqual(set(self.overall["price_year"]), {CURRENT_YEAR, SNAPSHOT_YEAR})
        self.assertTrue(self.overall["locality_id"].is_unique)
        self.assertTrue(self.overall["locality_name"].is_unique)

    def test_2021_localities_sit_only_in_filled_districts(self):
        filled = set(self.listing.loc[self.listing["fills_gap"], "district"])
        ids = set(self.overall.loc[self.overall["price_year"] == SNAPSHOT_YEAR, "locality_id"])
        used = self.priced[self.priced["price_year"] == SNAPSHOT_YEAR]
        placed = used.merge(self.listing[["restaurant_id", "district"]], on="restaurant_id")
        self.assertEqual(len(placed), len(used))
        self.assertTrue(placed["district"].isin(filled).all())
        self.assertTrue(set(used["locality_id"]) <= ids)

    def test_a_locality_never_mixes_years(self):
        years = self.priced.groupby("locality_id")["price_year"].nunique()
        self.assertTrue((years == 1).all())

    def test_2021_prices_are_compared_with_the_2021_benchmark(self):
        grouped = add_cuisine_group(self.listing)
        benchmark = grouped.groupby("cuisine_group")["cost_for_two"].median()
        used = self.priced[self.priced["price_year"] == SNAPSHOT_YEAR]
        for group, value in used.groupby("cuisine_group")["cuisine_benchmark"].first().items():
            self.assertAlmostEqual(value, benchmark[group], places=6, msg=group)
        np.testing.assert_allclose(
            used["relative_price"], used["cost_for_two"] / used["cuisine_benchmark"], rtol=1e-9
        )

    def test_suppression_rule_applies_to_both_years(self):
        small = self.overall[self.overall["restaurants"] < 5]
        self.assertTrue(small["gpi"].isna().all())
        shown = self.overall[self.overall["reliability"] != "suppressed"]
        self.assertTrue((shown["restaurants"] >= 5).all())


if __name__ == "__main__":
    unittest.main()
