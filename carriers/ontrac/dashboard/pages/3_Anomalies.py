"""
Page 3: Anomaly Detection
==========================

Flag billing anomalies, operational issues, surcharge surprises,
and monitor trends over time.
"""

import polars as pl
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from carriers.ontrac.dashboard.data import (
    DETERMINISTIC_SURCHARGES,
    COST_POSITIONS,
    init_page,
    drilldown_section,
    format_currency,
    format_pct,
)

st.set_page_config(page_title="Anomalies | OnTrac", layout="wide")
st.title("Anomaly Detection")

# ---------------------------------------------------------------------------
prepared_df, match_data, df = init_page()

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

with right_a:
    c1, c2, c3 = st.columns(3)
    c1.metric("Anomalous Shipments", f"{n_anomalies:,}")
    c2.metric("% of Total", f"{n_anomalies / len(df) * 100:.1f}%" if len(df) > 0 else "0%")
    c3.metric("Total Overcharge Impact", format_currency(total_impact))

if n_anomalies > 0:
    st.markdown("**Overcharge Breakdown by Component**")

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
            "cost_total", "actual_total", "deviation", "deviation_pct",
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

oml_df = df.filter(pl.col("actual_oml").fill_null(0) > 0)
oml_cost = float(oml_df["actual_oml"].sum()) if len(oml_df) > 0 else 0
issues.append(("OML (Over Maximum Limits)", len(oml_df), oml_cost, oml_df))

rts_df = df.filter(pl.col("return_to_sender").fill_null(False) == True)
rts_cost = float(rts_df["actual_total"].sum()) if len(rts_df) > 0 else 0
issues.append(("Return to Sender", len(rts_df), rts_cost, rts_df))

addr_corr_df = df.filter(pl.col("actual_address_correction").fill_null(0) > 0)
addr_cost = float(addr_corr_df["actual_address_correction"].sum()) if len(addr_corr_df) > 0 else 0
issues.append(("Address Correction", len(addr_corr_df), addr_cost, addr_corr_df))

unres_df = df.filter(pl.col("actual_unresolved_address").fill_null(0) > 0)
unres_cost = float(unres_df["actual_unresolved_address"].sum()) if len(unres_df) > 0 else 0
issues.append(("Unresolved Address", len(unres_df), unres_cost, unres_df))

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
                "ship_date", "production_site", "cost_total", "actual_total",
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
            detail_cols = [
                "pcs_orderid", "ship_date", "shipping_zone", "actual_zone",
                "billable_weight_lbs", "longest_side_in", "second_longest_in",
                actual_col, "cost_total", "actual_total",
            ]
            if len(fn_df) > 0:
                st.markdown("**False Negatives** — showing up to 20")
                st.dataframe(fn_df.select(detail_cols).head(20), use_container_width=True, hide_index=True)
                csv_fn = fn_df.select(detail_cols).to_pandas().to_csv(index=False)
                st.download_button(f"Download {surcharge.upper()} FN CSV", csv_fn,
                                   file_name=f"{surcharge}_fn.csv", mime="text/csv",
                                   key=f"anom_dl_fn_{surcharge}")
            if len(fp_df) > 0:
                st.markdown("**False Positives** — showing up to 20")
                fp_detail_cols = [
                    "pcs_orderid", "ship_date", "shipping_zone", "actual_zone",
                    "billable_weight_lbs", "longest_side_in", "second_longest_in",
                    f"cost_{surcharge}", "cost_total", "actual_total",
                ]
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

date_col = st.session_state.get("sidebar_date_col", "billing_date")

weekly_stats = (
    df.with_columns(
        pl.col(date_col).cast(pl.Date).dt.truncate("1w").alias("week"),
        (pl.col("deviation").abs() > 5).alias("is_anomaly"),
    )
    .group_by("week")
    .agg([
        pl.len().alias("total"),
        pl.col("is_anomaly").sum().alias("anomalies"),
    ])
    .with_columns(
        (pl.col("anomalies") / pl.col("total") * 100).alias("anomaly_rate"),
    )
    .sort("week")
)

if len(weekly_stats) > 1:
    ws_pd = weekly_stats.to_pandas()

    fig_t, ax_t = plt.subplots(figsize=(12, 4.5))
    ax_t.plot(ws_pd["week"], ws_pd["anomaly_rate"], color="#e74c3c", linewidth=2, marker="o", markersize=4)
    avg_rate = ws_pd["anomaly_rate"].mean()
    std_rate = ws_pd["anomaly_rate"].std()
    threshold_line = avg_rate + std_rate

    ax_t.axhline(avg_rate, color="#7f8c8d", linestyle="--", linewidth=1, label=f"Avg: {avg_rate:.1f}%")
    ax_t.axhline(threshold_line, color="#f39c12", linestyle=":", linewidth=1,
                  label=f"Alert threshold: {threshold_line:.1f}%")

    alert_mask = ws_pd["anomaly_rate"] > threshold_line
    if alert_mask.any():
        ax_t.scatter(ws_pd.loc[alert_mask, "week"], ws_pd.loc[alert_mask, "anomaly_rate"],
                     color="#e74c3c", s=80, zorder=5)

    ax_t.set_ylabel("Anomaly Rate (%)")
    ax_t.set_title("Weekly Anomaly Rate (|deviation| > $5)")
    ax_t.legend()
    ax_t.grid(axis="y", alpha=0.3)
    fig_t.autofmt_xdate()
    fig_t.tight_layout()
    st.pyplot(fig_t)
    plt.close(fig_t)

    latest_rate = float(ws_pd["anomaly_rate"].iloc[-1])
    if latest_rate > threshold_line:
        st.error(
            f"Latest week anomaly rate ({latest_rate:.1f}%) exceeds "
            f"baseline ({avg_rate:.1f}%) + 1 std ({threshold_line:.1f}%)."
        )
else:
    st.info("Not enough weekly data for trend analysis.")

# Weekly false negative rate by surcharge type
st.markdown("**Weekly False Negative Rate by Surcharge**")

has_fn_data = False
fig_fn, ax_fn = plt.subplots(figsize=(12, 4.5))
colors_list = ["#e74c3c", "#f39c12", "#3498db", "#27ae60", "#9b59b6"]

for idx, surcharge in enumerate(DETERMINISTIC_SURCHARGES):
    flag_col = f"surcharge_{surcharge}"
    actual_col = f"actual_{surcharge}"

    weekly_fn = (
        df.with_columns(
            pl.col(date_col).cast(pl.Date).dt.truncate("1w").alias("week"),
            (~df[flag_col].fill_null(False) & (df[actual_col].fill_null(0) > 0)).alias("is_fn"),
            (df[actual_col].fill_null(0) > 0).alias("actual_triggered"),
        )
        .group_by("week")
        .agg([
            pl.col("is_fn").sum().alias("fn_count"),
            pl.col("actual_triggered").sum().alias("actual_count"),
        ])
        .filter(pl.col("actual_count") > 0)
        .with_columns(
            (pl.col("fn_count") / pl.col("actual_count") * 100).alias("fn_rate"),
        )
        .sort("week")
    )

    if len(weekly_fn) > 1:
        has_fn_data = True
        wf_pd = weekly_fn.to_pandas()
        ax_fn.plot(
            wf_pd["week"], wf_pd["fn_rate"],
            label=surcharge.upper(),
            color=colors_list[idx % len(colors_list)],
            linewidth=1.5, marker="o", markersize=3,
        )

if has_fn_data:
    ax_fn.set_ylabel("False Negative Rate (%)")
    ax_fn.set_title("Weekly False Negative Rate by Surcharge Type")
    ax_fn.legend()
    ax_fn.grid(axis="y", alpha=0.3)
    fig_fn.autofmt_xdate()
    fig_fn.tight_layout()
    st.pyplot(fig_fn)
else:
    st.info("Not enough data for surcharge false-negative trend.")
plt.close(fig_fn)
