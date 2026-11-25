# Delhi Food Index

University project for the Computational Gastronomy course on Delhi restaurants, menus, and prices. The web app is **Delhi Gastronomic Intelligence**. All four deliverables are built:

1. **Dataset** — a structured Delhi menu dataset (restaurants, menu items, localities).
2. **Food Map** — an interactive map of Delhi's eleven revenue districts.
3. **Price Index** — a cuisine-adjusted Gastronomic Price Index by locality.
4. **What Drives Price?** — what goes with higher prices for 20 popular dishes.

Dish prices are not listed in the source, so they are **estimated** from each restaurant's observed cost for two and labelled as estimates throughout. Results are associations, not causal effects.

## Running the app

Requires Python 3.10–3.12. The processed data is committed, so nothing needs rebuilding.

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
streamlit run app/main.py
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py
```

Open http://localhost:8501. The app opens on a **Home** page with a card for each deliverable. Every other page has a
**← Home** button and a switcher for the four sections: **Dataset**, **Food Map** (the eleven Delhi districts),
**Price Index** and **What Drives Price?**. All maps use a plain white background with the district outlines, so they work offline.

Tests (69: unit tests plus page smoke tests that open every section and click through every cuisine and dish):

```bash
PYTHONPATH=src python -m pytest -q                 # macOS / Linux
$env:PYTHONPATH="src"; python -m pytest -q         # Windows PowerShell
```

Rebuilding the results is optional. In order:

```bash
python scripts/build_delhi_dataset.py     # Deliverable 1 tables
python scripts/build_addon_prices.py      # observed add-on prices
python scripts/build_overture_places.py   # Overture listings for all districts (needs network)
python scripts/build_gap_fill.py          # 2021 ratings and cost for the thin districts (needs the raw CSV, see script)
python scripts/build_price_index.py       # Deliverable 3 (seconds)
python scripts/build_price_drivers.py     # Deliverable 4 (about 2 minutes)
```

A Kaggle token is only needed to download the sources again. Put it in `.env` as `KAGGLE_API_TOKEN`. That file is not committed.

## Repository layout

| Path | Contents |
|---|---|
| `app/` | Streamlit app: `main.py` (entry point), one `*_page.py` per section, `ui.py` (theme and shared helpers) |
| `src/ingestion/` | Menu parsing, cuisine canonicalisation, price-role weights, 2021 gap fill |
| `src/map/` | District polygons and district assignment |
| `src/pricing/` | Price index (`gpi.py`) and observed add-on prices (`addon_prices.py`) |
| `src/modeling/`, `src/nlp/` | Dish matching, price-driver models, ingredient and technique extraction |
| `scripts/` | Build scripts that produce everything in `data/processed/` |
| `data/raw/`, `data/processed/`, `data/geo/` | Source extracts, processed tables, district outlines |
| `reports/` | Price index report, price drivers report, extraction audit, Phase 1 data-quality report |
| `tests/` | Unit and app tests |

Documentation: `METHODOLOGY.md` (all methods and assumptions), `DATA_DICTIONARY.md` (every table and field),
`DATA_SOURCES.md` (sources, licences, limitations), `HANDOFF.md` (project status and working rules).

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
index stay on it as grey dots, so thin areas are visible instead of silently dropped. Localities in North, South West, South and North East use 2021 prices, each compared with the 2021 Delhi median; the table has a "Prices" column with the year. The cuisine × locality grid has a
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

## Not built yet

- Menus and dish prices outside the 2026 snapshot. The four filled districts have a rating, cost for two and a price index, but no menus, so What Drives Price? does not cover them.
- Raw-material price integration. Commodity price sources such as data.gov.in and Agmarknet are still uncollected.
