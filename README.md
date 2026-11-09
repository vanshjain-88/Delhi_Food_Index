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

## Deliverable 3 — Gastronomic Price Index

How expensive each locality is relative to Delhi, comparing each restaurant with Delhi restaurants of the same
cuisine. 100 = Delhi benchmark.

| | |
|---|---|
| Localities with an index | 47 of 81 (35 reliable, 12 low-sample, 34 suppressed) |
| Cuisine × locality cells | 1,074 (109 reliable, 151 low-sample) |
| Most expensive (reliable) | Khan Market 388, Lodhi Colony 239, Chanakyapuri 196 |
| Least expensive (reliable) | Geeta Colony 59, Shadipur 69, Asaf Ali Road 69 |
| Robustness | Spearman ρ 0.91 with a hedonic regression index, 0.59 with an index built from observed add-on prices |

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

Open http://127.0.0.1:8501. The sections are **Dataset**, **Food Map** (the eleven Delhi districts), **Price Index**
and **What Drives Price?**. All maps use a plain white background with the district outlines, so they work offline.

Rebuild everything in order:

```bash
.venv/bin/python scripts/build_delhi_dataset.py   # Deliverable 1 tables
.venv/bin/python scripts/build_addon_prices.py    # observed add-on prices
.venv/bin/python scripts/build_price_index.py     # Deliverable 3 (seconds)
.venv/bin/python scripts/build_price_drivers.py   # Deliverable 4 (about 2 minutes)
```

Tests (unit tests plus page smoke tests that click through every cuisine and dish):

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

A Kaggle token is only needed to download the source again. Put it in `.env` as `KAGGLE_API_TOKEN`. That file is not committed.

## Deliverable 2 — Food map

A plain white map of the eleven revenue districts on the Delhi government district map. Click a district to colour it by restaurants per square kilometre and open its profile. North and South West have none. District outlines are OpenStreetMap, in `data/geo/delhi_districts.geojson`.

## Later deliverables

Not built yet: a Home page, OpenStreetMap listings for thin districts (`scripts/fetch_osm_restaurants.py` has never
completed), and raw-material price integration (commodity price sources such as data.gov.in and Agmarknet are still
uncollected).
