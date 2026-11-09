# Delhi Food Index

University project on Delhi restaurants, menus, and prices. The app is **Delhi Gastronomic Intelligence**. Deliverables are added one at a time.

## Deliverable 1 — Delhi menu dataset

Structured New Delhi restaurants, menus, and localities from the Kaggle snapshot `archangel0x01/zomato-india-delivery-menus`, downloaded 9 November 2026. The project does not scrape Zomato.

| | |
|---|---|
| Restaurants | 1,351 |
| Menu items | 114,472 |
| Localities | 81 |
| With a cost for two | 1,341 |

Cost for two is observed. Dish prices in the preview are estimates: a main is 35% of that restaurant's cost for two and a drink is 15%. See `METHODOLOGY.md`.

### Files

- `data/raw/zomato/delhi_restaurants.parquet` — Delhi extract, including the original menu JSON
- `data/processed/restaurants.parquet`
- `data/processed/menu_items.parquet`
- `data/processed/localities.parquet`

The all-India download was deleted after the Delhi filter was checked. Field definitions are in `DATA_DICTIONARY.md`.

### Preview

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app/main.py
```

Open http://127.0.0.1:8501. Rebuild the processed tables with:

```bash
.venv/bin/python scripts/build_delhi_dataset.py
```

A Kaggle token is only needed to download the source again. Put it in `.env` as `KAGGLE_API_TOKEN`. That file is not committed.

## Later deliverables

Not in this commit: the food map, the cuisine-adjusted price index, and the price-driver analysis.
