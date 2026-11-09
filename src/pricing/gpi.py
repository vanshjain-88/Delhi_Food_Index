"""Gastronomic Price Index (GPI).

Plan formula, one cell per locality ``l`` and cuisine ``c``::

    GPI[l, c] = median price of c in l / median price of c in Delhi * 100

The unit of observation is the restaurant, not the menu row. Within one item
role every estimated dish price is a fixed share of the restaurant's cost for
two, so counting menu rows would weight a restaurant by the length of its menu
without adding price information.

Overall cuisine-adjusted index for a locality::

    relative[r]  = price[r] / median price in Delhi of r's primary cuisine
    GPI[l]       = median over restaurants r in l of relative[r] * 100

Each restaurant is compared with Delhi restaurants of the same primary cuisine,
so a locality full of bakeries is not called cheap just because bakeries are
cheaper than fine-dining North Indian. For a locality with a single cuisine
this reduces to the cell formula.

Index values do not depend on whether price is cost for two, an estimated main
or an estimated drink: those are fixed multiples of one another, and the
multiple cancels in the ratio.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Cells and localities below MIN_REPORT restaurants are suppressed. Between
# MIN_REPORT and MIN_RELIABLE they are shown with a "low" flag.
MIN_REPORT = 5
MIN_RELIABLE = 10
# Primary cuisines with fewer Delhi restaurants than this are pooled into OTHER
# when building the cuisine benchmark.
MIN_CUISINE_RESTAURANTS = 15
BOOTSTRAP_DRAWS = 2000
SEED = 20261109


@dataclass(frozen=True)
class Reliability:
    label: str
    shown: bool


def reliability(count: int) -> Reliability:
    if count >= MIN_RELIABLE:
        return Reliability("reliable", True)
    if count >= MIN_REPORT:
        return Reliability("low", True)
    return Reliability("suppressed", False)


def primary_cuisine(canonical: str | None) -> str | None:
    """First cuisine token. Zomato lists the restaurant's main identity first."""
    if canonical is None or (isinstance(canonical, float) and np.isnan(canonical)):
        return None
    first = str(canonical).split(" | ")[0].strip()
    return first or None


def cuisine_tokens(canonical: str | None) -> list[str]:
    if canonical is None or (isinstance(canonical, float) and np.isnan(canonical)):
        return []
    return [token for token in str(canonical).split(" | ") if token]


def add_cuisine_group(restaurants: pd.DataFrame, min_count: int = MIN_CUISINE_RESTAURANTS) -> pd.DataFrame:
    """Attach ``primary_cuisine`` and the pooled ``cuisine_group`` used as benchmark."""
    frame = restaurants.copy()
    frame["primary_cuisine"] = frame["canonical_cuisines"].map(primary_cuisine)
    counts = frame.loc[frame["cost_for_two"].notna(), "primary_cuisine"].value_counts()
    keep = set(counts[counts >= min_count].index)
    frame["cuisine_group"] = frame["primary_cuisine"].where(frame["primary_cuisine"].isin(keep), "OTHER")
    frame.loc[frame["primary_cuisine"].isna(), "cuisine_group"] = None
    return frame


def _bootstrap_median_ci(values: np.ndarray, rng: np.random.Generator, draws: int) -> tuple[float, float]:
    if len(values) < 2:
        return (np.nan, np.nan)
    samples = rng.choice(values, size=(draws, len(values)), replace=True)
    medians = np.median(samples, axis=1)
    low, high = np.percentile(medians, [2.5, 97.5])
    return float(low), float(high)


def _bootstrap_ratio_ci(
    numerator: np.ndarray,
    denominator: np.ndarray,
    rng: np.random.Generator,
    draws: int,
) -> tuple[float, float]:
    if len(numerator) < 2 or len(denominator) < 2:
        return (np.nan, np.nan)
    top = np.median(rng.choice(numerator, size=(draws, len(numerator)), replace=True), axis=1)
    bottom = np.median(rng.choice(denominator, size=(draws, len(denominator)), replace=True), axis=1)
    ratios = 100 * top / bottom
    low, high = np.percentile(ratios, [2.5, 97.5])
    return float(low), float(high)


def relative_prices(restaurants: pd.DataFrame, price_col: str = "cost_for_two") -> pd.DataFrame:
    """Each restaurant's price relative to the Delhi median of its cuisine group."""
    frame = restaurants.dropna(subset=[price_col, "cuisine_group", "locality_name"]).copy()
    benchmark = frame.groupby("cuisine_group")[price_col].median().rename("cuisine_benchmark")
    frame = frame.join(benchmark, on="cuisine_group")
    frame["relative_price"] = frame[price_col] / frame["cuisine_benchmark"]
    return frame


def locality_index(
    restaurants: pd.DataFrame,
    price_col: str = "cost_for_two",
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = SEED,
) -> pd.DataFrame:
    """Overall cuisine-adjusted GPI and the unadjusted index for every locality."""
    rng = np.random.default_rng(seed)
    frame = relative_prices(restaurants, price_col)
    delhi_median = float(frame[price_col].median())
    delhi_prices = frame[price_col].to_numpy()
    rows = []
    for (locality_id, locality), group in frame.groupby(["locality_id", "locality_name"]):
        count = len(group)
        flag = reliability(count)
        relative = group["relative_price"].to_numpy()
        prices = group[price_col].to_numpy()
        gpi = 100 * float(np.median(relative))
        low, high = _bootstrap_median_ci(relative, rng, draws)
        raw = 100 * float(np.median(prices)) / delhi_median
        raw_low, raw_high = _bootstrap_ratio_ci(prices, delhi_prices, rng, draws)
        top = group["cuisine_group"].value_counts()
        rows.append(
            {
                "locality_id": locality_id,
                "locality_name": locality,
                "restaurants": count,
                "reliability": flag.label,
                "gpi": gpi if flag.shown else np.nan,
                "gpi_low": 100 * low if flag.shown else np.nan,
                "gpi_high": 100 * high if flag.shown else np.nan,
                "gpi_unadjusted": raw if flag.shown else np.nan,
                "gpi_unadjusted_low": raw_low if flag.shown else np.nan,
                "gpi_unadjusted_high": raw_high if flag.shown else np.nan,
                "median_cost_for_two": float(np.median(prices)),
                "p25_cost_for_two": float(np.percentile(prices, 25)),
                "p75_cost_for_two": float(np.percentile(prices, 75)),
                "top_cuisine": top.index[0],
                "top_cuisine_share": float(top.iloc[0] / count),
                "cuisine_groups": int(group["cuisine_group"].nunique()),
            }
        )
    out = pd.DataFrame(rows)
    out["cuisine_mix_effect"] = out["gpi_unadjusted"] - out["gpi"]
    return out.sort_values("restaurants", ascending=False).reset_index(drop=True)


def cuisine_cells(
    restaurants: pd.DataFrame,
    price_col: str = "cost_for_two",
    cuisines: list[str] | None = None,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = SEED,
) -> pd.DataFrame:
    """GPI[l, c] for every locality and listed cuisine token.

    Cells use every cuisine a restaurant lists, not just the primary one: the
    question for a cell is "what does Chinese food cost here", and a North
    Indian restaurant that also lists Chinese sells Chinese food.
    """
    rng = np.random.default_rng(seed)
    frame = restaurants.dropna(subset=[price_col, "locality_name"]).copy()
    frame["token"] = frame["canonical_cuisines"].map(cuisine_tokens)
    long = frame.explode("token").dropna(subset=["token"])
    if cuisines is not None:
        long = long[long["token"].isin(cuisines)]
    benchmark = long.groupby("token")[price_col].agg(list)
    rows = []
    for (locality_id, locality, token), group in long.groupby(["locality_id", "locality_name", "token"]):
        prices = group[price_col].to_numpy()
        delhi = np.asarray(benchmark[token])
        count = len(prices)
        flag = reliability(count)
        value = 100 * float(np.median(prices)) / float(np.median(delhi))
        if flag.shown:
            low, high = _bootstrap_ratio_ci(prices, delhi, rng, draws)
        else:
            low, high = np.nan, np.nan
        rows.append(
            {
                "locality_id": locality_id,
                "locality_name": locality,
                "cuisine": token,
                "restaurants": count,
                "delhi_restaurants": len(delhi),
                "reliability": flag.label,
                "median_cost_for_two": float(np.median(prices)),
                "delhi_median_cost_for_two": float(np.median(delhi)),
                "gpi": value if flag.shown else np.nan,
                "gpi_low": low,
                "gpi_high": high,
            }
        )
    return pd.DataFrame(rows)


def hedonic_index(restaurants: pd.DataFrame, price_col: str = "cost_for_two") -> pd.DataFrame:
    """Robustness check: log price on locality and primary-cuisine dummies.

    ``exp(locality effect)`` is rescaled so that the restaurant-weighted mean
    log effect is zero, then multiplied by 100. Only localities with at least
    ``MIN_REPORT`` restaurants enter the regression.
    """
    frame = restaurants.dropna(subset=[price_col, "cuisine_group", "locality_name"]).copy()
    counts = frame["locality_name"].value_counts()
    frame = frame[frame["locality_name"].isin(counts[counts >= MIN_REPORT].index)]
    y = np.log(frame[price_col].to_numpy())
    localities = sorted(frame["locality_name"].unique())
    cuisines = sorted(frame["cuisine_group"].unique())
    loc_dummies = pd.get_dummies(frame["locality_name"]).reindex(columns=localities, fill_value=0)
    cui_dummies = pd.get_dummies(frame["cuisine_group"]).reindex(columns=cuisines[1:], fill_value=0)
    design = np.column_stack([loc_dummies.to_numpy(float), cui_dummies.to_numpy(float)])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    effects = pd.Series(coef[: len(localities)], index=localities)
    weights = counts.reindex(localities).astype(float)
    effects = effects - np.average(effects, weights=weights)
    out = pd.DataFrame({"locality_name": localities, "gpi_hedonic": 100 * np.exp(effects.to_numpy())})
    return out
