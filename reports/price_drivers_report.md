# Deliverable 4 — What drives dish prices?

Built by `scripts/build_price_drivers.py`.

## Read this first

The snapshot has no listed dish prices. The outcome for every dish model is the **estimated dish price**: the dish's modal role weight × the restaurant's observed cost for two. One weight is used per dish, so the menu-category label cannot become a fake driver. Within one dish, the model therefore explains which restaurants that sell the dish are expensive. Ingredient and technique words are **associations** between how a dish is described and the restaurant's price level, not the extra rupees an ingredient adds in one kitchen.

A second, smaller analysis uses **observed add-on prices** (real item prices from 'best paired with' / 'add on' groups) to test the estimate itself.

Raw-material prices (plan Phase 12) are not integrated: no commodity price source has been collected yet.

## Dish selection

Rule: at least 150 restaurants and 40 localities with a cost for two, then the 20 largest. Canonical matching rules and aliases are in `src/modeling/dishes.py`. Combos, platters, pizzas, rolls and other dishes that only contain the target are excluded. One observation per restaurant and dish; size variants (half/full) are folded into one observation and counted in `variants`.

| label | restaurants | localities | menu_rows | p25_cost | p75_cost | iqr_ratio | modal_role | price_weight | reason |
|---|---|---|---|---|---|---|---|---|---|
| Dal Makhani | 394 | 59 | 441 | 300.00 | 700.00 | 2.33 | main | 0.35 | selected |
| Cold Coffee | 349 | 56 | 579 | 300.00 | 600.00 | 2.00 | beverage | 0.15 | selected |
| Kadai Paneer | 344 | 55 | 356 | 300.00 | 700.00 | 2.33 | main | 0.35 | selected |
| Shahi Paneer | 338 | 57 | 353 | 300.00 | 600.00 | 2.00 | main | 0.35 | selected |
| Paneer Tikka | 335 | 56 | 635 | 400.00 | 850.00 | 2.12 | starter | 0.18 | selected |
| French Fries | 305 | 57 | 320 | 300.00 | 600.00 | 2.00 | starter | 0.18 | selected |
| Chilli Paneer | 298 | 56 | 454 | 300.00 | 650.00 | 2.17 | main | 0.35 | selected |
| Dal Tadka | 298 | 52 | 385 | 300.00 | 650.00 | 2.17 | main | 0.35 | selected |
| Paneer Butter Masala | 293 | 52 | 338 | 300.00 | 750.00 | 2.50 | main | 0.35 | selected |
| Veg Fried Rice | 292 | 55 | 342 | 300.00 | 600.00 | 2.00 | main | 0.35 | selected |
| Veg Manchurian | 251 | 54 | 389 | 350.00 | 700.00 | 2.00 | main | 0.35 | selected |
| Veg Hakka Noodles | 250 | 51 | 265 | 350.00 | 800.00 | 2.29 | main | 0.35 | selected |
| Chicken Biryani | 233 | 57 | 398 | 400.00 | 700.00 | 1.75 | main | 0.35 | selected |
| Chilli Chicken | 228 | 46 | 388 | 400.00 | 800.00 | 2.00 | main | 0.35 | selected |
| Gulab Jamun | 227 | 50 | 326 | 300.00 | 600.00 | 2.00 | dessert | 0.12 | selected |
| Chicken Tikka | 222 | 47 | 422 | 500.00 | 1,000.00 | 2.00 | starter | 0.18 | selected |
| Veg Biryani | 220 | 55 | 261 | 350.00 | 750.00 | 2.14 | main | 0.35 | selected |
| Butter Chicken | 219 | 46 | 310 | 450.00 | 1,000.00 | 2.22 | main | 0.35 | selected |
| Veg Momos | 174 | 42 | 207 | 300.00 | 600.00 | 2.00 | starter | 0.18 | selected |
| Tandoori Chicken | 164 | 41 | 210 | 500.00 | 1,000.00 | 2.00 | starter | 0.18 | selected |
| Margherita Pizza | 159 | 45 | 246 | 300.00 | 1,000.00 | 3.33 |  |  | eligible, outside top 20 |
| Chole Bhature | 88 | 35 | 121 | 200.00 | 400.00 | 2.00 |  |  | below 150 restaurants or 40 localities |
| Masala Dosa | 87 | 33 | 207 | 300.00 | 500.00 | 1.67 |  |  | below 150 restaurants or 40 localities |

## Feature extraction

Rule-based, from dish name and description (`src/nlp/features.py`). Explicit evidence only enters the models. Recipe ingredients are stored as `inferred` with confidence 0.60 and are constant within a dish.

- Explicit feature mentions: 12,761 across 4,342 observations.
- Inferred recipe ingredients: 14,080.

Random sample of explicit extractions:

| dish_name | feature | evidence | confidence |
|---|---|---|---|
| Shahi Paneer | SIGNATURE | name | 0.95 |
| Shahi Paneer | PANEER | name | 0.95 |
| Veg Chilli Chicken Dry | CHICKEN | name | 0.95 |
| Dal Makhani | BUTTER | name | 0.95 |
| Dal Makhani | CREAM | description | 0.85 |
| Kadhai Paneer | CAPSICUM | description | 0.85 |
| Kadhai Paneer | STIR_FRIED | description | 0.85 |
| Shahi Paneer | PANEER | name | 0.95 |
| Chilli Paneer Gravy | CHILLI | name | 0.95 |
| Chilli Paneer | CHILLI | name | 0.95 |
| Special Chicken Biryani | SLOW_COOKED | name | 0.95 |
| Yellow Dal Makhani | CREAM | description | 0.85 |
| Shahi Paneer | SIGNATURE | name | 0.95 |
| Paneer Tikka | YOGURT | description | 0.85 |
| Veg Biryani | GRILLED | description | 0.85 |

## Models

Ridge (standardized, CV-chosen alpha), random forest and histogram gradient boosting on log price. 5-fold **GroupKFold by chain brand**, so the same chain never sits in both train and test. Baseline: training-fold median. Metrics are in rupees of the estimated dish price.

| dish | n | model | baseline_mae | mae | rmse | r2 | mae_gain_pct |
|---|---|---|---|---|---|---|---|
| butter_chicken | 219 | Gradient boosting | 175.08 | 146.80 | 281.75 | 0.21 | 16.15 |
| chicken_biryani | 233 | Ridge | 155.73 | 134.22 | 279.30 | 0.16 | 13.81 |
| chicken_tikka | 222 | Random forest | 87.28 | 76.76 | 148.08 | 0.15 | 12.05 |
| chilli_chicken | 228 | Ridge | 146.98 | 119.41 | 227.76 | 0.26 | 18.76 |
| chilli_paneer | 298 | Ridge | 107.88 | 91.88 | 195.89 | 0.18 | 14.83 |
| cold_coffee | 349 | Random forest | 38.25 | 33.13 | 58.00 | 0.23 | 13.40 |
| dal_makhani | 394 | Random forest | 123.61 | 97.09 | 198.72 | 0.26 | 21.46 |
| dal_tadka | 298 | Gradient boosting | 140.18 | 100.86 | 200.39 | 0.44 | 28.05 |
| french_fries | 305 | Ridge | 50.40 | 42.04 | 90.54 | 0.20 | 16.59 |
| gulab_jamun | 227 | Ridge | 51.17 | 40.37 | 75.23 | 0.39 | 21.11 |
| hakka_noodles | 250 | Gradient boosting | 134.12 | 102.62 | 213.03 | 0.33 | 23.49 |
| kadai_paneer | 344 | Gradient boosting | 122.75 | 91.25 | 182.27 | 0.38 | 25.66 |
| paneer_butter_masala | 293 | Random forest | 115.39 | 89.35 | 176.46 | 0.28 | 22.57 |
| paneer_tikka | 335 | Ridge | 79.15 | 68.24 | 130.81 | 0.22 | 13.78 |
| shahi_paneer | 338 | Random forest | 84.39 | 65.23 | 122.50 | 0.28 | 22.71 |
| tandoori_chicken | 164 | Ridge | 85.06 | 72.18 | 138.04 | 0.22 | 15.14 |
| veg_biryani | 220 | Random forest | 120.91 | 108.79 | 227.57 | 0.10 | 10.03 |
| veg_fried_rice | 292 | Random forest | 98.83 | 81.14 | 213.15 | 0.11 | 17.89 |
| veg_manchurian | 251 | Gradient boosting | 101.17 | 83.65 | 138.30 | 0.38 | 17.32 |
| veg_momos | 174 | Ridge | 39.41 | 33.06 | 52.33 | 0.27 | 16.13 |
| ALL_DISHES | 5434 | Gradient boosting | 113.60 | 83.04 | 173.03 | 0.36 | 26.90 |

## Share of explained variation by factor family (mean |SHAP|, best tree model)

| dish | Ingredients | Preparation technique | Dish descriptors | Locality | Restaurant cuisine | Restaurant characteristics | Rating | Dish identity |
|---|---|---|---|---|---|---|---|---|
| ALL_DISHES | 0 | 1 | 2 | 12 | 32 | 16 | 11 | 25 |
| butter_chicken | 3 | 4 | 8 | 6 | 42 | 19 | 19 | 0 |
| chicken_biryani | 1 | 1 | 5 | 6 | 42 | 15 | 30 | 0 |
| chicken_tikka | 12 | 3 | 4 | 2 | 34 | 7 | 38 | 0 |
| chilli_chicken | 3 | 0 | 4 | 5 | 44 | 14 | 29 | 0 |
| chilli_paneer | 1 | 2 | 3 | 8 | 38 | 33 | 16 | 0 |
| cold_coffee | 6 | 0 | 6 | 2 | 30 | 42 | 14 | 0 |
| dal_makhani | 1 | 1 | 3 | 3 | 39 | 32 | 22 | 0 |
| dal_tadka | 6 | 1 | 6 | 5 | 38 | 25 | 19 | 0 |
| french_fries | 0 | 2 | 2 | 3 | 44 | 31 | 17 | 0 |
| gulab_jamun | 1 | 1 | 4 | 2 | 49 | 32 | 13 | 0 |
| hakka_noodles | 1 | 2 | 7 | 6 | 34 | 29 | 22 | 0 |
| kadai_paneer | 2 | 4 | 5 | 7 | 40 | 25 | 18 | 0 |
| paneer_butter_masala | 1 | 0 | 4 | 3 | 51 | 23 | 18 | 0 |
| paneer_tikka | 1 | 3 | 3 | 4 | 41 | 20 | 27 | 0 |
| shahi_paneer | 1 | 0 | 1 | 2 | 50 | 32 | 13 | 0 |
| tandoori_chicken | 10 | 2 | 7 | 6 | 37 | 12 | 27 | 0 |
| veg_biryani | 0 | 2 | 3 | 2 | 43 | 21 | 29 | 0 |
| veg_fried_rice | 1 | 1 | 1 | 2 | 45 | 35 | 15 | 0 |
| veg_manchurian | 1 | 2 | 6 | 9 | 43 | 26 | 14 | 0 |
| veg_momos | 1 | 4 | 7 | 4 | 38 | 32 | 13 | 0 |

## Pooled associations (all dishes, dish fixed effects, SEs clustered by brand)

OLS of log estimated price, n = 5,434, R² = 0.68. Percent difference in estimated price when the word is present, holding dish, locality, cuisine, rating and restaurant characteristics fixed.

| feature | rows_with_feature | pct | pct_low | pct_high | p_value |
|---|---|---|---|---|---|
| ING_PREMIUM_IMPORT | 15 | 27.40 | -3.13 | 67.56 | 0.08 |
| ING_YOGURT | 242 | 13.18 | 3.59 | 23.66 | 0.01 |
| ING_CHILLI | 691 | 12.90 | 3.44 | 23.24 | 0.01 |
| ING_POTATO | 67 | 9.42 | -4.05 | 24.78 | 0.18 |
| TECH_STEAMED | 189 | 8.14 | -3.95 | 21.76 | 0.20 |
| TECH_STIR_FRIED | 654 | 7.62 | 1.83 | 13.74 | 0.01 |
| TECH_TANDOOR | 423 | 5.81 | -2.85 | 15.24 | 0.19 |
| DESC_PORTION_FULL | 86 | 5.64 | -13.39 | 28.86 | 0.59 |
| TECH_SLOW_COOKED | 567 | 5.15 | 0.00 | 10.56 | 0.05 |
| ING_SAFFRON | 91 | 4.17 | -4.32 | 13.42 | 0.35 |
| DESC_SIGNATURE | 777 | 4.10 | -1.70 | 10.24 | 0.17 |
| ING_NUTS | 205 | 3.51 | -5.44 | 13.31 | 0.45 |
| ING_TOMATO | 490 | 3.45 | -1.90 | 9.10 | 0.21 |
| ING_CHEESE | 76 | 3.37 | -8.76 | 17.12 | 0.60 |
| ING_CORN | 24 | 3.22 | -11.84 | 20.85 | 0.69 |
| ING_MUSHROOM | 10 | 3.03 | -29.59 | 50.78 | 0.88 |
| ING_GARLIC | 351 | 2.65 | -3.03 | 8.66 | 0.37 |
| ING_CAPSICUM | 401 | 0.84 | -5.40 | 7.48 | 0.80 |
| TECH_DEEP_FRIED | 599 | 0.25 | -4.48 | 5.21 | 0.92 |
| DESC_REGIONAL_STYLE | 201 | -0.01 | -8.41 | 9.16 | 1.00 |
| TECH_HANDMADE | 32 | -0.06 | -21.26 | 26.86 | 1.00 |
| DESC_HEALTH | 133 | -0.49 | -12.45 | 13.10 | 0.94 |
| ING_GHEE | 132 | -1.30 | -8.89 | 6.91 | 0.75 |
| ING_CREAM | 943 | -1.51 | -5.73 | 2.89 | 0.49 |
| TECH_BAKED | 86 | -1.62 | -11.56 | 9.45 | 0.76 |
| ING_ONION | 604 | -1.97 | -8.06 | 4.53 | 0.54 |
| TECH_CHARCOAL_SMOKED | 303 | -1.97 | -8.77 | 5.34 | 0.59 |
| DESC_PORTION_HALF | 70 | -3.40 | -18.55 | 14.58 | 0.69 |
| DESC_BONELESS | 228 | -4.44 | -10.83 | 2.42 | 0.20 |
| TECH_GRILLED | 302 | -5.02 | -12.31 | 2.88 | 0.21 |
| pieces_listed | 353 | -5.96 | -12.05 | 0.54 | 0.07 |
| ING_CHOCOLATE | 34 | -6.83 | -21.48 | 10.55 | 0.42 |
| ING_CHICKEN | 1085 | -7.24 | -22.03 | 10.37 | 0.40 |
| ING_BUTTER | 987 | -7.89 | -15.21 | 0.07 | 0.05 |
| ING_PANEER | 1639 | -11.16 | -27.43 | 8.77 | 0.25 |
| ING_EGG | 16 | -18.68 | -30.84 | -4.40 | 0.01 |
| DESC_HALAL | 6 | -25.30 | -48.02 | 7.34 | 0.11 |

## Observed add-on prices

822 observed item prices for 52 items listed by at least 8 restaurants (229 restaurants). Model: log price = item fixed effect + b·log(cost for two) + rating.

- Elasticity b = 0.36 (95% CI 0.26–0.45). The estimate assumes b = 1. Real item prices rise with restaurant cost for two, but less than proportionally: the estimate exaggerates the spread between cheap and expensive restaurants.
- Median within-item Spearman ρ between add-on price and cost for two: 0.49.
- R² = 0.73.

## Limitations

- No listed dish prices. Results describe restaurant price level among sellers of a dish.
- Portion words (half/full, pieces) cannot change the estimate, so they only proxy restaurant type.
- Rule-based extraction misses synonyms that are not in the lexicon and cannot read negation.
- Add-on prices may be discounted relative to the a-la-carte menu.
- Associations, not causal effects.
