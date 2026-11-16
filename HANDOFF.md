# Handoff: Delhi Gastronomic Intelligence

Read this first, then `plan.md`, `METHODOLOGY.md`, `DATA_DICTIONARY.md`, and `DATA_SOURCES.md`. It says what is finished, what is not, and what to watch for.

University Computational Gastronomy mini-project with four deliverables. All four are built and merged on `main`.

| # | Deliverable | Status |
|---|---|---|
| 1 | Delhi menu dataset | Done |
| 2 | Interactive Food Map (11 government districts) | Done, thin coverage in some districts |
| 3 | Cuisine-adjusted Gastronomic Price Index | Done |
| 4 | What drives dish prices | Done |
| – | Home page | **Not built** |
| – | OpenStreetMap listings for empty districts | **Not finished** |
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
PYTHONPATH=src .venv/bin/python -m pytest -q   # 44 tests, all passing at handoff
```

Streamlit caches imported modules. After editing a file under `app/` or `src/`, restart the server or the old code keeps running.

Plotly is 7.x. Use `go.Choroplethmap`, `go.Scattermap`, `go.Densitymap` and the layout keys `map_style`, `map_zoom`, `map_center`. The old `*mapbox` names do not exist. All maps use a plain white base with the district outlines (`district_layers()` in `app/ui.py`), so they work offline.

## Repository layout

| Path | What it is |
|---|---|
| `app/main.py` | Entry point. Section switch is `st.segmented_control` over the `SECTIONS` dict |
| `app/ui.py` | Theme (`apply_theme`), colour constants, `CHART`, `DIVERGING`, `pretty_token`, `pretty_feature`, `load_tables`, `district_layers` |
| `app/dataset_page.py` | Deliverable 1 page |
| `app/map_page.py` | Deliverable 2 page |
| `app/price_index_page.py` | Deliverable 3 page |
| `app/price_drivers_page.py` | Deliverable 4 page |
| `src/map/` | District polygons, point-in-polygon assignment, district profile |
| `src/pricing/` | `gpi.py` (index), `addon_prices.py` (observed add-on prices) |
| `src/modeling/` | `dishes.py` (dish selection), `drivers.py` (models, SHAP, regression) |
| `src/nlp/features.py` | Rule-based ingredient, technique, descriptor extraction |
| `src/ingestion/` | Cuisine canonicalisation, menu parsing, price-role weights |
| `scripts/` | `build_delhi_dataset.py`, `build_addon_prices.py`, `build_price_index.py`, `build_price_drivers.py`, `fetch_osm_restaurants.py` (unfinished) |
| `data/processed/` | All parquet tables. Field definitions in `DATA_DICTIONARY.md` |
| `data/geo/delhi_districts.geojson` | The 11 district outlines |
| `reports/` | Price index report, price drivers report, extraction audit |

## What was built

- **Deliverable 1.** 1,351 Delhi restaurants, 114,472 menu items, 81 localities from Kaggle `archangel0x01/zomato-india-delivery-menus` (MIT plus a scrape notice, in `data/raw/zomato/`). 1,341 restaurants have a cost for two; 10 stay null. `estimated_price` is a role share of cost for two (main 35%, drink 15%, and so on). See `METHODOLOGY.md`.
- **Deliverable 2.** Plain white map of the 11 government revenue districts. Hover shows count, density, rating and cost; clicking or the sidebar picks a district and opens a profile. Boundaries are OpenStreetMap: ten districts from the Overpass attic of 1 June 2018, and South from the current OSM South Delhi polygon with the other ten removed. This is not a delhi.gov.in file, and the 2026 official 13-district split is deliberately not used. Click-to-select on the map was not confirmed in automated testing; the sidebar works. Check it in a real browser.
- **Deliverable 3.** Index per locality and per cuisine-by-locality cell, with bootstrap intervals, reliability flags (suppressed under 5 restaurants, low at 5–9), a hedonic regression check and an add-on price check. Details in `METHODOLOGY.md` and `reports/price_index_report.md`.
- **Deliverable 4.** 20 dishes picked by a coverage rule, rule-based text features, ridge, random forest and gradient boosting grouped by chain, SHAP shares by factor family, a pooled regression with dish fixed effects, and a check against observed add-on prices. Details in `METHODOLOGY.md` and `reports/price_drivers_report.md`.

Findings to keep honest in any write-up:

- Within one role the estimate is a fixed share of cost for two, so locality rankings of estimated prices equal rankings of cost for two.
- Real add-on prices rise with cost for two with an elasticity of 0.36 (95% CI 0.26–0.45), not 1.0. Estimated rupee gaps between cheap and dear restaurants are exaggerated. Rankings are more trustworthy than rupee differences.
- Ingredients and techniques named on menus add little beyond restaurant-level factors. These are associations.

## Low coverage

The source holds about 1,352 Delhi restaurants and every one is under a "New Delhi" locality label. Coordinates span latitude 28.563–28.691 and longitude 77.138–77.282, central Delhi only. This is the data, not a bug.

| District | Restaurants | Status |
|---|---:|---|
| Central | 519 | fine |
| New Delhi | 383 | fine |
| South East | 193 | fine |
| West | 117 | fine |
| East | 89 | fine |
| North West | 26 | thin |
| Shahdara | 19 | thin |
| South | 3 | very low (all Safdarjung) |
| North East | 2 | very low (both Shastri Park) |
| North | 0 | empty |
| South West | 0 | empty |

Deliverables 3 and 4 only describe central Delhi. Do not publish an index or driver result for North, South West, South or North East.

The user wants roughly 20 to 30 listings for each thin district. That is **not finished**:

- `scripts/fetch_osm_restaurants.py` pulls restaurant, fast_food and cafe entries from OpenStreetMap through Overpass for every district under 20 Zomato restaurants, keeps up to 30 per district (cuisine-tagged first, then by OSM id) and writes `data/processed/osm_restaurants.parquet`. Overpass returned 502 errors and the run was stopped. It has never completed and no OSM data is in the repo. The script retries across three mirrors, so rerun it, perhaps at a quieter time.
- OSM gives name, type, coordinates and sometimes a cuisine. **No rating, no cost for two, no menu.** Those stay null.
- Keep OSM rows in their own table. Never merge them into the Zomato restaurants. Label them "OpenStreetMap listing, no rating or price".
- A capped sample is not a census. Do not compare density between a Zomato district and an OSM-only district. The script stores `osm_listed_in_district` (the true total found) so the UI can say "30 of N listed".
- OSM rows cannot feed Deliverables 3 or 4 because they carry no cost.
- After the table exists, plot those points on the selected district on the Food Map and add an OSM section to its profile.

## To do: Home page

Build a Home page and make it the first section. `plan.md` wants four visible buttons: Dataset, Food Map, Price Index, What Drives Price.

- Add `app/home_page.py`, register it first in the `SECTIONS` dict in `app/main.py`, and make it the default.
- Content: the title "Delhi Gastronomic Intelligence", one or two sentences on the project, four cards or buttons that open the four sections, and headline numbers read from the loaded tables (restaurants, menu items, localities, districts), not typed in.
- State the two main caveats: prices are estimates derived from cost for two, and coverage is central Delhi only.
- **Keep the theme.** Reuse `apply_theme()`, `CHART` and the colour constants in `app/ui.py`.

| Use | Colour |
|---|---|
| Page background | `#FFFBF5` |
| Sidebar | `#F6EDE4` |
| Accent, metrics, bars | `#9A3412` (terracotta) |
| Secondary accent | `#1F4E46` (green) |
| Text | `#1C1917` |

Same metric, caption and section-heading style as the other pages.

## To do: raw-material prices

Plan Phase 12 (commodity prices from sources such as data.gov.in and Agmarknet) is not integrated. If you add it, collect it only from a legitimate source, respect its terms, and stop for approval before building on it.

## Known data caveats

- All dish prices are derived estimates. Real menu prices were not available.
- 10 restaurants have no cost for two; their dishes have null estimates.
- Coverage is central Delhi only.
- The Kaggle snapshot is point-in-time delivery data, not the full dine-in market.

## Git

- Remote: `https://github.com/vanshjain-88/Delhi_Food_Index.git`, branch `main`. The repo is private.
- `deliverables-3-4` was merged into `main`; `main` is the branch to use.
- Data is committed on purpose. Commit only when asked. Never commit `.env`.
