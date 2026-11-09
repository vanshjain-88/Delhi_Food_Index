import unittest

import numpy as np
import pandas as pd

from pricing.gpi import (
    add_cuisine_group,
    cuisine_cells,
    locality_index,
    primary_cuisine,
    reliability,
)


def _frame():
    rows = []
    # Locality A: 10 North Indian at 800 (Delhi NI median 600) -> 133
    for i in range(10):
        rows.append(("A", "NORTH_INDIAN | CHINESE", 800.0))
    # Locality B: 10 North Indian at 400 and 10 bakeries at 200 (Delhi bakery median 200)
    for i in range(10):
        rows.append(("B", "NORTH_INDIAN", 400.0))
    for i in range(10):
        rows.append(("B", "BAKERY", 200.0))
    # Locality C: 3 restaurants, suppressed
    for i in range(3):
        rows.append(("C", "NORTH_INDIAN", 600.0))
    frame = pd.DataFrame(rows, columns=["locality_name", "canonical_cuisines", "cost_for_two"])
    frame["locality_id"] = "loc_" + frame["locality_name"].str.lower()
    frame["restaurant_id"] = [f"r{i}" for i in range(len(frame))]
    return frame


class GpiTests(unittest.TestCase):
    def test_primary_cuisine_is_first_token(self):
        self.assertEqual(primary_cuisine("NORTH_INDIAN | CHINESE"), "NORTH_INDIAN")
        self.assertIsNone(primary_cuisine(None))

    def test_thresholds(self):
        self.assertEqual(reliability(4).label, "suppressed")
        self.assertEqual(reliability(5).label, "low")
        self.assertEqual(reliability(10).label, "reliable")

    def test_cuisine_adjustment_does_not_penalise_cheap_cuisines(self):
        frame = add_cuisine_group(_frame(), min_count=1)
        out = locality_index(frame, draws=50).set_index("locality_name")
        # Bakery restaurants in B sit exactly at the Delhi bakery median.
        self.assertTrue(np.isnan(out.loc["C", "gpi"]))
        self.assertEqual(out.loc["C", "reliability"], "suppressed")
        self.assertGreater(out.loc["A", "gpi"], 100)
        # Raw index calls B much cheaper than the cuisine-adjusted one does.
        self.assertLess(out.loc["B", "gpi_unadjusted"], out.loc["B", "gpi"])

    def test_cell_formula(self):
        frame = add_cuisine_group(_frame(), min_count=1)
        cells = cuisine_cells(frame, draws=50)
        a = cells[(cells["locality_name"] == "A") & (cells["cuisine"] == "NORTH_INDIAN")].iloc[0]
        delhi = np.median([800.0] * 10 + [400.0] * 10 + [600.0] * 3)
        self.assertAlmostEqual(a["gpi"], 100 * 800 / delhi)
        chinese = cells[(cells["cuisine"] == "CHINESE")].iloc[0]
        self.assertAlmostEqual(chinese["gpi"], 100.0)

    def test_index_is_scale_free(self):
        frame = add_cuisine_group(_frame(), min_count=1)
        scaled = frame.copy()
        scaled["cost_for_two"] *= 0.35
        a = locality_index(frame, draws=20)["gpi"]
        b = locality_index(scaled, draws=20)["gpi"]
        np.testing.assert_allclose(a.fillna(-1), b.fillna(-1))


if __name__ == "__main__":
    unittest.main()
