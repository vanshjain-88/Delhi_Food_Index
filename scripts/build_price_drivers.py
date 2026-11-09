"""Deliverable 4: What drives dish prices?

Run after ``build_delhi_dataset.py`` and ``build_addon_prices.py``.
Writes observation, feature, model and explanation tables to data/processed
and a report to reports/price_drivers_report.md.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modeling.drivers import (  # noqa: E402
    FAMILIES,
    addon_model,
    build_observations,
    cross_validate,
    design_matrix,
    explain,
    ingredient_table,
    pooled_associations,
)

PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
SOURCE = "rule-based extraction from dish name and description (src/nlp/features.py)"


def _table(frame: pd.DataFrame, digits: int = 1) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in frame.itertuples(index=False):
        cells = []
        for value in row:
            if isinstance(value, (float, np.floating)):
                cells.append("" if np.isnan(value) else f"{value:,.{digits}f}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def run_one(obs: pd.DataFrame, key: str, include_dish: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    X, family = design_matrix(obs, include_dish=include_dish)
    metrics, predictions = cross_validate(obs, X)
    trees = metrics[metrics["model"].isin(["Random forest", "Gradient boosting"])]
    best_tree = trees.sort_values("mae").iloc[0]["model"]
    families, features, fitted = explain(obs, X, family, best_tree)
    best = metrics[metrics["model"] != "Baseline (median)"].sort_values("mae").iloc[0]["model"]
    metrics["dish"] = key
    metrics["n"] = len(obs)
    metrics["features"] = X.shape[1]
    metrics["best"] = metrics["model"] == best
    metrics["explained_by"] = metrics["model"] == best_tree
    families["dish"] = key
    families["model"] = best_tree
    features["dish"] = key
    features["model"] = best_tree
    oof = predictions[f"pred_{best}"].rename("predicted_price_cv")
    return metrics, families, features, oof


def main() -> None:
    started = time.time()
    menu = pd.read_parquet(PROCESSED / "menu_items.parquet")
    restaurants = pd.read_parquet(PROCESSED / "restaurants.parquet")
    obs, extraction, selection = build_observations(menu, restaurants)
    print(f"observations {len(obs)} across {obs['canonical_dish'].nunique()} dishes")

    all_metrics, all_families, all_features = [], [], []
    obs["predicted_price_cv"] = np.nan
    for key, group in obs.groupby("canonical_dish"):
        group = group.reset_index(drop=False)
        metrics, families, features, oof = run_one(group.set_index("index"), key, include_dish=False)
        obs.loc[oof.index, "predicted_price_cv"] = oof.to_numpy()
        all_metrics.append(metrics)
        all_families.append(families)
        all_features.append(features)
        best = metrics[metrics["best"]].iloc[0]
        print(f"{key:24s} n={len(group):4d} best={best['model']:18s} MAE ₹{best['mae']:.0f} R²={best['r2']:.2f}")

    pooled_metrics, pooled_families, pooled_features, _ = run_one(obs, "ALL_DISHES", include_dish=True)
    all_metrics.append(pooled_metrics)
    all_families.append(pooled_families)
    all_features.append(pooled_features)

    metrics = pd.concat(all_metrics, ignore_index=True)
    families = pd.concat(all_families, ignore_index=True)
    features = pd.concat(all_features, ignore_index=True)
    associations = pooled_associations(obs)

    addons = pd.read_parquet(PROCESSED / "observed_addon_prices.parquet")
    addon = addon_model(addons, restaurants)
    addon_frame = addon.pop("frame")
    addon_summary = pd.DataFrame([addon])

    # Observed add-on prices that fall on a selected dish.
    obs_addon = obs[["observation_id", "restaurant_id", "canonical_dish", "dish_name"]].merge(
        addons.rename(columns={"dish_name": "addon_dish_name"})[
            ["restaurant_id", "normalized_dish_name", "observed_addon_price", "addon_groups"]
        ].merge(
            menu[["restaurant_id", "normalized_dish_name"]].drop_duplicates(), on=["restaurant_id", "normalized_dish_name"]
        ),
        on="restaurant_id",
    )
    from modeling.dishes import match_dish  # noqa: E402

    obs_addon = obs_addon[obs_addon["normalized_dish_name"].map(match_dish) == obs_addon["canonical_dish"]]
    obs_addon = obs_addon.groupby("observation_id")["observed_addon_price"].median()
    obs["observed_addon_price"] = obs["observation_id"].map(obs_addon)

    # Tables. dish_ingredients follows the plan schema (dish_id, ingredient_id, quantity, unit, confidence, source).
    extraction["source"] = np.where(extraction["source_type"] == "explicit", SOURCE, "canonical recipe in src/modeling/dishes.py")
    dish_features = extraction.merge(obs[["observation_id", "canonical_dish", "restaurant_id"]], on="observation_id")
    dish_ingredients = dish_features[dish_features["family"] == "ingredient"].rename(columns={"feature": "ingredient_id"})
    dish_ingredients["quantity"] = np.nan
    dish_ingredients["unit"] = None
    dish_ingredients = dish_ingredients[
        ["dish_id", "observation_id", "canonical_dish", "ingredient_id", "quantity", "unit", "confidence",
         "source_type", "evidence", "source"]
    ]
    ingredients = ingredient_table()

    obs.to_parquet(PROCESSED / "dish_observations.parquet", index=False)
    dish_features.to_parquet(PROCESSED / "dish_features.parquet", index=False)
    dish_ingredients.to_parquet(PROCESSED / "dish_ingredients.parquet", index=False)
    ingredients.to_parquet(PROCESSED / "ingredients.parquet", index=False)
    selection.to_parquet(PROCESSED / "dish_selection.parquet", index=False)
    metrics.to_parquet(PROCESSED / "price_driver_metrics.parquet", index=False)
    families.to_parquet(PROCESSED / "price_driver_families.parquet", index=False)
    features.to_parquet(PROCESSED / "price_driver_features.parquet", index=False)
    associations.to_parquet(PROCESSED / "price_driver_associations.parquet", index=False)
    addon_summary.to_parquet(PROCESSED / "addon_price_model.parquet", index=False)
    addon_frame[["restaurant_id", "normalized_dish_name", "dish_name", "observed_addon_price", "estimated_price",
                 "cost_for_two", "locality_name"]].to_parquet(PROCESSED / "addon_model_rows.parquet", index=False)

    # Report.
    sel = selection[["label", "restaurants", "localities", "menu_rows", "p25_cost", "p75_cost", "iqr_ratio", "modal_role",
                     "price_weight", "reason"]].copy()
    best = metrics[metrics["best"]].copy()
    base = metrics[metrics["model"] == "Baseline (median)"][["dish", "mae"]].rename(columns={"mae": "baseline_mae"})
    best = best.merge(base, on="dish")
    best["mae_gain_pct"] = 100 * (1 - best["mae"] / best["baseline_mae"])
    perf = best[["dish", "n", "model", "baseline_mae", "mae", "rmse", "r2", "mae_gain_pct"]]
    share = families.pivot_table(index="dish", columns="family_label", values="share", aggfunc="sum").fillna(0) * 100
    share = share.reindex(columns=[v for v in FAMILIES.values() if v in share.columns]).reset_index()
    assoc_show = associations[associations["family"].isin(["ingredient", "technique", "descriptor"])].copy()
    assoc_show = assoc_show[assoc_show["binary"]].sort_values("pct", ascending=False)
    assoc_show = assoc_show[["feature", "rows_with_feature", "pct", "pct_low", "pct_high", "p_value"]]
    explicit = extraction[extraction["source_type"] == "explicit"]
    sample = (
        explicit.merge(obs[["observation_id", "dish_name", "description"]], on="observation_id")
        .sample(15, random_state=7)[["dish_name", "feature", "evidence", "confidence"]]
    )

    report = [
        "# Deliverable 4 — What drives dish prices?",
        "",
        "Built by `scripts/build_price_drivers.py`.",
        "",
        "## Read this first",
        "",
        "The snapshot has no listed dish prices. The outcome for every dish model is the **estimated dish price**: "
        "the dish's modal role weight × the restaurant's observed cost for two. One weight is used per dish, so the "
        "menu-category label cannot become a fake driver. Within one dish, the model therefore explains which "
        "restaurants that sell the dish are expensive. Ingredient and technique words are **associations** between how "
        "a dish is described and the restaurant's price level, not the extra rupees an ingredient adds in one kitchen.",
        "",
        "A second, smaller analysis uses **observed add-on prices** (real item prices from 'best paired with' / "
        "'add on' groups) to test the estimate itself.",
        "",
        "Raw-material prices (plan Phase 12) are not integrated: no commodity price source has been collected yet.",
        "",
        "## Dish selection",
        "",
        f"Rule: at least 150 restaurants and 40 localities with a cost for two, then the 20 largest. "
        "Canonical matching rules and aliases are in `src/modeling/dishes.py`. Combos, platters, pizzas, rolls and "
        "other dishes that only contain the target are excluded. One observation per restaurant and dish; size variants "
        "(half/full) are folded into one observation and counted in `variants`.",
        "",
        _table(sel, 2),
        "",
        "## Feature extraction",
        "",
        "Rule-based, from dish name and description (`src/nlp/features.py`). Explicit evidence only enters the models. "
        "Recipe ingredients are stored as `inferred` with confidence 0.60 and are constant within a dish.",
        "",
        f"- Explicit feature mentions: {len(explicit):,} across {explicit['observation_id'].nunique():,} observations.",
        f"- Inferred recipe ingredients: {(extraction['source_type'] == 'inferred').sum():,}.",
        "",
        "Random sample of explicit extractions:",
        "",
        _table(sample, 2),
        "",
        "## Models",
        "",
        "Ridge (standardized, CV-chosen alpha), random forest and histogram gradient boosting on log price. "
        "5-fold **GroupKFold by chain brand**, so the same chain never sits in both train and test. "
        "Baseline: training-fold median. Metrics are in rupees of the estimated dish price.",
        "",
        _table(perf, 2),
        "",
        "## Share of explained variation by factor family (mean |SHAP|, best tree model)",
        "",
        _table(share, 0),
        "",
        "## Pooled associations (all dishes, dish fixed effects, SEs clustered by brand)",
        "",
        f"OLS of log estimated price, n = {associations.attrs['n']:,}, R² = {associations.attrs['r2']:.2f}. "
        "Percent difference in estimated price when the word is present, holding dish, locality, cuisine, rating and "
        "restaurant characteristics fixed.",
        "",
        _table(assoc_show, 2),
        "",
        "## Observed add-on prices",
        "",
        f"{addon['rows']:,} observed item prices for {addon['items']} items listed by at least 8 restaurants "
        f"({addon['restaurants']} restaurants). Model: log price = item fixed effect + b·log(cost for two) + rating.",
        "",
        f"- Elasticity b = {addon['elasticity']:.2f} (95% CI {addon['elasticity_low']:.2f}–{addon['elasticity_high']:.2f}). "
        "The estimate assumes b = 1. Real item prices rise with restaurant cost for two, but less than proportionally: "
        "the estimate exaggerates the spread between cheap and expensive restaurants.",
        f"- Median within-item Spearman ρ between add-on price and cost for two: {addon['median_within_item_spearman']:.2f}.",
        f"- R² = {addon['r2']:.2f}.",
        "",
        "## Limitations",
        "",
        "- No listed dish prices. Results describe restaurant price level among sellers of a dish.",
        "- Portion words (half/full, pieces) cannot change the estimate, so they only proxy restaurant type.",
        "- Rule-based extraction misses synonyms that are not in the lexicon and cannot read negation.",
        "- Add-on prices may be discounted relative to the a-la-carte menu.",
        "- Associations, not causal effects.",
        "",
    ]
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "price_drivers_report.md").write_text("\n".join(report), encoding="utf-8")
    print(perf.to_string(index=False))
    print(f"addon elasticity {addon['elasticity']:.2f} [{addon['elasticity_low']:.2f}, {addon['elasticity_high']:.2f}]")
    print(f"done in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
