"""
Page 4: Cost Drivers
=====================

Understand what drives shipping costs: service type analysis, surcharge frequency,
dimensional analysis, zone/geography, and weight analysis.
"""

import polars as pl
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

from carriers.fedex.dashboard.data import (
    SURCHARGE_COST_COLS,
    init_page,
    get_filtered_shipments,
    drilldown_section,
    format_currency,
    apply_chart_layout,
)

st.set_page_config(page_title="Cost Drivers | FedEx", layout="wide")
st.title("Cost Drivers")

# ---------------------------------------------------------------------------
prepared_df, match_data, _ = init_page()
df = get_filtered_shipments()

if len(df) == 0:
    st.warning("No data matches current filters.")
    st.stop()

total_shipments = len(df)


# ===========================================================================
# SECTION 0 — Service Type Analysis
# ===========================================================================

st.subheader("Service Type Analysis")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Volume by Service Type**")
    service_volume = (
        df.group_by("service_type")
        .agg([pl.len().alias("Shipments")])
        .sort("Shipments", descending=True)
    )
    if len(service_volume) > 0:
        fig = go.Figure(data=[
            go.Pie(
                labels=service_volume["service_type"].to_list(),
                values=service_volume["Shipments"].to_list(),
                hole=0.4,
            )
        ])
        fig.update_layout(title="Shipment Distribution by Service")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("**Average Cost per Shipment by Service**")
    service_cost = (
        df.group_by("service_type")
        .agg([
            pl.col("cost_total").mean().alias("Avg Expected"),
            pl.col("actual_net_charge").mean().alias("Avg Actual"),
        ])
        .sort("service_type")
    )
    if len(service_cost) > 0:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=service_cost["service_type"].to_list(),
            y=service_cost["Avg Expected"].to_list(),
            name="Expected",
        ))
        fig.add_trace(go.Bar(
            x=service_cost["service_type"].to_list(),
            y=service_cost["Avg Actual"].to_list(),
            name="Actual",
        ))
        fig.update_layout(barmode="group", yaxis_title="Avg Cost ($)", yaxis_tickprefix="$")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")


# ===========================================================================
# SECTION 0B — SmartPost Weight Cliff Analysis
# ===========================================================================

st.subheader("SmartPost Weight Cliff Analysis")
st.caption("Ground Economy (SmartPost) shows significant rate increase at 10 lbs threshold")

smartpost_df = df.filter(pl.col("service_type") == "Ground Economy")
if len(smartpost_df) > 0:
    weight_cost = (
        smartpost_df
        .with_columns([
            (pl.col("billable_weight_lbs").floor()).alias("weight_floor")
        ])
        .filter(pl.col("weight_floor").is_between(5, 15))
        .group_by("weight_floor")
        .agg([
            pl.col("cost_total").mean().alias("Avg Cost"),
            pl.len().alias("Count"),
        ])
        .sort("weight_floor")
    )

    if len(weight_cost) > 0:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=weight_cost["weight_floor"].to_list(),
            y=weight_cost["Avg Cost"].to_list(),
            mode="lines+markers",
            name="Avg Cost",
            line=dict(width=3),
        ))
        fig.add_vline(x=10, line_dash="dash", line_color="red",
                     annotation_text="10 lb threshold")
        fig.update_layout(
            title="Average Cost by Weight (SmartPost Only)",
            xaxis_title="Billable Weight (lbs)",
            yaxis_title="Average Cost ($)",
            yaxis_tickprefix="$",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Calculate rate increase at 10 lbs
        under_10 = weight_cost.filter(pl.col("weight_floor") < 10)
        over_10 = weight_cost.filter(pl.col("weight_floor") >= 10)
        if len(under_10) > 0 and len(over_10) > 0:
            avg_under = under_10["Avg Cost"].mean()
            avg_over = over_10["Avg Cost"].mean()
            increase_pct = ((avg_over - avg_under) / avg_under * 100)
            st.metric(
                "Rate increase at 10 lbs",
                f"{increase_pct:+.1f}%",
                help=f"Average cost under 10 lbs: ${avg_under:.2f}, over 10 lbs: ${avg_over:.2f}"
            )

st.markdown("---")


# ===========================================================================
# SECTION A — Surcharge Frequency & Cost Impact
# ===========================================================================

st.header("A. Surcharge Frequency & Cost Impact")

surcharge_info = [
    ("ahs", "AHS"), ("ahs_weight", "AHS-Weight"), ("oversize", "Oversize"),
    ("das", "DAS"), ("residential", "Residential"),
    ("dem_base", "DEM-Base"), ("dem_ahs", "DEM-AHS"), ("dem_oversize", "DEM-Oversize"),
]

freq_data = []
for key, label in surcharge_info:
    cost_col = f"cost_{key}"
    triggered = int((df[cost_col].fill_null(0) > 0).sum())
    total_cost = float(df[cost_col].fill_null(0).sum())
    freq_data.append({
        "Surcharge": label, "key": key,
        "triggered": triggered,
        "pct": triggered / total_shipments * 100 if total_shipments > 0 else 0,
        "total_cost": total_cost,
    })

left_a, right_a = st.columns(2)

with left_a:
    st.markdown("**Surcharge Trigger Frequency**")
    # Sort by frequency — most common surcharges at the top
    freq_sorted = sorted(freq_data, key=lambda d: d["pct"])
    labels_f = [d["Surcharge"] for d in freq_sorted]
    pcts_f = [d["pct"] for d in freq_sorted]

    max_pct = max(pcts_f) if pcts_f else 0
    fig_f = go.Figure(go.Bar(
        y=labels_f, x=pcts_f,
        orientation="h",
        marker_color="#3498db",
        text=[f"{p:.1f}%" for p in pcts_f],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:.2f}% (%{customdata:,} shipments)<extra></extra>",
        customdata=[d["triggered"] for d in freq_sorted],
    ))
    fig_f.update_layout(
        title="Surcharge Trigger Rate",
        xaxis_title="% of Shipments",
        xaxis=dict(range=[0, max_pct * 1.25]),
        height=400,
        margin=dict(r=60),
    )
    apply_chart_layout(fig_f)
    st.plotly_chart(fig_f, use_container_width=True)

with right_a:
    st.markdown("**Total Cost Impact by Surcharge**")
    # Sort by cost — highest cost impact at the top
    cost_sorted = sorted(freq_data, key=lambda d: d["total_cost"])
    labels_c = [d["Surcharge"] for d in cost_sorted]
    costs_c = [d["total_cost"] for d in cost_sorted]

    max_cost = max(costs_c) if costs_c else 0
    fig_c = go.Figure(go.Bar(
        y=labels_c, x=costs_c,
        orientation="h",
        marker_color="#e74c3c",
        text=[f"${c:,.0f}" for c in costs_c],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: $%{x:,.2f}<extra></extra>",
    ))
    fig_c.update_layout(
        title="Total Cost by Surcharge",
        xaxis_title="Total Cost ($)",
        xaxis=dict(range=[0, max_cost * 1.25], tickprefix="$", tickformat=",.0f"),
        height=400,
        margin=dict(r=80),
    )
    apply_chart_layout(fig_c)
    st.plotly_chart(fig_c, use_container_width=True)

# Weekly surcharge trend
st.markdown("**Weekly Surcharge Trigger Trend**")

selected_surcharges = st.multiselect(
    "Select surcharges to display",
    [d["Surcharge"] for d in freq_data],
    default=["AHS", "AHS-Weight", "DAS", "Residential"],
    key="surcharge_trend_select",
)

color_cycle = ["#e74c3c", "#f39c12", "#3498db", "#27ae60", "#9b59b6",
               "#1abc9c", "#e67e22", "#2980b9", "#8e44ad", "#34495e"]

date_label = st.session_state.get("filter_time_axis", "Invoice Date")
date_col = "invoice_date" if date_label == "Invoice Date" else "ship_date"
time_grain = st.session_state.get("sidebar_time_grain", "Daily")
truncate_map = {"Daily": "1d", "Weekly": "1w", "Monthly": "1mo"}
truncate_unit = truncate_map[time_grain]

fig_st = go.Figure()
for idx, item in enumerate(freq_data):
    if item["Surcharge"] not in selected_surcharges:
        continue
    cost_col = f"cost_{item['key']}"
    weekly = (
        df.with_columns(
            pl.col(date_col).cast(pl.Date).dt.truncate(truncate_unit).alias("period"),
            (pl.col(cost_col).fill_null(0) > 0).alias("triggered"),
        )
        .group_by("period")
        .agg([
            pl.len().alias("total"),
            pl.col("triggered").sum().alias("trig_count"),
        ])
        .with_columns(
            (pl.col("trig_count") / pl.col("total") * 100).alias("rate"),
        )
        .sort("period")
    )
    if len(weekly) > 0:
        w_pd = weekly.to_pandas()
        fig_st.add_trace(go.Scatter(
            x=w_pd["period"], y=w_pd["rate"],
            mode="lines+markers",
            line=dict(color=color_cycle[idx % len(color_cycle)], width=1.5),
            marker=dict(size=4),
            name=item["Surcharge"],
            hovertemplate="%{x|%b %d}: %{y:.1f}%<extra></extra>",
        ))

fig_st.update_layout(
    title=f"{time_grain} Surcharge Frequency",
    yaxis_title="% of Shipments Triggered",
    yaxis_ticksuffix="%",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
apply_chart_layout(fig_st)
st.plotly_chart(fig_st, use_container_width=True)

st.markdown("---")


# ===========================================================================
# SECTION B — Dimensional Analysis
# ===========================================================================

st.header("B. Dimensional Analysis")

st.markdown("**Package Dimension Scatter — Surcharge Boundaries**")

dim_df = df.filter(
    pl.col("longest_side_in").is_not_null() & pl.col("second_longest_in").is_not_null()
)

if len(dim_df) > 0:
    longest = dim_df["longest_side_in"].cast(pl.Float64).to_numpy()
    second = dim_df["second_longest_in"].cast(pl.Float64).to_numpy()

    ahs_flag = dim_df["surcharge_ahs"].fill_null(False).to_numpy()
    ahs_weight_flag = dim_df["surcharge_ahs_weight"].fill_null(False).to_numpy()
    oversize_flag = dim_df["surcharge_oversize"].fill_null(False).to_numpy()

    categories = np.full(len(dim_df), "No dim surcharge", dtype=object)
    categories[ahs_flag] = "AHS"
    categories[ahs_weight_flag] = "AHS-Weight"
    categories[oversize_flag] = "Oversize"

    # Sample if needed
    n = len(longest)
    if n > 5000:
        idx = np.random.choice(n, 5000, replace=False)
        longest_s, second_s, cats_s = longest[idx], second[idx], categories[idx]
    else:
        longest_s, second_s, cats_s = longest, second, categories

    fig_d = go.Figure()

    # Layer order matters: plain packages underneath, surcharges on top and more visible
    trace_config = [
        ("No dim surcharge", "#bdc3c7", 0.15, 3),
        ("AHS",              "#f39c12", 0.6,  5),
        ("AHS-Weight",       "#e67e22", 0.6,  5),
        ("Oversize",         "#e74c3c", 0.7,  6),
    ]
    for cat_name, color, opacity, size in trace_config:
        mask = cats_s == cat_name
        if mask.any():
            fig_d.add_trace(go.Scattergl(
                x=longest_s[mask], y=second_s[mask],
                mode="markers",
                marker=dict(color=color, size=size, opacity=opacity),
                name=cat_name,
                hovertemplate="Longest: %{x:.1f}\"<br>2nd Longest: %{y:.1f}\"<extra></extra>",
            ))

    # Boundary lines — AHS at 30" second longest
    fig_d.add_hline(y=30, line_dash="dash", line_color="#f39c12", line_width=1.5, opacity=0.7)
    fig_d.add_annotation(
        text="<b>AHS</b> (2nd side > 30\")",
        xref="paper", x=0.99, y=30, xanchor="right", yanchor="bottom", yshift=4,
        showarrow=False, font=dict(color="#ffffff", size=10),
        bgcolor="rgba(0,0,0,0.65)",
        bordercolor="#f39c12",
        borderwidth=1,
    )

    # Oversize at 96" longest or 130" length + girth
    fig_d.add_vline(x=96, line_dash="dash", line_color="#e74c3c", line_width=1.5, opacity=0.7)
    fig_d.add_annotation(
        text="<b>Oversize</b> (> 96\")",
        x=96, yref="paper", y=0.99, xanchor="left", yanchor="top", xshift=4,
        showarrow=False, font=dict(color="#ffffff", size=10),
        bgcolor="rgba(0,0,0,0.65)",
        bordercolor="#e74c3c",
        borderwidth=1,
    )

    fig_d.update_layout(
        title="Package Dimensions with Surcharge Boundaries",
        xaxis_title="Longest Side (in)",
        yaxis_title="Second Longest Side (in)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=600,
    )
    apply_chart_layout(fig_d)
    st.plotly_chart(fig_d, use_container_width=True)

    # Threshold proximity
    st.markdown("**Threshold Proximity (Below Surcharge Cutoffs)**")

    thresholds = [
        ("AHS (2nd side)", "second_longest_in", 30),
        ("Oversize (longest side)", "longest_side_in", 96),
    ]

    proximity_rows = []
    for label, col, threshold in thresholds:
        if col not in dim_df.columns:
            continue
        within_1 = dim_df.filter(
            (pl.col(col) >= threshold - 1) & (pl.col(col) < threshold)
        )
        within_2 = dim_df.filter(
            (pl.col(col) >= threshold - 2) & (pl.col(col) < threshold)
        )
        within_5 = dim_df.filter(
            (pl.col(col) >= threshold - 5) & (pl.col(col) < threshold)
        )
        total = len(dim_df)
        proximity_rows.append({
            "Threshold": label,
            "Within 1\"": len(within_1),
            "Within 2\"": len(within_2),
            "Within 5\"": len(within_5),
            "Share of Dim Shipments": (len(within_5) / total * 100) if total else 0,
        })

    if proximity_rows:
        prox_df = pl.DataFrame(proximity_rows)
        prox_display = prox_df.with_columns(
            pl.col("Share of Dim Shipments").map_elements(
                lambda v: f"{v:.1f}%", return_dtype=pl.Utf8
            ).alias("Share of Dim Shipments")
        )
        st.dataframe(prox_display, use_container_width=True, hide_index=True)

        fig_p = go.Figure()
        fig_p.add_trace(go.Bar(
            x=prox_df["Threshold"],
            y=prox_df["Within 1\""],
            name="Within 1\"",
            marker_color="#f39c12",
            text=prox_df["Within 1\""],
            textposition="outside",
            cliponaxis=False,
        ))
        fig_p.add_trace(go.Bar(
            x=prox_df["Threshold"],
            y=prox_df["Within 2\""],
            name="Within 2\"",
            marker_color="#e67e22",
            text=prox_df["Within 2\""],
            textposition="outside",
            cliponaxis=False,
        ))
        fig_p.add_trace(go.Bar(
            x=prox_df["Threshold"],
            y=prox_df["Within 5\""],
            name="Within 5\"",
            marker_color="#e74c3c",
            text=prox_df["Within 5\""],
            textposition="outside",
            cliponaxis=False,
        ))
        max_val = max(prox_df["Within 5\""].max(), 1)
        fig_p.update_layout(
            barmode="group",
            title="Shipments Just Below Surcharge Thresholds",
            yaxis_title="Shipments",
            height=420,
            margin=dict(t=60, b=60, l=40, r=20),
        )
        fig_p.update_yaxes(range=[0, max_val * 1.2], automargin=True)
        apply_chart_layout(fig_p)
        st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.info("No dimensional proximity data available.")
else:
    st.info("No dimensional data available.")

st.markdown("---")


# ===========================================================================
# SECTION C — Zone & Geography
# ===========================================================================

st.header("C. Zone & Geography")

left_c, right_c = st.columns(2)

with left_c:
    st.markdown("**Shipment Volume by State (Top 20)**")
    state_vol = (
        df.group_by("shipping_region")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
        .head(20)
    )
    if len(state_vol) > 0:
        sv_pd = state_vol.to_pandas()
        max_count = sv_pd["count"].max()
        fig_sv = go.Figure(go.Bar(
            y=sv_pd["shipping_region"], x=sv_pd["count"],
            orientation="h",
            marker_color="#3498db",
            text=sv_pd["count"].apply(lambda v: f"{v:,}"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:,} shipments<extra></extra>",
        ))
        fig_sv.update_layout(
            title="Top 20 States by Volume",
            xaxis_title="Shipments",
            xaxis=dict(range=[0, max_count * 1.25]),
            yaxis=dict(autorange="reversed"),
            height=500,
            margin=dict(r=60),
        )
        apply_chart_layout(fig_sv)
        st.plotly_chart(fig_sv, use_container_width=True)

with right_c:
    st.markdown("**Average Cost per Shipment by Zone**")
    zone_avg = (
        df.group_by("shipping_zone")
        .agg([
            pl.col("cost_total").mean().alias("avg_expected"),
            pl.col("actual_net_charge").mean().alias("avg_actual"),
            pl.len().alias("count"),
        ])
        .sort("shipping_zone")
    )
    if len(zone_avg) > 0:
        za_pd = zone_avg.fill_null(0).to_pandas()
        zones = za_pd["shipping_zone"].astype(str).tolist()

        fig_za = go.Figure()
        fig_za.add_trace(go.Bar(
            x=zones, y=za_pd["avg_expected"],
            name="Expected", marker_color="#3498db",
            hovertemplate="Zone %{x}<br>Expected: $%{y:.2f}<extra></extra>",
        ))
        fig_za.add_trace(go.Bar(
            x=zones, y=za_pd["avg_actual"],
            name="Actual", marker_color="#e74c3c",
            hovertemplate="Zone %{x}<br>Actual: $%{y:.2f}<extra></extra>",
        ))
        fig_za.update_layout(
            barmode="group",
            title="Average Cost per Shipment by Zone",
            xaxis_title="Zone",
            yaxis_title="Avg Cost ($)",
            yaxis_tickprefix="$", yaxis_tickformat=",.2f",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            height=500,
        )
        apply_chart_layout(fig_za)
        st.plotly_chart(fig_za, use_container_width=True)

# Zone distribution by origin
st.markdown("**Zone Distribution by Origin**")
origin_zone = (
    df.group_by(["production_site", "shipping_zone"])
    .agg(pl.len().alias("count"))
    .sort(["production_site", "shipping_zone"])
)

sites_list = sorted(df["production_site"].drop_nulls().unique().to_list())
if len(sites_list) >= 1 and len(origin_zone) > 0:
    fig_oz = make_subplots(
        rows=1, cols=max(len(sites_list), 1),
        subplot_titles=sites_list,
        shared_yaxes=True,
    )
    max_zone_count = origin_zone["count"].max()
    for col_idx, site in enumerate(sites_list, 1):
        site_data = origin_zone.filter(pl.col("production_site") == site).to_pandas()
        if len(site_data) > 0:
            fig_oz.add_trace(
                go.Bar(
                    x=site_data["shipping_zone"].astype(str),
                    y=site_data["count"],
                    marker_color="#3498db",
                    text=site_data["count"].apply(lambda v: f"{v:,}"),
                    textposition="outside",
                    cliponaxis=False,
                    showlegend=False,
                    hovertemplate="Zone %{x}: %{y:,}<extra></extra>",
                ),
                row=1, col=col_idx,
            )
    fig_oz.update_layout(
        title_text="Zone Distribution by Production Site",
        height=400,
    )
    fig_oz.update_xaxes(title_text="Zone")
    fig_oz.update_yaxes(title_text="Shipments", range=[0, max_zone_count * 1.15], col=1)
    apply_chart_layout(fig_oz)
    st.plotly_chart(fig_oz, use_container_width=True)

drilldown_section(df, "Geography Data", key_suffix="geo")

st.markdown("---")


# ===========================================================================
# SECTION D — Weight Analysis
# ===========================================================================

st.header("D. Weight Analysis")

valid = df.filter(
    pl.col("weight_lbs").is_not_null() & pl.col("billable_weight_lbs").is_not_null()
)

if len(valid) > 0:
    actual_wt = valid["weight_lbs"].cast(pl.Float64).to_numpy()
    dim_wt = valid["dim_weight_lbs"].fill_null(0).cast(pl.Float64).to_numpy()
    billable_wt = valid["billable_weight_lbs"].cast(pl.Float64).to_numpy()

    uses_dim = valid["uses_dim_weight"].fill_null(False)
    dim_pct = float(uses_dim.sum()) / len(valid) * 100

    left_d, right_d = st.columns(2)

    with left_d:
        st.markdown("**Actual Weight vs DIM Weight Distribution**")
        max_display = min(float(np.percentile(billable_wt, 99)) * 1.2, 100)

        fig_wh = go.Figure()
        fig_wh.add_trace(go.Histogram(
            x=actual_wt[actual_wt < max_display], nbinsx=60,
            marker_color="#3498db", opacity=0.6,
            name="Actual Weight",
            hovertemplate="%{x:.1f} lbs: %{y:,}<extra></extra>",
        ))
        fig_wh.add_trace(go.Histogram(
            x=dim_wt[dim_wt < max_display], nbinsx=60,
            marker_color="#e74c3c", opacity=0.5,
            name="DIM Weight",
            hovertemplate="%{x:.1f} lbs: %{y:,}<extra></extra>",
        ))
        fig_wh.update_layout(
            barmode="overlay",
            title="Actual vs DIM Weight Distribution",
            xaxis_title="Weight (lbs)",
            yaxis_title="Count",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        apply_chart_layout(fig_wh)
        st.plotly_chart(fig_wh, use_container_width=True)

    with right_d:
        st.markdown("**DIM Weight Usage**")
        c1, c2 = st.columns(2)
        c1.metric("Using DIM Weight", f"{dim_pct:.1f}%")
        c2.metric("Using Actual Weight", f"{100 - dim_pct:.1f}%")

        dim_shipments = valid.filter(pl.col("uses_dim_weight").fill_null(False))
        if len(dim_shipments) > 0:
            extra_weight = (
                dim_shipments["billable_weight_lbs"].cast(pl.Float64)
                - dim_shipments["weight_lbs"].cast(pl.Float64)
            )
            avg_extra = float(extra_weight.mean())
            st.metric("Avg Extra Weight from DIM", f"{avg_extra:.1f} lbs")
            st.metric("DIM Shipments", f"{len(dim_shipments):,}")

    drilldown_section(
        valid.filter(pl.col("uses_dim_weight").fill_null(False)),
        "DIM Weight Shipments",
        columns=[
            "pcs_orderid", "pcs_ordernumber", "packagetype",
            "weight_lbs", "dim_weight_lbs", "billable_weight_lbs",
            "longest_side_in", "second_longest_in", "cubic_in",
            "cost_total", "actual_net_charge",
        ],
        key_suffix="dim_weight",
    )
else:
    st.info("No weight data available.")
