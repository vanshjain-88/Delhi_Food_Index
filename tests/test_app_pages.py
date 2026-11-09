"""Smoke tests: every section renders, every cuisine and dish option works."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover
    AppTest = None

HAS_DATA = (ROOT / "data" / "processed" / "gpi_locality.parquet").exists() and (
    ROOT / "data" / "processed" / "dish_observations.parquet"
).exists()


def _section(module: str, function: str) -> str:
    return (
        "import sys\n"
        f"sys.path[:0] = [{str(APP)!r}, {str(ROOT / 'src')!r}]\n"
        f"from {module} import {function}\n"
        f"{function}()\n"
    )


@unittest.skipUnless(AppTest is not None and HAS_DATA, "streamlit or built tables missing")
class PageTests(unittest.TestCase):
    def run_section(self, module, function):
        app = AppTest.from_string(_section(module, function), default_timeout=60)
        app.run()
        self.assertFalse(app.exception, app.exception)
        return app

    def test_main_entry_point(self):
        app = AppTest.from_file(str(APP / "main.py"), default_timeout=60)
        app.run()
        self.assertFalse(app.exception, app.exception)

    def test_dataset_section(self):
        self.run_section("dataset_page", "render_dataset")

    def test_food_map_section(self):
        self.run_section("map_page", "render_map")

    def test_price_index_every_cuisine_and_toggle(self):
        app = self.run_section("price_index_page", "render_price_index")
        for i, option in enumerate(list(app.selectbox[0].options)):
            app.selectbox[0].select_index(i).run()
            self.assertFalse(app.exception, f"{option}: {app.exception}")
        app.selectbox[0].select_index(0).run()
        app.toggle[0].set_value(False).run()
        app.toggle[1].set_value(False).run()
        app.selectbox[1].select_index(2).run()
        self.assertFalse(app.exception)

    def test_price_drivers_every_dish(self):
        app = self.run_section("price_drivers_page", "render_price_drivers")
        for i, option in enumerate(list(app.selectbox[0].options)):
            app.selectbox[0].select_index(i).run()
            self.assertFalse(app.exception, f"{option}: {app.exception}")


if __name__ == "__main__":
    unittest.main()
