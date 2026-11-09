"""Smoke tests: every page renders, every dish and cuisine option works."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover
    AppTest = None

HAS_DATA = (ROOT / "data" / "processed" / "gpi_locality.parquet").exists() and (
    ROOT / "data" / "processed" / "dish_observations.parquet"
).exists()


@unittest.skipUnless(AppTest is not None and HAS_DATA, "streamlit or built tables missing")
class PageTests(unittest.TestCase):
    def run_page(self, name):
        app = AppTest.from_file(str(APP / "pages" / name), default_timeout=60)
        app.run()
        self.assertFalse(app.exception, app.exception)
        return app

    def test_dataset_page(self):
        self.run_page("dataset.py")

    def test_price_index_every_cuisine_and_toggle(self):
        app = self.run_page("price_index.py")
        for i, option in enumerate(list(app.selectbox[0].options)):
            app.selectbox[0].select_index(i).run()
            self.assertFalse(app.exception, f"{option}: {app.exception}")
        app.selectbox[0].select_index(0).run()
        app.toggle[0].set_value(False).run()
        app.toggle[1].set_value(False).run()
        app.selectbox[1].select_index(2).run()
        self.assertFalse(app.exception)

    def test_price_drivers_every_dish(self):
        app = self.run_page("price_drivers.py")
        for i, option in enumerate(list(app.selectbox[0].options)):
            app.selectbox[0].select_index(i).run()
            self.assertFalse(app.exception, f"{option}: {app.exception}")


if __name__ == "__main__":
    unittest.main()
