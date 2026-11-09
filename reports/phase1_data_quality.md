# Phase 1 data-quality report

Pilot only. Three Delhi localities from the Kaggle Zomato delivery-menu snapshot.

## Source

- Dataset: `archangel0x01/zomato-india-delivery-menus`
- Downloaded at: 2026-11-09T07:26:39.033092+00:00
- Kaggle last updated: None
- Access method: Kaggle API download of the published parquet. This run did not scrape Zomato.
- License note: the Kaggle card lists MIT and also warns that the contents are scraped marketplace data. Raw files are local only and are gitignored.

## Pilot definition

- Localities: Connaught Place, Hauz Khas, Karol Bagh
- Delhi rows matching those locality names, before the cap: 312
- Cap of 200 restaurants applied: yes

## Counts

- Restaurants: 200
- Menu items: 20147
- Unique dishes (normalized name): 14068
- Cuisine labels: 61
- Localities in the pilot: 3
- Price coverage: 0.0% of menu items have a positive price
- Locality coverage: 100.0% of restaurants
- Coordinate coverage: 100.0% of restaurants
- Duplicate restaurant ids: 0
- Duplicate dish rows (same restaurant, name, category, price): 4

## Pilot locality counts

| pilot_locality | restaurants |
| --- | --- |
| Connaught Place | 104 |
| Hauz Khas | 1 |
| Karol Bagh | 95 |

## Problems

- Dish prices are missing. 200 of 200 pilot menus set `price_login_blocker` to true, and the dish objects have no price field.
- Modifier-group prices exist for some add-ons. Those were not copied onto dishes.
- Hauz Khas is almost absent as a locality label in this snapshot. The Delhi inventory below shows the labels that do occur.

## Restaurant missing values

| column | missing | missing % |
|---|---:|---:|
| restaurant_id | 0 | 0.0 |
| name | 0 | 0.0 |
| normalized_name | 0 | 0.0 |
| address | 0 | 0.0 |
| locality_name | 0 | 0.0 |
| pilot_locality | 0 | 0.0 |
| city_name | 0 | 0.0 |
| latitude | 0 | 0.0 |
| longitude | 0 | 0.0 |
| rating | 0 | 0.0 |
| rating_count | 18 | 9.0 |
| cost_for_two | 3 | 1.5 |
| cuisine | 0 | 0.0 |
| phone | 0 | 0.0 |
| url | 0 | 0.0 |
| source | 0 | 0.0 |
| source_id | 0 | 0.0 |
| collection_date | 0 | 0.0 |
| dish_price_blocked | 0 | 0.0 |
| veg_nonveg | 0 | 0.0 |

## Menu-item missing values

| column | missing | missing % |
|---|---:|---:|
| dish_id | 0 | 0.0 |
| restaurant_id | 0 | 0.0 |
| dish_name | 0 | 0.0 |
| normalized_dish_name | 0 | 0.0 |
| category | 0 | 0.0 |
| cuisine | 0 | 0.0 |
| price | 20147 | 100.0 |
| description | 4463 | 22.2 |
| is_veg | 451 | 2.2 |
| is_bestseller | 20126 | 99.9 |
| image_url | 5107 | 25.3 |
| source | 0 | 0.0 |
| source_id | 0 | 0.0 |
| collection_date | 0 | 0.0 |

## Delhi locality inventory (top 25 by restaurant count)

This is a count only. Menu rows were parsed for the pilot localities.

| city_name | locality_name | restaurants |
| --- | --- | --- |
| Delhi NCR | Connaught Place, New Delhi | 163 |
| Delhi NCR | Karol Bagh, New Delhi | 148 |
| Delhi NCR | Rajinder Nagar, New Delhi | 88 |
| Delhi NCR | Kamla Nagar, New Delhi | 64 |
| Delhi NCR | Laxmi Nagar, New Delhi | 64 |
| Delhi NCR | Paharganj, New Delhi | 60 |
| Delhi NCR | West Patel Nagar, New Delhi | 56 |
| Delhi NCR | Defence Colony, New Delhi | 51 |
| Delhi NCR | Jangpura, New Delhi | 33 |
| Delhi NCR | East Patel Nagar, New Delhi | 31 |
| Delhi NCR | Chanakyapuri, New Delhi | 30 |
| Delhi NCR | Inderlok, New Delhi | 30 |
| Delhi NCR | Khan Market, New Delhi | 28 |
| Delhi NCR | Chandni Chowk, New Delhi | 25 |
| Delhi NCR | Civil Lines, New Delhi | 25 |
| Delhi NCR | Lajpat Nagar 1, New Delhi | 25 |
| Delhi NCR | Lodhi Colony, New Delhi | 24 |
| Delhi NCR | Satyaniketan, New Delhi | 24 |
| Delhi NCR | Janpath, New Delhi | 23 |
| Delhi NCR | Gole Market, New Delhi | 20 |
| Delhi NCR | Daryaganj, New Delhi | 19 |
| Delhi NCR | South Extension 1, New Delhi | 18 |
| Delhi NCR | Geeta Colony, New Delhi | 16 |
| Delhi NCR | Naraina, New Delhi | 15 |
| Delhi NCR | Lajpat Nagar 2, New Delhi | 13 |

## Sample restaurants

| name | pilot_locality | locality_name | cuisine | rating | cost_for_two | latitude | longitude |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Kwality | Connaught Place | Connaught Place, New Delhi | North Indian, BBQ, Mughlai, Finger Food, Desserts, Beverages | 4.4 | 4000.0 | 28.629808717 | 77.2173076496 |
| VEDA - Ancient Recipes, Modern Palates | Connaught Place | Connaught Place, New Delhi | North Indian | 3.9 | 1800.0 | 28.6351574055 | 77.2180867705 |
| Biryani Blues | Connaught Place | Connaught Place, New Delhi | Biryani, Hyderabadi, Mughlai, Healthy Food, Kebab, North Indian | 4.1 | 1200.0 | 28.6299561527 | 77.220502831 |
| Bikkgane Biryani | Connaught Place | Connaught Place, New Delhi | Biryani, Hyderabadi, Andhra, Lucknowi, Desserts, Beverages | 4.1 | 700.0 | 28.6314431531 | 77.216197215 |
| Chaayos Chai+Snacks=Relax | Connaught Place | Connaught Place, New Delhi | Tea, Cafe, Coffee, Rolls, Fast Food, Beverages | 4.1 | 500.0 | 28.6313725262 | 77.2204924375 |
| Burger Singh - Big Punjabi Burgers | Connaught Place | Connaught Place, New Delhi | Burger, Fast Food, Momos, Beverages, Desserts | 3.7 | 300.0 | 28.6342308173 | 77.2176737711 |
| 38 Barracks | Connaught Place | Connaught Place, New Delhi | North Indian, Biryani, Chinese, Kebab, Desserts, Beverages | 4.4 | 2000.0 | 28.6330379319 | 77.2227720233 |
| Wagh Bakri Tea Lounge | Connaught Place | Connaught Place, New Delhi | Tea, Beverages, Fast Food, Street Food, Bakery, Desserts | 3.7 | 500.0 | 28.6345059602 | 77.2221939638 |

## Sample dishes

| dish_name | category | price | is_veg | description | image_url |
| --- | --- | --- | --- | --- | --- |
| Amritsari Fish | Appetizers |  | False |  |  |
| Banana Peanut Tikki | Appetizers |  | True |  |  |
| Beetroot Tikki | Appetizers |  | True |  |  |
| Dahi Ke Kebab | Appetizers |  | True |  |  |
| Golden Fried Prawns | Appetizers |  | False |  |  |
| Harra Bhara Kebab | Appetizers |  | True |  |  |
| Kerala Prawn | Appetizers |  | False |  |  |
| Khatti Meethi Gobhi | Appetizers |  | True |  |  |
