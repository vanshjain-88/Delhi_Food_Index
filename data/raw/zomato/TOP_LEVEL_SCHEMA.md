# Top-Level JSON Guide

Each line in `zomato_restaurants_india.jsonl` is one restaurant record.

## Main Keys
- `city`: City metadata such as city name, slug, and delivery page URL.
- `res_id`: Zomato restaurant identifier.
- `name`: Restaurant name.
- `restaurant_url`: Restaurant page URL.
- `order_url`: Direct delivery-order URL.
- `cuisine_string`: Human-readable cuisine list.
- `cuisines`: Cuisine labels in list form.
- `listing`: Listing-card data from the delivery browse surface.
- `basic_info`: Restaurant profile details, rating blocks, timing data, and other detail-page fields.
- `locality`: Locality and address information.
- `contact`: Contact-related information when present.
- `order_details`: Delivery-specific details such as delivery time text and order-related metadata.
- `menu`: Nested delivery menu content.

## Common Nested Sections

### `listing`
- Listing-card level restaurant metadata.
- Common fields include locality name, image URL, rating blocks, cost for two, and delivery time.

### `basic_info`
- Restaurant detail-page style metadata.
- Often includes timing, rating blocks, dining and delivery rating variants, and other presentation fields.

### `menu`
- The main menu payload.
- Common nested arrays:
  - `menus`: Top-level menu groups.
  - `menus[].categories`: Menu categories.
  - `menus[].categories[].items`: Individual menu items.
  - `modifier_groups`: Add-ons, customizations, and option groups.
  - `tags`: Tag metadata.
  - `navigation`: UI navigation labels for menu sections.

## Menu Item Shape
Menu items commonly include:
- `item_id`
- `name`
- `description`
- `image_url`
- `price` fields or price variants
- dietary or service tags
- modifier-group references

## Important Notes
- The schema is nested and not perfectly uniform across all restaurants.
- Missing or null fields are normal.
- The parquet version keeps the full record in the `json` column so the original structure is still available even when using parquet for faster filtering.
