"""
Page 1: Portfolio Overview
==========================

Executive overview with KPIs, time series, cost breakdown, and distribution snapshots.
"""

import polars as pl
import streamlit as st
import plotly.graph_objects as go

from carriers.ontrac.dashboard.data import (
    COST_POSITIONS,
    init_page,
    drilldown_section,
    format_currency,
    format_pct,
)

st.set_page_config(page_title="Portfolio | OnTrac", layout="wide")
st.title("Portfolio Overview")

# ---------------------------------------------------------------------------
prepared_df, match_data, df = init_page()

if len(df) == 0:
    st.warning("No data matches current filters.")
    st.stop()


# ===========================================================================
# ROW 1 — KPI Cards
# ===========================================================================

total_expected = df["cost_total"].sum()
total_actual = df["actual_total"].sum()
variance_d = total_actual - total_expected
variance_pct = (variance_d / total_expected * 100) if total_expected else 0
order_count = len(df)

match_rate = 0.0
if match_data:
    act_ids = match_data.get("actual_orderids", 0)
    matched_ids = match_data.get("matched_orderids", 0)
    if act_ids > 0:
        match_rate = matched_ids / act_ids * 100

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Expected", format_currency(total_expected))
c2.metric("Total Actual", format_currency(total_actual))
c3.metric("Variance ($)", format_currency(variance_d))
c4.metric("Variance (%)", format_pct(variance_pct))
c5.metric("Orders", f"{order_count:,}")
c6.metric("Match Rate", f"{match_rate:.1f}%")

st.markdown("---")


# ===========================================================================
# ROW 2 — Time Series
# ===========================================================================

st.subheader("Weekly Expected vs Actual")

date_col = st.session_state.get("sidebar_date_col", "billing_date")

weekly = (
    df.with_columns(
        pl.col(date_col).cast(pl.Date).dt.truncate("1w").alias("week")
    )
    .group_by("week")
    .agg([
        pl.col("cost_total").sum().alias("Expected"),
        pl.col("actual_total").sum().alias("Actual"),
        pl.len().alias("shipments"),
    ])
    .sort("week")
)

if len(weekly) > 0:
    weekly_pd = weekly.to_pandas()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekly_pd["week"], y=weekly_pd["Expected"],
        name="Expected", line=dict(color="#3498db", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=weekly_pd["week"], y=weekly_pd["Actual"],
        name="Actual", line=dict(color="#e74c3c", width=2),
    ))
    fig.update_layout(
        title=f"Weekly Cost by {date_col}",
        yaxis_title="Total Cost ($)",
        yaxis_tickprefix="$", yaxis_tickformat=",.0f",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough data for weekly chart.")

st.markdown("---")


# ===========================================================================
# ROW 3 — Cost Breakdown
# ===========================================================================

st.subheader("Cost Breakdown")

left, right = st.columns(2)

with left:
    st.markdown("**Expected vs Actual by Component**")

    component_labels = []
    exp_values = []
    act_values = []

    for exp_col, act_col, label in COST_POSITIONS:
        if label == "TOTAL":
            continue
        component_labels.append(label)
        exp_values.append(df[exp_col].sum())
        act_values.append(df[act_col].sum())

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=component_labels, y=exp_values, name="Expected", marker_color="#3498db"))
    fig2.add_trace(go.Bar(x=component_labels, y=act_values, name="Actual", marker_color="#e74c3c"))
    fig2.update_layout(
        barmode="group",
        title="Cost Components: Expected vs Actual",
        yaxis_tickprefix="$", yaxis_tickformat=",.0f",
    )
    st.plotly_chart(fig2, use_container_width=True)

with right:
    st.markdown("**Cost Position Accuracy**")

    rows = []
    for exp_col, act_col, label in COST_POSITIONS:
        exp = df[exp_col].sum()
        act = df[act_col].sum()
        var_d = act - exp
        var_p = (var_d / exp * 100) if exp else 0
        rows.append({
            "Position": label,
            "Expected": format_currency(exp),
            "Actual": format_currency(act),
            "Variance ($)": format_currency(var_d),
            "Variance (%)": format_pct(var_p),
        })

    st.dataframe(
        pl.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")


# ===========================================================================
# ROW 4 — Distribution Snapshots
# ===========================================================================

st.subheader("Distribution Snapshots")

left2, right2 = st.columns(2)

with left2:
    st.markdown("**Shipments by Zone**")
    zone_counts = (
        df.group_by("shipping_zone")
        .agg(pl.len().alias("count"))
        .sort("shipping_zone")
    )
    if len(zone_counts) > 0:
        zc_pd = zone_counts.to_pandas()
        fig3 = go.Figure(go.Bar(
            x=zc_pd["shipping_zone"].astype(str),
            y=zc_pd["count"],
            marker_color="#3498db",
            text=zc_pd["count"].apply(lambda v: f"{v:,}"),
            textposition="outside",
        ))
        fig3.update_layout(
            title="Shipment Count by Zone",
            xaxis_title="Zone", yaxis_title="Shipments",
        )
        st.plotly_chart(fig3, use_container_width=True)

with right2:
    st.markdown("**Shipments by Production Site**")
    site_counts = (
        df.group_by("production_site")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    if len(site_counts) > 0:
        sc_pd = site_counts.to_pandas()
        fig4 = go.Figure(go.Bar(
            x=sc_pd["production_site"],
            y=sc_pd["count"],
            marker_color="#27ae60",
            text=sc_pd["count"].apply(lambda v: f"{v:,}"),
            textposition="outside",
        ))
        fig4.update_layout(
            title="Shipment Count by Production Site",
            xaxis_title="Production Site", yaxis_title="Shipments",
        )
        st.plotly_chart(fig4, use_container_width=True)

# Drilldown
drilldown_section(df, "Portfolio Data", key_suffix="portfolio")
