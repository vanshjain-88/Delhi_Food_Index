"""Deliverable 3: build the Gastronomic Price Index tables and report.

Run after ``build_delhi_dataset.py`` and ``build_addon_prices.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pricing.gpi import (  # noqa: E402
    MIN_CUISINE_RESTAURANTS,
    MIN_RELIABLE,
    MIN_REPORT,
    add_cuisine_group,
    cuisine_cells,
    hedonic_index,
    locality_index,
    relative_prices,
)

PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
# Cuisine tokens need this many Delhi restaurants to get locality cells.
MIN_CELL_CUISINE = 40
# Add-on validation: an item needs this many restaurants to have a Delhi median.
MIN_ADDON_ITEM = 8


def addon_validation(addons: pd.DataFrame, restaurants: pd.DataFrame) -> pd.DataFrame:
    """Locality index from observed add-on prices, for comparison with the GPI."""
    counts = addons.groupby("normalized_dish_name")["restaurant_id"].nunique()
    common = counts[counts >= MIN_ADDON_ITEM].index
    frame = addons[addons["normalized_dish_name"].isin(common)].copy()
    benchmark = frame.groupby("normalized_dish_name")["observed_addon_price"].median()
    frame["relative"] = frame["observed_addon_price"] / frame["normalized_dish_name"].map(benchmark)
    per_restaurant = frame.groupby("restaurant_id")["relative"].median().rename("addon_relative")
    joined = restaurants[["restaurant_id", "locality_name"]].join(per_restaurant, on="restaurant_id", how="inner")
    out = (
        joined.groupby("locality_name")
        .agg(addon_restaurants=("restaurant_id", "size"), addon_index=("addon_relative", "median"))
        .reset_index()
    )
    out["addon_index"] = 100 * out["addon_index"]
    out.loc[out["addon_restaurants"] < MIN_REPORT, "addon_index"] = np.nan
    return out


def _table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in frame.itertuples(index=False):
        cells = []
        for value in row:
            if isinstance(value, float):
                cells.append("" if np.isnan(value) else f"{value:,.1f}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    restaurants = pd.read_parquet(PROCESSED / "restaurants.parquet")
    localities = pd.read_parquet(PROCESSED / "localities.parquet")
    restaurants = add_cuisine_group(restaurants)

    priced = relative_prices(restaurants)
    keep = [
        "restaurant_id", "name", "locality_id", "locality_name", "latitude", "longitude",
        "cost_for_two", "rating", "primary_cuisine", "cuisine_group", "canonical_cuisines",
        "cuisine_benchmark", "relative_price",
    ]
    priced = priced[keep].copy()
    priced["estimated_main_price"] = (0.35 * priced["cost_for_two"]).round(2)
    priced["estimated_beverage_price"] = (0.15 * priced["cost_for_two"]).round(2)
    priced.to_parquet(PROCESSED / "gpi_restaurants.parquet", index=False)

    overall = locality_index(restaurants)
    overall = overall.merge(hedonic_index(restaurants), on="locality_name", how="left")
    overall.loc[overall["reliability"] == "suppressed", "gpi_hedonic"] = np.nan
    addons = pd.read_parquet(PROCESSED / "observed_addon_prices.parquet")
    overall = overall.merge(addon_validation(addons, restaurants), on="locality_name", how="left")
    overall = overall.merge(localities[["locality_id", "latitude", "longitude"]], on="locality_id", how="left")
    overall["median_estimated_main"] = 0.35 * overall["median_cost_for_two"]
    overall["median_estimated_beverage"] = 0.15 * overall["median_cost_for_two"]
    overall.to_parquet(PROCESSED / "gpi_locality.parquet", index=False)

    token_counts = (
        restaurants.dropna(subset=["cost_for_two"])["canonical_cuisines"]
        .str.split(" | ", regex=False)
        .explode()
        .value_counts()
    )
    cell_cuisines = token_counts[token_counts >= MIN_CELL_CUISINE].index.tolist()
    cells = cuisine_cells(restaurants, cuisines=cell_cuisines)
    cells.to_parquet(PROCESSED / "gpi_cells.parquet", index=False)

    shown = overall[overall["reliability"] != "suppressed"]
    spearman_hedonic = shown[["gpi", "gpi_hedonic"]].corr(method="spearman").iloc[0, 1]
    both = shown.dropna(subset=["addon_index"])
    spearman_addon = both[["gpi", "addon_index"]].corr(method="spearman").iloc[0, 1]

    # Worked example for the report: Khan Market.
    example_name = "Khan Market"
    example = priced[priced["locality_name"] == example_name]
    example_counts = example["cuisine_group"].value_counts().head(4)
    benchmarks = priced.groupby("cuisine_group")["cost_for_two"].median()

    report = [
        "# Deliverable 3 — Gastronomic Price Index",
        "",
        "Built by `scripts/build_price_index.py` from `data/processed/restaurants.parquet`.",
        "",
        "## What is measured",
        "",
        "The price is the observed **cost for two**. Estimated main and drink prices are 35% and 15% of it, "
        "so every index below is identical for all three price columns. Rupee levels differ and are shown separately.",
        "",
        "The unit is the restaurant. Menu rows are not counted separately, because within one role every "
        "estimated dish price at a restaurant is the same share of its cost for two.",
        "",
        "## Formulas",
        "",
        "```text",
        "Cell:     GPI[l,c] = median cost for two of cuisine c in locality l",
        "                   / median cost for two of cuisine c in Delhi × 100",
        "Overall:  relative[r] = cost for two of r / Delhi median of r's primary-cuisine group",
        "          GPI[l]      = median of relative[r] over restaurants in l × 100",
        "Raw:      GPI_raw[l]  = median cost for two in l / Delhi median × 100   (no cuisine adjustment)",
        "```",
        "",
        f"- Primary cuisine is the first listed cuisine. Primary cuisines with fewer than {MIN_CUISINE_RESTAURANTS} "
        "Delhi restaurants are pooled into OTHER for the benchmark.",
        f"- Cells use every listed cuisine token with at least {MIN_CELL_CUISINE} Delhi restaurants "
        f"({len(cell_cuisines)} cuisines).",
        f"- Fewer than {MIN_REPORT} restaurants: suppressed. {MIN_REPORT}–{MIN_RELIABLE - 1}: shown and flagged low. "
        f"{MIN_RELIABLE}+: reliable.",
        "- 95% intervals: 2,000 bootstrap resamples of restaurants. For the overall index, Delhi cuisine "
        "benchmarks are held fixed. For cells and the raw index, the locality and the Delhi benchmark are both resampled.",
        "- Outliers are not trimmed. The median already limits their pull, and the highest costs for two "
        "(₹4,000–₹8,000) are real fine-dining restaurants, not errors.",
        "",
        "## Coverage",
        "",
        f"- Localities: {len(overall)}. Reliable: {(overall['reliability'] == 'reliable').sum()}. "
        f"Low: {(overall['reliability'] == 'low').sum()}. Suppressed: {(overall['reliability'] == 'suppressed').sum()}.",
        f"- Restaurants in shown localities: {int(shown['restaurants'].sum()):,} of {len(priced):,} with a cost for two.",
        f"- Cells: {len(cells):,}. Reliable: {(cells['reliability'] == 'reliable').sum()}. "
        f"Low: {(cells['reliability'] == 'low').sum()}. Suppressed: {(cells['reliability'] == 'suppressed').sum()}.",
        "",
        "## Robustness",
        "",
        f"- Hedonic check (log cost for two on locality and primary-cuisine dummies): Spearman ρ with the overall GPI = "
        f"{spearman_hedonic:.2f} across {len(shown)} shown localities.",
        f"- Observed add-on prices (real rupee prices of items such as butter naan or cold coffee, items with ≥{MIN_ADDON_ITEM} "
        f"restaurants): Spearman ρ with the GPI = {spearman_addon:.2f} across {len(both)} localities with ≥{MIN_REPORT} "
        "such restaurants. This is the only check in the project that uses item prices the restaurant actually set.",
        "",
        f"## Worked example: {example_name}",
        "",
        f"{len(example)} restaurants have a cost for two. Largest primary-cuisine groups:",
        "",
    ]
    rows = []
    for group, count in example_counts.items():
        local = example.loc[example["cuisine_group"] == group, "cost_for_two"].median()
        rows.append({"cuisine group": group, "restaurants": int(count), "local median ₹": local,
                     "Delhi median ₹": benchmarks[group], "ratio × 100": 100 * local / benchmarks[group]})
    report.append(_table(pd.DataFrame(rows)))
    ex = overall[overall["locality_name"] == example_name].iloc[0]
    report += [
        "",
        f"Median of the {len(example)} restaurant ratios × 100 = **{ex['gpi']:.0f}** "
        f"(95% CI {ex['gpi_low']:.0f}–{ex['gpi_high']:.0f}). The raw index is {ex['gpi_unadjusted']:.0f}.",
        "",
        "## Localities (shown only)",
        "",
    ]
    table = shown[
        ["locality_name", "restaurants", "reliability", "gpi", "gpi_low", "gpi_high", "gpi_unadjusted",
         "gpi_hedonic", "addon_index", "median_cost_for_two", "top_cuisine"]
    ].sort_values("gpi", ascending=False)
    report.append(_table(table))
    report += [
        "",
        "## Limitations",
        "",
        "- Cost for two is a single published number per restaurant and is rounded (₹50/₹100 steps), "
        "so many medians tie and many indices land on round values.",
        "- The snapshot is delivery menus, not every restaurant in a locality.",
        "- Localities are Zomato labels, not official boundaries. Map points are mean restaurant coordinates.",
        "- Add-on prices can be discounted relative to a-la-carte prices. They validate ranking, not rupee levels.",
        "",
    ]
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "price_index_report.md").write_text("\n".join(report), encoding="utf-8")

    print(f"localities {len(overall)}; shown {len(shown)}; cells {len(cells)}")
    print(f"spearman hedonic {spearman_hedonic:.3f}; addon {spearman_addon:.3f} (n={len(both)})")
    print(table.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
