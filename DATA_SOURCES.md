# Data sources

## Kaggle Zomato India Delivery Menus

- Source name: Zomato India Delivery Menus
- Publisher: Kaggle user `archangel0x01`
- URL: https://www.kaggle.com/datasets/archangel0x01/zomato-india-delivery-menus
- Data obtained: restaurant identity, locality, cuisines, delivery rating, cost for two, and nested delivery menus (dish name, category, price, description, tags, images) where those fields exist in the snapshot
- Access method: Kaggle API download of the published files. This project does not scrape Zomato.
- Collection date: written into `data/raw/zomato/SOURCE_MANIFEST.json` when the pilot script runs
- License / usage notes: the Kaggle dataset card lists an MIT license. The same release includes a notice that the contents were scraped from a marketplace and should be checked against the source platform's terms before redistribution. Both files are kept in `data/raw/zomato/`. This repository publishes the Delhi extract and the processed tables. It does not publish the deleted all-India file.
- Limitations: point-in-time delivery menus, not the full dine-in universe of Delhi. Nested fields are not uniform. Dish prices are blocked in the snapshot. The local raw file is Delhi only: `data/raw/zomato/delhi_restaurants.parquet`, 1,351 restaurants whose locality label contains "New Delhi". One Ghaziabad row that had been filed under Delhi NCR was left out. The 311 MB all-India parquet was deleted after that extract was checked. The source's Delhi NCR slice has 1,352 restaurants and every Delhi one is under a "New Delhi" locality label, so the filter dropped nothing outside the centre. Latitude spans 28.563 to 28.691 and longitude 77.138 to 77.282. The government districts North and South West therefore have no restaurants, and South (3), North East (2), Shahdara (19), and North West (26) are thin.

## District boundaries

- Source: OpenStreetMap, under the Open Database License
- What it is: outlines of the eleven revenue districts shown on the Delhi government district map (North, North West, West, South West, Central, New Delhi, South, South East, East, North East, Shahdara)
- Access: Overpass attic at 1 June 2018 for ten districts. The South Delhi relation did not download, so South is the current OSM South Delhi polygon with the other ten removed
- File: `data/geo/delhi_districts.geojson`
- This is not a shapefile from delhi.gov.in. The government poster was the reference for which districts to draw. Restaurant locations come from the Kaggle snapshot and from Overture Maps

## Zomato Restaurants in Delhi NCR (2021)

- Source name: Zomato Restaurants in Delhi NCR
- Publisher: Kaggle user `aestheteaman01`
- URL: https://www.kaggle.com/datasets/aestheteaman01/zomato-restaurants-in-delhi-ncr
- License: CC0-1.0. Last updated on Kaggle 2021-08-30; the collection date is not stated, so the table says 2021.
- Access method: Kaggle API download. Nothing is scraped. The raw CSV (`data/raw/zomato_2021/DelhiNCR Restaurants.csv`) carries restaurant phone numbers, so it is not committed; `scripts/build_gap_fill.py` says how to download it. A manifest is committed in the same folder.
- Fields used: restaurant name, cuisines, cost for two, locality, delivery rating and rating count, Zomato URL, address, latitude and longitude. Phone numbers, dining ratings and the two "known for" fields are not used.
- Why: the 2026 snapshot has fewer than 10 restaurants in North (0), South West (0), North East (2) and South (3). This file has a cost for two and a rating for restaurants in every district.
- How it is used (`scripts/build_gap_fill.py`, `src/ingestion/gap_fill.py`): rows are assigned to districts by point in polygon (NCR rows outside the eleven districts are dropped, leaving 1,188). The 307 restaurants in the four thin districts fill them. In a filled district every number comes from 2021; nothing is averaged with 2026.
- Limitations: the prices are 2021 rupees. On the 106 restaurants both files list (matched on the Zomato URL, never the name) the 2026 cost for two is a median 17% higher. The file only contains restaurants with a dining rating of 3.9 or more, so it leans toward well-liked places. It has no menus, so dish prices, common mains and What Drives Price? stay 2026-only. A missing delivery rating stays missing (53 of the 307).

## Overture Maps Places

- Source: Overture Maps Foundation, places theme, release 2026-10-21.0 (https://overturemaps.org)
- Why: the Zomato snapshot covers central Delhi only. Overture lists places in every district, which fixes the empty and thin districts on the Food Map.
- Access: DuckDB reads the public Parquet files in `s3://overturemaps-us-west-2/release/<release>/theme=places/type=place/`. Nothing is scraped. Script: `scripts/build_overture_places.py`.
- Filter: base category restaurant, casual eatery, fast-food restaurant, cafe or coffee shop; Overture's existence confidence of 0.5 or more; a name; not an internet cafe; not marked closed; inside one of the eleven district polygons. Gurugram, Noida, Faridabad and other NCR points are dropped by the polygon test. 10,310 places remain.
- What it gives: name, category, location, confidence, source datasets. **No ratings, no cost for two, no prices, no menus.** Those are not estimated.
- Licenses: the records come from Meta, Microsoft, Foursquare, AllThePlaces and others. The source licenses in the data are CDLA-Permissive-2.0, Apache-2.0 and CC0-1.0. Overture asks for attribution: "Overture Maps Foundation". The `source_datasets` and `source_licenses` columns keep the per-record provenance.
- Limitations: a place registry is not a census. Categories are coarse (about a fifth are only "restaurant"), some records are stale or duplicated, and the confidence score is Overture's, not ours. The Zomato and Overture tables are kept apart and never merged on name.
- File: `data/processed/overture_places.parquet`

## Not used in this phase

data.gov.in commodity prices and Agmarknet are part of the approved architecture and are not collected yet. OpenStreetMap is used for district outlines only, not for restaurant locations.

## Derived in this project (no new external source)

- Observed add-on prices are read from the `modifier_groups` already inside the Kaggle snapshot's menu JSON. No new collection.
- The Price Index and dish maps draw the same OpenStreetMap district outlines as the Food Map under their points. No street tiles are loaded.
