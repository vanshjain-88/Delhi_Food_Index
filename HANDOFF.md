# Handoff: Delhi Gastronomic Intelligence

Read this first, then `plan.md`, `METHODOLOGY.md`, `DATA_DICTIONARY.md`, and `DATA_SOURCES.md`. It says what is finished, what is not, and what to watch for.

University Computational Gastronomy mini-project with four deliverables. All four are built and merged on `main`.

| # | Deliverable | Status |
|---|---|---|
| 1 | Delhi menu dataset | Done |
| 2 | Interactive Food Map (11 government districts) | Done. All 11 districts have listings (Overture Maps), ratings and cost for two (2026, or 2021 in four thin districts) |
| 3 | Cuisine-adjusted Gastronomic Price Index | Done. Covers all 11 districts; four use 2021 prices |
| 4 | What drives dish prices | Done |
| – | Home page and back button | Done |
| – | Place listings for empty and thin districts | Done, from Overture Maps (`scripts/build_overture_places.py`) |
| – | Ratings and prices for North, South West, South, North East | Done from a 2021 listing (`scripts/build_gap_fill.py`). No menus there, so Deliverable 4 does not cover them |
| – | Raw-material (commodity) prices, plan Phase 12 | **Not started** |

## Working rules (from `plan.md`, do not relax them)

- Work in small phases. After each phase run the checks, show the output, then **stop and ask for approval**.
- No fabricated data. A missing value stays null.
- Estimated prices are always labelled as estimates. The source has **no listed dish prices**. The only real item prices are 3,753 add-on prices at 417 restaurants (`observed_addon_prices`), used as a check, not as the main price.
- No causal claims. Price drivers are associations.
- Do not scrape Zomato or Swiggy. Do not bypass logins, CAPTCHAs, or rate limits.
- Do not merge restaurants from two sources on name alone.
- Never commit `.env` (it holds `KAGGLE_API_TOKEN`). It is git-ignored. Do not print it.
- Do not re-download the all-India Kaggle file. It was deleted on purpose.
- Do not change the price methodology silently. Update `METHODOLOGY.md` and say so.

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app/main.py        # http://127.0.0.1:8501
PYTHONPATH=src .venv/bin/python -m pytest -q   # 69 tests, all passing at handoff
```

Streamlit caches imported modules. After editing a file under `app/` or `src/`, restart the server or the old code keeps running.

Plotly is 7.x. Use `go.Choroplethmap`, `go.Scattermap`, `go.Densitymap` and the layout keys `map_style`, `map_zoom`, `map_center`. The old `*mapbox` names do not exist. All maps use a plain white base with the district outlines (`district_layers()` in `app/ui.py`), so they work offline.

## Repository layout

| Path | What it is |
|---|---|
| `app/main.py` | Entry point. Opens on Home. `st.session_state["page"]` holds the current page; the `← Home` button and the section switcher (`st.segmented_control`) both change it through the `go` callback |
| `app/home_page.py` | Home page: headline numbers, one card per deliverable, caveats. Numbers are read from the tables |
| `app/ui.py` | Theme (`apply_theme`), colour constants, `CHART`, `DIVERGING`, `pretty_token`, `pretty_feature`, `load_tables`, `district_layers`, `delhi_bounds`, `map_view` |
| `app/dataset_page.py` | Deliverable 1 page |
| `app/map_page.py` | Deliverable 2 page |
| `app/price_index_page.py` | Deliverable 3 page |
| `app/price_drivers_page.py` | Deliverable 4 page |
| `src/map/` | District polygons, point-in-polygon assignment, district profile |
| `src/pricing/` | `gpi.py` (index), `addon_prices.py` (observed add-on prices) |
| `src/modeling/` | `dishes.py` (dish selection), `drivers.py` (models, SHAP, regression) |
| `src/nlp/features.py` | Rule-based ingredient, technique, descriptor extraction |
| `src/ingestion/` | Cuisine canonicalisation, menu parsing, price-role weights, `gap_fill.py` (2021 listing: cleaning, which districts are filled, locality naming, combining) |
| `scripts/` | `build_delhi_dataset.py`, `build_addon_prices.py`, `build_price_index.py`, `build_price_drivers.py`, `build_overture_places.py` (needs network), `build_gap_fill.py` (needs the raw 2021 CSV) |
| `data/processed/` | All parquet tables. Field definitions in `DATA_DICTIONARY.md` |
| `data/geo/delhi_districts.geojson` | The 11 district outlines |
| `reports/` | Price index report, price drivers report, extraction audit |

## What was built

- **Deliverable 1.** 1,351 Delhi restaurants, 114,472 menu items, 81 localities from Kaggle `archangel0x01/zomato-india-delivery-menus` (MIT plus a scrape notice, in `data/raw/zomato/`). 1,341 restaurants have a cost for two; 10 stay null. `estimated_price` is a role share of cost for two (main 35%, drink 15%, and so on). See `METHODOLOGY.md`.
- **Deliverable 2.** Plain white map of the 11 government revenue districts. Hover shows places listed (Overture), density, and median rating and cost; clicking or the sidebar picks a district and opens a profile with two parts: what is listed (Overture: counts, types, names) and restaurants, ratings and prices (2026 snapshot, or the 2021 listing in the four thin districts, where there are no menus). Boundaries are OpenStreetMap: ten districts from the Overpass attic of 1 June 2018, and South from the current OSM South Delhi polygon with the other ten removed. This is not a delhi.gov.in file, and the 2026 official 13-district split is deliberately not used. Click-to-select on the map was not confirmed in automated testing; the sidebar works. Check it in a real browser.
- **Deliverable 3.** Index per locality and per cuisine-by-locality cell (66 of 148 localities have an index; 19 of those are in the four districts filled from 2021), with bootstrap intervals, reliability flags (suppressed under 5 restaurants, low at 5–9), a hedonic regression check and an add-on price check. Details in `METHODOLOGY.md` and `reports/price_index_report.md`.
- **Deliverable 4.** 20 dishes picked by a coverage rule, rule-based text features, ridge, random forest and gradient boosting grouped by chain, SHAP shares by factor family, a pooled regression with dish fixed effects, and a check against observed add-on prices. Details in `METHODOLOGY.md` and `reports/price_drivers_report.md`.

Findings to keep honest in any write-up:

- Within one role the estimate is a fixed share of cost for two, so locality rankings of estimated prices equal rankings of cost for two.
- Real add-on prices rise with cost for two with an elasticity of 0.36 (95% CI 0.26–0.45), not 1.0. Estimated rupee gaps between cheap and dear restaurants are exaggerated. Rankings are more trustworthy than rupee differences.
- Ingredients and techniques named on menus add little beyond restaurant-level factors. These are associations.

## Coverage: three tables

**2026 delivery snapshot** (`restaurants.parquet`: ratings, cost for two, menus). 1,351 Delhi restaurants, all under a "New Delhi" locality label, mostly central. It drives Deliverables 1 and 4 and most of 3.

**Overture Maps places** (`overture_places.parquet`: names, types, locations). 10,310 restaurants, cafes, bakeries and sweet shops across all 11 districts. It has **no rating, no cost for two, no menu**, and none are imputed.

**2021 listing** (`restaurants_2021.parquet`: rating, cost for two, cuisines, no menus). 1,188 restaurants inside the 11 districts; the 307 in the four districts where the 2026 snapshot has fewer than 10 restaurants are used.

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

Rules for these tables:

- Keep them apart. Never merge rows across tables on name. Restaurants in the 2026 and 2021 files are matched only on the Zomato URL, and only for the same-restaurant price check. Never sum counts across tables.
- A district uses one price year. Where the 2026 snapshot has fewer than 10 restaurants (`MIN_DISTRICT_RESTAURANTS`), the 2021 rows replace it in district figures on the Food Map and add the localities of those districts to the index tables. The 5 stray 2026 restaurants in those districts are ignored for district figures, but stay in the 2026 locality they are labelled with (Safdarjung, Shastri Park). The 2026 Delhi benchmarks still use every 2026 restaurant, so no 2026 index value moved.
- 2021 rupees are lower (on 106 restaurants in both files the 2026 cost for two is a median 17% higher). The index compares each restaurant with the Delhi median of its own year, so index values are comparable across years and rupee levels are not. The app marks the year on rupee figures. Do not pool raw 2021 and 2026 rupees.
- The 2021 file only has restaurants with a dining rating of 3.9 or more, and no menus. North East has 6 restaurants there: a small sample, shown as such.
- A rating that is missing stays missing (53 of the 307 have none).
- Density on the Food Map is Overture places per km², because Overture covers every district.
- Overture is a place registry, not a census. About a fifth of records are only "restaurant" with no type, some are stale or duplicated, and `confidence` is Overture's own estimate that the place exists (0.5 and above are kept). Attribute "Overture Maps Foundation". Source licenses in the data are CDLA-Permissive-2.0, Apache-2.0 and CC0-1.0 (`source_licenses` column).
- The raw 2021 CSV is not committed (it carries phone numbers). `scripts/build_gap_fill.py` prints the Kaggle download command if it is missing.
- Deliverable 4 uses the 2026 menus only. Do not publish a driver result for the four filled districts.

## Theme

Reuse `apply_theme()`, `CHART` and the colour constants in `app/ui.py` for any new page. Same metric, caption and section-heading style as the other pages.

| Use | Colour |
|---|---|
| Page background | `#FFFBF5` |
| Sidebar | `#F6EDE4` |
| Accent, metrics, bars | `#9A3412` (terracotta) |
| Secondary accent | `#1F4E46` (green) |
| Text | `#1C1917` |

A toggle placed in a row with labelled inputs: use `st.columns(..., vertical_alignment="bottom")`, which lines it up with the input box. Cards on Home are `st.container(key="card_...")`, styled in `apply_theme`.

## To do: raw-material prices

Plan Phase 12 (commodity prices from sources such as data.gov.in and Agmarknet) is not integrated. If you add it, collect it only from a legitimate source, respect its terms, and stop for approval before building on it.

## Known data caveats

- All dish prices are derived estimates. Real menu prices were not available.
- 10 restaurants have no cost for two; their dishes have null estimates.
- Menus exist only for the 2026 snapshot (mostly central Delhi). The four thin districts have ratings and cost for two from 2021, no menus.
- The Kaggle snapshot is point-in-time delivery data, not the full dine-in market.

## Git

- Remote: `https://github.com/vanshjain-88/Delhi_Food_Index.git`, branch `main`. The repo is private.
- `deliverables-3-4` was merged into `main`; `main` is the branch to use.
- Data is committed on purpose. Commit only when asked. Never commit `.env`.
