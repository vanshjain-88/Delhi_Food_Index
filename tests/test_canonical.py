import unittest

from ingestion.canonical import canonicalize_token, split_cuisines


class CanonicalTests(unittest.TestCase):
    def test_spaces_and_hyphens(self):
        self.assertEqual(canonicalize_token("North Indian"), "NORTH_INDIAN")
        self.assertEqual(canonicalize_token("Indo-Chinese"), "INDO_CHINESE")
        self.assertEqual(canonicalize_token("Tex-Mex"), "TEX_MEX")

    def test_aliases(self):
        self.assertEqual(canonicalize_token("Hot dogs"), "HOT_DOG")
        self.assertEqual(canonicalize_token("Cafe"), "CAFE")

    def test_split_keeps_order_and_drops_duplicates(self):
        self.assertEqual(
            split_cuisines("North Indian, BBQ, North Indian"),
            ["NORTH_INDIAN", "BBQ"],
        )


if __name__ == "__main__":
    unittest.main()
