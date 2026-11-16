# Deliverable 3 — Gastronomic Price Index

Built by `scripts/build_price_index.py` from `data/processed/restaurants.parquet`.

## What is measured

The price is the observed **cost for two**. Estimated main and drink prices are 35% and 15% of it, so every index below is identical for all three price columns. Rupee levels differ and are shown separately.

The unit is the restaurant. Menu rows are not counted separately, because within one role every estimated dish price at a restaurant is the same share of its cost for two.

## Formulas

```text
Cell:     GPI[l,c] = median cost for two of cuisine c in locality l
                   / median cost for two of cuisine c in Delhi × 100
Overall:  relative[r] = cost for two of r / Delhi median of r's primary-cuisine group
          GPI[l]      = median of relative[r] over restaurants in l × 100
Raw:      GPI_raw[l]  = median cost for two in l / Delhi median × 100   (no cuisine adjustment)
```

- Primary cuisine is the first listed cuisine. Primary cuisines with fewer than 15 Delhi restaurants are pooled into OTHER for the benchmark.
- Cells use every listed cuisine token with at least 40 Delhi restaurants (29 cuisines).
- Fewer than 5 restaurants: suppressed. 5–9: shown and flagged low. 10+: reliable.
- 95% intervals: 2,000 bootstrap resamples of restaurants. For the overall index, Delhi cuisine benchmarks are held fixed. For cells and the raw index, the locality and the Delhi benchmark are both resampled.
- Outliers are not trimmed. The median already limits their pull, and the highest costs for two (₹4,000–₹8,000) are real fine-dining restaurants, not errors.

## Coverage

- Localities: 148. Reliable: 45. Low: 21. Suppressed: 82.
- Restaurants in shown localities: 1,471 of 1,648 with a cost for two.
- Cells: 1,563. Reliable: 116. Low: 176. Suppressed: 1271.

## Districts filled from the 2021 listing

The 2026 snapshot has fewer than 10 restaurants in North, North East, South, South West. For localities in those districts the index comes from the 2021 listing (`data/processed/restaurants_2021.parquet`), 307 restaurants. Rules:

- A district uses one year only. The 2026 snapshot has 5 restaurants inside these districts; the Food Map ignores them for district figures. In the index tables a 2026 locality keeps all its restaurants, because localities are Zomato labels, not districts (a label such as Safdarjung also covers restaurants in other districts). The 2026 Delhi benchmarks use every 2026 restaurant, so no 2026 number changes.
- Each 2021 restaurant is compared with the Delhi median of the 2021 listing (all 1,188 of its Delhi restaurants), never with a 2026 median. The index is therefore comparable across the two years; rupee levels are not: 2021 medians are in 2021 rupees. Where both years list the same restaurant (matched on its Zomato URL, 106 restaurants), the 2026 cost for two is a median 17% higher than the 2021 one.
- The 2021 listing only contains restaurants rated 3.9 or higher for dining, so it leans toward well-liked places. It has no menus, so estimated dish prices here are cost-for-two shares only.
- A locality label used in two districts is split by district, for example `Rohini (North)`.

## Robustness

- Hedonic check (log cost for two on locality and primary-cuisine dummies): Spearman ρ with the overall GPI = 0.90 across 66 shown localities.
- Observed add-on prices (real rupee prices of items such as butter naan or cold coffee, items with ≥8 restaurants): Spearman ρ with the GPI = 0.59 across 14 localities with ≥5 such restaurants. This is the only check in the project that uses item prices the restaurant actually set.

## Worked example: Khan Market

28 restaurants have a cost for two. Largest primary-cuisine groups:

| cuisine group | restaurants | local median ₹ | Delhi median ₹ | ratio × 100 |
|---|---|---|---|---|
| OTHER | 9 | 2,300.0 | 500.0 | 460.0 |
| PIZZA | 3 | 2,000.0 | 400.0 | 500.0 |
| BAKERY | 3 | 500.0 | 400.0 | 125.0 |
| CAFE | 3 | 1,400.0 | 800.0 | 175.0 |

Median of the 28 restaurant ratios × 100 = **388** (95% CI 208–543). The raw index is 438.

## Localities (shown only)

| locality_name | restaurants | reliability | gpi | gpi_low | gpi_high | gpi_unadjusted | gpi_hedonic | addon_index | median_cost_for_two | top_cuisine |
|---|---|---|---|---|---|---|---|---|---|---|
| Pandara Road Market | 5 | low | 450.0 | 350.0 | 600.0 | 450.0 | 398.1 |  | 1,800.0 | NORTH_INDIAN |
| R K Puram | 6 | low | 437.5 | 127.7 | 587.5 | 437.5 | 275.6 |  | 1,750.0 | NORTH_INDIAN |
| Khan Market | 28 | reliable | 387.5 | 207.5 | 542.7 | 437.5 | 298.9 |  | 1,750.0 | OTHER |
| Lodhi Colony | 24 | reliable | 239.3 | 168.8 | 400.0 | 262.5 | 249.9 |  | 1,050.0 | OTHER |
| Chanakyapuri | 30 | reliable | 196.0 | 150.0 | 250.0 | 181.2 | 197.6 |  | 725.0 | NORTH_INDIAN |
| City Centre Mall, Sector 12, Dwarka | 6 | low | 150.0 | 86.0 | 225.0 | 150.0 | 135.5 |  | 1,200.0 | NORTH_INDIAN |
| Bhikaji Cama Place | 10 | reliable | 143.8 | 62.5 | 1,250.0 | 143.8 | 201.6 |  | 575.0 | NORTH_INDIAN |
| Connaught Place | 158 | reliable | 141.4 | 125.0 | 162.5 | 125.0 | 145.0 | 100.0 | 500.0 | NORTH_INDIAN |
| Saket (South) | 6 | low | 137.5 | 78.1 | 265.0 | 175.0 | 131.1 |  | 1,400.0 | NORTH_INDIAN |
| Defence Colony | 50 | reliable | 125.0 | 100.0 | 142.9 | 125.0 | 114.0 | 119.0 | 500.0 | NORTH_INDIAN |
| Mehrauli | 9 | low | 125.0 | 70.6 | 357.1 | 275.0 | 195.8 |  | 2,200.0 | OTHER |
| Janpath | 23 | reliable | 125.0 | 85.7 | 200.0 | 125.0 | 150.0 |  | 500.0 | NORTH_INDIAN |
| Green Park | 12 | reliable | 119.6 | 86.6 | 200.9 | 93.8 | 110.7 |  | 750.0 | NORTH_INDIAN |
| South Extension 2 | 11 | reliable | 114.3 | 75.0 | 137.5 | 100.0 | 127.3 |  | 400.0 | MOMOS |
| Chandni Chowk | 25 | reliable | 114.3 | 87.5 | 137.5 | 112.5 | 95.7 |  | 450.0 | NORTH_INDIAN |
| Select Citywalk Mall, Saket | 10 | reliable | 113.4 | 93.1 | 184.8 | 112.5 | 130.3 |  | 900.0 | ASIAN |
| Shahpur Jat | 9 | low | 112.5 | 75.0 | 160.0 | 112.5 | 106.9 |  | 900.0 | CAFE |
| Rana Pratap Bagh | 10 | reliable | 106.2 | 75.0 | 197.9 | 106.2 | 96.6 |  | 425.0 | NORTH_INDIAN |
| Delhi University-GTB Nagar (North) | 26 | reliable | 103.1 | 78.1 | 112.5 | 103.1 | 88.5 |  | 825.0 | NORTH_INDIAN |
| Lajpat Nagar 2 | 13 | reliable | 100.0 | 80.0 | 125.0 | 100.0 | 90.5 |  | 400.0 | OTHER |
| Barakhamba Road | 7 | low | 100.0 | 75.0 | 125.0 | 100.0 | 101.5 |  | 400.0 | NORTH_INDIAN |
| Rajendra Place | 10 | reliable | 100.0 | 72.3 | 175.0 | 100.0 | 116.2 |  | 400.0 | DESSERTS |
| Jama Masjid | 7 | low | 100.0 | 60.0 | 125.0 | 100.0 | 77.0 |  | 400.0 | NORTH_INDIAN |
| Hauz Khas Village | 11 | reliable | 100.0 | 82.4 | 242.9 | 175.0 | 143.0 |  | 1,400.0 | CONTINENTAL |
| Karol Bagh | 147 | reliable | 100.0 | 87.5 | 114.3 | 100.0 | 86.5 | 100.0 | 400.0 | NORTH_INDIAN |
| Mandi House | 6 | low | 100.0 | 87.5 | 198.3 | 100.0 | 102.9 |  | 400.0 | NORTH_INDIAN |
| Hauz Khas (South) | 13 | reliable | 100.0 | 89.5 | 142.9 | 150.0 | 118.4 |  | 1,200.0 | OTHER |
| DLF Avenue, Saket | 5 | low | 100.0 | 73.7 | 185.7 | 162.5 | 136.8 |  | 1,300.0 | OTHER |
| East Patel Nagar | 31 | reliable | 100.0 | 64.0 | 120.0 | 87.5 | 92.0 | 92.2 | 350.0 | OTHER |
| Malviya Nagar | 20 | reliable | 100.0 | 67.0 | 100.0 | 87.5 | 72.5 |  | 700.0 | NORTH_INDIAN |
| Rajinder Nagar | 88 | reliable | 100.0 | 95.5 | 114.3 | 100.0 | 92.9 | 99.3 | 400.0 | NORTH_INDIAN |
| Civil Lines | 25 | reliable | 100.0 | 62.5 | 233.3 | 100.0 | 117.9 | 115.0 | 400.0 | NORTH_INDIAN |
| Lajpat Nagar 1 | 25 | reliable | 100.0 | 62.5 | 152.0 | 87.5 | 95.7 | 91.6 | 350.0 | NORTH_INDIAN |
| Daryaganj | 19 | reliable | 100.0 | 80.0 | 125.0 | 100.0 | 91.7 |  | 400.0 | NORTH_INDIAN |
| Satyaniketan | 24 | reliable | 100.0 | 100.0 | 132.1 | 100.0 | 111.9 |  | 400.0 | CHINESE |
| Jangpura | 33 | reliable | 100.0 | 75.0 | 110.0 | 100.0 | 79.3 | 87.5 | 400.0 | NORTH_INDIAN |
| Gole Market | 19 | reliable | 90.0 | 85.7 | 114.3 | 100.0 | 87.5 |  | 400.0 | NORTH_INDIAN |
| South Extension 1 | 18 | reliable | 88.3 | 70.8 | 100.0 | 75.0 | 72.5 | 76.2 | 300.0 | NORTH_INDIAN |
| West Patel Nagar | 56 | reliable | 87.5 | 80.0 | 100.0 | 87.5 | 76.4 |  | 350.0 | NORTH_INDIAN |
| Kirti Nagar | 7 | low | 87.5 | 66.7 | 142.9 | 87.5 | 92.0 |  | 350.0 | NORTH_INDIAN |
| Vijay Nagar (North) | 11 | reliable | 87.5 | 75.0 | 114.3 | 87.5 | 82.2 |  | 700.0 | NORTH_INDIAN |
| Krishna Nagar | 6 | low | 87.5 | 56.2 | 125.0 | 87.5 | 74.1 |  | 350.0 | NORTH_INDIAN |
| Safdarjung (South) | 23 | reliable | 85.7 | 71.4 | 100.0 | 75.0 | 85.6 |  | 600.0 | OTHER |
| Paharganj | 60 | reliable | 85.7 | 75.0 | 100.0 | 75.0 | 80.2 | 72.3 | 300.0 | NORTH_INDIAN |
| Vijay Nagar | 12 | reliable | 85.7 | 75.0 | 100.0 | 75.0 | 81.1 |  | 300.0 | NORTH_INDIAN |
| Kamla Nagar | 64 | reliable | 85.7 | 75.0 | 100.0 | 75.0 | 74.6 | 84.7 | 300.0 | NORTH_INDIAN |
| Shakarpur | 11 | reliable | 83.3 | 62.5 | 100.0 | 75.0 | 66.8 |  | 300.0 | NORTH_INDIAN |
| INA | 10 | reliable | 81.2 | 62.5 | 156.2 | 87.5 | 83.1 |  | 350.0 | OTHER |
| Mukherjee Nagar | 6 | low | 80.4 | 59.8 | 93.8 | 68.8 | 64.9 |  | 550.0 | NORTH_INDIAN |
| Sector 7, Dwarka | 11 | reliable | 80.0 | 64.3 | 118.8 | 75.0 | 69.6 |  | 600.0 | NORTH_INDIAN |
| Rohini (North) | 12 | reliable | 78.6 | 53.6 | 110.0 | 59.4 | 65.1 |  | 475.0 | CHINESE |
| Inderlok | 30 | reliable | 75.0 | 62.5 | 86.6 | 75.0 | 62.4 | 70.7 | 300.0 | NORTH_INDIAN |
| Laxmi Nagar | 63 | reliable | 75.0 | 75.0 | 100.0 | 75.0 | 72.7 | 68.7 | 300.0 | NORTH_INDIAN |
| Sarojini Nagar | 5 | low | 75.0 | 50.0 | 85.7 | 75.0 | 64.2 |  | 300.0 | NORTH_INDIAN |
| Champa Gali, Saket | 5 | low | 75.0 | 38.9 | 100.0 | 75.0 | 73.7 |  | 600.0 | CAFE |
| Naraina | 15 | reliable | 75.0 | 64.0 | 125.0 | 75.0 | 84.3 |  | 300.0 | NORTH_INDIAN |
| Pandav Nagar | 6 | low | 73.9 | 51.2 | 118.8 | 68.8 | 69.3 |  | 275.0 | PIZZA |
| Chawri Bazar | 10 | reliable | 70.8 | 50.0 | 112.5 | 68.8 | 70.8 |  | 275.0 | NORTH_INDIAN |
| Asaf Ali Road | 10 | reliable | 68.8 | 50.0 | 125.0 | 68.8 | 74.6 | 114.1 | 275.0 | NORTH_INDIAN |
| Shadipur | 12 | reliable | 68.8 | 50.0 | 125.0 | 68.8 | 67.1 |  | 275.0 | NORTH_INDIAN |
| Moti Bagh | 6 | low | 68.8 | 53.6 | 150.0 | 68.8 | 71.4 |  | 275.0 | BAKERY |
| Yusuf Sarai | 7 | low | 62.5 | 31.2 | 75.0 | 62.5 | 53.9 |  | 500.0 | NORTH_INDIAN |
| Geeta Colony | 16 | reliable | 58.6 | 50.0 | 87.5 | 62.5 | 60.3 |  | 250.0 | NORTH_INDIAN |
| Shahdara (North East) | 6 | low | 58.1 | 40.6 | 95.0 | 43.8 | 51.8 |  | 350.0 | NORTH_INDIAN |
| Azad Market | 6 | low | 56.2 | 43.8 | 137.5 | 56.2 | 69.6 |  | 225.0 | NORTH_INDIAN |
| Ashok Vihar Phase 3 | 6 | low | 56.2 | 43.8 | 212.5 | 56.2 | 68.2 |  | 225.0 | NORTH_INDIAN |

## Limitations

- Cost for two is a single published number per restaurant and is rounded (₹50/₹100 steps), so many medians tie and many indices land on round values.
- The snapshot is delivery menus, not every restaurant in a locality.
- Localities are Zomato labels, not official boundaries. Map points are mean restaurant coordinates.
- Add-on prices can be discounted relative to a-la-carte prices. They validate ranking, not rupee levels.
