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
- This is not a shapefile from delhi.gov.in. The government poster was the reference for which districts to draw. Restaurant locations still come only from the Kaggle snapshot

## Not used in this phase

Overture Maps Places, data.gov.in commodity prices, and Agmarknet are part of the approved architecture and are not collected yet. OpenStreetMap is used for district outlines only, not for restaurant locations.

## Derived in this project (no new external source)

- Observed add-on prices are read from the `modifier_groups` already inside the Kaggle snapshot's menu JSON. No new collection.
- The Price Index and dish maps draw the same OpenStreetMap district outlines as the Food Map under their points. No street tiles are loaded.
