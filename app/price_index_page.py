"""Deliverable 3: Gastronomic Price Index."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ingestion.gap_fill import CURRENT_YEAR
from ui import ACCENT, CHART, DATA, delhi_bounds, district_layers, DIVERGING, GREY, map_view, MUTED, SECONDARY, pretty_token

MEASURES = {
    "Cost for two (observed)": ("cost_for_two", 1.0),
    "Estimated main dish": ("estimated_main_price", 0.35),
    "Estimated drink": ("estimated_beverage_price", 0.15),
}
OVERALL = "All cuisines (cuisine-adjusted)"


@st.cache_data(show_spinner=False)
def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    overall = pd.read_parquet(DATA / "gpi_locality.parquet")
    cells = pd.read_parquet(DATA / "gpi_cells.parquet")
    restaurants = pd.read_parquet(DATA / "gpi_restaurants.parquet")
    return overall, cells, restaurants


def _clip_range(values: pd.Series) -> tuple[float, float]:
    """Symmetric range on a log scale around 100, so 50 and 200 sit equally far from the midpoint."""
    finite = values.dropna()
    if finite.empty:
        return 50.0, 200.0
    spread = float(np.nanmax(np.abs(np.log(finite / 100))))
    spread = min(max(spread, np.log(1.25)), np.log(4))
    return 100 * np.exp(-spread), 100 * np.exp(spread)


METHOD = """
- **Cell index**: `GPI[l,c] = median cost for two of cuisine c in locality l ÷ Delhi median for c × 100`.
  A restaurant counts in every cuisine it lists.
- **Overall index**: each restaurant's cost for two is divided by the Delhi median of its *primary* cuisine
  (first listed; cuisines with < 15 restaurants pooled as Other). The locality index is the median of those
  ratios × 100. This compares like with like, so a locality full of sweet shops is not labelled cheap only
  because sweet shops are cheap.
- **Thresholds**: < 5 restaurants suppressed, 5–9 flagged low, 10+ reliable.
- **Intervals**: 2,000 bootstrap resamples of restaurants.
- **Why one index for all price columns**: estimated main = 35% and drink = 15% of cost for two, so the
  ratio is identical. Rupee levels differ and are shown.
- **Two price years**: North, South West, South and North East have almost no restaurants in the 2026
  snapshot, so their localities use a 2021 listing. Each restaurant is compared with the Delhi median of its own
  year, so the index is comparable across years; rupee amounts are not (2021 rupees are lower). A district never
  mixes the two. The 2021 listing has no menus and only well-rated restaurants.
- **Limits**: cost for two is rounded to ₹50/₹100, so medians tie; delivery menus only; locality labels are
  Zomato's, not official boundaries. Full report: `reports/price_index_report.md`.
"""


def render_price_index() -> None:
    overall, cells, restaurants = load()
    current = restaurants[restaurants["price_year"] == CURRENT_YEAR]
    delhi_cost = float(current["cost_for_two"].median())
    older = sorted(overall.loc[overall["price_year"] != CURRENT_YEAR, "locality_name"])

    st.title("Gastronomic Price Index")
    st.caption(
        "Deliverable 3. How expensive each Delhi locality is relative to Delhi, after comparing restaurants with others "
        "of the same cuisine. 100 = Delhi benchmark, 120 = 20% above, 80 = 20% below. Unit: the restaurant."
    )

    controls = st.columns([2.2, 2.2, 1.5, 1.5], vertical_alignment="bottom")
    cuisine_options = [OVERALL] + sorted(cells["cuisine"].unique(), key=pretty_token)
    cuisine = controls[0].selectbox("Cuisine", cuisine_options, format_func=lambda c: c if c == OVERALL else pretty_token(c))
    measure = controls[1].selectbox("Show rupee levels as", list(MEASURES), help=(
        "The index is the same for all three: estimated main and drink prices are fixed shares of cost for two, "
        "and the share cancels in the ratio. Only the rupee columns change."))
    show_low = controls[2].toggle("Include low-sample", value=True, key="gpi_low_sample",
                                  help="Localities or cells with 5–9 restaurants.")
    adjusted = controls[3].toggle("Cuisine-adjusted", value=True, disabled=cuisine != OVERALL, key="gpi_adjusted",
                                  help="Off shows the raw index: locality median ÷ Delhi median, ignoring cuisine mix.")
    column, share = MEASURES[measure]

    if cuisine == OVERALL:
        view = overall.copy()
        value_col = "gpi" if adjusted else "gpi_unadjusted"
        low_col, high_col = ("gpi_low", "gpi_high") if adjusted else ("gpi_unadjusted_low", "gpi_unadjusted_high")
        view["index"] = view[value_col]
        view["low"] = view[low_col]
        view["high"] = view[high_col]
        view["median_level"] = share * view["median_cost_for_two"]
        benchmark_level = share * delhi_cost
    else:
        view = cells[cells["cuisine"] == cuisine].merge(
            overall[["locality_id", "latitude", "longitude"]], on="locality_id", how="left"
        )
        view["index"] = view["gpi"]
        view["low"] = view["gpi_low"]
        view["high"] = view["gpi_high"]
        view["median_level"] = share * view["median_cost_for_two"]
        now = view[view["price_year"] == CURRENT_YEAR]
        benchmark_level = share * float(now["delhi_median_cost_for_two"].iloc[0]) if len(now) else np.nan

    allowed = {"reliable", "low"} if show_low else {"reliable"}
    shown = view[view["reliability"].isin(allowed) & view["index"].notna()].copy()
    suppressed = int((view["reliability"] == "suppressed").sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Localities shown", f"{len(shown)}", help=f"{suppressed} suppressed (fewer than 5 restaurants).")
    m2.metric(f"Delhi benchmark · {measure.split(' (')[0].lower()}", f"₹{benchmark_level:,.0f}",
              help=("2026 median. Localities marked 2021 in the table use 2021 prices and are compared with the "
                    "Delhi median of 2021, so their index is comparable but their rupee amounts are not.") if older else None)
    if len(shown):
        reliable = shown[shown["reliability"] == "reliable"]
        pool = reliable if len(reliable) else shown
        top = pool.sort_values("index").iloc[-1]
        bottom = pool.sort_values("index").iloc[0]
        tag = "reliable" if len(reliable) else "low sample"
        m3.metric(f"Most expensive ({tag}) · GPI {top['index']:.0f}", top["locality_name"])
        m4.metric(f"Least expensive ({tag}) · GPI {bottom['index']:.0f}", bottom["locality_name"])

    if shown.empty:
        st.info("No locality has enough restaurants for this cuisine. Try another cuisine or include low-sample cells.")
        st.stop()

    lo, hi = _clip_range(shown["index"])
    shown["log_index"] = np.log(shown["index"].clip(lo, hi) / 100)
    shown["label"] = shown["reliability"].map({"reliable": "", "low": " (low sample)"})
    shown["prices"] = shown["price_year"].astype(str)
    shown["ci"] = shown.apply(
        lambda r: f"{r['low']:.0f}–{r['high']:.0f}" if pd.notna(r["low"]) else "n/a", axis=1
    )

    # Localities without an index (too few restaurants, or hidden by the low-sample toggle) stay on the map as grey
    # dots, so the map shows where the data is thin instead of silently dropping it.
    hidden = view[~view.index.isin(shown.index) & view["latitude"].notna()].copy()

    map_col, table_col = st.columns([3, 2])
    with map_col:
        head = st.columns([1, 1.7], vertical_alignment="center")
        head[0].subheader("Map")
        view_mode = head[1].segmented_control(
            "Map view", ["All Delhi", "Zoom to data"], default="All Delhi", required=True,
            label_visibility="collapsed", key="gpi_map_view",
        )
        if view_mode == "All Delhi":
            frame = map_view(delhi_bounds(), width_px=420, height_px=560)
            size_max = 20
        else:
            points = pd.concat([shown[["latitude", "longitude"]], hidden[["latitude", "longitude"]]])
            frame = map_view(
                (points["longitude"].min(), points["latitude"].min(), points["longitude"].max(), points["latitude"].max()),
                width_px=420, height_px=560, pad=1.5,
            )
            size_max = 32
        figure = px.scatter_map(
            shown,
            lat="latitude",
            lon="longitude",
            color="log_index",
            size="restaurants",
            size_max=size_max,
            color_continuous_scale=DIVERGING,
            range_color=(np.log(lo / 100), np.log(hi / 100)),
            hover_name="locality_name",
            custom_data=["index", "ci", "restaurants", "median_level", "reliability", "prices"],
            zoom=frame["zoom"],
            center=frame["center"],
            map_style="white-bg",
            height=560,
        )
        figure.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br>GPI %{customdata[0]:.0f} (95% CI %{customdata[1]})<br>"
                "Restaurants %{customdata[2]} · %{customdata[4]}<br>Median ₹%{customdata[3]:,.0f} (%{customdata[5]} prices)<extra></extra>"
            ),
            marker={"opacity": 0.85},
        )
        if not hidden.empty:
            grey = go.Scattermap(
                lat=hidden["latitude"], lon=hidden["longitude"], mode="markers",
                marker={"size": 8, "color": GREY, "opacity": 0.75},
                text=hidden["locality_name"], customdata=hidden[["restaurants", "reliability"]],
                hovertemplate="<b>%{text}</b><br>No index shown: %{customdata[0]} restaurants "
                              "(%{customdata[1]})<extra></extra>",
                showlegend=False,
            )
            figure.add_trace(grey)
            figure.data = figure.data[-1:] + figure.data[:-1]  # draw grey dots underneath the coloured ones
        ticks = [t for t in (25, 50, 67, 80, 100, 125, 150, 200, 300, 400) if lo <= t <= hi]
        figure.update_layout(
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
            map_layers=district_layers(),
            coloraxis_colorbar={"title": "GPI", "tickvals": [np.log(t / 100) for t in ticks], "ticktext": [str(t) for t in ticks]},
            paper_bgcolor=CHART["paper_bgcolor"],
        )
        st.plotly_chart(figure, width="stretch")
        st.caption(
            f"Coloured dots have an index. The {len(hidden)} grey dots are localities with too few restaurants for one. "
"Localities in North, South West, South and North East use 2021 prices, because the 2026 snapshot has too few "
            "restaurants there; each locality is compared with the Delhi median of its own year, so the index is "
            "comparable but the rupee amounts are not. Dots sit at the mean restaurant position for each locality label "
            "and are sized by restaurant count. Localities have no official boundaries, so none are drawn. Colour is on "
            "a log scale: 50 and 200 are equally far from 100."
        )

    with table_col:
        st.subheader("Locality comparison")
        table = shown.sort_values("index", ascending=False)[
            ["locality_name", "index", "ci", "restaurants", "reliability", "median_level", "prices"]
        ].rename(columns={
            "locality_name": "Locality", "index": "GPI", "ci": "95% CI", "restaurants": "Restaurants",
            "reliability": "Sample", "median_level": f"Median ₹ ({measure.split(' (')[0].lower()})",
            "prices": "Prices",
        })
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            height=560,
            column_config={
                "GPI": st.column_config.ProgressColumn(format="%.0f", min_value=0, max_value=float(max(200, table["GPI"].max()))),
                table.columns[-2]: st.column_config.NumberColumn(format="₹%.0f"),
                "Prices": st.column_config.TextColumn(width="small", help="Year of the prices behind the row."),
            },
        )

    st.subheader("Cuisine × locality")
    st.caption("GPI for each cuisine within each locality (plan formula: local median ÷ Delhi median × 100). "
               "Blank = fewer than 5 restaurants of that cuisine. Rows are the localities in the table above, "
               "columns are the cuisines with the most localities that have an index.")
    ranked_cuisines = (
        cells[cells["reliability"] != "suppressed"].groupby("cuisine").size().sort_values(ascending=False).index
    )
    n_cuisines = st.slider("Cuisines shown", min_value=4, max_value=len(ranked_cuisines),
                           value=min(12, len(ranked_cuisines)), key="gpi_heat_cuisines")
    heat_localities = (
        overall[overall["reliability"].isin(allowed) & overall["gpi"].notna()].sort_values("gpi", ascending=False)["locality_name"]
    )
    top_cuisines = ranked_cuisines[:n_cuisines]
    heat = cells[cells["cuisine"].isin(top_cuisines) & cells["locality_name"].isin(heat_localities)]
    if not show_low:
        heat = heat[heat["reliability"] == "reliable"]
    grid = heat.pivot_table(index="locality_name", columns="cuisine", values="gpi").reindex(
        index=heat_localities, columns=top_cuisines
    )
    counts = heat.pivot_table(index="locality_name", columns="cuisine", values="restaurants").reindex_like(grid)
    heat_lo, heat_hi = _clip_range(pd.Series(grid.to_numpy().ravel()))
    z = np.log(grid.clip(heat_lo, heat_hi) / 100)
    text = grid.map(lambda v: "" if pd.isna(v) else f"{v:.0f}")
    heatmap = go.Figure(
        go.Heatmap(
            z=z.to_numpy(),
            x=[pretty_token(c) for c in grid.columns],
            y=grid.index.tolist(),
            text=text.to_numpy(),
            texttemplate="%{text}",
            customdata=np.dstack([grid.to_numpy(), counts.to_numpy()]),
            hovertemplate="%{y} · %{x}<br>GPI %{customdata[0]:.0f}<br>%{customdata[1]:.0f} restaurants<extra></extra>",
            colorscale=DIVERGING,
            zmid=0,
            zmin=np.log(heat_lo / 100),
            zmax=np.log(heat_hi / 100),
            showscale=False,
            xgap=2,
            ygap=2,
        )
    )
    heatmap.update_layout(height=max(360, 26 * len(grid) + 80), margin={"l": 10, "r": 10, "t": 10, "b": 10},
                          yaxis={"autorange": "reversed"}, **CHART)
    st.plotly_chart(heatmap, width="stretch")

    st.subheader("Price distribution")
    st.caption("The index is a median. These are the restaurant prices behind it, so the spread is not hidden. "
               "Each dot is a restaurant; the dotted line is the Delhi median.")
    default = shown.sort_values("restaurants", ascending=False)["locality_name"].head(8).tolist()
    picked = st.multiselect("Localities", sorted(shown["locality_name"]), default=default)
    dist = restaurants[restaurants["locality_name"].isin(picked)].copy()
    if cuisine != OVERALL:
        dist = dist[dist["canonical_cuisines"].fillna("").str.split(" | ", regex=False).map(lambda ts: cuisine in ts)]
    if dist.empty:
        st.info("Pick at least one locality.")
    else:
        order = dist.groupby("locality_name")[column].median().sort_values(ascending=False).index.tolist()
        box = px.box(
            dist,
            x=column,
            y="locality_name",
            points="all",
            category_orders={"locality_name": order},
            hover_data={"name": True, "primary_cuisine": True, column: ":,.0f", "locality_name": False},
            labels={column: f"{measure} (₹, log scale)", "locality_name": ""},
            color_discrete_sequence=[ACCENT],
            log_x=True,
        )
        box.add_vline(x=benchmark_level, line_dash="dot", line_color=MUTED,
                      annotation_text="Delhi median", annotation_font_color=MUTED)
        box.update_traces(marker={"size": 6, "opacity": 0.55}, line={"width": 1.5}, pointpos=0, jitter=0.4,
                          fillcolor="rgba(154,52,18,0.12)")
        box.update_layout(height=max(320, 48 * len(order) + 80), margin={"l": 10, "r": 10, "t": 30, "b": 10},
                          showlegend=False, xaxis={"tickvals": [15, 30, 50, 100, 200, 500, 1000, 2000, 5000]}, **CHART)
        st.plotly_chart(box, width="stretch")

    with st.expander("Robustness checks"):
        checks = overall[overall["reliability"] != "suppressed"].copy()
        left, middle, right = st.columns(3)
        pairs = [
            (left, "gpi_unadjusted", "Raw index (no cuisine adjustment)"),
            (middle, "gpi_hedonic", "Hedonic index (regression)"),
            (right, "addon_index", "Observed add-on price index"),
        ]
        for slot, other, label in pairs:
            data = checks.dropna(subset=["gpi", other])
            rho = data[["gpi", other]].corr(method="spearman").iloc[0, 1] if len(data) > 2 else np.nan
            fig = px.scatter(data, x="gpi", y=other, hover_name="locality_name", log_x=True, log_y=True,
                             labels={"gpi": "Cuisine-adjusted GPI", other: label}, color_discrete_sequence=[SECONDARY])
            fig.add_shape(type="line", x0=data["gpi"].min(), y0=data["gpi"].min(), x1=data["gpi"].max(),
                          y1=data["gpi"].max(), line={"dash": "dot", "color": MUTED, "width": 1})
            fig.update_traces(marker={"size": 9, "line": {"width": 2, "color": CHART["paper_bgcolor"]}})
            fig.update_xaxes(tickvals=[50, 100, 200, 400])
            fig.update_yaxes(tickvals=[50, 100, 200, 400])
            fig.update_layout(height=300, margin={"l": 10, "r": 10, "t": 30, "b": 10},
                              title={"text": f"{label}<br><sup>Spearman ρ = {rho:.2f}, n = {len(data)}</sup>", "font": {"size": 13}},
                              **CHART)
            slot.plotly_chart(fig, width="stretch")
        st.caption(
            "Hedonic: log cost for two regressed on locality and primary-cuisine dummies. Add-on: real item prices "
            "(butter naan, cold coffee, …) recovered from 'add on' and 'best paired with' menu groups, each divided by "
            "that item's Delhi median; only localities with 5+ such restaurants."
        )

    with st.expander("Method"):
        st.markdown(METHOD)
