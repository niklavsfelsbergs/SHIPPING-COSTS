"""
Page 1: Portfolio Overview
==========================

Executive overview with KPIs, time series, cost breakdown, and distribution snapshots.
"""

import polars as pl
import streamlit as st
import plotly.graph_objects as go

from carriers.usps.dashboard.data import (
    COST_POSITIONS,
    init_page,
    drilldown_section,
    load_unmatched_expected,
    load_unmatched_actual,
    UNMATCHED_EXPECTED_PATH,
    UNMATCHED_ACTUAL_PATH,
    format_currency,
    format_pct,
    apply_chart_layout,
)

st.set_page_config(page_title="Portfolio | USPS", layout="wide")
st.title("Portfolio Overview")

# ---------------------------------------------------------------------------
prepared_df, match_data, df = init_page()
unmatched_expected = load_unmatched_expected()
unmatched_actual = load_unmatched_actual()

if len(df) == 0:
    st.warning("No data matches current filters.")
    st.stop()

metric_mode = st.session_state.get("metric_mode", "Total")
use_avg = metric_mode.startswith("Average")

def _metric_value(total: float, count: int) -> float:
    return (total / count) if use_avg and count > 0 else total

def _metric_label(label: str) -> str:
    return f"Avg {label}/Shipment" if use_avg else f"Total {label}"

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

    if date_from is not None and "billing_date" in df_unmatched.columns:
        df_unmatched = df_unmatched.filter(
            pl.col("billing_date").cast(pl.Date) >= pl.lit(date_from).cast(pl.Date)
        )
    if date_to is not None and "billing_date" in df_unmatched.columns:
        df_unmatched = df_unmatched.filter(
            pl.col("billing_date").cast(pl.Date) <= pl.lit(date_to).cast(pl.Date)
        )

    return df_unmatched


# ===========================================================================
# ROW 1 - KPI Cards
# ===========================================================================

total_expected = df["cost_total"].sum()
total_actual = df["actual_total"].sum()
variance_d = total_actual - total_expected
variance_pct = (variance_d / total_expected * 100) if total_expected else 0
order_count = len(df)

match_rate = 0.0
match_rate_label = "Match Rate"
match_rate_help = None
unmatched_expected_filtered = _filter_unmatched_expected(unmatched_expected)
unmatched_actual_filtered = _filter_unmatched_actual(unmatched_actual)

if UNMATCHED_EXPECTED_PATH.exists():
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
c1.metric(_metric_label("Expected"), format_currency(_metric_value(total_expected, order_count)))
c2.metric(_metric_label("Actual"), format_currency(_metric_value(total_actual, order_count)))
c3.metric(
    "Avg Variance ($)/Shipment" if use_avg else "Variance ($)",
    format_currency(_metric_value(variance_d, order_count)),
)
c4.metric("Variance (%)", format_pct(variance_pct))
c5.metric("Orders", f"{order_count:,}")
c6.metric(match_rate_label, f"{match_rate:.1f}%", help=match_rate_help)

st.markdown("---")


# ===========================================================================
# ROW 1.5 - Unmatched Shipments
# ===========================================================================

st.subheader("Unmatched Shipments")
st.caption(
    "Expected-only = calculated shipments with no invoice match. "
    "Actual-only = invoice shipments with no expected record. "
    "Date/site filters apply where columns exist."
)

with st.expander("View unmatched shipments"):
    tab_exp, tab_act = st.tabs(["Expected without Actual", "Actual without Expected"])

    max_rows = 200

    with tab_exp:
        if not UNMATCHED_EXPECTED_PATH.exists():
            st.info("Unmatched expected data not found. Re-run export_data to generate.")
        else:
            exp_filtered = unmatched_expected_filtered
            exp_cost_total = float(exp_filtered["cost_total"].sum()) if "cost_total" in exp_filtered.columns and len(exp_filtered) > 0 else 0
            col1, col2 = st.columns(2)
            col1.metric("Expected-only shipments", f"{len(exp_filtered):,}")
            col2.metric("Expected-only cost", format_currency(exp_cost_total))
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
            act_filtered = unmatched_actual_filtered
            act_cost_total = float(act_filtered["actual_total"].sum()) if "actual_total" in act_filtered.columns and len(act_filtered) > 0 else 0
            col1, col2 = st.columns(2)
            col1.metric("Actual-only shipments", f"{len(act_filtered):,}")
            col2.metric("Actual-only cost", format_currency(act_cost_total))
            act_cols = [
                "pcs_orderid", "actual_trackingnumber",
                "billing_date", "actual_zone", "actual_billed_weight_lbs",
                "actual_total", "has_adjustment", "adjustment_reason",
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
# ROW 2 - Time Series
# ===========================================================================

st.subheader("Expected vs Actual Over Time")

date_label = st.session_state.get("sidebar_date_col", "Ship Date")
date_col = "billing_date" if date_label == "Billing Date" else "ship_date"
time_grain = st.session_state.get("sidebar_time_grain", "Weekly")
value_mode = metric_mode
use_avg_ts = value_mode.startswith("Average")

truncate_map = {"Daily": "1d", "Weekly": "1w", "Monthly": "1mo"}
truncate_unit = truncate_map[time_grain]

weekly = (
    df.with_columns(
        pl.col(date_col).cast(pl.Date).dt.truncate(truncate_unit).alias("period")
    )
    .group_by("period")
    .agg([
        pl.col("cost_total").sum().alias("Expected"),
        pl.col("actual_total").sum().alias("Actual"),
        pl.len().alias("shipments"),
    ])
    .sort("period")
)

if len(weekly) > 0:
    weekly_pd = weekly.to_pandas()
    weekly_pd["Variance"] = weekly_pd["Actual"] - weekly_pd["Expected"]
    weekly_pd["Variance_pct"] = (weekly_pd["Variance"] / weekly_pd["Expected"] * 100).fillna(0)
    if use_avg_ts:
        weekly_pd["Expected"] = weekly_pd["Expected"] / weekly_pd["shipments"]
        weekly_pd["Actual"] = weekly_pd["Actual"] / weekly_pd["shipments"]
        weekly_pd["Variance"] = weekly_pd["Variance"] / weekly_pd["shipments"]

    fig = go.Figure()
    hover_fmt = "$%{y:,.2f}" if use_avg_ts else "$%{y:,.0f}"
    fig.add_trace(go.Scatter(
        x=weekly_pd["period"], y=weekly_pd["Expected"],
        name="Expected", line=dict(color="#3498db", width=2),
        customdata=weekly_pd["shipments"],
        hovertemplate=f"Expected: {hover_fmt}<br>Shipments: %{{customdata:,}}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=weekly_pd["period"], y=weekly_pd["Actual"],
        name="Actual", line=dict(color="#e74c3c", width=2),
        customdata=weekly_pd["shipments"],
        hovertemplate=f"Actual: {hover_fmt}<br>Shipments: %{{customdata:,}}<extra></extra>",
    ))
    fig.update_layout(
        title=f"{time_grain} Cost by {date_label}",
        yaxis_title="Avg Cost ($)" if use_avg_ts else "Total Cost ($)",
        yaxis_tickprefix="$", yaxis_tickformat=",.2f" if use_avg_ts else ",.0f",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    apply_chart_layout(fig)
    st.plotly_chart(fig, use_container_width=True)

    # Variance over time chart
    st.markdown("**Variance Over Time**")
    fig_var = go.Figure()
    fig_var.add_trace(go.Scatter(
        x=weekly_pd["period"], y=weekly_pd["Variance"],
        name="Variance ($)", line=dict(color="#9b59b6", width=2),
        customdata=weekly_pd[["Variance_pct", "shipments"]].values,
        hovertemplate="Variance: $%{y:,.2f}<br>Variance %%: %{customdata[0]:.2f}%%<br>Shipments: %{customdata[1]:,}<extra></extra>",
    ))
    fig_var.add_hline(y=0, line_dash="dash", line_color="#666", line_width=1)
    fig_var.update_layout(
        title=f"{time_grain} Variance (Actual - Expected) by {date_label}",
        yaxis_title="Avg Variance ($)" if use_avg_ts else "Total Variance ($)",
        yaxis_tickprefix="$", yaxis_tickformat=",.2f" if use_avg_ts else ",.0f",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    apply_chart_layout(fig_var)
    st.plotly_chart(fig_var, use_container_width=True)
else:
    st.info("Not enough data for time series chart.")

st.markdown("---")


# ===========================================================================
# ROW 2.5 - Top Variance Shipments
# ===========================================================================

st.subheader("Top Variance Shipments")
st.caption("Shipments with the largest absolute variance between expected and actual cost.")

top_n = st.number_input(
    "Number of shipments to show",
    min_value=5,
    max_value=100,
    value=10,
    step=5,
    key="top_variance_n",
)

top_variance_df = (
    df.with_columns(
        (pl.col("actual_total") - pl.col("cost_total")).abs().alias("abs_variance")
    )
    .sort("abs_variance", descending=True)
    .head(int(top_n))
)

with st.expander(f"View Top {int(top_n)} Variance Shipments"):
    top_var_cols = [
        "pcs_orderid", "pcs_ordernumber", "ship_date", "billing_date",
        "production_site", "packagetype", "shipping_zone", "actual_zone",
        "billable_weight_lbs", "actual_billed_weight_lbs",
        "cost_total", "actual_total", "deviation",
    ]
    top_var_available = [c for c in top_var_cols if c in top_variance_df.columns]
    st.dataframe(
        top_variance_df.select(top_var_available),
        use_container_width=True,
        hide_index=True,
    )
    top_var_csv = top_variance_df.select(top_var_available).to_pandas().to_csv(index=False)
    st.download_button(
        "Download Top Variance CSV",
        top_var_csv,
        file_name="top_variance_shipments.csv",
        mime="text/csv",
        key="dl_top_variance",
    )

st.markdown("---")


# ===========================================================================
# ROW 3 - Cost Breakdown
# ===========================================================================

st.subheader("Cost Breakdown")
st.caption(
    "Note: USPS invoices include peak surcharge in the base rate. "
    "For comparison, 'Base' shows expected (base + peak) vs actual base."
)

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
        exp_values.append(_metric_value(df[exp_col].sum(), order_count))
        if act_col and act_col in df.columns:
            act_values.append(_metric_value(df[act_col].sum(), order_count))
        else:
            act_values.append(0.0)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=component_labels, y=exp_values, name="Expected", marker_color="#3498db"))
    fig2.add_trace(go.Bar(x=component_labels, y=act_values, name="Actual", marker_color="#e74c3c"))
    max_val = max(exp_values + act_values) if (exp_values or act_values) else 0
    fig2.update_layout(
        barmode="group",
        title="Cost Components: Expected vs Actual",
        yaxis_title="Avg Cost ($)" if use_avg else "Total Cost ($)",
        yaxis_tickprefix="$", yaxis_tickformat=",.2f" if use_avg else ",.0f",
        yaxis=dict(range=[0, max_val * 1.1] if max_val else None),
    )
    apply_chart_layout(fig2)
    st.plotly_chart(fig2, use_container_width=True)

with right:
    st.markdown("**Cost Position Accuracy**")

    rows = []
    var_label = "Variance ($/Shipment)" if use_avg else "Variance ($)"
    for exp_col, act_col, label in COST_POSITIONS:
        exp = df[exp_col].sum()
        if act_col and act_col in df.columns:
            act = df[act_col].sum()
        else:
            act = 0.0
        var_d = act - exp
        var_p = (var_d / exp * 100) if exp else 0
        rows.append({
            "Position": label,
            "Expected": format_currency(_metric_value(exp, order_count)),
            "Actual": format_currency(_metric_value(act, order_count)),
            var_label: format_currency(_metric_value(var_d, order_count)),
            "Variance (%)": format_pct(var_p),
        })

    st.dataframe(
        pl.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")


# ===========================================================================
# ROW 3.5 - Adjustment Impact
# ===========================================================================

st.subheader("Adjustment Impact")

if "has_adjustment" in df.columns:
    adj_df = df.filter(pl.col("has_adjustment") == True)
    no_adj_df = df.filter((pl.col("has_adjustment") == False) | pl.col("has_adjustment").is_null())

    adj_count = len(adj_df)
    adj_pct = adj_count / len(df) * 100 if len(df) > 0 else 0
    adj_variance = float((adj_df["actual_total"] - adj_df["cost_total"]).sum()) if adj_count > 0 else 0
    no_adj_variance = float((no_adj_df["actual_total"] - no_adj_df["cost_total"]).sum()) if len(no_adj_df) > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Shipments with Adjustments", f"{adj_count:,}")
    c2.metric("% with Adjustments", f"{adj_pct:.1f}%")
    c3.metric("Variance (Adjusted)", format_currency(adj_variance))
    c4.metric("Variance (Non-Adjusted)", format_currency(no_adj_variance))

    # Breakdown by adjustment reason if available
    if "adjustment_reason" in df.columns and adj_count > 0:
        reason_stats = (
            adj_df.group_by("adjustment_reason")
            .agg([
                pl.len().alias("Count"),
                (pl.col("actual_total") - pl.col("cost_total")).sum().alias("Variance"),
            ])
            .sort("Count", descending=True)
        )
        if len(reason_stats) > 0:
            with st.expander("Adjustment Breakdown by Reason"):
                reason_display = reason_stats.with_columns(
                    pl.col("Variance").map_elements(format_currency, return_dtype=pl.Utf8)
                )
                st.dataframe(reason_display, use_container_width=True, hide_index=True)
else:
    st.info("No adjustment data available.")

st.markdown("---")


# ===========================================================================
# ROW 4 - Distribution Snapshots
# ===========================================================================

st.subheader("Distribution Snapshots")

dist_mode = st.radio(
    "Distribution metric",
    ["Count", "Share (%)"],
    key="portfolio_dist_mode",
    horizontal=True,
    index=1,
)
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
        values = zc_pd["count"] if dist_mode == "Count" else zc_pd["count"] / zc_pd["count"].sum() * 100
        y_title = "Shipments" if dist_mode == "Count" else "% of Shipments"
        fig3 = go.Figure(go.Bar(
            x=zc_pd["shipping_zone"].astype(str),
            y=values,
            marker_color="#3498db",
            text=[
                f"{v:,.0f}%" if dist_mode != "Count" else f"{v:,}"
                for v in values
            ],
            textposition="outside",
            cliponaxis=False,
        ))
        max_val = float(values.max()) if len(values) > 0 else 0
        fig3.update_layout(
            title="Shipment Count by Zone" if dist_mode == "Count" else "Shipment Share by Zone",
            xaxis_title="Zone", yaxis_title=y_title,
            height=420,
            margin=dict(t=60, b=50, l=40, r=20),
        )
        fig3.update_yaxes(range=[0, max_val * 1.15] if max_val else None, automargin=True)
        apply_chart_layout(fig3)
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
        values = sc_pd["count"] if dist_mode == "Count" else sc_pd["count"] / sc_pd["count"].sum() * 100
        y_title = "Shipments" if dist_mode == "Count" else "% of Shipments"
        fig4 = go.Figure(go.Bar(
            x=sc_pd["production_site"],
            y=values,
            marker_color="#27ae60",
            text=[
                f"{v:,.0f}%" if dist_mode != "Count" else f"{v:,}"
                for v in values
            ],
            textposition="outside",
            cliponaxis=False,
        ))
        max_val = float(values.max()) if len(values) > 0 else 0
        fig4.update_layout(
            title="Shipment Count by Production Site" if dist_mode == "Count" else "Shipment Share by Production Site",
            xaxis_title="Production Site", yaxis_title=y_title,
            height=420,
            margin=dict(t=60, b=50, l=40, r=20),
        )
        fig4.update_yaxes(range=[0, max_val * 1.15] if max_val else None, automargin=True)
        apply_chart_layout(fig4)
        st.plotly_chart(fig4, use_container_width=True)

# Drilldown
drilldown_section(df, "Portfolio Data", key_suffix="portfolio")

st.markdown("---")


# ===========================================================================
# DATA QUALITY & COVERAGE
# ===========================================================================

st.subheader("Data Quality & Coverage")
pk_unique = df["pcs_orderid"].n_unique()
multi_line_rows = len(df) - pk_unique
missing_cols = ["ship_date", "billing_date", "shipping_zone", "actual_zone"]
missing_stats = []
for col in missing_cols:
    if col in df.columns:
        missing = int(df[col].is_null().sum())
        missing_stats.append(
            {"Field": col, "Missing": f"{missing:,}", "Missing %": f"{missing / len(df) * 100:.2f}%"}
        )

max_ship = df["ship_date"].max() if "ship_date" in df.columns else None
max_bill = df["billing_date"].max() if "billing_date" in df.columns else None

q1, q2, q3, q4 = st.columns(4)
q1.metric("Rows (Line Items)", f"{len(df):,}")
q2.metric("Unique Orders", f"{pk_unique:,}")
q3.metric("Extra Rows from Multi-Line Orders", f"{multi_line_rows:,}")
q4.metric("Latest Ship Date", str(max_ship) if max_ship else "-")

q5, q6, q7, q8 = st.columns(4)
q5.metric("Latest Billing Date", str(max_bill) if max_bill else "-")
q6.metric("Expected-only", f"{len(unmatched_expected_filtered):,}" if len(unmatched_expected_filtered) > 0 else "0")
q7.metric("Actual-only", f"{len(unmatched_actual_filtered):,}" if len(unmatched_actual_filtered) > 0 else "0")
q8.metric("Match Rate", f"{match_rate:.1f}%")

if missing_stats:
    st.markdown("**Missingness (key fields)**")
    st.dataframe(pl.DataFrame(missing_stats), use_container_width=True, hide_index=True)


# ===========================================================================
# TOP VARIANCE DRIVERS
# ===========================================================================

st.subheader("Top Variance Drivers")
driver_tabs = st.tabs(["By Production Site", "By Zone", "By Package Type"])

def _driver_table(df_in: pl.DataFrame, group_col: str) -> pl.DataFrame:
    grouped = (
        df_in.group_by(group_col)
        .agg([
            pl.len().alias("Shipments"),
            pl.col("cost_total").sum().alias("Expected"),
            pl.col("actual_total").sum().alias("Actual"),
        ])
        .with_columns([
            (pl.col("Actual") - pl.col("Expected")).alias("Variance"),
            pl.when(pl.col("Expected") != 0)
              .then((pl.col("Actual") - pl.col("Expected")) / pl.col("Expected") * 100)
              .otherwise(0.0)
              .alias("Variance %"),
            ((pl.col("Actual") - pl.col("Expected")) / pl.col("Shipments")).alias("Var/Shipment"),
        ])
        .sort(pl.col("Variance").abs(), descending=True)
        .head(10)
    )
    return grouped

for tab, col_name, label in zip(
    driver_tabs,
    ["production_site", "shipping_zone", "packagetype"],
    ["Production Site", "Zone", "Package Type"],
):
    with tab:
        if col_name not in df.columns:
            st.info(f"{label} not available in data.")
            continue
        table = _driver_table(df, col_name)
        display = table.with_columns([
            pl.col("Expected").map_elements(format_currency, return_dtype=pl.Utf8).alias("Expected"),
            pl.col("Actual").map_elements(format_currency, return_dtype=pl.Utf8).alias("Actual"),
            pl.col("Variance").map_elements(format_currency, return_dtype=pl.Utf8).alias("Variance"),
            pl.col("Var/Shipment").map_elements(format_currency, return_dtype=pl.Utf8).alias("Var/Shipment"),
            pl.col("Variance %").map_elements(format_pct, return_dtype=pl.Utf8).alias("Variance %"),
        ])
        st.dataframe(display, use_container_width=True, hide_index=True)
