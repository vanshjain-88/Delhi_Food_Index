"""Deliverable 4: observations, features and models for selected dishes.

Outcome
-------
The snapshot has no listed dish prices. The outcome is the estimated dish price
``weight × cost_for_two`` where ``weight`` is the *modal* item role of that
canonical dish across Delhi (butter chicken is a main, 35%; paneer tikka a
starter, 18%). Using one weight per dish stops the menu-category label from
showing up as a fake price driver: the same chilli paneer is filed under
"Starters" at one restaurant and "Main Course" at another.

Because the weight is constant inside a dish, a model of log estimated price
for one dish is a model of log cost for two among restaurants that sell it.
Ingredient and technique words are therefore associations between how a
restaurant describes the dish and how expensive that restaurant is. They are
not the price gap between two versions of a dish in one kitchen.

Observed add-on prices (``observed_addon_prices.parquet``) are the one place
where an item price was set by the restaurant. They are modelled separately.
"""

from __future__ import annotations

import re
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ingestion.price_weights import WEIGHTS
from modeling.dishes import DISH_BY_KEY, match_menu
from nlp.features import INGREDIENTS, extract, feature_columns, piece_count, wide_flags
from pricing.gpi import cuisine_tokens

SEED = 20261109
MIN_DISH_RESTAURANTS = 150
MIN_DISH_LOCALITIES = 40
MAX_DISHES = 20
MIN_LOCALITY_OBS = 10
TOP_CUISINES = 15
FOLDS = 5

FAMILIES = {
    "ingredient": "Ingredients",
    "technique": "Preparation technique",
    "descriptor": "Dish descriptors",
    "locality": "Locality",
    "cuisine": "Restaurant cuisine",
    "restaurant": "Restaurant characteristics",
    "rating": "Rating",
    "dish": "Dish identity",
}


def brand_key(name: str | None) -> str:
    """Chain key: the restaurant name before a dash, pipe or bracket."""
    if not isinstance(name, str):
        return ""
    head = re.split(r"\s[-|(]\s?|\s-\s|\|", name)[0]
    return re.sub(r"[^a-z0-9]+", " ", head.lower()).strip()


def restaurant_features(restaurants: pd.DataFrame, menu: pd.DataFrame) -> pd.DataFrame:
    frame = restaurants.copy()
    stats = menu.groupby("restaurant_id").agg(
        menu_items=("dish_id", "size"),
        description_share=("description", lambda s: float(s.notna().mean())),
        image_share=("image_url", lambda s: float((s.fillna("") != "").mean())),
    )
    frame = frame.join(stats, on="restaurant_id")
    frame["brand"] = frame["name"].map(brand_key)
    brand_counts = frame.groupby("brand")["restaurant_id"].transform("nunique")
    frame["is_chain"] = (brand_counts >= 2).astype(int)
    frame["rating_clean"] = frame["rating"].where(frame["rating"] > 0)
    frame["log_rating_count"] = np.log1p(frame["rating_count"])
    frame["n_cuisines"] = frame["canonical_cuisines"].map(lambda v: len(cuisine_tokens(v)))
    frame["log_menu_items"] = np.log(frame["menu_items"].fillna(1))
    return frame


def select_dishes(matched: pd.DataFrame) -> pd.DataFrame:
    """Rule-based selection: coverage first, then the largest dishes, capped at MAX_DISHES."""
    table = (
        matched.groupby("canonical_dish")
        .agg(
            restaurants=("restaurant_id", "nunique"),
            localities=("locality_name", "nunique"),
            menu_rows=("dish_id", "size"),
            p25_cost=("cost_for_two", lambda s: s.quantile(0.25)),
            p75_cost=("cost_for_two", lambda s: s.quantile(0.75)),
        )
        .reset_index()
    )
    table["label"] = table["canonical_dish"].map(lambda k: DISH_BY_KEY[k].label)
    table["iqr_ratio"] = table["p75_cost"] / table["p25_cost"]
    table = table.sort_values("restaurants", ascending=False).reset_index(drop=True)
    eligible = (table["restaurants"] >= MIN_DISH_RESTAURANTS) & (table["localities"] >= MIN_DISH_LOCALITIES)
    table["selected"] = False
    chosen = table[eligible].head(MAX_DISHES).index
    table.loc[chosen, "selected"] = True
    table["reason"] = np.where(
        table["selected"], "selected",
        np.where(eligible, f"eligible, outside top {MAX_DISHES}",
                 f"below {MIN_DISH_RESTAURANTS} restaurants or {MIN_DISH_LOCALITIES} localities"),
    )
    return table


def build_observations(
    menu: pd.DataFrame, restaurants: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (observations, extraction rows, selection table)."""
    rest = restaurant_features(restaurants, menu)
    matched = match_menu(menu).merge(
        rest[["restaurant_id", "locality_name", "cost_for_two"]], on="restaurant_id", how="left"
    )
    matched = matched[matched["cost_for_two"].notna()]
    selection = select_dishes(matched)
    keep = set(selection.loc[selection["selected"], "canonical_dish"])
    matched = matched[matched["canonical_dish"].isin(keep)].copy()

    modal_role = matched.groupby("canonical_dish")["item_role"].agg(lambda s: s.value_counts().index[0])
    selection["modal_role"] = selection["canonical_dish"].map(modal_role)
    selection["price_weight"] = selection["modal_role"].map(WEIGHTS)

    matched["name_len"] = matched["dish_name"].str.len()
    matched = matched.sort_values(["restaurant_id", "canonical_dish", "name_len", "dish_id"])
    matched["observation_id"] = matched["restaurant_id"] + "|" + matched["canonical_dish"]

    extraction = []
    for row in matched.itertuples(index=False):
        for hit in extract(row.dish_name, row.description):
            hit.update(observation_id=row.observation_id, dish_id=row.dish_id, source_type="explicit")
            extraction.append(hit)
    extraction = pd.DataFrame(extraction)
    if not extraction.empty:
        extraction = (
            extraction.sort_values("confidence", ascending=False)
            .drop_duplicates(["observation_id", "family", "feature"])
        )

    grouped = matched.groupby("observation_id", sort=False)
    first = grouped.first()
    obs = pd.DataFrame(
        {
            "observation_id": first.index,
            "restaurant_id": first["restaurant_id"].to_numpy(),
            "canonical_dish": first["canonical_dish"].to_numpy(),
            "dish_id": first["dish_id"].to_numpy(),
            "dish_name": first["dish_name"].to_numpy(),
            "variants": grouped.size().to_numpy(),
            "variant_names": grouped["dish_name"].agg(lambda s: " | ".join(s.head(6))).to_numpy(),
            "description": first["description"].to_numpy(),
            "row_role": first["item_role"].to_numpy(),
            "row_estimated_price": first["estimated_price"].to_numpy(),
            "image_url": grouped["image_url"].agg(lambda s: next((u for u in s if isinstance(u, str) and u), None)).to_numpy(),
            "is_veg": first["is_veg"].to_numpy(),
        }
    )
    obs["dish_label"] = obs["canonical_dish"].map(lambda k: DISH_BY_KEY[k].label)
    obs["modal_role"] = obs["canonical_dish"].map(modal_role)
    obs["price_weight"] = obs["modal_role"].map(WEIGHTS)
    obs["description_words"] = obs["description"].fillna("").str.split().str.len()
    obs["has_description"] = (obs["description_words"] > 0).astype(int)
    obs["pieces"] = obs["dish_name"].map(piece_count)

    obs = obs.merge(
        rest[
            [
                "restaurant_id", "name", "brand", "locality_id", "locality_name", "latitude", "longitude",
                "cost_for_two", "rating", "rating_clean", "rating_count", "log_rating_count", "veg_nonveg",
                "canonical_cuisines", "n_cuisines", "menu_items", "log_menu_items", "description_share",
                "image_share", "is_chain",
            ]
        ],
        on="restaurant_id",
        how="left",
    )
    obs["dish_price_estimate"] = (obs["price_weight"] * obs["cost_for_two"]).round(2)
    obs = obs.merge(wide_flags(extraction), on="observation_id", how="left")
    flag_cols = [c for group in feature_columns().values() for c in group]
    obs[flag_cols] = obs[flag_cols].fillna(0).astype(int)

    inferred = []
    for row in obs[["observation_id", "dish_id", "canonical_dish"]].itertuples(index=False):
        for ingredient in DISH_BY_KEY[row.canonical_dish].recipe:
            inferred.append(
                {
                    "observation_id": row.observation_id,
                    "dish_id": row.dish_id,
                    "family": "ingredient",
                    "feature": ingredient.upper().replace(" ", "_"),
                    "evidence": "canonical recipe",
                    "confidence": 0.60,
                    "source_type": "inferred",
                }
            )
    extraction = pd.concat([extraction, pd.DataFrame(inferred)], ignore_index=True)
    return obs, extraction, selection


def _cuisine_columns(obs: pd.DataFrame) -> list[str]:
    tokens = obs["canonical_cuisines"].map(cuisine_tokens).explode().value_counts()
    return tokens.head(TOP_CUISINES).index.tolist()


def design_matrix(obs: pd.DataFrame, include_dish: bool = False) -> tuple[pd.DataFrame, dict[str, str]]:
    """Feature matrix and a map from column to feature family."""
    family: dict[str, str] = {}
    parts = []

    flag_groups = feature_columns()
    for fam, cols in flag_groups.items():
        varying = [c for c in cols if obs[c].nunique() > 1 and obs[c].sum() >= 5]
        parts.append(obs[varying].astype(float))
        family.update({c: fam for c in varying})
    descriptor_numeric = pd.DataFrame(
        {
            "description_words": obs["description_words"].astype(float),
            "pieces_listed": obs["pieces"].notna().astype(float),
            "variants": obs["variants"].astype(float),
        }
    )
    parts.append(descriptor_numeric)
    family.update({c: "descriptor" for c in descriptor_numeric})

    counts = obs["locality_name"].value_counts()
    common = counts[counts >= MIN_LOCALITY_OBS].index
    locality = obs["locality_name"].where(obs["locality_name"].isin(common), "Other localities")
    loc_dummies = pd.get_dummies(locality, prefix="LOC", dtype=float)
    parts.append(loc_dummies)
    family.update({c: "locality" for c in loc_dummies})

    tokens = obs["canonical_cuisines"].map(cuisine_tokens)
    cuisine = pd.DataFrame(
        {f"CUI_{t}": tokens.map(lambda ts, t=t: float(t in ts)) for t in _cuisine_columns(obs)}, index=obs.index
    )
    cuisine["n_cuisines"] = obs["n_cuisines"].astype(float)
    cuisine = cuisine.loc[:, cuisine.nunique() > 1]
    parts.append(cuisine)
    family.update({c: "cuisine" for c in cuisine})

    restaurant = pd.DataFrame(
        {
            "log_menu_items": obs["log_menu_items"].astype(float),
            "description_share": obs["description_share"].astype(float),
            "image_share": obs["image_share"].astype(float),
            "is_chain": obs["is_chain"].astype(float),
            "pure_veg": (obs["veg_nonveg"] == "veg").astype(float),
        }
    )
    parts.append(restaurant)
    family.update({c: "restaurant" for c in restaurant})

    rating_median = obs["rating_clean"].median()
    count_median = obs["log_rating_count"].median()
    rating = pd.DataFrame(
        {
            "rating": obs["rating_clean"].fillna(rating_median).astype(float),
            "rating_missing": obs["rating_clean"].isna().astype(float),
            "log_rating_count": obs["log_rating_count"].fillna(count_median).astype(float),
        }
    )
    parts.append(rating)
    family.update({c: "rating" for c in rating})

    if include_dish:
        dish = pd.get_dummies(obs["canonical_dish"], prefix="DISH", drop_first=True, dtype=float)
        parts.append(dish)
        family.update({c: "dish" for c in dish})

    X = pd.concat(parts, axis=1)
    X = X.loc[:, ~X.columns.duplicated()]
    return X, family


def _models() -> dict[str, object]:
    return {
        "Ridge": make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 30))),
        "Random forest": RandomForestRegressor(
            n_estimators=300, min_samples_leaf=5, max_features=0.4, random_state=SEED, n_jobs=-1
        ),
        "Gradient boosting": HistGradientBoostingRegressor(
            max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=10,
            l2_regularization=1.0, random_state=SEED,
        ),
    }


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    error = predicted - actual
    ss_res = float(np.sum(error**2))
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "r2": 1 - ss_res / ss_tot if ss_tot > 0 else np.nan,
    }


def cross_validate(obs: pd.DataFrame, X: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Grouped K-fold by chain brand. Metrics are in rupees of the dish estimate."""
    y = np.log(obs["dish_price_estimate"].to_numpy())
    rupees = obs["dish_price_estimate"].to_numpy()
    groups = obs["brand"].fillna(obs["restaurant_id"]).to_numpy()
    folds = min(FOLDS, len(np.unique(groups)))
    splitter = GroupKFold(n_splits=folds)
    oof = {name: np.zeros(len(y)) for name in ["Baseline (median)", *_models()]}
    for train, test in splitter.split(X, y, groups):
        oof["Baseline (median)"][test] = np.median(y[train])
        for name, model in _models().items():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(X.iloc[train], y[train])
            oof[name][test] = model.predict(X.iloc[test])
    rows = []
    for name, pred in oof.items():
        stats = _metrics(rupees, np.exp(pred))
        stats.update({"model": name, "r2_log": _metrics(y, pred)["r2"]})
        rows.append(stats)
    metrics = pd.DataFrame(rows)
    predictions = pd.DataFrame({f"pred_{k}": np.exp(v) for k, v in oof.items()}, index=obs.index)
    return metrics, predictions


def explain(obs: pd.DataFrame, X: pd.DataFrame, family: dict[str, str], model_name: str) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    """SHAP on a tree model fit to all rows. Returns family shares, feature table, fitted log predictions."""
    import shap

    y = np.log(obs["dish_price_estimate"].to_numpy())
    model = _models()[model_name]
    model.fit(X, y)
    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(X, check_additivity=False)
    mean_abs = np.abs(values).mean(axis=0)
    features = pd.DataFrame({"feature": X.columns, "mean_abs_shap": mean_abs})
    features["family"] = features["feature"].map(family)
    directions = []
    prevalence = []
    for i, col in enumerate(X.columns):
        x = X[col].to_numpy()
        if set(np.unique(x)) <= {0.0, 1.0}:
            on = values[x == 1, i]
            off = values[x == 0, i]
            gap = float(on.mean() - off.mean()) if len(on) and len(off) else 0.0
            directions.append(100 * (np.exp(gap) - 1))
            prevalence.append(float(x.mean()))
        else:
            spread = np.std(x) > 0 and np.std(values[:, i]) > 0
            corr = np.corrcoef(x, values[:, i])[0, 1] if spread else 0.0
            directions.append(np.nan if np.isnan(corr) else float(np.sign(corr)))
            prevalence.append(np.nan)
    features["effect_pct_or_sign"] = directions
    features["prevalence"] = prevalence
    features["binary"] = features["prevalence"].notna()
    fam = features.groupby("family")["mean_abs_shap"].sum()
    fam = (fam / fam.sum()).rename("share").reset_index()
    fam["family_label"] = fam["family"].map(FAMILIES)
    return fam, features.sort_values("mean_abs_shap", ascending=False), model.predict(X)


def pooled_associations(obs: pd.DataFrame) -> pd.DataFrame:
    """OLS of log estimated price with dish fixed effects, SEs clustered by brand.

    Coefficients on binary dish-text features are reported as percent
    differences, ``exp(b) - 1``. Associations only.
    """
    import statsmodels.api as sm

    X, family = design_matrix(obs, include_dish=True)
    # Drop the reference locality so the dummies are not collinear with the constant.
    X = X.drop(columns=[c for c in X.columns if c == "LOC_Other localities"])
    y = np.log(obs["dish_price_estimate"].to_numpy())
    design = sm.add_constant(X, has_constant="add")
    codes = pd.factorize(obs["brand"].fillna(obs["restaurant_id"]))[0]
    fit = sm.OLS(y, design).fit(cov_type="cluster", cov_kwds={"groups": codes})
    conf = fit.conf_int()
    rows = []
    for col in X.columns:
        fam = family[col]
        if fam not in {"ingredient", "technique", "descriptor", "rating", "restaurant"}:
            continue
        binary = set(np.unique(X[col])) <= {0.0, 1.0}
        b, lo, hi = fit.params[col], conf.loc[col, 0], conf.loc[col, 1]
        rows.append(
            {
                "feature": col,
                "family": fam,
                "family_label": FAMILIES[fam],
                "binary": binary,
                "rows_with_feature": int(X[col].sum()) if binary else len(X),
                "coef": b,
                "pct": 100 * (np.exp(b) - 1),
                "pct_low": 100 * (np.exp(lo) - 1),
                "pct_high": 100 * (np.exp(hi) - 1),
                "p_value": fit.pvalues[col],
            }
        )
    out = pd.DataFrame(rows)
    out.attrs["r2"] = fit.rsquared
    out.attrs["n"] = int(fit.nobs)
    return out.sort_values("p_value")


def addon_model(addons: pd.DataFrame, restaurants: pd.DataFrame, min_restaurants: int = 8) -> dict:
    """Observed add-on price elasticity with respect to cost for two.

    log(addon price) = item fixed effect + b * log(cost for two) + rating terms.
    Under the project's estimate every item price is proportional to cost for
    two, i.e. b = 1. The fitted b shows how far real item prices follow that.
    """
    import statsmodels.api as sm

    counts = addons.groupby("normalized_dish_name")["restaurant_id"].nunique()
    items = counts[counts >= min_restaurants].index
    frame = addons[addons["normalized_dish_name"].isin(items)].merge(
        restaurants[["restaurant_id", "cost_for_two", "rating", "locality_name"]], on="restaurant_id"
    )
    frame = frame[frame["cost_for_two"].notna()].copy()
    frame["rating_clean"] = frame["rating"].where(frame["rating"] > 0)
    frame["rating_missing"] = frame["rating_clean"].isna().astype(float)
    frame["rating_clean"] = frame["rating_clean"].fillna(frame["rating_clean"].median())
    dummies = pd.get_dummies(frame["normalized_dish_name"], prefix="ITEM", drop_first=True, dtype=float)
    design = pd.concat(
        [np.log(frame["cost_for_two"]).rename("log_cost_for_two"), frame[["rating_clean", "rating_missing"]], dummies],
        axis=1,
    )
    design = sm.add_constant(design, has_constant="add")
    y = np.log(frame["observed_addon_price"].to_numpy())
    codes = pd.factorize(frame["restaurant_id"])[0]
    fit = sm.OLS(y, design).fit(cov_type="cluster", cov_kwds={"groups": codes})
    ci = fit.conf_int().loc["log_cost_for_two"]
    within = frame.groupby("normalized_dish_name").apply(
        lambda g: g[["observed_addon_price", "cost_for_two"]].corr(method="spearman").iloc[0, 1]
        if len(g) >= 8 else np.nan,
        include_groups=False,
    )
    return {
        "rows": int(len(frame)),
        "items": int(len(items)),
        "restaurants": int(frame["restaurant_id"].nunique()),
        "elasticity": float(fit.params["log_cost_for_two"]),
        "elasticity_low": float(ci[0]),
        "elasticity_high": float(ci[1]),
        "r2": float(fit.rsquared),
        "rating_coef_pct": float(100 * (np.exp(fit.params["rating_clean"]) - 1)),
        "median_within_item_spearman": float(np.nanmedian(within.to_numpy())),
        "frame": frame,
    }


def ingredient_table() -> pd.DataFrame:
    rows = []
    categories = {
        "CHICKEN": "meat", "MUTTON": "meat", "FISH": "seafood", "PRAWN": "seafood", "EGG": "egg",
        "PANEER": "dairy", "CHEESE": "dairy", "BUTTER": "dairy", "CREAM": "dairy", "GHEE": "dairy",
        "YOGURT": "dairy", "NUTS": "nuts", "SAFFRON": "spice", "CHILLI": "spice", "MUSHROOM": "vegetable",
        "CORN": "vegetable", "TOMATO": "vegetable", "ONION": "vegetable", "GARLIC": "vegetable",
        "CAPSICUM": "vegetable", "POTATO": "vegetable", "CHOCOLATE": "sweet", "PREMIUM_IMPORT": "premium",
    }
    for key, words in INGREDIENTS.items():
        rows.append({"ingredient_id": key, "canonical_name": key.replace("_", " ").title(),
                     "category": categories.get(key, "other"), "aliases": " | ".join(words)})
    recipe_only = sorted({i.upper().replace(" ", "_") for d in DISH_BY_KEY.values() for i in d.recipe} - set(INGREDIENTS))
    for key in recipe_only:
        rows.append({"ingredient_id": key, "canonical_name": key.replace("_", " ").title(),
                     "category": "recipe", "aliases": key.lower().replace("_", " ")})
    return pd.DataFrame(rows)
