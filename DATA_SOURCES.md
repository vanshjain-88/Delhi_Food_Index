# Data sources

## Kaggle Zomato India Delivery Menus

- Source name: Zomato India Delivery Menus
- Publisher: Kaggle user `archangel0x01`
- URL: https://www.kaggle.com/datasets/archangel0x01/zomato-india-delivery-menus
- Data obtained: restaurant identity, locality, cuisines, delivery rating, cost for two, and nested delivery menus (dish name, category, price, description, tags, images) where those fields exist in the snapshot
- Access method: Kaggle API download of the published files. This project does not scrape Zomato.
- Collection date: written into `data/raw/zomato/SOURCE_MANIFEST.json` when the pilot script runs
- License / usage notes: the Kaggle dataset card lists an MIT license. The same release includes a notice that the contents were scraped from a marketplace and should be checked against the source platform's terms before redistribution. Both files are kept in `data/raw/zomato/`. This repository publishes the Delhi extract and the processed tables. It does not publish the deleted all-India file.
- Limitations: point-in-time delivery menus, not the full dine-in universe of Delhi. Nested fields are not uniform. Dish prices are blocked in the snapshot. The local raw file is Delhi only: `data/raw/zomato/delhi_restaurants.parquet`, 1,351 restaurants whose locality label contains "New Delhi". One Ghaziabad row that had been filed under Delhi NCR was left out. The 311 MB all-India parquet was deleted after that extract was checked.

## Not used in this phase

OpenStreetMap, Overture Maps Places, data.gov.in commodity prices, and Agmarknet are part of the approved architecture and are not collected in the Phase 1 pilot.

## Derived in this project (no new external source)

- Observed add-on prices are read from the `modifier_groups` already inside the Kaggle snapshot's menu JSON. No new collection.
- Map tiles in the app are loaded by the viewer's browser from CARTO (OpenStreetMap data). No map data is stored in the repository.
