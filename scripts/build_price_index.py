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

from ingestion.gap_fill import CURRENT_YEAR, SNAPSHOT_YEAR, same_restaurant_costs, unique_localities  # noqa: E402
from map.districts import assign_district  # noqa: E402
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
GAP_FILL = PROCESSED / "restaurants_2021.parquet"
PRICED_COLUMNS = [
    "restaurant_id", "name", "locality_id", "locality_name", "latitude", "longitude",
    "cost_for_two", "rating", "primary_cuisine", "cuisine_group", "canonical_cuisines",
    "cuisine_benchmark", "relative_price",
]
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


def gap_fill_tables(
    listing: pd.DataFrame, gaps: list[str], current_names: set[str], cell_cuisines: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Index tables for the districts the 2026 snapshot barely covers, from the 2021 listing.

    Every 2021 restaurant is compared with the Delhi median of the 2021 listing, not of 2026, so the index is
    comparable with the 2026 one even though 2021 rupees are lower. Only localities inside the filled districts
    are returned; the other 2021 restaurants only build the benchmark.
    """
    listing = unique_localities(listing.drop(columns="fills_gap"), current_names)
    listing = add_cuisine_group(listing)

    place = (
        listing.groupby("locality_id")
        .agg(locality_name=("locality_name", "first"), district=("district", "first"),
             latitude=("latitude", "mean"), longitude=("longitude", "mean"))
        .reset_index()
    )
    wanted = set(place.loc[place["district"].isin(gaps), "locality_id"])

    priced = relative_prices(listing)[PRICED_COLUMNS]
    priced = priced[priced["locality_id"].isin(wanted)].copy()

    overall = locality_index(listing)
    overall = overall.merge(hedonic_index(listing), on="locality_name", how="left")
    overall.loc[overall["reliability"] == "suppressed", "gpi_hedonic"] = np.nan
    overall = overall.merge(place[["locality_id", "latitude", "longitude"]], on="locality_id", how="left")
    overall = overall[overall["locality_id"].isin(wanted)].copy()

    cells = cuisine_cells(listing, cuisines=cell_cuisines)
    cells = cells[cells["locality_id"].isin(wanted)].copy()
    return priced, overall, cells


def main() -> None:
    restaurants = pd.read_parquet(PROCESSED / "restaurants.parquet")
    localities = pd.read_parquet(PROCESSED / "localities.parquet")
    restaurants = add_cuisine_group(restaurants)

    priced = relative_prices(restaurants)
    priced = priced[PRICED_COLUMNS].copy()

    overall = locality_index(restaurants)
    overall = overall.merge(hedonic_index(restaurants), on="locality_name", how="left")
    overall.loc[overall["reliability"] == "suppressed", "gpi_hedonic"] = np.nan
    addons = pd.read_parquet(PROCESSED / "observed_addon_prices.parquet")
    overall = overall.merge(addon_validation(addons, restaurants), on="locality_name", how="left")
    overall = overall.merge(localities[["locality_id", "latitude", "longitude"]], on="locality_id", how="left")

    token_counts = (
        restaurants.dropna(subset=["cost_for_two"])["canonical_cuisines"]
        .str.split(" | ", regex=False)
        .explode()
        .value_counts()
    )
    cell_cuisines = token_counts[token_counts >= MIN_CELL_CUISINE].index.tolist()
    cells = cuisine_cells(restaurants, cuisines=cell_cuisines)

    # The 2026 benchmarks above use every 2026 restaurant. Localities whose restaurants all sit in a district the
    # 2026 snapshot barely covers are then replaced by the 2021 listing's, so a district never mixes the two years.
    for table in (priced, overall, cells):
        table["price_year"] = CURRENT_YEAR
    listing = pd.read_parquet(GAP_FILL) if GAP_FILL.exists() else pd.DataFrame(columns=["fills_gap", "district"])
    gaps = sorted(listing.loc[listing["fills_gap"].astype(bool), "district"].unique())
    stray = 0
    if gaps:
        placed = restaurants.assign(district=assign_district(restaurants))
        stray = int(placed["district"].isin(gaps).sum())
        in_gap = placed.groupby("locality_id")["district"].agg(lambda s: bool(s.isin(gaps).all()))
        drop = set(in_gap[in_gap].index)
        priced = priced[~priced["locality_id"].isin(drop)]
        overall = overall[~overall["locality_id"].isin(drop)]
        cells = cells[~cells["locality_id"].isin(drop)]
        extra_priced, extra_overall, extra_cells = gap_fill_tables(
            listing, gaps, set(overall["locality_name"]), cell_cuisines
        )
        for table in (extra_priced, extra_overall, extra_cells):
            table["price_year"] = SNAPSHOT_YEAR
        priced = pd.concat([priced, extra_priced], ignore_index=True)
        overall = pd.concat([overall, extra_overall], ignore_index=True)
        cells = pd.concat([cells, extra_cells], ignore_index=True)

    priced["estimated_main_price"] = (0.35 * priced["cost_for_two"]).round(2)
    priced["estimated_beverage_price"] = (0.15 * priced["cost_for_two"]).round(2)
    overall["median_estimated_main"] = 0.35 * overall["median_cost_for_two"]
    overall["median_estimated_beverage"] = 0.15 * overall["median_cost_for_two"]
    overall = overall.sort_values("restaurants", ascending=False).reset_index(drop=True)
    priced.to_parquet(PROCESSED / "gpi_restaurants.parquet", index=False)
    overall.to_parquet(PROCESSED / "gpi_locality.parquet", index=False)
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
    ]
    if gaps:
        pairs = same_restaurant_costs(restaurants, listing)
        lift = float((pairs["cost_for_two_2026"] / pairs["cost_for_two_2021"]).median()) - 1
        report += [
            "## Districts filled from the 2021 listing",
            "",
            f"The 2026 snapshot has fewer than 10 restaurants in {', '.join(gaps)}. For localities in those districts "
            f"the index comes from the {SNAPSHOT_YEAR} listing (`data/processed/restaurants_2021.parquet`), "
            f"{int((priced['price_year'] == SNAPSHOT_YEAR).sum())} restaurants. Rules:",
            "",
            "- A district uses one year only. The 2026 snapshot has "
            f"{stray} restaurants inside these districts; the Food Map ignores them for district figures. In the "
            "index tables a 2026 locality keeps all its restaurants, because localities are Zomato labels, not "
            "districts (a label such as Safdarjung also covers restaurants in other districts). The 2026 Delhi "
            "benchmarks use every 2026 restaurant, so no 2026 number changes.",
            f"- Each {SNAPSHOT_YEAR} restaurant is compared with the Delhi median of the {SNAPSHOT_YEAR} listing "
            f"(all {len(listing):,} of its Delhi restaurants), never with a 2026 median. The index is therefore "
            f"comparable across the two years; rupee levels are not: {SNAPSHOT_YEAR} medians are in {SNAPSHOT_YEAR} "
            f"rupees. Where both years list the same restaurant (matched on its Zomato URL, {len(pairs)} restaurants), "
            f"the 2026 cost for two is a median {lift:.0%} higher than the 2021 one.",
            f"- The {SNAPSHOT_YEAR} listing only contains restaurants rated 3.9 or higher for dining, so it leans "
            "toward well-liked places. It has no menus, so estimated dish prices here are cost-for-two shares only.",
            "- A locality label used in two districts is split by district, for example `Rohini (North)`.",
            "",
        ]
    report += [
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
