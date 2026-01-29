"""
Page 2: Estimation Accuracy
============================

Deep-dive into shipment-level estimation precision: deviation analysis,
surcharge detection accuracy, zone accuracy, and weight accuracy.
"""

import polars as pl
import streamlit as st
import plotly.graph_objects as go
import numpy as np

from carriers.ontrac.dashboard.data import (
    DETERMINISTIC_SURCHARGES,
    WEIGHT_BRACKETS,
    init_page,
    calc_segment_stats,
    drilldown_section,
    format_currency,
    format_pct,
)

st.set_page_config(page_title="Accuracy | OnTrac", layout="wide")
st.title("Estimation Accuracy")

# ---------------------------------------------------------------------------
prepared_df, match_data, df = init_page()

if len(df) == 0:
    st.warning("No data matches current filters.")
    st.stop()


# ===========================================================================
# SECTION A — Overall Deviation Distribution
# ===========================================================================

st.header("A. Overall Deviation Distribution")

deviation_mode = st.radio(
    "Show deviation as", ["Dollar ($)", "Percentage (%)"], horizontal=True, key="dev_mode"
)
dev_col = "deviation" if deviation_mode.startswith("Dollar") else "deviation_pct"
dev_label = "Actual - Expected ($)" if dev_col == "deviation" else "Actual - Expected (%)"

devs = df[dev_col].drop_nulls().cast(pl.Float64).to_numpy()

if len(devs) > 0:
    p1, p99 = np.percentile(devs, [1, 99])
    margin = max(abs(p1), abs(p99)) * 0.2
    lo, hi = p1 - margin, p99 + margin

    mean_val = float(np.mean(devs))
    median_val = float(np.median(devs))

    bin_size = (hi - lo) / 80

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=devs,
        xbins=dict(start=lo, end=hi, size=bin_size),
        marker=dict(color="#3498db", line=dict(color="white", width=0.5)),
        opacity=0.8,
        name="Shipments",
        hovertemplate="Range: %{x}<br>Count: %{y:,}<extra></extra>",
    ))

    # Reference lines — no annotation text on the lines themselves (avoids overlap)
    fig.add_vline(x=0, line_dash="dash", line_color="#2c3e50", line_width=1.5)
    fig.add_vline(x=mean_val, line_dash="dash", line_color="#e74c3c", line_width=1.5)
    fig.add_vline(x=median_val, line_dash="dash", line_color="#27ae60", line_width=1.5)

    # Stats box in top-right corner — clean, no collision
    if dev_col == "deviation":
        stats_text = f"<b>Mean</b>: ${mean_val:.2f}<br><b>Median</b>: ${median_val:.2f}"
    else:
        stats_text = f"<b>Mean</b>: {mean_val:.2f}%<br><b>Median</b>: {median_val:.2f}%"

    fig.add_annotation(
        text=stats_text,
        xref="paper", yref="paper", x=0.98, y=0.95,
        xanchor="right", yanchor="top",
        showarrow=False,
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#ddd", borderwidth=1,
        font=dict(size=12),
        align="left",
    )

    # Legend entries for reference line colors
    for color, name in [("#2c3e50", "Zero"), ("#e74c3c", "Mean"), ("#27ae60", "Median")]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines",
            line=dict(color=color, dash="dash", width=1.5),
            name=name, showlegend=True,
        ))

    fig.update_layout(
        title=f"Deviation Distribution (n={len(devs):,})",
        xaxis_title=dev_label,
        yaxis_title="Shipment Count",
        xaxis=dict(range=[lo, hi]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    abs_devs = np.abs(df["deviation"].drop_nulls().to_numpy())
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Mean", f"${np.mean(df['deviation'].drop_nulls().to_numpy()):.2f}")
    c2.metric("Median", f"${np.median(df['deviation'].drop_nulls().to_numpy()):.2f}")
    c3.metric("Std Dev", f"${np.std(df['deviation'].drop_nulls().to_numpy()):.2f}")
    c4.metric("Within $1", f"{(abs_devs <= 1).sum() / len(abs_devs) * 100:.1f}%")
    c5.metric("Within $2", f"{(abs_devs <= 2).sum() / len(abs_devs) * 100:.1f}%")
    c6.metric("Within $5", f"{(abs_devs <= 5).sum() / len(abs_devs) * 100:.1f}%")

drilldown_section(df, "All Shipments", key_suffix="acc_all")

st.markdown("---")


# ===========================================================================
# SECTION B — Accuracy by Segment (tabs)
# ===========================================================================

st.header("B. Accuracy by Segment")

tab_pkg, tab_err, tab_zone, tab_weight, tab_site = st.tabs([
    "By Package Type", "By Error Source", "By Zone", "By Weight Bracket", "By Production Site"
])


def _stats_table(grouped_stats: list[dict], segment_label: str) -> None:
    rows = []
    for s in grouped_stats:
        rows.append({
            segment_label: s["segment"],
            "Count": f"{s['count']:,}",
            "Expected": format_currency(s["total_expected"]),
            "Actual": format_currency(s["total_actual"]),
            "Var ($)": format_currency(s["variance_dollars"]),
            "Var (%)": format_pct(s["variance_pct"]),
            "Mean Dev": format_currency(s["mean_dev"]),
            "Median Dev": format_currency(s["median_dev"]),
            "Std Dev": format_currency(s["std_dev"]),
            "MAD": format_currency(s["mad"]),
            "Within $1": f"{s['within_1']:.1f}%",
            "Within $2": f"{s['within_2']:.1f}%",
        })
    st.dataframe(pl.DataFrame(rows), use_container_width=True, hide_index=True)


with tab_pkg:
    pkg_types = (
        df.group_by("packagetype")
        .agg(pl.len().alias("n"))
        .sort("n", descending=True)
    )["packagetype"].to_list()

    stats_pkg = []
    for pkg in pkg_types:
        seg = df.filter(pl.col("packagetype") == pkg)
        s = calc_segment_stats(seg)
        s["segment"] = pkg or "Unknown"
        stats_pkg.append(s)
    _stats_table(stats_pkg, "Package Type")

with tab_err:
    stats_err = []
    for seg_name in ["Clean match", "Zone mismatch only", "Surcharge mismatch"]:
        seg = df.filter(pl.col("error_source") == seg_name)
        s = calc_segment_stats(seg)
        s["segment"] = seg_name
        stats_err.append(s)
    _stats_table(stats_err, "Error Source")

    COLORS = {"Clean match": "#27ae60", "Zone mismatch only": "#f39c12", "Surcharge mismatch": "#e74c3c"}
    all_devs_np = df["deviation"].drop_nulls().cast(pl.Float64).to_numpy()
    if len(all_devs_np) > 0:
        p1, p99 = np.percentile(all_devs_np, [1, 99])
        margin = max(abs(p1), abs(p99)) * 0.2
        lo, hi = p1 - margin, p99 + margin

        fig_e = go.Figure()
        for seg_name, color in COLORS.items():
            seg_devs = df.filter(pl.col("error_source") == seg_name)["deviation"].drop_nulls().cast(pl.Float64).to_numpy()
            n_seg = len(seg_devs)
            if n_seg > 0:
                fig_e.add_trace(go.Histogram(
                    x=seg_devs, nbinsx=80,
                    xbins=dict(start=lo, end=hi),
                    histnorm="percent",
                    marker_color=color, opacity=0.6,
                    name=f"{seg_name} (n={n_seg:,})",
                    hovertemplate="%{x:.2f}: %{y:.1f}%<extra></extra>",
                ))
        fig_e.add_vline(x=0, line_dash="dash", line_color="#2c3e50", line_width=1.5, opacity=0.7)
        fig_e.update_layout(
            barmode="overlay",
            title="Deviation Distribution by Error Source (normalized)",
            xaxis_title="Deviation ($)",
            yaxis_title="% of Segment",
            xaxis=dict(range=[lo, hi]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig_e, use_container_width=True)

with tab_zone:
    zones = sorted(df["shipping_zone"].drop_nulls().unique().to_list())
    stats_z = []
    for z in zones:
        seg = df.filter(pl.col("shipping_zone") == z)
        s = calc_segment_stats(seg)
        s["segment"] = str(z)
        stats_z.append(s)
    _stats_table(stats_z, "Zone")

with tab_weight:
    stats_w = []
    for lower, upper, label in WEIGHT_BRACKETS:
        seg = df.filter(pl.col("weight_bracket") == label)
        s = calc_segment_stats(seg)
        s["segment"] = label
        stats_w.append(s)
    _stats_table(stats_w, "Weight Bracket")

with tab_site:
    sites = sorted(df["production_site"].drop_nulls().unique().to_list())
    stats_s = []
    for site in sites:
        seg = df.filter(pl.col("production_site") == site)
        s = calc_segment_stats(seg)
        s["segment"] = site
        stats_s.append(s)
    _stats_table(stats_s, "Production Site")

st.markdown("---")


# ===========================================================================
# SECTION C — Surcharge Detection Accuracy
# ===========================================================================

st.header("C. Surcharge Detection Accuracy")

detection_rows = []
for surcharge in DETERMINISTIC_SURCHARGES:
    flag_col = f"surcharge_{surcharge}"
    actual_col = f"actual_{surcharge}"

    expected_flag = df[flag_col].fill_null(False)
    actual_charged = df[actual_col].fill_null(0) > 0

    tp = int((expected_flag & actual_charged).sum())
    fp = int((expected_flag & ~actual_charged).sum())
    fn = int((~expected_flag & actual_charged).sum())

    precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 100.0
    recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 100.0

    detection_rows.append({
        "Surcharge": surcharge.upper(),
        "True Pos": tp,
        "False Pos": fp,
        "False Neg": fn,
        "Precision": f"{precision:.1f}%",
        "Recall": f"{recall:.1f}%",
    })

st.dataframe(pl.DataFrame(detection_rows), use_container_width=True, hide_index=True)

for surcharge in DETERMINISTIC_SURCHARGES:
    flag_col = f"surcharge_{surcharge}"
    actual_col = f"actual_{surcharge}"

    expected_flag = df[flag_col].fill_null(False)
    actual_charged = df[actual_col].fill_null(0) > 0

    fp_df = df.filter(expected_flag & ~actual_charged)
    fn_df = df.filter(~expected_flag & actual_charged)

    if len(fp_df) > 0 or len(fn_df) > 0:
        with st.expander(f"{surcharge.upper()} — FP: {len(fp_df):,} | FN: {len(fn_df):,}"):
            detail_cols = [
                "pcs_orderid", "pcs_ordernumber", "shipping_zone", "actual_zone",
                "billable_weight_lbs", "longest_side_in", "second_longest_in",
                "cost_total", "actual_total",
            ]
            if len(fp_df) > 0:
                st.markdown(f"**False Positives** (predicted but not charged) — showing up to 20")
                st.dataframe(fp_df.select(detail_cols).head(20), use_container_width=True, hide_index=True)
                csv_fp = fp_df.select(detail_cols).to_pandas().to_csv(index=False)
                st.download_button(f"Download {surcharge.upper()} FP CSV", csv_fp,
                                   file_name=f"{surcharge}_false_positives.csv", mime="text/csv",
                                   key=f"dl_fp_{surcharge}")
            if len(fn_df) > 0:
                st.markdown(f"**False Negatives** (not predicted but charged) — showing up to 20")
                st.dataframe(fn_df.select(detail_cols).head(20), use_container_width=True, hide_index=True)
                csv_fn = fn_df.select(detail_cols).to_pandas().to_csv(index=False)
                st.download_button(f"Download {surcharge.upper()} FN CSV", csv_fn,
                                   file_name=f"{surcharge}_false_negatives.csv", mime="text/csv",
                                   key=f"dl_fn_{surcharge}")

st.markdown("---")


# ===========================================================================
# SECTION D — Zone Accuracy
# ===========================================================================

st.header("D. Zone Accuracy")

zone_match_count = int(df["zone_match"].sum())
zone_total = len(df)
zone_match_rate = zone_match_count / zone_total * 100 if zone_total > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("Zone Match Rate", f"{zone_match_rate:.1f}%")
c2.metric("Matches / Total", f"{zone_match_count:,} / {zone_total:,}")

mismatch_df = df.filter(~pl.col("zone_match"))
mismatch_cost = float((mismatch_df["actual_total"] - mismatch_df["cost_total"]).sum()) if len(mismatch_df) > 0 else 0
c3.metric("Mismatch Cost Impact", format_currency(mismatch_cost))

# Confusion matrix
st.markdown("**Zone Confusion Matrix**")

if len(df) > 0:
    zone_cross = (
        df.group_by(["shipping_zone", "actual_zone"])
        .agg(pl.len().alias("count"))
        .sort(["shipping_zone", "actual_zone"])
    )

    all_zones = sorted(set(
        zone_cross["shipping_zone"].to_list() + zone_cross["actual_zone"].to_list()
    ))

    matrix = np.zeros((len(all_zones), len(all_zones)))
    zone_idx = {z: i for i, z in enumerate(all_zones)}
    for row in zone_cross.iter_rows(named=True):
        i = zone_idx.get(row["shipping_zone"])
        j = zone_idx.get(row["actual_zone"])
        if i is not None and j is not None:
            matrix[i][j] = row["count"]

    zone_labels = [str(z) for z in all_zones]

    text_matrix = []
    for i in range(len(all_zones)):
        row_text = []
        for j in range(len(all_zones)):
            val = int(matrix[i][j])
            row_text.append(f"{val:,}" if val > 0 else "")
        text_matrix.append(row_text)

    fig_cm = go.Figure(go.Heatmap(
        z=matrix,
        x=zone_labels,
        y=zone_labels,
        text=text_matrix,
        texttemplate="%{text}",
        colorscale="Blues",
        hovertemplate="Expected Zone: %{y}<br>Actual Zone: %{x}<br>Count: %{z:,}<extra></extra>",
    ))
    fig_cm.update_layout(
        title="Expected vs Actual Zone (count)",
        xaxis_title="Actual Zone",
        yaxis_title="Expected Zone",
        yaxis=dict(autorange="reversed"),
        height=max(500, len(all_zones) * 60 + 100),
    )
    st.plotly_chart(fig_cm, use_container_width=True)

# By-state
st.markdown("**Zone Match by State**")

state_stats = (
    df.with_columns([
        (pl.col("shipping_zone") < pl.col("actual_zone")).alias("zone_smaller"),
        (pl.col("shipping_zone") > pl.col("actual_zone")).alias("zone_bigger"),
    ])
    .group_by("shipping_region")
    .agg([
        pl.len().alias("Shipments"),
        (pl.col("zone_match").sum() / pl.len() * 100).alias("Match %"),
        (pl.col("zone_smaller").sum() / pl.len() * 100).alias("Smaller Zone %"),
        (pl.col("zone_bigger").sum() / pl.len() * 100).alias("Bigger Zone %"),
    ])
    .sort("Shipments", descending=True)
    .rename({"shipping_region": "State"})
)

st.dataframe(state_stats, use_container_width=True, hide_index=True)

drilldown_section(mismatch_df, "Zone Mismatches", key_suffix="zone_mm")

st.markdown("---")


# ===========================================================================
# SECTION E — Weight Accuracy
# ===========================================================================

st.header("E. Weight Accuracy")

valid_weight = df.filter(
    pl.col("billable_weight_lbs").is_not_null() &
    pl.col("actual_billed_weight_lbs").is_not_null()
)

if len(valid_weight) > 0:
    exp_w = valid_weight["billable_weight_lbs"].cast(pl.Float64).to_numpy()
    act_w = valid_weight["actual_billed_weight_lbs"].cast(pl.Float64).to_numpy()
    diff_w = act_w - exp_w

    tolerance = 0.5
    w_matches = int(np.sum(np.abs(diff_w) <= tolerance))
    w_rate = w_matches / len(diff_w) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Weight Match Rate", f"{w_rate:.1f}%", help=f"Within +/-{tolerance} lbs")
    c2.metric("Matches / Total", f"{w_matches:,} / {len(diff_w):,}")
    c3.metric("Avg Difference", f"{np.mean(diff_w):+.2f} lbs")

    # Density contour — shows actual weight patterns instead of a point-cloud blob
    st.markdown("**Expected vs Actual Billable Weight**")

    n_pts = len(exp_w)
    if n_pts > 15000:
        idx = np.random.choice(n_pts, 15000, replace=False)
        px, py = exp_w[idx], act_w[idx]
    else:
        px, py = exp_w, act_w

    max_val = max(float(np.max(px)), float(np.max(py))) * 1.05

    fig_w = go.Figure()
    fig_w.add_trace(go.Scattergl(
        x=px, y=py,
        mode="markers",
        marker=dict(color="#3498db", size=3, opacity=0.25),
        name="Shipments",
        hovertemplate="Expected: %{x:.1f} lbs<br>Actual: %{y:.1f} lbs<extra></extra>",
    ))
    fig_w.add_trace(go.Scatter(
        x=[0, max_val], y=[0, max_val],
        mode="lines",
        line=dict(color="#e74c3c", dash="dash", width=2),
        name="Perfect match",
        hoverinfo="skip",
    ))
    fig_w.update_layout(
        title="Expected vs Actual Weight",
        xaxis_title="Expected Billable Weight (lbs)",
        yaxis_title="Actual Billed Weight (lbs)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig_w, use_container_width=True)

    # Weight difference distribution
    st.markdown("**Weight Difference Distribution**")
    clipped = diff_w[(diff_w > -10) & (diff_w < 10)]

    wd_bin_size = 20 / 120  # ~0.17 lbs per bin across the ±10 range
    fig_wd = go.Figure()
    fig_wd.add_trace(go.Histogram(
        x=clipped,
        xbins=dict(start=-10, end=10, size=wd_bin_size),
        marker=dict(color="#3498db", line=dict(color="white", width=0.5)),
        opacity=0.8,
        hovertemplate="Diff: %{x:.1f} lbs<br>Count: %{y:,}<extra></extra>",
    ))
    fig_wd.add_vline(x=0, line_dash="dash", line_color="#2c3e50", line_width=1.5)
    fig_wd.update_layout(
        title="Weight Difference Distribution (clipped to +/-10 lbs)",
        xaxis_title="Weight Difference (Actual - Expected) lbs",
        yaxis_title="Count",
        showlegend=False,
    )
    st.plotly_chart(fig_wd, use_container_width=True)
else:
    st.info("No valid weight data for comparison.")
