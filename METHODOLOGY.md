# Methodology

## Price variables

The Zomato snapshot does not contain observed dish prices. Menus set `price_login_blocker`, and dish records have no price field. The project keeps the observed restaurant cost and an estimated item price beside it.

### Observed: cost for two

`cost_for_two` is the published meal cost for two people at that restaurant. Maps and tables show this number directly. It is not a sum of listed dish prices.

### Estimated: item price

A cost-for-two meal is treated as two main dishes and two drinks. Those four shares use the whole bill:

```text
2 × 35% + 2 × 15% = 100%
estimated_main_price     = 0.35 × cost_for_two
estimated_beverage_price = 0.15 × cost_for_two
```

At a restaurant whose cost for two is ₹500, a main dish is ₹175 and a drink is ₹75.

Other menu rows are priced as smaller shares of the same bill. They are not added on top of the 100% meal.

| Role | Share of cost for two | ₹ at a ₹500 restaurant | What it covers |
|---|---:|---:|---|
| main | 35% | 175 | main course, biryani, pizza, thali, dosa, curry |
| starter | 18% | 90 | starters, snacks, momos, rolls, soups |
| other | 20% | 100 | food whose category is too vague to classify |
| beverage | 15% | 75 | drinks, shakes, coffee, tea, juice |
| dessert | 12% | 60 | sweets, ice cream, cakes |
| accompaniment | 8% | 40 | breads, plain rice, salads, raita |
| non_food | none | null | props and other non-dish rows |

The role comes from the menu category and the dish name. An explicit category wins over words in the dish name. Keyword rules live in `src/ingestion/price_weights.py`. In the Delhi dataset, about 39% of rows are mains, 23% starters, 12% accompaniments, 10% desserts, 9% drinks, 7% unclassified food, and under 1% non-food.

`estimated_price` is null when `cost_for_two` is null, and when the row is non-food. In the Delhi dataset that is 606 of 114,472 menu rows. The missing cost is not filled in.

These rupee amounts are estimates. The observed price column stays null.

Within one role, the estimate is a fixed fraction of that restaurant's cost for two. A locality ranking of median main-dish estimates therefore matches the ranking of median cost for two. The weights change the rupees, and they make a curry more expensive than a naan at the same restaurant.

## Observed add-on prices

Dish records carry no price, but menu modifier groups ("Best paired with", "Add on", "Choose your sides") do.
Many of their items are ordinary dishes on the same restaurant's menu. A modifier item is kept as an observed
price only when its normalized name equals a food dish on the same restaurant's menu and its price is positive.
If an item appears in several groups at one restaurant, the median is kept. Result: 3,753 restaurant–item prices
at 417 restaurants (`observed_addon_prices.parquet`). Code: `src/pricing/addon_prices.py`.

These are real prices set by the restaurant, but for the item sold as an add-on, which can be discounted. They are
used to check the estimate, not to replace it.

Median observed ÷ estimated price by role: main 1.03, other 1.14, accompaniment 1.50, starter 1.77,
beverage 1.81, dessert 2.10. The role weights are about right for mains and too low for small items.

## Deliverable 3 — Gastronomic Price Index

Code: `src/pricing/gpi.py`, `scripts/build_price_index.py`. Report: `reports/price_index_report.md`.

### Unit and price

The unit is the restaurant. Counting menu rows would weight a restaurant by the length of its menu, while every
estimated price inside one role is the same share of its cost for two. The price is the observed cost for two.
Index values are identical for cost for two, estimated main and estimated drink, because the shares cancel in the
ratio. The app shows the index once and the rupee levels for all three.

### Formulas

```text
Cell:     GPI[l,c] = median cost for two of cuisine c in l / median of c in Delhi × 100
Overall:  relative[r] = cost for two of r / Delhi median of r's primary-cuisine group
          GPI[l] = median over restaurants in l of relative[r] × 100
Raw:      GPI_raw[l] = median cost for two in l / Delhi median × 100
```

- The cell formula is the plan formula. A restaurant counts in every cuisine it lists, because a North Indian
  restaurant that also lists Chinese sells Chinese food. Cells exist for the 29 cuisine tokens with at least 40
  Delhi restaurants.
- The overall index compares each restaurant with Delhi restaurants of the same primary cuisine (first listed
  token). Primary cuisines with fewer than 15 Delhi restaurants are pooled as OTHER. A locality with one cuisine
  gets exactly the cell value. This avoids calling a locality cheap only because it has many sweet shops.
- The raw index is shown beside it. Their difference is the effect of cuisine mix.

### Reliability

- Fewer than 5 restaurants: suppressed (no index shown).
- 5–9: shown and flagged low.
- 10 or more: reliable.
- 95% intervals: 2,000 bootstrap resamples of restaurants. The overall index holds the Delhi cuisine benchmarks
  fixed. Cell and raw intervals resample both the locality and Delhi.
- Outliers are not trimmed. The median limits their pull, and ₹4,000–₹8,000 costs for two are real fine dining.

### Robustness

- Hedonic index: OLS of log cost for two on locality and primary-cuisine dummies. Spearman ρ = 0.91 with the
  overall GPI across the 47 shown localities.
- Add-on index: each observed add-on price divided by that item's Delhi median (items at 8+ restaurants),
  median per restaurant, median per locality (5+ restaurants). Spearman ρ = 0.59 across 14 localities.

### Limits

Cost for two is rounded, so medians tie and many indices land on round numbers. Delivery menus only. Locality
labels are Zomato's; map points are mean restaurant coordinates, not boundaries.

## Deliverable 4 — What drives dish prices?

Code: `src/modeling/dishes.py`, `src/nlp/features.py`, `src/modeling/drivers.py`,
`scripts/build_price_drivers.py`. Report: `reports/price_drivers_report.md`.

### Dish selection and matching

Canonical dishes are name patterns plus exclusions (`src/modeling/dishes.py`). Aliases were checked against the
menu: murgh makhani and chicken makhani are butter chicken; paneer makhani is paneer butter masala; dum biryani is
biryani. Combos, platters, and dishes that only contain the target (butter chicken pizza, paneer tikka roll,
butter chicken biryani, dal makhani with rice) are excluded.

Selection rule: at least 150 restaurants and 40 localities with a cost for two, then the 20 largest. Margherita
pizza (160 restaurants) was eligible but 21st. Chole bhature and masala dosa did not meet the coverage rule.

One observation per restaurant and dish. Size variants (half, full, 6 pcs) are folded into one observation; the
number of listings is kept as `variants`.

### Outcome

`dish_price_estimate = weight × cost_for_two`, with one weight per dish: the dish's most common menu role across
Delhi. The same chilli paneer is filed as a starter at one restaurant and a main at another; with the row's own
role, the menu-category label would show up as a price driver. The row-level `estimated_price` is kept as
`row_estimated_price`.

Inside one dish, the weight is constant, so the model explains which restaurants that sell the dish are
expensive. Ingredient and technique words are associations between menu copy and restaurant price level. They are
not the price difference between two versions of the dish in one kitchen.

### Features

| Family | Features |
|---|---|
| Ingredients | 23 explicit ingredient flags from name and description |
| Preparation technique | tandoor, grilled, charcoal/smoked, slow-cooked/dum, deep-fried, steamed, baked, stir-fried, handmade |
| Dish descriptors | signature/special, boneless, halal, health, regional style, half/full portion, piece count, description length, variant count |
| Locality | one-hot for localities with 10+ observations of the dish, rest pooled |
| Restaurant cuisine | top 15 listed cuisine tokens, number of cuisines |
| Restaurant characteristics | menu size, share of menu with descriptions, share with photos, chain (2+ outlets), pure veg |
| Rating | delivery rating (0 treated as missing), missing flag, log number of ratings |

Extraction is rule-based (`src/nlp/features.py`). Confidence: 0.95 in the name, 0.85 in the description, 0.60 for
ingredients inferred from the canonical recipe (stored as `source_type = inferred`, not used in models). Fixed
phrases are handled first ("fried rice", "ice cream", "cottage cheese", "stir-fried") and a simple negation rule
drops "without X". Manual audit: 55/60 correct before fixes, 57/60 after (`reports/extraction_audit.md`).

`dish_ingredients.parquet` follows the plan schema. Quantity and unit are null: menus do not state them.

### Models

Ridge (standardized, alpha by CV), random forest and histogram gradient boosting on log price, against a
training-fold median baseline. 5-fold GroupKFold by chain brand, so outlets of one chain are never split between
train and test. Metrics are in rupees of the estimated price. One model per dish and one pooled model with dish
dummies.

Explanation: SHAP (TreeExplainer) on the better of the two tree models, fit on all rows. Mean |SHAP| is summed by
family and shown as a share. For yes/no features, the app shows the average SHAP gap between rows with and without
the feature, as a percent.

Pooled association model: OLS of log estimated price on all features plus dish fixed effects, standard errors
clustered by brand. Coefficients on yes/no features are reported as `exp(b) − 1`.

### Check against observed prices

`log(add-on price) = item fixed effect + b·log(cost for two) + rating terms`, items at 8+ restaurants, standard
errors clustered by restaurant. The estimate assumes b = 1. Fitted b = 0.36 (95% CI 0.26–0.45). Real item prices
rise with restaurant price level but much less than proportionally, so estimated rupee gaps are too wide. Rankings
are more trustworthy than rupee differences.

### Not done

Raw-material prices (plan Phase 12) are not integrated. No commodity price source has been collected.

### Language

Results are described as associations. Nothing here supports a causal claim.
