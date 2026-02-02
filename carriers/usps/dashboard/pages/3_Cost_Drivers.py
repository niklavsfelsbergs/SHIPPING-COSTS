"""
Page 3: Cost Drivers
====================

Understand what drives costs: surcharge frequency, dimensional analysis,
geography, and weight patterns.
"""

import polars as pl
import streamlit as st
import plotly.graph_objects as go
import numpy as np

from carriers.usps.dashboard.data import (
    init_page,
    get_filtered_shipments,
    apply_chart_layout,
    drilldown_section,
    format_currency,
)

st.set_page_config(page_title="Cost Drivers | USPS", layout="wide")
st.title("Cost Drivers")

# ---------------------------------------------------------------------------
prepared_df, match_data, _ = init_page()
df = get_filtered_shipments()

if len(df) == 0:
    st.warning("No data matches current filters.")
    st.stop()


# ===========================================================================
# SECTION A - Surcharge Frequency & Cost Impact
# ===========================================================================

st.header("A. Surcharge Frequency & Cost Impact")

# Calculate surcharge stats
surcharge_stats = []
surcharges = [
    ("surcharge_nsl1", "cost_nsl1", "NSL1", "Nonstandard Length 22-30\""),
    ("surcharge_nsl2", "cost_nsl2", "NSL2", "Nonstandard Length >30\""),
    ("surcharge_nsv", "cost_nsv", "NSV", "Nonstandard Volume >2 cu ft"),
    ("surcharge_peak", "cost_peak", "Peak", "Peak Season Surcharge"),
]

total_shipments = len(df)
for flag_col, cost_col, label, description in surcharges:
    if flag_col in df.columns and cost_col in df.columns:
        triggered = df[flag_col].fill_null(False).sum()
        cost_total = df[cost_col].fill_null(0).sum()
        surcharge_stats.append({
            "Surcharge": label,
            "Description": description,
            "Triggered": int(triggered),
            "% of Shipments": triggered / total_shipments * 100 if total_shipments > 0 else 0,
            "Total Cost": float(cost_total),
        })

if surcharge_stats:
    left, right = st.columns(2)

    with left:
        st.markdown("**Surcharge Trigger Rate**")
        stats_df = pl.DataFrame(surcharge_stats).sort("% of Shipments", descending=False)
        x_vals = stats_df["% of Shipments"].to_list()
        triggered_vals = stats_df["Triggered"].to_list()
        max_val = max(x_vals) if x_vals else 0
        fig1 = go.Figure(go.Bar(
            x=x_vals,
            y=stats_df["Surcharge"].to_list(),
            orientation="h",
            marker_color="#3498db",
            text=[f"{v:.1f}%" for v in x_vals],
            textposition="outside",
            cliponaxis=False,
            customdata=triggered_vals,
            hovertemplate="%{y}: %{x:.1f}%<br>Triggered: %{customdata:,} / " + f"{total_shipments:,}<extra></extra>",
        ))
        fig1.update_layout(
            title="% of Shipments Triggering Each Surcharge",
            xaxis_title="% of Shipments",
            yaxis_title="Surcharge",
            height=300,
            xaxis=dict(range=[0, max_val * 1.25] if max_val else None),
        )
        apply_chart_layout(fig1)
        st.plotly_chart(fig1, use_container_width=True)

    with right:
        st.markdown("**Surcharge Cost Impact**")
        stats_df = pl.DataFrame(surcharge_stats).sort("Total Cost", descending=False)
        x_vals = stats_df["Total Cost"].to_list()
        triggered_vals = stats_df["Triggered"].to_list()
        max_val = max(x_vals) if x_vals else 0
        fig2 = go.Figure(go.Bar(
            x=x_vals,
            y=stats_df["Surcharge"].to_list(),
            orientation="h",
            marker_color="#e74c3c",
            text=[format_currency(v) for v in x_vals],
            textposition="outside",
            cliponaxis=False,
            customdata=triggered_vals,
            hovertemplate="%{y}: %{x:$,.2f}<br>Shipments: %{customdata:,}<extra></extra>",
        ))
        fig2.update_layout(
            title="Total Cost by Surcharge Type",
            xaxis_title="Total Cost ($)",
            yaxis_title="Surcharge",
            xaxis_tickprefix="$",
            height=300,
            xaxis=dict(range=[0, max_val * 1.3] if max_val else None),
        )
        apply_chart_layout(fig2)
        st.plotly_chart(fig2, use_container_width=True)

    # Summary table
    st.markdown("**Surcharge Summary**")
    display_stats = pl.DataFrame(surcharge_stats).with_columns([
        pl.col("% of Shipments").map_elements(lambda v: f"{v:.2f}%", return_dtype=pl.Utf8),
        pl.col("Total Cost").map_elements(format_currency, return_dtype=pl.Utf8),
    ])
    st.dataframe(display_stats, use_container_width=True, hide_index=True)

    # Surcharge trend over time
    st.markdown("**Surcharge Trigger Rate Over Time**")
    date_col = "ship_date"
    time_grain = st.session_state.get("sidebar_time_grain", "Weekly")
    truncate_map = {"Daily": "1d", "Weekly": "1w", "Monthly": "1mo"}
    truncate_unit = truncate_map[time_grain]

    selected_surcharges = st.multiselect(
        "Select surcharges to plot",
        ["NSL1", "NSL2", "NSV", "Peak"],
        default=["NSL1", "NSL2"],
        key="surcharge_trend_select",
    )

    if selected_surcharges:
        trend_df = (
            df.with_columns(
                pl.col(date_col).cast(pl.Date).dt.truncate(truncate_unit).alias("period")
            )
            .group_by("period")
            .agg([
                pl.len().alias("total"),
                pl.col("surcharge_nsl1").fill_null(False).sum().alias("NSL1"),
                pl.col("surcharge_nsl2").fill_null(False).sum().alias("NSL2"),
                pl.col("surcharge_nsv").fill_null(False).sum().alias("NSV"),
                pl.col("surcharge_peak").fill_null(False).sum().alias("Peak"),
            ])
            .sort("period")
        )

        if len(trend_df) > 0:
            trend_pd = trend_df.to_pandas()
            fig_trend = go.Figure()
            colors = {"NSL1": "#3498db", "NSL2": "#e74c3c", "NSV": "#27ae60", "Peak": "#f39c12"}
            for surcharge in selected_surcharges:
                rate = trend_pd[surcharge] / trend_pd["total"] * 100
                fig_trend.add_trace(go.Scatter(
                    x=trend_pd["period"],
                    y=rate,
                    name=surcharge,
                    line=dict(color=colors.get(surcharge, "#333"), width=2),
                    customdata=np.column_stack([trend_pd[surcharge], trend_pd["total"]]),
                    hovertemplate=f"{surcharge}: %{{y:.1f}}%<br>Triggered: %{{customdata[0]:,}} / %{{customdata[1]:,}}<extra></extra>",
                ))
            fig_trend.update_layout(
                title=f"Surcharge Trigger Rate Over Time ({time_grain})",
                xaxis_title="Period",
                yaxis_title="% of Shipments",
                yaxis_ticksuffix="%",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            )
            apply_chart_layout(fig_trend)
            st.plotly_chart(fig_trend, use_container_width=True)

st.markdown("---")


# ===========================================================================
# SECTION B - Dimensional Analysis
# ===========================================================================

st.header("B. Dimensional Analysis")
st.caption(
    "USPS thresholds: NSL1 triggers at longest > 22\", NSL2 at longest > 30\", "
    "NSV triggers at cubic > 3,456 cu in (2 cu ft)."
)

# Scatter plot: longest vs second longest
if "longest_side_in" in df.columns and "second_longest_in" in df.columns:
    st.markdown("**Longest vs Second Longest Dimension**")

    # Sample if too many points
    plot_df = df.select([
        "pcs_orderid", "longest_side_in", "second_longest_in",
        "surcharge_nsl1", "surcharge_nsl2", "surcharge_nsv"
    ]).drop_nulls()

    if len(plot_df) > 5000:
        plot_df = plot_df.sample(5000)

    # Assign colors based on surcharges
    def _get_category(row):
        if row["surcharge_nsl2"]:
            return "NSL2"
        elif row["surcharge_nsl1"]:
            return "NSL1"
        elif row["surcharge_nsv"]:
            return "NSV"
        else:
            return "None"

    plot_pd = plot_df.to_pandas()
    plot_pd["category"] = plot_pd.apply(_get_category, axis=1)

    colors_map = {"None": "rgba(150,150,150,0.3)", "NSL1": "#f39c12", "NSL2": "#e74c3c", "NSV": "#27ae60"}

    fig_dim = go.Figure()

    # Plot each category
    for cat in ["None", "NSV", "NSL1", "NSL2"]:
        cat_df = plot_pd[plot_pd["category"] == cat]
        if len(cat_df) > 0:
            fig_dim.add_trace(go.Scattergl(
                x=cat_df["longest_side_in"],
                y=cat_df["second_longest_in"],
                mode="markers",
                marker=dict(color=colors_map[cat], size=6),
                name=f"{cat} ({len(cat_df):,})",
                hovertemplate="Longest: %{x:.1f}\"<br>2nd Longest: %{y:.1f}\"<extra></extra>",
            ))

    # Add threshold lines
    fig_dim.add_vline(x=22, line_dash="dash", line_color="#f39c12", annotation_text="22\" (NSL1)")
    fig_dim.add_vline(x=30, line_dash="dash", line_color="#e74c3c", annotation_text="30\" (NSL2)")

    fig_dim.update_layout(
        title="Package Dimensions by Surcharge Category",
        xaxis_title="Longest Side (inches)",
        yaxis_title="Second Longest Side (inches)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    apply_chart_layout(fig_dim)
    st.plotly_chart(fig_dim, use_container_width=True)

    # Threshold proximity analysis
    st.markdown("**Threshold Proximity Analysis**")
    st.caption("Packages near dimensional thresholds may have measurement variability.")

    thresholds = [
        ("22\" (NSL1)", "longest_side_in", 22),
        ("30\" (NSL2)", "longest_side_in", 30),
    ]

    proximity_rows = []
    for label, col, threshold in thresholds:
        if col in df.columns:
            vals = df[col].drop_nulls()
            within_1 = int(((vals >= threshold - 1) & (vals < threshold)).sum())
            within_2 = int(((vals >= threshold - 2) & (vals < threshold)).sum())
            within_5 = int(((vals >= threshold - 5) & (vals < threshold)).sum())
            proximity_rows.append({
                "Threshold": label,
                "Within 1\"": within_1,
                "Within 2\"": within_2,
                "Within 5\"": within_5,
            })

    if proximity_rows:
        st.dataframe(pl.DataFrame(proximity_rows), use_container_width=True, hide_index=True)

st.markdown("---")


# ===========================================================================
# SECTION C - Zone & Geography
# ===========================================================================

st.header("C. Zone & Geography")

left, right = st.columns(2)

with left:
    st.markdown("**Top 20 States by Volume**")
    state_counts = (
        df.group_by("shipping_region")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
        .head(20)
    )
    if len(state_counts) > 0:
        sc_pd = state_counts.to_pandas()
        x_vals = sc_pd["count"].tolist()
        max_val = max(x_vals) if x_vals else 0
        fig_state = go.Figure(go.Bar(
            y=sc_pd["shipping_region"],
            x=x_vals,
            orientation="h",
            marker_color="#3498db",
            text=[f"{v:,}" for v in x_vals],
            textposition="outside",
            cliponaxis=False,
        ))
        fig_state.update_layout(
            title="Shipments by State",
            xaxis_title="Shipments",
            yaxis_title="State",
            yaxis=dict(autorange="reversed"),
            height=600,
            xaxis=dict(range=[0, max_val * 1.2] if max_val else None),
        )
        apply_chart_layout(fig_state)
        st.plotly_chart(fig_state, use_container_width=True)

with right:
    st.markdown("**Average Cost per Shipment by Zone**")
    zone_costs = (
        df.group_by("shipping_zone")
        .agg([
            pl.len().alias("count"),
            pl.col("cost_total").mean().alias("avg_expected"),
            pl.col("actual_total").mean().alias("avg_actual"),
        ])
        .sort("shipping_zone")
    )
    if len(zone_costs) > 0:
        zc_pd = zone_costs.to_pandas()
        fig_zone = go.Figure()
        fig_zone.add_trace(go.Bar(
            x=zc_pd["shipping_zone"].astype(str),
            y=zc_pd["avg_expected"],
            name="Expected",
            marker_color="#3498db",
            customdata=zc_pd["count"],
            hovertemplate="Zone %{x}<br>Expected: $%{y:.2f}<br>Shipments: %{customdata:,}<extra></extra>",
        ))
        fig_zone.add_trace(go.Bar(
            x=zc_pd["shipping_zone"].astype(str),
            y=zc_pd["avg_actual"],
            name="Actual",
            marker_color="#e74c3c",
            customdata=zc_pd["count"],
            hovertemplate="Zone %{x}<br>Actual: $%{y:.2f}<br>Shipments: %{customdata:,}<extra></extra>",
        ))
        fig_zone.update_layout(
            barmode="group",
            title="Average Cost by Zone",
            xaxis_title="Zone",
            yaxis_title="Avg Cost ($)",
            yaxis_tickprefix="$",
        )
        apply_chart_layout(fig_zone)
        st.plotly_chart(fig_zone, use_container_width=True)

# Zone distribution by production site
st.markdown("**Zone Distribution by Production Site**")
sites = sorted(df["production_site"].drop_nulls().unique().to_list())

if len(sites) > 0:
    cols = st.columns(len(sites))
    for i, site in enumerate(sites):
        with cols[i]:
            site_df = df.filter(pl.col("production_site") == site)
            zone_dist = (
                site_df.group_by("shipping_zone")
                .agg(pl.len().alias("count"))
                .sort("shipping_zone")
            )
            if len(zone_dist) > 0:
                zd_pd = zone_dist.to_pandas()
                total = zd_pd["count"].sum()
                y_vals = (zd_pd["count"] / total * 100).tolist()
                max_val = max(y_vals) if y_vals else 0
                fig_site = go.Figure(go.Bar(
                    x=zd_pd["shipping_zone"].astype(str),
                    y=y_vals,
                    marker_color="#27ae60",
                    text=[f"{v:.1f}%" for v in y_vals],
                    textposition="outside",
                    cliponaxis=False,
                ))
                fig_site.update_layout(
                    title=f"{site}",
                    xaxis_title="Zone",
                    yaxis_title="% of Shipments",
                    yaxis_ticksuffix="%",
                    height=350,
                    yaxis=dict(range=[0, max_val * 1.15] if max_val else None),
                )
                apply_chart_layout(fig_site)
                st.plotly_chart(fig_site, use_container_width=True)

drilldown_section(df, "Geography Data", key_suffix="geo")

st.markdown("---")


# ===========================================================================
# SECTION D - Weight Analysis
# ===========================================================================

st.header("D. Weight Analysis")

left, right = st.columns(2)

with left:
    st.markdown("**Weight Distribution**")
    if "billable_weight_lbs" in df.columns:
        weights = df["billable_weight_lbs"].drop_nulls().cast(pl.Float64).to_numpy()
        if len(weights) > 0:
            fig_weight = go.Figure(go.Histogram(
                x=weights,
                nbinsx=40,
                marker_color="#3498db",
                hovertemplate="Weight: %{x:.1f} lbs<br>Count: %{y:,}<extra></extra>",
            ))
            fig_weight.update_layout(
                title="Billable Weight Distribution",
                xaxis_title="Weight (lbs)",
                yaxis_title="Shipment Count",
            )
            apply_chart_layout(fig_weight)
            st.plotly_chart(fig_weight, use_container_width=True)

with right:
    st.markdown("**DIM Weight Usage**")
    if "uses_dim_weight" in df.columns:
        dim_count = int(df["uses_dim_weight"].fill_null(False).sum())
        actual_count = len(df) - dim_count
        dim_pct = dim_count / len(df) * 100 if len(df) > 0 else 0

        c1, c2 = st.columns(2)
        c1.metric("Using DIM Weight", f"{dim_count:,}")
        c2.metric("% Using DIM", f"{dim_pct:.1f}%")

        if "dim_weight_lbs" in df.columns and "weight_lbs" in df.columns:
            dim_df = df.filter(pl.col("uses_dim_weight") == True)
            if len(dim_df) > 0:
                avg_extra = (dim_df["dim_weight_lbs"] - dim_df["weight_lbs"]).mean()
                st.metric("Avg Extra Weight from DIM", f"{avg_extra:.2f} lbs")

# Weight by zone
st.markdown("**Average Weight by Zone**")
weight_by_zone = (
    df.group_by("shipping_zone")
    .agg([
        pl.col("billable_weight_lbs").mean().alias("avg_weight"),
        pl.len().alias("count"),
    ])
    .sort("shipping_zone")
)
if len(weight_by_zone) > 0:
    wz_pd = weight_by_zone.to_pandas()
    y_vals = wz_pd["avg_weight"].tolist()
    max_val = max(y_vals) if y_vals else 0
    fig_wz = go.Figure(go.Bar(
        x=wz_pd["shipping_zone"].astype(str),
        y=y_vals,
        marker_color="#f39c12",
        text=[f"{v:.2f}" for v in y_vals],
        textposition="outside",
        cliponaxis=False,
        customdata=wz_pd["count"],
        hovertemplate="Zone %{x}<br>Avg Weight: %{y:.2f} lbs<br>Shipments: %{customdata:,}<extra></extra>",
    ))
    fig_wz.update_layout(
        title="Average Billable Weight by Zone",
        xaxis_title="Zone",
        yaxis_title="Avg Weight (lbs)",
        yaxis=dict(range=[0, max_val * 1.15] if max_val else None),
    )
    apply_chart_layout(fig_wz)
    st.plotly_chart(fig_wz, use_container_width=True)

drilldown_section(
    df.filter(pl.col("uses_dim_weight") == True),
    "DIM Weight Shipments",
    key_suffix="dim_weight"
)
