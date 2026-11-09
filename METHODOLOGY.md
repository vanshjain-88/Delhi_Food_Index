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

## Deliverable 3

Show both:

- median observed `cost_for_two` by locality
- median `estimated_price` by locality, separately for mains and for drinks

The cuisine-adjusted index uses the plan formula and the median. For mains, that index ranks localities the same way as an index built on cost for two, because every main is 35% of cost for two. Both levels are still shown. Cells with too few restaurants are flagged or suppressed. The minimum count is set in the price-index phase.

## Deliverable 4

The outcome is `estimated_price`. Role, cuisine, locality, rating, and restaurant characteristics can be used as predictors. Ingredients and preparation can be added when they are extracted.

Role already fixes the price ratio inside a restaurant. Ingredient and technique effects are associations across restaurants, not price gaps between two dishes in one kitchen. Results are described as associations.
