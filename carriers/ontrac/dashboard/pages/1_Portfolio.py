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
    load_unmatched_expected,
    load_unmatched_actual,
    UNMATCHED_EXPECTED_PATH,
    UNMATCHED_ACTUAL_PATH,
    format_currency,
    format_pct,
)

st.set_page_config(page_title="Portfolio | OnTrac", layout="wide")
st.title("Portfolio Overview")

# ---------------------------------------------------------------------------
prepared_df, match_data, df = init_page()
unmatched_expected = load_unmatched_expected()
unmatched_actual = load_unmatched_actual()

if len(df) == 0:
    st.warning("No data matches current filters.")
    st.stop()

def _filter_unmatched_expected(df_unmatched: pl.DataFrame) -> pl.DataFrame:
    if len(df_unmatched) == 0:
        return df_unmatched

    date_from = st.session_state.get("filter_date_from")
    date_to = st.session_state.get("filter_date_to")
    sites = st.session_state.get("filter_sites")

    if date_from is not None and "ship_date" in df_unmatched.columns:
        df_unmatched = df_unmatched.filter(
            pl.col("ship_date").cast(pl.Date) >= pl.lit(date_from).cast(pl.Date)
        )
    if date_to is not None and "ship_date" in df_unmatched.columns:
        df_unmatched = df_unmatched.filter(
            pl.col("ship_date").cast(pl.Date) <= pl.lit(date_to).cast(pl.Date)
        )
    if sites and "production_site" in df_unmatched.columns:
        df_unmatched = df_unmatched.filter(pl.col("production_site").is_in(list(sites)))

    return df_unmatched


def _filter_unmatched_actual(df_unmatched: pl.DataFrame) -> pl.DataFrame:
    if len(df_unmatched) == 0:
        return df_unmatched

    date_from = st.session_state.get("filter_date_from")
    date_to = st.session_state.get("filter_date_to")
    invoices = st.session_state.get("filter_invoices", ())

    if date_from is not None and "billing_date" in df_unmatched.columns:
        df_unmatched = df_unmatched.filter(
            pl.col("billing_date").cast(pl.Date) >= pl.lit(date_from).cast(pl.Date)
        )
    if date_to is not None and "billing_date" in df_unmatched.columns:
        df_unmatched = df_unmatched.filter(
            pl.col("billing_date").cast(pl.Date) <= pl.lit(date_to).cast(pl.Date)
        )
    if invoices and "invoice_number" in df_unmatched.columns:
        df_unmatched = df_unmatched.filter(pl.col("invoice_number").is_in(list(invoices)))

    return df_unmatched


# ===========================================================================
# ROW 1 — KPI Cards
# ===========================================================================

total_expected = df["cost_total"].sum()
total_actual = df["actual_total"].sum()
variance_d = total_actual - total_expected
variance_pct = (variance_d / total_expected * 100) if total_expected else 0
order_count = len(df)

match_rate = 0.0
match_rate_label = "Match Rate"
match_rate_help = None

if UNMATCHED_EXPECTED_PATH.exists():
    unmatched_expected_filtered = _filter_unmatched_expected(unmatched_expected)
    matched_ids = int(df["pcs_orderid"].n_unique())
    unmatched_ids = int(
        unmatched_expected_filtered["pcs_orderid"].n_unique()
    ) if len(unmatched_expected_filtered) > 0 else 0
    total_expected_orders = matched_ids + unmatched_ids
    if total_expected_orders > 0:
        match_rate = matched_ids / total_expected_orders * 100
    match_rate_label = "Match Rate (Expected)"
    match_rate_help = "Matched / total expected within current filters"
elif match_data:
    act_ids = match_data.get("actual_orderids", 0)
    matched_ids = match_data.get("matched_orderids", 0)
    if act_ids > 0:
        match_rate = matched_ids / act_ids * 100
    match_rate_label = "Match Rate (All Actuals)"
    match_rate_help = "Based on global actuals from match_rate.json"

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Expected", format_currency(total_expected))
c2.metric("Total Actual", format_currency(total_actual))
c3.metric("Variance ($)", format_currency(variance_d))
c4.metric("Variance (%)", format_pct(variance_pct))
c5.metric("Orders", f"{order_count:,}")
c6.metric(match_rate_label, f"{match_rate:.1f}%", help=match_rate_help)

st.markdown("---")


# ===========================================================================
# ROW 1.5 — Unmatched Shipments
# ===========================================================================

st.subheader("Unmatched Shipments")
st.caption(
    "Expected-only = calculated shipments with no invoice match. "
    "Actual-only = invoice shipments with no expected record. "
    "Date/site filters apply where columns exist (expected: ship_date/site; actual: billing_date/invoice)."
)

with st.expander("View unmatched shipments"):
    tab_exp, tab_act = st.tabs(["Expected without Actual", "Actual without Expected"])

    max_rows = 200

    with tab_exp:
        if not UNMATCHED_EXPECTED_PATH.exists():
            st.info("Unmatched expected data not found. Re-run export_data to generate.")
        else:
            exp_filtered = _filter_unmatched_expected(unmatched_expected)
            st.metric("Expected-only shipments", f"{len(exp_filtered):,}")
            exp_cols = [
                "pcs_orderid", "pcs_ordernumber", "shop_ordernumber",
                "ship_date", "production_site", "shipping_zip_code",
                "shipping_zone", "billable_weight_lbs", "cost_total",
            ]
            exp_available = [c for c in exp_cols if c in exp_filtered.columns]
            if len(exp_filtered) > 0:
                st.dataframe(
                    exp_filtered.select(exp_available).head(max_rows),
                    use_container_width=True,
                    hide_index=True,
                )
                exp_csv = exp_filtered.select(exp_available).to_pandas().to_csv(index=False)
                st.download_button(
                    "Download Expected-only CSV",
                    exp_csv,
                    file_name="unmatched_expected.csv",
                    mime="text/csv",
                    key="dl_unmatched_expected",
                )
            else:
                st.info("No expected-only shipments in current filters.")

    with tab_act:
        if not UNMATCHED_ACTUAL_PATH.exists():
            st.info("Unmatched actual data not found. Re-run export_data to generate.")
        else:
            act_filtered = _filter_unmatched_actual(unmatched_actual)
            st.metric("Actual-only shipments", f"{len(act_filtered):,}")
            act_cols = [
                "pcs_orderid", "actual_trackingnumber", "invoice_number",
                "billing_date", "actual_zone", "actual_billed_weight_lbs",
                "actual_total", "actual_unresolved_address",
                "actual_address_correction", "return_to_sender",
            ]
            act_available = [c for c in act_cols if c in act_filtered.columns]
            if len(act_filtered) > 0:
                st.dataframe(
                    act_filtered.select(act_available).head(max_rows),
                    use_container_width=True,
                    hide_index=True,
                )
                act_csv = act_filtered.select(act_available).to_pandas().to_csv(index=False)
                st.download_button(
                    "Download Actual-only CSV",
                    act_csv,
                    file_name="unmatched_actual.csv",
                    mime="text/csv",
                    key="dl_unmatched_actual",
                )
            else:
                st.info("No actual-only shipments in current filters.")


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
