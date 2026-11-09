"""Deliverable 4: What drives dish prices?"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui import CHART, DATA, district_layers, MUTED, RUST, TEAL, pretty_feature, pretty_token

FAMILY_ORDER = [
    "Restaurant cuisine", "Restaurant characteristics", "Rating", "Locality",
    "Ingredients", "Preparation technique", "Dish descriptors",
]


@st.cache_data(show_spinner=False)
def load() -> dict[str, pd.DataFrame]:
    names = [
        "dish_observations", "dish_features", "dish_selection", "price_driver_metrics", "price_driver_families",
        "price_driver_features", "price_driver_associations", "addon_price_model", "addon_model_rows",
    ]
    return {name: pd.read_parquet(DATA / f"{name}.parquet") for name in names}


def render_price_drivers() -> None:
    tables = load()
    obs = tables["dish_observations"]
    selection = tables["dish_selection"]
    metrics = tables["price_driver_metrics"]
    families = tables["price_driver_families"]
    features = tables["price_driver_features"]
    dish_features = tables["dish_features"]
    addon = tables["addon_price_model"].iloc[0]

    st.title("What Drives Dish Prices?")
    st.caption(
        "Deliverable 4. Twenty popular Delhi dishes, one observation per restaurant that sells them. "
        "Factors shown are associated with higher or lower prices. They are not causes."
    )
    st.warning(
        "**The prices here are estimates.** The source hides listed dish prices, so each dish's price is its role share "
        "of the restaurant's observed cost for two (a main is 35%). Within one dish, the model is therefore explaining "
        "which restaurants that sell it are expensive. A check against real add-on prices is at the bottom of the page.",
        icon="⚠️",
    )

    chosen = selection[selection["selected"]].sort_values("label")
    labels = dict(zip(chosen["canonical_dish"], chosen["label"]))
    dish = st.selectbox("Dish", list(labels), format_func=lambda k: labels.get(k, k),
                        index=list(labels).index("butter_chicken") if "butter_chicken" in labels else 0)
    d = obs[obs["canonical_dish"] == dish].copy()
    info = chosen[chosen["canonical_dish"] == dish].iloc[0]
    dish_metrics = metrics[metrics["dish"] == dish]
    best = dish_metrics[dish_metrics["best"]].iloc[0]
    baseline = dish_metrics[dish_metrics["model"] == "Baseline (median)"].iloc[0]

    # 1. Header: images and headline numbers.
    img_col, stat_col = st.columns([2, 3])
    with img_col:
        images = (
            d.dropna(subset=["image_url"]).sort_values(["rating_count"], ascending=False)["image_url"].drop_duplicates().head(3)
        )
        if images.empty:
            st.info("No menu photo for this dish in the snapshot.")
        else:
            cols = st.columns(len(images))
            for slot, url in zip(cols, images):
                slot.image(url, width="stretch")
            st.caption("Menu photos from the snapshot, from the most-rated restaurants that sell the dish.")
    with stat_col:
        a, b, c = st.columns(3)
        a.metric("Restaurants", f"{len(d):,}")
        b.metric("Localities", f"{d['locality_name'].nunique():,}")
        c.metric("Median estimated price", f"₹{d['dish_price_estimate'].median():,.0f}")
        a2, b2, c2 = st.columns(3)
        a2.metric("Middle 50%", f"₹{d['dish_price_estimate'].quantile(.25):,.0f}–{d['dish_price_estimate'].quantile(.75):,.0f}")
        b2.metric(f"Model error (MAE) · baseline ₹{baseline['mae']:,.0f}", f"₹{best['mae']:,.0f}")
        observed = d["observed_addon_price"].dropna()
        if len(observed):
            c2.metric(f"Observed add-on price · n={len(observed)}", f"₹{observed.median():,.0f}")
        else:
            c2.metric("Observed add-on price", "none")
        st.caption(
            f"Role used for the estimate: **{info['modal_role']}** ({info['price_weight']:.0%} of cost for two), the most "
            f"common menu role for {info['label']} across Delhi. Best model: {best['model']} "
            f"(grouped cross-validated R² {best['r2']:.2f})."
        )

    # 2. Price across Delhi.
    st.subheader("Price across Delhi")
    map_col, loc_col = st.columns([3, 2])
    with map_col:
        geo = d.dropna(subset=["latitude", "longitude"])
        fig = px.scatter_map(
            geo,
            lat="latitude",
            lon="longitude",
            color="dish_price_estimate",
            color_continuous_scale=[[0, "#F3E4D7"], [1, RUST]],
            range_color=(geo["dish_price_estimate"].quantile(0.05), geo["dish_price_estimate"].quantile(0.95)),
            hover_name="name",
            custom_data=["dish_name", "locality_name", "dish_price_estimate", "cost_for_two"],
            zoom=10.6,
            center={"lat": 28.625, "lon": 77.21},
            map_style="white-bg",
            height=460,
        )
        fig.update_traces(
            marker={"size": 10, "opacity": 0.85},
            hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]} · %{customdata[1]}<br>"
                          "Estimated ₹%{customdata[2]:,.0f} (cost for two ₹%{customdata[3]:,.0f})<extra></extra>",
        )
        fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0}, coloraxis_colorbar={"title": "₹"},
                          map_layers=district_layers(),
                          paper_bgcolor=CHART["paper_bgcolor"])
        st.plotly_chart(fig, width="stretch")
    with loc_col:
        by_loc = (
            d.groupby("locality_name")["dish_price_estimate"]
            .agg(["median", "size"])
            .query("size >= 5")
            .sort_values("median")
            .reset_index()
        )
        if by_loc.empty:
            st.info("No locality has 5 or more restaurants selling this dish.")
        else:
            bar = px.bar(by_loc, x="median", y="locality_name", orientation="h", text="size",
                         labels={"median": "Median estimated price (₹)", "locality_name": ""},
                         color_discrete_sequence=[RUST])
            bar.add_vline(x=d["dish_price_estimate"].median(), line_dash="dot", line_color=MUTED,
                          annotation_text="Delhi", annotation_font_color=MUTED)
            bar.update_traces(texttemplate="n=%{text}", textposition="outside", textfont_color=MUTED,
                              hovertemplate="%{y}: ₹%{x:,.0f} median, %{text} restaurants<extra></extra>")
            bar.update_layout(height=460, margin={"l": 10, "r": 30, "t": 10, "b": 10},
                              xaxis_range=[0, float(by_loc["median"].max()) * 1.2], **CHART)
            st.plotly_chart(bar, width="stretch")
            st.caption("Localities with 5+ restaurants selling the dish.")

    # 3. Distribution.
    st.subheader("Price distribution")
    hist = px.histogram(d, x="dish_price_estimate", nbins=30, labels={"dish_price_estimate": "Estimated price (₹)"},
                        color_discrete_sequence=[RUST])
    hist.update_traces(marker_line_width=2, marker_line_color=CHART["paper_bgcolor"],
                       hovertemplate="₹%{x}: %{y} restaurants<extra></extra>")
    if len(observed):
        hist.add_trace(go.Histogram(x=observed, nbinsx=20, name="Observed add-on price", marker_color=TEAL, opacity=0.8,
                                    hovertemplate="₹%{x}: %{y} observed<extra></extra>"))
        hist.update_traces(selector={"type": "histogram"}, showlegend=True)
        hist.data[0].name = "Estimated price"
    hist.update_layout(height=280, margin={"l": 10, "r": 10, "t": 10, "b": 10}, yaxis_title="Restaurants",
                       barmode="overlay", legend={"orientation": "h", "y": 1.12}, **CHART)
    st.plotly_chart(hist, width="stretch")

    # 4–5. Ingredients and techniques.
    st.subheader("Ingredients and techniques")
    explicit = dish_features[(dish_features["canonical_dish"] == dish) & (dish_features["source_type"] == "explicit")]
    inferred = dish_features[(dish_features["canonical_dish"] == dish) & (dish_features["source_type"] == "inferred")]
    recipe = sorted(inferred["feature"].unique())
    st.markdown(
        "**From the canonical recipe (inferred, confidence 0.6):** "
        + (", ".join(pretty_token(r) for r in recipe) if recipe else "none")
    )
    prev = (
        explicit.groupby(["family", "feature"])["observation_id"].nunique().div(len(d)).rename("share").reset_index()
    )
    prev = prev[prev["family"].isin(["ingredient", "technique"])]
    ing_col, tech_col = st.columns(2)
    for slot, family, title in ((ing_col, "ingredient", "Ingredients named on the menu"),
                                (tech_col, "technique", "Techniques named on the menu")):
        part = prev[prev["family"] == family].sort_values("share").tail(10)
        with slot:
            st.markdown(f"**{title}**")
            if part.empty:
                st.info("None found in names or descriptions.")
                continue
            part["label"] = part["feature"].map(pretty_token)
            fig = px.bar(part, x="share", y="label", orientation="h", labels={"share": "Share of restaurants", "label": ""},
                         color_discrete_sequence=[TEAL])
            fig.update_traces(hovertemplate="%{y}: %{x:.0%} of restaurants<extra></extra>")
            fig.update_layout(height=300, margin={"l": 10, "r": 10, "t": 10, "b": 10}, xaxis_tickformat=".0%", **CHART)
            st.plotly_chart(fig, width="stretch")
    st.caption("Explicit = the word appears in that restaurant's dish name (confidence 0.95) or description (0.85). "
               "Descriptions exist for about two-thirds of menu rows, so absence is weak evidence.")

    # 6. Drivers.
    st.subheader("Price-associated factors")
    fam = families[families["dish"] == dish].set_index("family_label")["share"].reindex(FAMILY_ORDER).fillna(0)
    fam_frame = fam.reset_index().rename(columns={"family_label": "Factor", "share": "Share"})
    fam_frame = fam_frame.sort_values("Share")
    left, right = st.columns([2, 3])
    with left:
        fig = px.bar(fam_frame, x="Share", y="Factor", orientation="h", color_discrete_sequence=[RUST],
                     labels={"Share": "Share of explained variation", "Factor": ""})
        fig.update_traces(hovertemplate="%{y}: %{x:.0%}<extra></extra>", texttemplate="%{x:.0%}", textposition="outside",
                          textfont_color=MUTED)
        fig.update_layout(height=340, margin={"l": 10, "r": 40, "t": 10, "b": 10}, xaxis_tickformat=".0%",
                          xaxis_range=[0, float(fam_frame["Share"].max()) * 1.25], **CHART)
        st.plotly_chart(fig, width="stretch")
        st.caption(f"Mean |SHAP| of the {families[families['dish'] == dish]['model'].iloc[0].lower()} model, summed by "
                   "factor family. Shows what the model leans on, not what sets the price.")
    with right:
        top = features[(features["dish"] == dish) & (features["mean_abs_shap"] > 0)].head(12).copy()
        top["Feature"] = top["feature"].map(pretty_feature)

        def direction(row: pd.Series) -> str:
            value = row["effect_pct_or_sign"]
            if pd.isna(value):
                return "mixed"
            if row["binary"]:
                return f"{value:+.0f}%"
            return "higher" if value > 0 else "lower" if value < 0 else "flat"

        top["Associated price"] = top.apply(direction, axis=1)
        top["Share of restaurants"] = top["prevalence"].map(lambda v: "—" if pd.isna(v) else f"{100 * v:.0f}%")
        st.dataframe(
            top[["Feature", "Associated price", "Share of restaurants", "mean_abs_shap"]].rename(
                columns={"mean_abs_shap": "Importance"}),
            hide_index=True,
            width="stretch",
            height=340,
            column_config={
                "Importance": st.column_config.ProgressColumn(format="%.3f", min_value=0,
                                                              max_value=float(top["mean_abs_shap"].max() or 1)),
            },
        )
        st.caption("For yes/no features: average model-predicted price difference when present vs absent. "
                   "For numbers (rating, menu size): whether higher values go with higher or lower prices.")

    with st.expander("Model comparison (grouped 5-fold CV by chain)"):
        show = dish_metrics[["model", "mae", "rmse", "r2", "r2_log"]].rename(columns={
            "model": "Model", "mae": "MAE (₹)", "rmse": "RMSE (₹)", "r2": "R² (₹)", "r2_log": "R² (log)"})
        st.dataframe(show, hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.2f") for c in show.columns[1:]})
        st.caption("Folds are grouped by restaurant brand, so a chain's outlets are never split between train and test.")

    # 7. Context.
    st.subheader("Raw-material context")
    st.info(
        "Not available yet. Commodity prices (data.gov.in / Agmarknet) are in the plan but have not been collected, so "
        "there is no estimated raw-material cost to set beside the menu price.",
        icon="ℹ️",
    )

    st.divider()
    st.header("Across all 20 dishes")
    assoc = tables["price_driver_associations"]
    assoc = assoc[assoc["family"].isin(["ingredient", "technique", "descriptor"]) & assoc["binary"]]
    assoc = assoc[assoc["rows_with_feature"] >= 30].sort_values("pct")
    assoc["Feature"] = assoc["feature"].map(pretty_feature)
    assoc["significant"] = assoc["p_value"] < 0.05
    forest = go.Figure()
    forest.add_vline(x=0, line_color=MUTED, line_width=1)
    for sig, color, name in ((True, RUST, "p < 0.05"), (False, "#A8A29E", "not significant")):
        part = assoc[assoc["significant"] == sig]
        forest.add_trace(go.Scatter(
            x=part["pct"], y=part["Feature"], mode="markers", name=name,
            marker={"size": 10, "color": color, "line": {"width": 2, "color": CHART["paper_bgcolor"]}},
            error_x={"type": "data", "symmetric": False, "array": part["pct_high"] - part["pct"],
                     "arrayminus": part["pct"] - part["pct_low"], "color": color, "thickness": 1.5, "width": 0},
            customdata=np.stack([part["pct_low"], part["pct_high"], part["rows_with_feature"]], axis=-1),
            hovertemplate="%{y}<br>%{x:+.1f}% (95% CI %{customdata[0]:+.1f} to %{customdata[1]:+.1f})"
                          "<br>%{customdata[2]} observations<extra></extra>",
        ))
    forest.update_layout(height=max(360, 24 * len(assoc) + 80), margin={"l": 10, "r": 10, "t": 30, "b": 10},
                         xaxis_title="% difference in estimated price when the word is on the menu",
                         yaxis={"categoryorder": "array", "categoryarray": assoc["Feature"].tolist()},
                         legend={"orientation": "h", "y": 1.04}, **CHART)
    st.plotly_chart(forest, width="stretch")
    st.caption(
        "Pooled regression of log estimated price on all features with dish fixed effects; standard errors clustered by "
        "brand. Features on at least 30 observations. A word that restaurants use in their menu copy is a marker of the "
        "kind of restaurant, which is why it moves the estimate."
    )

    st.subheader("How good is the estimate? Check against observed add-on prices")
    rows = tables["addon_model_rows"]
    fig = px.scatter(rows, x="cost_for_two", y="observed_addon_price", log_x=True, log_y=True,
                     hover_name="dish_name", hover_data={"locality_name": True},
                     labels={"cost_for_two": "Restaurant cost for two (₹)", "observed_addon_price": "Observed item price (₹)"},
                     color_discrete_sequence=[TEAL], opacity=0.55)
    xs = np.array([rows["cost_for_two"].min(), rows["cost_for_two"].max()])
    centre_x = np.exp(np.log(rows["cost_for_two"]).mean())
    centre_y = np.exp(np.log(rows["observed_addon_price"]).mean())
    fig.add_trace(go.Scatter(x=xs, y=centre_y * (xs / centre_x) ** addon["elasticity"], mode="lines",
                             name=f"Fitted slope {addon['elasticity']:.2f}", line={"color": RUST, "width": 2}))
    fig.add_trace(go.Scatter(x=xs, y=centre_y * (xs / centre_x), mode="lines", name="Slope the estimate assumes (1.0)",
                             line={"color": MUTED, "width": 2, "dash": "dot"}))
    fig.update_traces(selector={"mode": "markers"}, marker={"size": 8})
    fig.update_layout(height=380, margin={"l": 10, "r": 10, "t": 10, "b": 10},
                      legend={"orientation": "h", "y": 1.08},
                      xaxis={"tickvals": [100, 200, 500, 1000, 2000, 5000]},
                      yaxis={"tickvals": [10, 20, 50, 100, 200, 500, 1000]}, **CHART)
    st.plotly_chart(fig, width="stretch")
    st.markdown(
        f"{int(addon['rows']):,} real item prices ({int(addon['items'])} items such as butter naan, cold coffee and "
        f"gulab jamun, at {int(addon['restaurants'])} restaurants) were recovered from add-on menu groups. Holding the "
        f"item fixed, a 10% higher cost for two goes with about **{100 * (1.1 ** addon['elasticity'] - 1):.1f}%** higher "
        f"item price (elasticity {addon['elasticity']:.2f}, 95% CI {addon['elasticity_low']:.2f}–"
        f"{addon['elasticity_high']:.2f}). The estimate assumes 10%. So real prices do rise with restaurant cost, but "
        "the estimate exaggerates how far apart cheap and expensive restaurants are. Rankings hold up better than rupee gaps."
    )

    with st.expander("Dish selection"):
        sel = selection[["label", "restaurants", "localities", "menu_rows", "modal_role", "reason"]].rename(columns={
            "label": "Dish", "restaurants": "Restaurants", "localities": "Localities", "menu_rows": "Menu rows",
            "modal_role": "Role", "reason": "Status"})
        st.dataframe(sel, hide_index=True, width="stretch")
        st.caption("Rule: at least 150 restaurants and 40 localities, then the 20 largest. Matching rules and aliases "
                   "(murgh makhani = butter chicken, paneer makhani = paneer butter masala, …) are in "
                   "`src/modeling/dishes.py`. Combos and dishes that only contain the target are excluded. "
                   "Full report: `reports/price_drivers_report.md`.")
