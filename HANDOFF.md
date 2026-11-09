# Handoff: Delhi Gastronomic Intelligence

Read this first, then read `plan.md`, `METHODOLOGY.md`, `DATA_DICTIONARY.md`, and `DATA_SOURCES.md`. This file says what is finished, what is not, and what to watch for.

The project is a university Computational Gastronomy mini-project with four deliverables:

1. Delhi menu dataset. **Done.**
2. Interactive Food Map. **Done, with thin coverage in some districts.**
3. Cuisine-adjusted Gastronomic Price Index. **Built; methodology awaiting team sign-off** (see below).
4. What drives dish prices. **Built; methodology awaiting team sign-off** (see below).

Also still to build: a **Home page**.

## Working rules (from `plan.md`, do not relax them)

- Work in small phases. After each phase, run the checks, show the output, then **stop and ask for approval** before the next phase. This applies to the Price Index methodology (plan Phase 8) before any code.
- No fabricated data. A missing value stays null. Do not fill gaps with guesses.
- Estimated prices must always be labelled as estimates. This snapshot has **no observed dish prices**.
- No causal claims. Describe price drivers as associations.
- Do not scrape Zomato or Swiggy. Do not bypass logins, CAPTCHAs, or rate limits.
- Do not merge restaurants from two sources on name alone.
- Never commit `.env` (it holds `KAGGLE_API_TOKEN`). It is git-ignored. Do not print it.
- Do not re-download the all-India Kaggle file. It was deleted on purpose. The Delhi extract is already in `data/raw/zomato/`.
- Do not change the price methodology silently. If you change it, update `METHODOLOGY.md` and say so.

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app/main.py        # http://127.0.0.1:8501
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests   # 44 tests, all passing (includes page smoke tests)
```

Streamlit caches imported modules. After editing a file under `app/` or `src/`, restart the server or the old code keeps running.

Plotly is 7.x. Map traces are `go.Choroplethmap`, `go.Scattermap`, and `go.Densitymap`, and layout keys are `map_style`, `map_zoom`, `map_center`. The old `*mapbox` names do not exist.

## Repository layout

| Path | What it is |
|---|---|
| `app/main.py` | Entry point. Page switch is `st.segmented_control` over Dataset, Food Map, Price Index, What Drives Price? |
| `app/ui.py` | Theme CSS (`apply_theme`), `CHART` Plotly style, `pretty_token`, cached `load_tables` |
| `app/dataset_page.py` | Deliverable 1 page |
| `app/map_page.py` | Deliverable 2 page |
| `app/price_index_page.py` | Deliverable 3 page (`render_price_index`) |
| `app/price_drivers_page.py` | Deliverable 4 page (`render_price_drivers`) |
| `src/pricing/` | `gpi.py` (index, cells, bootstrap, hedonic check), `addon_prices.py` (observed add-on prices) |
| `src/modeling/` | `dishes.py` (canonical dish matching), `drivers.py` (features, grouped CV, SHAP, pooled OLS) |
| `src/nlp/features.py` | Rule-based ingredient, technique and descriptor extraction |
| `scripts/build_addon_prices.py`, `build_price_index.py`, `build_price_drivers.py` | Rebuild Deliverable 3 and 4 tables, in that order |
| `src/map/districts.py` | District polygons, restaurant-to-district assignment, district profile |
| `src/map/regions.py` | `top_cuisines`, `top_mains`, and an older locality Voronoi helper that the app no longer uses |
| `src/ingestion/` | Cuisine canonicalisation, menu parsing, price-role weights |
| `scripts/build_delhi_dataset.py` | Rebuilds `data/processed/` from the raw Delhi extract |
| `scripts/fetch_osm_restaurants.py` | **Written, never completed.** See "Low coverage" |
| `data/processed/` | `restaurants`, `menu_items`, `localities` parquet tables |
| `data/geo/delhi_districts.geojson` | The 11 district outlines |

## Done: Deliverable 1, Delhi menu dataset

- Source: Kaggle `archangel0x01/zomato-india-delivery-menus`, downloaded 9 November 2026. MIT licence plus a notice that the content was scraped; both files are in `data/raw/zomato/`.
- Filter: `city_name = 'Delhi NCR'` and locality contains "New Delhi".
- Size: **1,351 restaurants, 114,472 menu items, 81 localities.** 1,341 restaurants have `cost_for_two`; 10 do not and stay null.
- Dish prices are blocked in the source, so `observed_price` is null everywhere.
- `estimated_price` is a share of that restaurant's cost for two, set by dish role (main 35%, starter 18%, other food 20%, drink 15%, dessert 12%, bread or side 8%, non-food unpriced). The reference meal is two mains plus two drinks: 2 × 35% + 2 × 15% = 100%. Details and the role classifier are in `METHODOLOGY.md` and `src/ingestion/price_weights.py`.
- 606 of 114,472 rows have a null estimate (missing cost or non-food).
- Consequence you must keep in mind: within one role, the estimate is a fixed fraction of cost for two, so **a locality ranking of median main-dish estimates is the same as a ranking of median cost for two.**

## Done: Deliverable 2, Food Map

- Plain white map of the **11 Delhi government revenue districts**: North, North West, West, South West, Central, New Delhi, South, South East, East, North East, Shahdara. Pastel fills follow the government district poster the user supplied.
- Hover a district for restaurant count, restaurants per km², median rating, median cost for two, top cuisines.
- Clicking a district (or choosing it in the sidebar) colours it from its own colour toward terracotta by restaurant density and opens a profile: metrics, cuisine bar, common mains, restaurant table.
- Each restaurant is assigned to a district by point-in-polygon on its latitude and longitude (`assign_district`).
- Click-to-select on the map itself was not confirmed in automated browser testing. The sidebar District selector is the reliable control. Check clicking in a real browser and fix it if it does not work.
- Boundary source: OpenStreetMap (ODbL). Ten districts come from the Overpass attic dated 1 June 2018, because the current OSM tree uses a newer 13-district split that does not match the government poster. **South** is the current OSM South Delhi polygon with the other ten removed, because its 2018 relation would not download. This is not a delhi.gov.in shapefile. Do not describe it as one. Attribution to OpenStreetMap contributors is required.
- The 2026 official split has 13 districts (adds Central North, Old Delhi, Outer North). The user chose the 11-district version on purpose.

## Low coverage: read this before building Deliverables 3 and 4

The source holds only about 1,352 Delhi restaurants and **every one is under a "New Delhi" locality label.** Coordinates span latitude 28.563 to 28.691 and longitude 77.138 to 77.282, which is central Delhi only. This is the data, not a bug.

| District | Restaurants in snapshot | Status |
|---|---:|---|
| Central | 519 | fine |
| New Delhi | 383 | fine |
| South East | 193 | fine |
| West | 117 | fine |
| East | 89 | fine |
| North West | 26 | thin |
| Shahdara | 19 | thin |
| South | 3 | **very low** (all in Safdarjung) |
| North East | 2 | **very low** (both in Shastri Park) |
| North | 0 | **empty** |
| South West | 0 | **empty** (no Dwarka, Najafgarh, and so on) |

The user does not want districts left empty and asked for roughly 20 to 30 listings for each. That work is **not finished**:

- `scripts/fetch_osm_restaurants.py` was written to pull `amenity` restaurant, fast_food, and cafe entries from OpenStreetMap through Overpass for every district under 20 Zomato restaurants, keep up to 30 per district (listings with a cuisine tag first, then by OSM id), and save `data/processed/osm_restaurants.parquet`. Overpass answered with 502 errors and the run was stopped. **It has never completed, and no OSM data is in the repo.** The script retries across three Overpass mirrors; run it again, possibly at a quieter time.
- OSM gives name, type, coordinates, and sometimes a cuisine tag. **It has no rating, no cost for two, and no menu.** Those fields must stay null for OSM rows.
- Keep OSM rows in their own table. Do not merge them into the Zomato restaurants. Label them clearly as "OpenStreetMap listings, no rating or price".
- A capped sample is not a census. Do not compare restaurants-per-km² between a Zomato district and an OSM-only district. Either compute density from Zomato rows only or label the OSM figure as a sample. The script stores `osm_listed_in_district` (the true total found) so the UI can say "30 of N listed".
- These rows cannot feed the price index or the price-driver model, because they carry no cost. Overture Maps Places is another option for locations; it has the same limitation.
- The map page currently shows a coverage line and an explicit empty state for districts with no Zomato data. After the OSM table exists, plot those points on the selected district and add an OSM section to the profile.
- For Deliverables 3 and 4, **suppress or flag any district, locality, or cuisine cell with too few restaurants.** Never publish an index for North or South West from the current data, and treat South and North East as unreliable.

## To do: Home page

Build a Home page and make it the first thing a user sees. `plan.md` shows four visible buttons: Dataset, Food Map, Price Index, What Drives Price.

- Add `app/home_page.py` and register it in `app/main.py`. Extend the page switch to Home, Dataset, Food Map, Price Index, What Drives Price. Pages for deliverables not yet built can show "Coming next" and say what they will do.
- Content: the title "Delhi Gastronomic Intelligence", one or two sentences on the project, four cards or buttons linking to the pages, and the headline numbers (1,351 restaurants, 114,472 menu items, 81 localities, 11 districts). Take the numbers from the loaded tables, not typed constants.
- State the main caveats on the page: prices are estimates derived from cost for two, and coverage is central Delhi only.
- **Keep the theme consistent.** Reuse `apply_theme()` and `CHART` from `app/ui.py`. Do not introduce a new look.

| Use | Colour |
|---|---|
| Page background | `#FFFBF5` cream |
| Sidebar | `#F6EDE4` |
| Accent, metrics, bars | `#9A3412` terracotta |
| Secondary accent | `#1F4E46` green |
| Text | `#1C1917` |

  Warm light theme, `plotly_white` chart template, Streamlit `layout="wide"`. Use the same metric, caption, and section-heading style as the Dataset and Food Map pages.
- Add `st.sidebar` controls per page, as the existing pages do.

## Built: Deliverable 3, Gastronomic Price Index

Details: `METHODOLOGY.md` and `reports/price_index_report.md`.

- Unit is the restaurant, price is observed cost for two. Estimated main and drink are fixed shares of it, so the
  index is identical for all three; the page says so and shows rupee levels for each.
- Cell index is the plan formula. Overall locality index: each restaurant ÷ Delhi median of its primary cuisine
  (first label; < 15 restaurants pooled as Other), median per locality × 100. Raw (unadjusted) index shown too.
- Thresholds: < 5 restaurants suppressed, 5–9 flagged low, 10+ reliable. 2,000-draw bootstrap intervals.
  No outlier trimming.
- Checks: hedonic regression index ρ = 0.91; index from observed add-on prices ρ = 0.59 (14 localities).
- Map: locality centroids as points over the district outlines on a white base. No locality boundaries are drawn.
  A district-level index is a possible addition; South and North East would be suppressed, North and South West empty.
- **Plan Phase 8 asked for methodology approval before code. That stop was skipped at the user's request;
  the choices above still need the team's sign-off.**

## Built: Deliverable 4, What drives dish prices

Details: `METHODOLOGY.md`, `reports/price_drivers_report.md`, `reports/extraction_audit.md`.

- 20 dishes by rule (150+ restaurants, 40+ localities, then the 20 largest), 5,434 restaurant–dish observations.
- Outcome: the dish's modal-role weight × cost for two, so the menu-category label cannot act as a fake driver.
  Within a dish this models restaurant price level. Results are described as associations.
- Explicit ingredient/technique extraction from names and descriptions, about 92–95% precision on a manual audit.
  Recipe ingredients stored as `inferred` (confidence 0.6) and not used in models.
- Ridge, random forest, gradient boosting; 5-fold GroupKFold by chain brand; SHAP family shares; pooled OLS with
  dish fixed effects and brand-clustered SEs.
- Observed add-on prices (3,753 real item prices from menu add-on groups) test the estimate: elasticity of item price
  to cost for two is 0.36 (95% CI 0.26–0.45), not 1. Estimated rupee gaps are too wide; rankings hold up better.
- Raw-material prices (plan Phase 12) are not integrated.
- **Plan Phases 10–11 asked for approval of the dish list and extraction. Those stops were skipped at the user's
  request; the choices still need the team's sign-off.**

## Known data caveats

- All dish prices are derived estimates. Real menu prices were not available.
- 10 restaurants have no cost for two; their dishes have null estimates.
- Coverage is central Delhi only (see table above).
- The Kaggle snapshot is point-in-time delivery data, not the full dine-in market.

## Git

- Remote: `https://github.com/vanshjain-88/Delhi_Food_Index.git`, branch `main`. The repo is private.
- Data is committed on purpose (about 40 MB).
- Commit only when asked. Never commit `.env`.
