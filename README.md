# Delhi Food Index

University project on Delhi restaurants, menus, and prices. The app is **Delhi Gastronomic Intelligence**. Deliverables are added one at a time.

## Deliverable 1 — Delhi menu dataset

Structured New Delhi restaurants, menus, and localities from the Kaggle snapshot `archangel0x01/zomato-india-delivery-menus`, downloaded 9 November 2026. The project does not scrape Zomato.

| | |
|---|---|
| Restaurants | 1,351 |
| Menu items | 114,472 |
| Localities | 81 |
| With a cost for two | 1,341 |

Cost for two is observed. Dish prices in the preview are estimates: a main is 35% of that restaurant's cost for two and a drink is 15%. See `METHODOLOGY.md`.

### Files

- `data/raw/zomato/delhi_restaurants.parquet` — Delhi extract, including the original menu JSON
- `data/processed/restaurants.parquet`
- `data/processed/menu_items.parquet`
- `data/processed/localities.parquet`

The all-India download was deleted after the Delhi filter was checked. Field definitions are in `DATA_DICTIONARY.md`.

## Deliverable 2 — Food Map

A plain white map of the eleven revenue districts on the Delhi government district map. Hover a district for the number of places listed, density, median rating and cost for two. Click a district, or pick it in the sidebar, to colour it by places per square kilometre and open its profile: what is listed, then ratings, prices and cuisines (and menus where they exist). District outlines are OpenStreetMap (ODbL), in `data/geo/delhi_districts.geojson`.

The 2026 delivery snapshot has menus but few restaurants outside the centre: North 0, South West 0, North East 2, South 3. Two sources close the gap:

- **Overture Maps Places** (open data, `scripts/build_overture_places.py`): 10,310 restaurants, cafes, bakeries and sweet shops in all eleven districts. Names, types and locations only. **No ratings, no cost for two, no menus, and none are estimated.** File: `data/processed/overture_places.parquet`.
- **A 2021 restaurant listing** (`scripts/build_gap_fill.py`): rating and cost for two for 307 restaurants in the four thin districts. Used only where the 2026 snapshot has fewer than 10 restaurants, never averaged with it. Its prices are 2021 rupees, so the app marks the year and compares each restaurant with the Delhi median of its own year. No menus. File: `data/processed/restaurants_2021.parquet`.

| District | Overture places | 2026 restaurants | 2021 restaurants | Ratings and prices from |
|---|---:|---:|---:|---|
| New Delhi | 1,634 | 383 | 282 | 2026 |
| West | 1,594 | 117 | 165 | 2026 |
| South East | 1,514 | 193 | 189 | 2026 |
| South | 1,141 | 3 | 172 | **2021** |
| Central | 1,056 | 519 | 83 | 2026 |
| North West | 860 | 26 | 69 | 2026 |
| South West | 643 | 0 | 53 | **2021** |
| East | 592 | 89 | 55 | 2026 |
| North | 585 | 0 | 76 | **2021** |
| Shahdara | 517 | 19 | 38 | 2026 |
| North East | 174 | 2 | 6 | **2021** (small sample) |

The tables are never merged on name. Details in `DATA_SOURCES.md`.

## Deliverable 3 — Gastronomic Price Index

How expensive each locality is relative to Delhi, comparing each restaurant with Delhi restaurants of the same
cuisine. 100 = Delhi benchmark.

| | |
|---|---|
| Localities with an index | 66 of 148 (45 reliable, 21 low-sample, 82 suppressed). 19 of the 66 are in the four districts filled from 2021 |
| Cuisine × locality cells | 1,563 (116 reliable, 176 low-sample) |
| Most expensive (reliable) | Khan Market 388, Lodhi Colony 239, Chanakyapuri 196 |
| Least expensive (reliable) | Geeta Colony 59, Shadipur 69, Asaf Ali Road 69 |
| Robustness | Spearman ρ 0.90 with a hedonic regression index, 0.59 with an index built from observed add-on prices |

The page map shows all of Delhi by default (with a "Zoom to data" switch). Localities with too few restaurants for an
index stay on it as grey dots, so thin areas are visible instead of silently dropped. North, South West, South and North East localities use 2021 prices, each compared with the 2021 Delhi median; the table has a "Prices" column with the year. The cuisine × locality grid has a
slider for how many cuisines to show.

Files: `data/processed/gpi_locality.parquet`, `gpi_cells.parquet`, `gpi_restaurants.parquet`.
Report with worked example: `reports/price_index_report.md`.

## Deliverable 4 — What drives dish prices?

Twenty dishes chosen by a coverage rule (150+ restaurants, 40+ localities): dal makhani, cold coffee, kadai
paneer, shahi paneer, paneer tikka, French fries, chilli paneer, dal tadka, paneer butter masala, veg fried rice,
veg manchurian, hakka noodles, chicken biryani, chilli chicken, gulab jamun, chicken tikka, butter chicken,
veg biryani, veg momos, tandoori chicken. 5,434 restaurant–dish observations.

- Rule-based ingredient, technique and descriptor extraction from names and descriptions
  (`src/nlp/features.py`), about 92–95% precision on a manual audit (`reports/extraction_audit.md`).
- Ridge, random forest and gradient boosting per dish, 5-fold cross-validation grouped by chain.
  Best models cut MAE 10–28% against a median baseline. SHAP shares by factor family.
- Pooled regression with dish fixed effects for "word on the menu → % price difference".
- A check against **observed add-on prices**: 3,753 real item prices recovered from menu add-on groups.

Main finding: within a dish, restaurant cuisine mix, rating and restaurant characteristics account for most of the
model's explanation; ingredients and techniques named on the menu add little. Real add-on prices rise with cost for
two with an elasticity of 0.36 (95% CI 0.26–0.45), not the 1.0 the estimate assumes, so estimated rupee gaps between
cheap and expensive restaurants are exaggerated.

Files: `data/processed/dish_observations.parquet`, `dish_features.parquet`, `dish_ingredients.parquet`,
`ingredients.parquet`, `dish_selection.parquet`, `price_driver_*.parquet`, `observed_addon_prices.parquet`,
`addon_price_model.parquet`. Report: `reports/price_drivers_report.md`.

Raw-material prices are not integrated yet.

### Preview

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app/main.py
```

Open http://127.0.0.1:8501. The app opens on a **Home** page with a card for each deliverable. Every other page has a
**← Home** button and a switcher for the four sections: **Dataset**, **Food Map** (the eleven Delhi districts),
**Price Index** and **What Drives Price?**. All maps use a plain white background with the district outlines, so they work offline.

Rebuild everything in order:

```bash
.venv/bin/python scripts/build_delhi_dataset.py   # Deliverable 1 tables
.venv/bin/python scripts/build_addon_prices.py    # observed add-on prices
.venv/bin/python scripts/build_overture_places.py # Overture listings for all districts (needs network)
.venv/bin/python scripts/build_gap_fill.py        # 2021 ratings and cost for the thin districts (needs the raw CSV, see script)
.venv/bin/python scripts/build_price_index.py     # Deliverable 3 (seconds)
.venv/bin/python scripts/build_price_drivers.py   # Deliverable 4 (about 2 minutes)
```

Tests (unit tests plus page smoke tests that click through every cuisine and dish):

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

A Kaggle token is only needed to download the source again. Put it in `.env` as `KAGGLE_API_TOKEN`. That file is not committed.

## Not built yet

- Menus and dish prices outside the 2026 snapshot. The four filled districts have a rating, cost for two and a price index, but no menus, so What Drives Price? does not cover them.
- Raw-material price integration. Commodity price sources such as data.gov.in and Agmarknet are still uncollected.
