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

- Observed dish price is unavailable in this source.
- Hauz Khas has one restaurant under that locality label, so that label cannot support a locality statistic.
- `cuisine` on a menu row describes the restaurant, not the dish.
- Locality latitude and longitude are restaurant averages, not official boundaries.
