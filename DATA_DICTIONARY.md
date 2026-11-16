# Data dictionary

Published Deliverable 1 tables, built on 9 November 2026 from `data/raw/zomato/delhi_restaurants.parquet`.

Source: `kaggle:archangel0x01/zomato-india-delivery-menus`. The file keeps restaurants whose city is Delhi NCR and whose locality contains "New Delhi": 1,351 restaurants, 114,472 menu items, 81 localities.

## restaurants

`data/processed/restaurants.parquet`

| Field | Type | Rule |
|---|---|---|
| restaurant_id | string | `zomato:{source_id}`. Unique |
| name | string | original restaurant name |
| normalized_name | string | lowercase, `&` to `and`, punctuation removed, spaces collapsed |
| address | string | first address-like string found outside the menu. Null stays null |
| locality_id | string | `loc_` plus the normalized locality name |
| locality_name | string | display locality, with the trailing `, New Delhi` removed |
| locality_raw | string | original locality label from the snapshot |
| city_name | string | `Delhi` |
| latitude | float | WGS84 decimal degrees |
| longitude | float | WGS84 decimal degrees |
| rating | float | delivery rating. Null stays null |
| rating_count | integer | null when the snapshot has no count |
| cost_for_two | float | observed rupees for two people. Not imputed. Missing for 10 restaurants |
| cuisine | string | original comma-separated cuisine string |
| canonical_cuisines | string | cuisine tokens joined with ` \| ` |
| url | string | restaurant or order URL from the snapshot |
| source | string | `kaggle:archangel0x01/zomato-india-delivery-menus` |
| source_id | string | Zomato `res_id` |
| collection_date | date | `2026-11-09` |
| dish_price_blocked | boolean | snapshot flag. Explains why observed dish price is null |
| veg_nonveg | string | `veg`, `nonveg`, or `mixed`, from dish dietary tags |

Phone numbers are not copied into this table.

## menu_items

`data/processed/menu_items.parquet`

| Field | Type | Rule |
|---|---|---|
| dish_id | string | `zomato:{restaurant source_id}:{item source_id}`. Unique after duplicate menu tabs are collapsed |
| restaurant_id | string | foreign key to restaurants |
| dish_name | string | original dish name |
| normalized_dish_name | string | same normalization as restaurant names |
| category | string | original menu category |
| cuisine | string | the restaurant cuisine string. It is not a per-dish cuisine |
| canonical_cuisines | string | same restaurant cuisine tokens |
| item_role | string | `main`, `starter`, `accompaniment`, `dessert`, `beverage`, `other`, or `non_food` |
| price_weight | float | share of `cost_for_two`. Null for non-food |
| observed_price | float | listed menu price. Null for every row in this snapshot |
| estimated_price | float | `price_weight × cost_for_two`, rounded to paise. Null if the cost is missing or the row is non-food |
| description | string | original description. Null stays null |
| is_veg | boolean | from dietary tags. `egg` is null, not veg and not non-veg |
| image_url | string | original image URL |
| source | string | same source string as the restaurant |
| source_id | string | Zomato item id when the menu had one |
| collection_date | date | `2026-11-09` |

Modifier groups (add-ons such as extra cheese) are not menu items. The same item listed under a menu tab and a real category is kept once, preferring the more specific category.

## localities

`data/processed/localities.parquet`

| Field | Type | Rule |
|---|---|---|
| locality_id | string | same id as on the restaurant |
| locality_name | string | display name |
| city_name | string | `Delhi` |
| normalized_name | string | normalized locality name |
| restaurant_count | integer | restaurants in that locality |
| latitude | float | mean of restaurant latitudes. Not an official boundary |
| longitude | float | mean of restaurant longitudes |
| median_cost_for_two | float | median observed cost for two |

## Identifiers

- A restaurant id is the source system plus that source's id. It is not a hash of the name.
- A dish id adds the item id from that same source.
- If a later source has no item id, the dish id may add the normalized name and category.

## Canonical forms

- Names: keep `name` / `dish_name`. `normalized_name` is lowercase ASCII letters, digits, and single spaces, with `&` read as `and`.
- Cuisines: split the restaurant string on commas. Each token becomes uppercase with non-alphanumeric characters turned into `_`. `Hot dogs` becomes `HOT_DOG`. `Cafe` becomes `CAFE`. The list keeps source order and drops duplicate tokens.
- Coordinates: WGS84 latitude and longitude in decimal degrees.
- Money: rupees. `cost_for_two` is observed. `estimated_price` is estimated and is labeled that way in the app.
- Dates: ISO `YYYY-MM-DD`.

## Entity resolution

This dataset has one source, so nothing is merged.

- The same `source` and `source_id` are the same restaurant.
- Similar names are not merged on their own. Two restaurants with the same name in different localities stay separate.

## Missing values

Null stays null. The pipeline does not invent ratings, vote counts, coordinates, cuisines, descriptions, or costs.

`estimated_price` is computed only from an observed `cost_for_two` and a role weight. A missing cost produces a missing estimate.

## Fields that are weak

- Observed dish price is unavailable in this source. The only real item prices are the 3,753 add-on prices in `observed_addon_prices`, which are for items sold as add-ons and can be discounted.
- Hauz Khas has one restaurant under that locality label, so that label cannot support a locality statistic.
- `cuisine` on a menu row describes the restaurant, not the dish.
- Locality latitude and longitude are restaurant averages, not official boundaries.

## observed_addon_prices

`data/processed/observed_addon_prices.parquet`. Built by `scripts/build_addon_prices.py`. One row per restaurant and dish whose name appears, with a positive price, in one of that restaurant's menu add-on groups.

| Field | Type | Rule |
|---|---|---|
| restaurant_id | string | foreign key to restaurants |
| normalized_dish_name | string | matched dish name (same normalization as menu_items) |
| dish_id | string | first matching menu row |
| dish_name, item_role, estimated_price | | copied from that menu row |
| observed_addon_price | float | median rupee price across the add-on listings. **Observed** |
| addon_price_min / addon_price_max | float | range across listings |
| addon_listings | integer | number of add-on listings found |
| addon_groups | string | add-on group names, ` \| ` joined |
| price_source | string | `observed_addon` |

## Deliverable 3 tables

Built by `scripts/build_price_index.py`. Reliability is `reliable` (10+ restaurants), `low` (5–9) or `suppressed` (<5, index null).

**gpi_locality** — one row per locality.

| Field | Rule |
|---|---|
| locality_id, locality_name, latitude, longitude | as in localities |
| restaurants | restaurants with a cost for two |
| reliability | see above |
| gpi, gpi_low, gpi_high | cuisine-adjusted index and 95% bootstrap interval |
| gpi_unadjusted (+ _low, _high) | median cost for two ÷ Delhi median × 100 |
| cuisine_mix_effect | gpi_unadjusted − gpi |
| gpi_hedonic | regression index (robustness) |
| addon_restaurants, addon_index | index from observed add-on prices; null below 5 restaurants |
| median / p25 / p75_cost_for_two | observed rupees |
| median_estimated_main, median_estimated_beverage | 0.35 and 0.15 × median cost for two. **Estimated** |
| top_cuisine, top_cuisine_share, cuisine_groups | primary-cuisine mix |

**gpi_cells** — one row per locality and cuisine token (29 tokens with 40+ Delhi restaurants): restaurants, delhi_restaurants, reliability, median_cost_for_two, delhi_median_cost_for_two, gpi, gpi_low, gpi_high.

**gpi_restaurants** — one row per restaurant with a cost for two: primary_cuisine, cuisine_group (pooled benchmark group), cuisine_benchmark (Delhi median of that group), relative_price, estimated_main_price, estimated_beverage_price.

## Deliverable 4 tables

Built by `scripts/build_price_drivers.py`.

**dish_selection** — every candidate canonical dish: restaurants, localities, menu_rows, p25_cost, p75_cost, iqr_ratio, selected, reason, modal_role, price_weight.

**dish_observations** — one row per restaurant and selected dish.

| Field | Rule |
|---|---|
| observation_id | `{restaurant_id}\|{canonical_dish}` |
| canonical_dish, dish_label | canonical key and display name |
| dish_id, dish_name, description, image_url | shortest-named matching menu row |
| variants, variant_names | number and names of matching menu rows (sizes, styles) |
| row_role, row_estimated_price | that row's own role and estimate |
| modal_role, price_weight | most common role of the dish across Delhi and its weight |
| dish_price_estimate | price_weight × cost_for_two. **Estimated**. The model outcome |
| ING_\*, TECH_\*, DESC_\* | 0/1 explicit mentions in any matching row's name or description |
| description_words, has_description, pieces | text descriptors |
| restaurant fields | name, brand (chain key), locality, coordinates, cost_for_two, rating, rating_clean (0 → null), rating_count, veg_nonveg, cuisines, menu_items, description_share, image_share, is_chain |
| predicted_price_cv | out-of-fold prediction of the best model for that dish. **Predicted** |
| observed_addon_price | observed add-on price of the same dish at that restaurant, if any. **Observed** |

**dish_features** — long table of every extraction: family (`ingredient`, `technique`, `descriptor`), feature, evidence (`name`, `description`, `canonical recipe`), confidence, source_type (`explicit` or `inferred`), source.

**dish_ingredients** — plan schema: dish_id, ingredient_id, quantity (null), unit (null), confidence, source, plus observation_id, canonical_dish, source_type, evidence.

**ingredients** — ingredient_id, canonical_name, category, aliases (the lexicon words).

**price_driver_metrics** — per dish (and `ALL_DISHES`) and model: mae, rmse, r2 (rupees), r2_log, n, features, best, explained_by.

**price_driver_families** — per dish: family, family_label, share of mean |SHAP|, model.

**price_driver_features** — per dish and feature: mean_abs_shap, family, effect_pct_or_sign (percent gap for 0/1 features, ±1 for numeric), prevalence, binary.

**price_driver_associations** — pooled OLS with dish fixed effects: coef, pct, pct_low, pct_high, p_value, rows_with_feature.

**addon_price_model** — one row: rows, items, restaurants, elasticity (+ 95% CI), r2, rating_coef_pct, median_within_item_spearman. **addon_model_rows** holds the rows used.
