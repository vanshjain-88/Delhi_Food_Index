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

    def test_main_entry_point_opens_on_home(self):
        app = AppTest.from_file(str(APP / "main.py"), default_timeout=60)
        app.run()
        self.assertFalse(app.exception, app.exception)
        self.assertEqual(app.title[0].value, "Delhi Gastronomic Intelligence")
        self.assertEqual(len(app.button), 4)
        self.assertEqual(len(app.get("segmented_control")), 0)

    def test_home_opens_every_section_and_back_button_returns(self):
        for page, title in (
            ("Dataset", "Delhi Gastronomic Dataset"),
            ("Food Map", "Food Map"),
            ("Price Index", "Gastronomic Price Index"),
            ("What Drives Price?", "What Drives Dish Prices?"),
        ):
            app = AppTest.from_file(str(APP / "main.py"), default_timeout=60)
            app.run()
            app.button(key=f"open_{page}").click().run()
            self.assertFalse(app.exception, f"{page}: {app.exception}")
            self.assertEqual(app.title[0].value, title)
            app.button(key="back_home").click().run()
            self.assertFalse(app.exception, app.exception)
            self.assertEqual(app.title[0].value, "Delhi Gastronomic Intelligence")

    def test_dataset_section(self):
        self.run_section("dataset_page", "render_dataset")

    def test_food_map_section(self):
        self.run_section("map_page", "render_map")

    def test_food_map_every_district_including_empty_zomato_ones(self):
        app = self.run_section("map_page", "render_map")
        districts = list(app.sidebar.selectbox[0].options)
        self.assertEqual(len(districts), 11)
        for name in districts:
            app.sidebar.selectbox[0].select(name).run()
            self.assertFalse(app.exception, f"{name}: {app.exception}")
            self.assertEqual(app.subheader[0].value, name)
            self.assertEqual(app.metric[0].label, "Places listed")

    def test_filled_districts_show_rating_and_cost_but_no_menus(self):
        app = self.run_section("map_page", "render_map")
        for name in ("North", "South West", "South"):
            app.sidebar.selectbox[0].select(name).run()
            self.assertFalse(app.exception, f"{name}: {app.exception}")
            values = {metric.label: metric.value for metric in app.metric}
            self.assertNotEqual(values["Median cost for two"], "—", name)
            self.assertNotEqual(values["Median rating"], "—", name)
            self.assertIn("No menus are available", " ".join(c.value for c in app.caption), name)

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
