"""
Page 3: Anomaly Detection
==========================

Flag billing anomalies, operational issues, surcharge surprises,
and monitor trends over time.
"""

import polars as pl
import streamlit as st
import plotly.graph_objects as go
import numpy as np

from carriers.fedex.dashboard.data import (
    DETERMINISTIC_SURCHARGES,
    COST_POSITIONS,
    init_page,
    get_filtered_shipments,
    drilldown_section,
    format_currency,
    format_pct,
    apply_chart_layout,
)

st.set_page_config(page_title="Anomalies | FedEx", layout="wide")
st.title("Anomaly Detection")

# ---------------------------------------------------------------------------
prepared_df, match_data, _ = init_page()
df = get_filtered_shipments()

if len(df) == 0:
    st.warning("No data matches current filters.")
    st.stop()


# ===========================================================================
# SECTION A — Billing Anomalies
# ===========================================================================

st.header("A. Billing Anomalies (Carrier Overcharges)")

left_a, right_a = st.columns([1, 3])
with left_a:
    threshold_type = st.radio("Threshold type", ["Dollar ($)", "Percentage (%)"], key="anom_thresh_type")
    if threshold_type.startswith("Dollar"):
        threshold_val = st.number_input("Threshold ($)", value=5.0, min_value=0.0, step=1.0, key="anom_thresh_d")
        anomalies = df.filter(pl.col("deviation") > threshold_val)
    else:
        threshold_val = st.number_input("Threshold (%)", value=20.0, min_value=0.0, step=5.0, key="anom_thresh_p")
        anomalies = df.filter(pl.col("deviation_pct") > threshold_val)

n_anomalies = len(anomalies)
total_impact = float(anomalies["deviation"].sum()) if n_anomalies > 0 else 0

# Calculate SmartPost anomaly metrics
smartpost_anomaly_count = df.filter(pl.col("smartpost_anomaly") == True).shape[0] if "smartpost_anomaly" in df.columns else 0
smartpost_anomaly_pct = (smartpost_anomaly_count / len(df) * 100) if len(df) > 0 else 0

# Calculate unpredictable charges metrics
unpredictable_charges_total = df.filter(pl.col("actual_unpredictable").fill_null(0) > 0).shape[0] if "actual_unpredictable" in df.columns else 0
unpredictable_charges_amount = df["actual_unpredictable"].fill_null(0).sum() if "actual_unpredictable" in df.columns else 0

with right_a:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Anomalous Shipments", f"{n_anomalies:,}")
    c2.metric("% of Total", f"{n_anomalies / len(df) * 100:.1f}%" if len(df) > 0 else "0%")
    c3.metric("Total Overcharge Impact", format_currency(total_impact))
    c4.metric("SmartPost Anomalies", f"{smartpost_anomaly_count:,}", help=f"{smartpost_anomaly_pct:.1f}% of shipments")

# Display unpredictable charges metric
if unpredictable_charges_total > 0:
    st.info(f"**Unpredictable Charges:** {unpredictable_charges_total:,} shipments with {format_currency(unpredictable_charges_amount)} in charges")

if n_anomalies > 0:
    st.markdown("**Overcharge Breakdown by Component**")

    diff_exprs = [
        (pl.col(act_col).fill_null(0) - pl.col(exp_col).fill_null(0)).abs()
        for exp_col, act_col, label in COST_POSITIONS
        if label != "TOTAL"
    ]
    diff_labels = [
        label for _, _, label in COST_POSITIONS if label != "TOTAL"
    ]
    anomalies = anomalies.with_columns(
        pl.max_horizontal(*diff_exprs).alias("_max_abs_diff")
    )
    driver_expr = pl.lit("Unknown")
    for label, diff_expr in zip(diff_labels, diff_exprs):
        driver_expr = (
            pl.when(diff_expr == pl.col("_max_abs_diff"))
            .then(pl.lit(label))
            .otherwise(driver_expr)
        )
    anomalies = anomalies.with_columns(driver_expr.alias("anomaly_driver"))

    component_impact = []
    for exp_col, act_col, label in COST_POSITIONS:
        if label == "TOTAL":
            continue
        comp_diff = float((anomalies[act_col].fill_null(0) - anomalies[exp_col].fill_null(0)).sum())
        if abs(comp_diff) > 0.01:
            component_impact.append({"Component": label, "Overcharge ($)": comp_diff})

    if component_impact:
        component_impact.sort(key=lambda x: abs(x["Overcharge ($)"]), reverse=True)
        st.dataframe(
            pl.DataFrame([
                {"Component": c["Component"], "Overcharge ($)": format_currency(c["Overcharge ($)"])}
                for c in component_impact
            ]),
            use_container_width=True,
            hide_index=True,
        )

    drilldown_section(
        anomalies,
        "Anomalous Shipments",
        columns=[
            "pcs_orderid", "pcs_ordernumber", "shop_ordernumber", "invoice_number",
            "ship_date", "production_site", "shipping_zone", "actual_zone",
            "billable_weight_lbs", "actual_billed_weight_lbs",
            "anomaly_driver",
            "cost_total", "actual_net_charge", "deviation", "deviation_pct",
        ],
        key_suffix="anomalies",
    )
else:
    st.success("No anomalies detected at this threshold.")

st.markdown("---")


# ===========================================================================
# SECTION B — Operational Issues
# ===========================================================================

st.header("B. Operational Issues")

issues = []

# Only check for columns that exist in FedEx data
if "actual_address_correction" in df.columns:
    addr_corr_df = df.filter(pl.col("actual_address_correction").fill_null(0) > 0)
    addr_cost = float(addr_corr_df["actual_address_correction"].sum()) if len(addr_corr_df) > 0 else 0
    issues.append(("Address Correction", len(addr_corr_df), addr_cost, addr_corr_df))

if "actual_undeliverable" in df.columns:
    undeliverable_df = df.filter(pl.col("actual_undeliverable").fill_null(0) > 0)
    undeliverable_cost = float(undeliverable_df["actual_undeliverable"].sum()) if len(undeliverable_df) > 0 else 0
    issues.append(("Undeliverable", len(undeliverable_df), undeliverable_cost, undeliverable_df))

if "actual_unpredictable" in df.columns:
    unpred_df = df.filter(pl.col("actual_unpredictable").fill_null(0) > 0)
    unpred_cost = float(unpred_df["actual_unpredictable"].sum()) if len(unpred_df) > 0 else 0
    issues.append(("Unpredictable Charges", len(unpred_df), unpred_cost, unpred_df))

if len(issues) > 0:
    cols = st.columns(len(issues))
    for col, (label, count, cost, _) in zip(cols, issues):
        col.metric(label, f"{count:,}", help=f"Cost impact: {format_currency(cost)}")

    for i, (label, count, cost, issue_df) in enumerate(issues):
        if count > 0:
            drilldown_section(
                issue_df,
                label,
            columns=[
                "pcs_orderid", "pcs_ordernumber", "shop_ordernumber", "invoice_number",
                "ship_date", "production_site", "cost_total", "actual_net_charge",
            ],
            key_suffix=f"issue_{i}",
        )

st.markdown("---")


# ===========================================================================
# SECTION C — Surcharge Surprises
# ===========================================================================

st.header("C. Surcharge Surprises")

fn_rows = []
fp_rows = []

for surcharge in DETERMINISTIC_SURCHARGES:
    flag_col = f"surcharge_{surcharge}"
    actual_col = f"actual_{surcharge}"
    cost_col = f"cost_{surcharge}"

    expected_flag = df[flag_col].fill_null(False)
    actual_charged = df[actual_col].fill_null(0) > 0

    fn_df = df.filter(~expected_flag & actual_charged)
    fn_cost = float(fn_df[actual_col].sum()) if len(fn_df) > 0 else 0
    fn_rows.append({
        "Surcharge": surcharge.upper(),
        "False Negatives": len(fn_df),
        "Unexpected Cost ($)": fn_cost,
    })

    fp_df = df.filter(expected_flag & ~actual_charged)
    fp_cost = float(fp_df[cost_col].sum()) if len(fp_df) > 0 else 0
    fp_rows.append({
        "Surcharge": surcharge.upper(),
        "False Positives": len(fp_df),
        "Overestimation ($)": fp_cost,
    })

left_c, right_c = st.columns(2)

with left_c:
    st.markdown("**False Negatives** (carrier charged, we didn't predict)")
    st.dataframe(
        pl.DataFrame([
            {"Surcharge": r["Surcharge"], "Count": f"{r['False Negatives']:,}",
             "Unexpected Cost": format_currency(r["Unexpected Cost ($)"])}
            for r in fn_rows
        ]),
        use_container_width=True, hide_index=True,
    )

with right_c:
    st.markdown("**False Positives** (we predicted, carrier didn't charge)")
    st.dataframe(
        pl.DataFrame([
            {"Surcharge": r["Surcharge"], "Count": f"{r['False Positives']:,}",
             "Overestimation": format_currency(r["Overestimation ($)"])}
            for r in fp_rows
        ]),
        use_container_width=True, hide_index=True,
    )

for surcharge in DETERMINISTIC_SURCHARGES:
    flag_col = f"surcharge_{surcharge}"
    actual_col = f"actual_{surcharge}"

    expected_flag = df[flag_col].fill_null(False)
    actual_charged = df[actual_col].fill_null(0) > 0

    fn_df = df.filter(~expected_flag & actual_charged)
    fp_df = df.filter(expected_flag & ~actual_charged)

    if len(fn_df) > 0 or len(fp_df) > 0:
        with st.expander(f"{surcharge.upper()} detail — FN: {len(fn_df):,} | FP: {len(fp_df):,}"):
            # Build detail columns list - only include columns that exist
            detail_cols = [
                "pcs_orderid", "ship_date", "shipping_zone", "actual_zone",
            ]
            if "shipping_zip_code" in df.columns:
                detail_cols.append("shipping_zip_code")
            detail_cols.extend([
                "billable_weight_lbs", "longest_side_in", "second_longest_in",
                actual_col, "cost_total", "actual_net_charge",
            ])
            # Filter to only columns that exist in the dataframe
            detail_cols = [c for c in detail_cols if c in fn_df.columns or c in fp_df.columns]

            if len(fn_df) > 0:
                st.markdown("**False Negatives** — showing up to 20")
                fn_cols = [c for c in detail_cols if c in fn_df.columns]
                st.dataframe(fn_df.select(fn_cols).head(20), use_container_width=True, hide_index=True)
                csv_fn = fn_df.select(fn_cols).to_pandas().to_csv(index=False)
                st.download_button(f"Download {surcharge.upper()} FN CSV", csv_fn,
                                   file_name=f"{surcharge}_fn.csv", mime="text/csv",
                                   key=f"anom_dl_fn_{surcharge}")
            if len(fp_df) > 0:
                st.markdown("**False Positives** — showing up to 20")
                fp_detail_cols = [
                    "pcs_orderid", "ship_date", "shipping_zone", "actual_zone",
                    "billable_weight_lbs", "longest_side_in", "second_longest_in",
                    f"cost_{surcharge}", "cost_total", "actual_net_charge",
                ]
                # Filter to only columns that exist
                fp_detail_cols = [c for c in fp_detail_cols if c in fp_df.columns]
                st.dataframe(fp_df.select(fp_detail_cols).head(20), use_container_width=True, hide_index=True)
                csv_fp = fp_df.select(fp_detail_cols).to_pandas().to_csv(index=False)
                st.download_button(f"Download {surcharge.upper()} FP CSV", csv_fp,
                                   file_name=f"{surcharge}_fp.csv", mime="text/csv",
                                   key=f"anom_dl_fp_{surcharge}")

st.markdown("---")


# ===========================================================================
# SECTION D — Trend Monitoring
# ===========================================================================

st.header("D. Trend Monitoring")

date_label = st.session_state.get("filter_time_axis", "Invoice Date")
date_col = "billing_date" if date_label == "Billing Date" else "ship_date"
time_grain = st.session_state.get("sidebar_time_grain", "Weekly")
truncate_map = {"Daily": "1d", "Weekly": "1w", "Monthly": "1mo"}
truncate_unit = truncate_map[time_grain]

weekly_stats = (
    df.with_columns(
        pl.col(date_col).cast(pl.Date).dt.truncate(truncate_unit).alias("period"),
        (pl.col("deviation").abs() > 5).alias("is_anomaly"),
    )
    .group_by("period")
    .agg([
        pl.len().alias("total"),
        pl.col("is_anomaly").sum().alias("anomalies"),
    ])
    .with_columns(
        (pl.col("anomalies") / pl.col("total") * 100).alias("anomaly_rate"),
    )
    .sort("period")
)

if len(weekly_stats) > 1:
    ws_pd = weekly_stats.to_pandas()

    avg_rate = float(ws_pd["anomaly_rate"].mean())
    std_rate = float(ws_pd["anomaly_rate"].std())
    threshold_line = avg_rate + std_rate

    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(
        x=ws_pd["period"], y=ws_pd["anomaly_rate"],
        mode="lines+markers",
        line=dict(color="#e74c3c", width=2),
        marker=dict(size=5),
        name="Anomaly Rate",
        customdata=ws_pd[["anomalies", "total"]].to_numpy(),
        hovertemplate="%{fullData.name}: %{y:.2f}% (%{customdata[0]:,})<extra></extra>",
    ))

    # Highlight alert points
    alert_mask = ws_pd["anomaly_rate"] > threshold_line
    if alert_mask.any():
        alert_data = ws_pd[alert_mask]
        fig_t.add_trace(go.Scatter(
            x=alert_data["period"], y=alert_data["anomaly_rate"],
            mode="markers",
            marker=dict(color="#e74c3c", size=10, symbol="circle"),
            name="Alert",
            showlegend=False,
            customdata=alert_data[["anomalies", "total"]].to_numpy(),
            hovertemplate="%{fullData.name}: %{y:.2f}% (%{customdata[0]:,})<extra></extra>",
        ))

    fig_t.add_hline(y=avg_rate, line_dash="dash", line_color="#7f8c8d", line_width=1,
                    annotation_text=f"Avg: {avg_rate:.1f}%", annotation_position="top left")
    fig_t.add_hline(y=threshold_line, line_dash="dot", line_color="#f39c12", line_width=1,
                    annotation_text=f"Alert: {threshold_line:.1f}%", annotation_position="top right")

    fig_t.update_layout(
        title=f"{time_grain} Anomaly Rate (|deviation| > $5)",
        yaxis_title="Anomaly Rate (%)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    apply_chart_layout(fig_t)
    st.plotly_chart(fig_t, use_container_width=True)

    latest_rate = float(ws_pd["anomaly_rate"].iloc[-1])
    if latest_rate > threshold_line:
        st.error(
            f"Latest {time_grain.lower()} anomaly rate ({latest_rate:.1f}%) exceeds "
            f"baseline ({avg_rate:.1f}%) + 1 std ({threshold_line:.1f}%)."
        )
else:
    st.info(f"Not enough {time_grain.lower()} data for trend analysis.")

colors_list = ["#e74c3c", "#f39c12", "#3498db", "#27ae60", "#9b59b6"]

tab_fn, tab_fp = st.tabs(["False Negative Rate", "False Positive Rate"])

with tab_fn:
    fig_fn = go.Figure()
    has_fn_data = False

    for idx, surcharge in enumerate(DETERMINISTIC_SURCHARGES):
        flag_col = f"surcharge_{surcharge}"
        actual_col = f"actual_{surcharge}"

        weekly_fn = (
            df.with_columns(
            pl.col(date_col).cast(pl.Date).dt.truncate(truncate_unit).alias("period"),
            (~df[flag_col].fill_null(False) & (df[actual_col].fill_null(0) > 0)).alias("is_fn"),
            (df[actual_col].fill_null(0) > 0).alias("actual_triggered"),
        )
        .group_by("period")
        .agg([
            pl.col("is_fn").sum().alias("fn_count"),
            pl.col("actual_triggered").sum().alias("actual_count"),
        ])
            .filter(pl.col("actual_count") > 0)
            .with_columns(
                (pl.col("fn_count") / pl.col("actual_count") * 100).alias("fn_rate"),
            )
        .sort("period")
    )

        if len(weekly_fn) > 1:
            has_fn_data = True
            wf_pd = weekly_fn.to_pandas()
            fig_fn.add_trace(go.Scatter(
                x=wf_pd["period"], y=wf_pd["fn_rate"],
                mode="lines+markers",
                line=dict(color=colors_list[idx % len(colors_list)], width=1.5),
                marker=dict(size=4),
                name=surcharge.upper(),
                customdata=wf_pd[["fn_count", "actual_count"]].to_numpy(),
                hovertemplate="%{fullData.name}: %{y:.2f}% (%{customdata[0]:,})<extra></extra>",
            ))

    if has_fn_data:
        fig_fn.update_layout(
            title=f"{time_grain} False Negative Rate by Surcharge Type",
            yaxis_title="False Negative Rate (%)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        apply_chart_layout(fig_fn)
        st.plotly_chart(fig_fn, use_container_width=True)
    else:
        st.info("Not enough data for surcharge false-negative trend.")

with tab_fp:
    fig_fp = go.Figure()
    has_fp_data = False

    for idx, surcharge in enumerate(DETERMINISTIC_SURCHARGES):
        flag_col = f"surcharge_{surcharge}"
        actual_col = f"actual_{surcharge}"

        weekly_fp = (
            df.with_columns(
            pl.col(date_col).cast(pl.Date).dt.truncate(truncate_unit).alias("period"),
            (df[flag_col].fill_null(False) & (df[actual_col].fill_null(0) <= 0)).alias("is_fp"),
            (df[flag_col].fill_null(False)).alias("expected_triggered"),
        )
        .group_by("period")
        .agg([
            pl.col("is_fp").sum().alias("fp_count"),
            pl.col("expected_triggered").sum().alias("expected_count"),
        ])
            .filter(pl.col("expected_count") > 0)
            .with_columns(
                (pl.col("fp_count") / pl.col("expected_count") * 100).alias("fp_rate"),
            )
        .sort("period")
    )

        if len(weekly_fp) > 1:
            has_fp_data = True
            wf_pd = weekly_fp.to_pandas()
            fig_fp.add_trace(go.Scatter(
                x=wf_pd["period"], y=wf_pd["fp_rate"],
                mode="lines+markers",
                line=dict(color=colors_list[idx % len(colors_list)], width=1.5),
                marker=dict(size=4),
                name=surcharge.upper(),
                customdata=wf_pd[["fp_count", "expected_count"]].to_numpy(),
                hovertemplate="%{fullData.name}: %{y:.2f}% (%{customdata[0]:,})<extra></extra>",
            ))

    if has_fp_data:
        fig_fp.update_layout(
            title=f"{time_grain} False Positive Rate by Surcharge Type",
            yaxis_title="False Positive Rate (%)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        apply_chart_layout(fig_fp)
        st.plotly_chart(fig_fp, use_container_width=True)
    else:
        st.info("Not enough data for surcharge false-positive trend.")
