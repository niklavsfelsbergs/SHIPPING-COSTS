"""
Page 2: Estimation Accuracy
============================

Deep-dive into shipment-level estimation precision: deviation analysis,
surcharge detection accuracy, zone accuracy, and weight accuracy.
"""

import math

import polars as pl
import streamlit as st
import plotly.graph_objects as go
import numpy as np

from carriers.fedex.dashboard.data import (
    DETERMINISTIC_SURCHARGES,
    WEIGHT_BRACKETS,
    init_page,
    get_filtered_shipments,
    apply_chart_layout,
    calc_segment_stats,
    drilldown_section,
    format_currency,
    format_pct,
)

st.set_page_config(page_title="Accuracy | FedEx", layout="wide")
st.title("Estimation Accuracy")

# ---------------------------------------------------------------------------
prepared_df, match_data, _ = init_page()
df = get_filtered_shipments()

if len(df) == 0:
    st.warning("No data matches current filters.")
    st.stop()

metric_mode = st.session_state.get("filter_metric_mode", "Total")

def _hist_bounds(values: np.ndarray, bins: int = 80) -> tuple[float, float, float]:
    if len(values) == 0:
        return -1.0, 1.0, 1.0

    p1, p99 = np.percentile(values, [1, 99])
    margin = max(abs(p1), abs(p99)) * 0.2
    lo, hi = p1 - margin, p99 + margin

    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        vmin = float(np.min(values))
        vmax = float(np.max(values))
        if vmin == vmax:
            lo, hi = vmin - 1.0, vmax + 1.0
        else:
            pad = max(abs(vmax - vmin) * 0.1, 1.0)
            lo, hi = vmin - pad, vmax + pad

    raw_bin = (hi - lo) / bins
    if raw_bin <= 0 or not np.isfinite(raw_bin):
        raw_bin = 1.0

    exp = math.floor(math.log10(raw_bin)) if raw_bin > 0 else 0
    frac = raw_bin / (10 ** exp) if raw_bin > 0 else 1
    nice = 1 if frac <= 1 else 2 if frac <= 2 else 5 if frac <= 5 else 10
    bin_size = nice * (10 ** exp)

    lo = math.floor(lo / bin_size) * bin_size
    hi = math.ceil(hi / bin_size) * bin_size
    return lo, hi, bin_size


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
    mean_val = round(float(np.mean(devs)), 2)
    median_val = round(float(np.median(devs)), 2)

    lo, hi, bin_size = _hist_bounds(devs, bins=80)

    # Split into exact zeros, negatives, non-negatives
    exact_zero = devs[devs == 0]
    negatives = devs[devs < 0]
    nonnegatives = devs[devs >= 0]

    fig = go.Figure()
    # Negative deviations
    if len(negatives) > 0:
        fig.add_trace(go.Histogram(
            x=negatives,
            xbins=dict(start=lo, end=0, size=bin_size),
            marker=dict(color="#3498db", line=dict(color="white", width=0.5)),
            opacity=0.8,
            name="Shipments",
            hovertemplate="Range: %{x}<br>Count: %{y:,}<extra></extra>",
            showlegend=False,
        ))
    # Exact matches shown as annotation (no separate bar)
    # Non-negative deviations (includes zeros)
    if len(nonnegatives) > 0:
        fig.add_trace(go.Histogram(
            x=nonnegatives,
            xbins=dict(start=0, end=hi, size=bin_size),
            marker=dict(color="#3498db", line=dict(color="white", width=0.5)),
            opacity=0.8,
            name="Shipments",
            showlegend=False,
            hovertemplate="Range: %{x}<br>Count: %{y:,}<extra></extra>",
        ))

    # Reference lines as shapes (no legend clutter)
    fmt = lambda v: f"${v:.2f}" if dev_col == "deviation" else f"{v:.2f}%"
    for val, color, label in [
        (0, "#2c3e50", "Zero"),
        (mean_val, "#e74c3c", f"Mean: {fmt(mean_val)}"),
        (median_val, "#27ae60", f"Median: {fmt(median_val)}"),
    ]:
        fig.add_shape(
            type="line", x0=val, x1=val, y0=0, y1=1, yref="paper",
            line=dict(dash="dash", color=color, width=1.5),
        )
        fig.add_trace(go.Scatter(
            x=[val, val], y=[0, 0], mode="lines",
            line=dict(dash="dash", color=color, width=2),
            name=label,
        ))

    if len(exact_zero) > 0:
        zero_pct = len(exact_zero) / len(devs) * 100
        fig.add_annotation(
            x=0, y=1, xref="x", yref="paper",
            text=(
                "<span style='background:#2c3e50;color:#fff;"
                "padding:4px 6px;border-radius:6px;'>"
                f"Exact match: {len(exact_zero):,} ({zero_pct:.1f}%)</span>"
            ),
            showarrow=False,
            yanchor="bottom",
        )
    fig.update_layout(
        title=f"Deviation Distribution (n={len(devs):,})",
        xaxis_title=dev_label,
        yaxis_title="Shipment Count",
        xaxis=dict(range=[lo, hi]),
        barmode="overlay",
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
    )
    apply_chart_layout(fig)
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

tab_pkg, tab_err, tab_zone, tab_weight, tab_site, tab_service = st.tabs([
    "By Package Type", "By Error Source", "By Zone", "By Weight Bracket",
    "By Production Site", "By Service Type"
])

segment_mode = st.radio(
    "Segment metric",
    ["Total", "Average per shipment"],
    key="accuracy_segment_mode",
    horizontal=True,
    index=0 if metric_mode == "Total" else 1,
)
use_avg_seg = segment_mode.startswith("Average")

def _stats_table(grouped_stats: list[dict], segment_label: str) -> None:
    exp_label = "Expected (Avg)" if use_avg_seg else "Expected"
    act_label = "Actual (Avg)" if use_avg_seg else "Actual"
    var_label = "Var ($/Shipment)" if use_avg_seg else "Var ($)"
    rows = []
    for s in grouped_stats:
        count = s["count"]
        expected = s["total_expected"] / count if use_avg_seg and count else s["total_expected"]
        actual = s["total_actual"] / count if use_avg_seg and count else s["total_actual"]
        variance = s["variance_dollars"] / count if use_avg_seg and count else s["variance_dollars"]
        rows.append({
            segment_label: s["segment"],
            "Count": f"{s['count']:,}",
            exp_label: format_currency(expected),
            act_label: format_currency(actual),
            var_label: format_currency(variance),
            "Var (%)": format_pct(s["variance_pct"]),
            "Mean Dev": format_currency(s["mean_dev"]),
            "Median Dev": format_currency(s["median_dev"]),
            "Std Dev": format_currency(s["std_dev"]),
            "Mean Abs Dev": format_currency(s["mad"]),
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
        lo_e, hi_e, bin_size_e = _hist_bounds(all_devs_np, bins=80)

        fig_e = go.Figure()
        for seg_name, color in COLORS.items():
            seg_devs = df.filter(pl.col("error_source") == seg_name)["deviation"].drop_nulls().cast(pl.Float64).to_numpy()
            n_seg = len(seg_devs)
            if n_seg == 0:
                continue

            negatives_e = seg_devs[seg_devs < 0]
            exact_zero_e = seg_devs[seg_devs == 0]
            nonnegatives_e = seg_devs[seg_devs >= 0]

            if len(negatives_e) > 0:
                fig_e.add_trace(go.Histogram(
                    x=negatives_e,
                    xbins=dict(start=lo_e, end=0, size=bin_size_e),
                    histnorm="percent",
                    marker_color=color, opacity=0.6,
                    name=f"{seg_name} (n={n_seg:,})",
                    legendgroup=seg_name,
                    hovertemplate="%{x:.2f}: %{y:.1f}%<extra></extra>",
                ))
            if len(exact_zero_e) > 0:
                zero_pct = len(exact_zero_e) / n_seg * 100
                fig_e.add_annotation(
                    x=0, y=1, xref="x", yref="paper",
                    text=(
                        "<span style='background:#2c3e50;color:#fff;"
                        "padding:3px 5px;border-radius:6px;'>"
                        f"{seg_name} exact: {zero_pct:.1f}%</span>"
                    ),
                    showarrow=False,
                    yanchor="bottom",
                )
            if len(nonnegatives_e) > 0:
                fig_e.add_trace(go.Histogram(
                    x=nonnegatives_e,
                    xbins=dict(start=0, end=hi_e, size=bin_size_e),
                    histnorm="percent",
                    marker_color=color, opacity=0.6,
                    name=f"{seg_name} (n={n_seg:,})",
                    legendgroup=seg_name,
                    showlegend=len(negatives_e) == 0,
                    hovertemplate="%{x:.2f}: %{y:.1f}%<extra></extra>",
                ))

        fig_e.update_layout(
            barmode="overlay",
            title="Deviation Distribution by Error Source (normalized)",
            xaxis_title="Deviation ($)",
            yaxis_title="% of Segment",
            xaxis=dict(range=[lo_e, hi_e]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        apply_chart_layout(fig_e)
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

with tab_service:
    services = sorted(df["service_type"].drop_nulls().unique().to_list())
    stats_srv = []
    for srv in services:
        seg = df.filter(pl.col("service_type") == srv)
        s = calc_segment_stats(seg)
        s["segment"] = srv
        stats_srv.append(s)
    _stats_table(stats_srv, "Service Type")

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
                "shipping_zip_code",
                "billable_weight_lbs", "longest_side_in", "second_longest_in",
                "cost_total", "actual_net_charge",
            ]
            # Filter to only existing columns
            available_cols = [c for c in detail_cols if c in df.columns]

            if len(fp_df) > 0:
                st.markdown(f"**False Positives** (predicted but not charged) — showing up to 20")
                st.dataframe(fp_df.select(available_cols).head(20), use_container_width=True, hide_index=True)
                csv_fp = fp_df.select(available_cols).to_pandas().to_csv(index=False)
                st.download_button(f"Download {surcharge.upper()} FP CSV", csv_fp,
                                   file_name=f"{surcharge}_false_positives.csv", mime="text/csv",
                                   key=f"dl_fp_{surcharge}")
            if len(fn_df) > 0:
                st.markdown(f"**False Negatives** (not predicted but charged) — showing up to 20")
                st.dataframe(fn_df.select(available_cols).head(20), use_container_width=True, hide_index=True)
                csv_fn = fn_df.select(available_cols).to_pandas().to_csv(index=False)
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
mismatch_cost = float((mismatch_df["actual_net_charge"] - mismatch_df["cost_total"]).sum()) if len(mismatch_df) > 0 else 0
c3.metric("Mismatch Cost Impact", format_currency(mismatch_cost))

# Confusion matrix
st.markdown("**Zone Confusion Matrix**")
heatmap_mode = st.radio(
    "Heatmap mode",
    ["Count", "Row %"],
    key="zone_heatmap_mode",
    horizontal=True,
)

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
    z_vals = matrix.copy()
    if heatmap_mode == "Row %":
        row_sums = z_vals.sum(axis=1)
        for i in range(len(row_sums)):
            if row_sums[i] > 0:
                z_vals[i] = z_vals[i] / row_sums[i] * 100
    for i in range(len(all_zones)):
        row_text = []
        for j in range(len(all_zones)):
            val = z_vals[i][j]
            if heatmap_mode == "Row %":
                row_text.append(f"{val:.1f}%" if val > 0 else "")
            else:
                row_text.append(f"{int(matrix[i][j]):,}" if matrix[i][j] > 0 else "")
        text_matrix.append(row_text)

    heatmap_kwargs = {}
    if heatmap_mode == "Row %":
        heatmap_kwargs = {"zmin": 0, "zmax": 100}

    fig_cm = go.Figure(go.Heatmap(
        z=z_vals,
        x=zone_labels,
        y=zone_labels,
        text=text_matrix,
        texttemplate="%{text}",
        textfont=dict(size=19, color="#1f2d3d"),
        colorscale=[[0, "#6f88b4"], [0.5, "#86a0c8"], [1, "#c0d3ea"]],
        zmin=0.001 if heatmap_mode == "Count" else 0.1,
        hovertemplate=(
            "Expected Zone: %{y}<br>Actual Zone: %{x}<br>"
            + ("Row %: %{z:.1f}%<extra></extra>" if heatmap_mode == "Row %" else "Count: %{z:,}<extra></extra>")
        ),
        **heatmap_kwargs,
    ))
    fig_cm.update_layout(
        title="Expected vs Actual Zone",
        xaxis_title="Actual Zone",
        yaxis_title="Expected Zone",
        yaxis=dict(autorange="reversed"),
        height=max(600, len(all_zones) * 45 + 200),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=70, b=60, l=60, r=20),
    )
    fig_cm.update_xaxes(title_font=dict(size=16), tickfont=dict(size=14))
    fig_cm.update_yaxes(title_font=dict(size=16), tickfont=dict(size=14))
    apply_chart_layout(fig_cm)
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
    pl.col("actual_rated_weight_lbs").is_not_null()
)

if len(valid_weight) > 0:
    exp_w = valid_weight["billable_weight_lbs"].cast(pl.Float64).to_numpy()
    act_w = valid_weight["actual_rated_weight_lbs"].cast(pl.Float64).to_numpy()
    diff_w = act_w - exp_w

    tolerance = 0.5
    w_matches = int(np.sum(np.abs(diff_w) <= tolerance))
    w_rate = w_matches / len(diff_w) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Weight Match Rate", f"{w_rate:.1f}%", help=f"Within +/-{tolerance} lbs")
    c2.metric("Matches / Total", f"{w_matches:,} / {len(diff_w):,}")
    c3.metric("Avg Difference", f"{np.mean(diff_w):+.2f} lbs")
    c4.metric("Actual > Expected", f"{(diff_w > 0).sum() / len(diff_w) * 100:.1f}%")

    w1, w2 = st.columns(2)
    w1.metric("Avg Expected Weight", f"{np.mean(exp_w):.2f} lbs")
    w2.metric("Avg Actual Weight", f"{np.mean(act_w):.2f} lbs")

    # Density contour — shows actual weight patterns instead of a point-cloud blob
    st.markdown("**Expected vs Actual Billable Weight**")

    max_w = float(np.max(np.concatenate([exp_w, act_w])))
    default_hi = min(50.0, max_w)
    weight_range = st.slider(
        "Weight range (lbs)",
        min_value=0.0,
        max_value=max(0.0, round(max_w, 1)),
        value=(0.0, default_hi),
        step=0.5,
        key="weight_range",
    )

    lo_w, hi_w = weight_range
    mask = (
        (exp_w >= lo_w) & (exp_w <= hi_w) &
        (act_w >= lo_w) & (act_w <= hi_w)
    )
    exp_w_plot = exp_w[mask]
    act_w_plot = act_w[mask]

    if len(exp_w_plot) == 0:
        st.info("No shipments within the selected weight range.")
    else:
        n_pts = len(exp_w_plot)
        if n_pts > 15000:
            idx = np.random.choice(n_pts, 15000, replace=False)
            px, py = exp_w_plot[idx], act_w_plot[idx]
        else:
            px, py = exp_w_plot, act_w_plot

        max_val = hi_w * 1.05

        fig_w = go.Figure()
        fig_w.add_trace(go.Scattergl(
            x=px, y=py,
            mode="markers",
            marker=dict(color="#3498db", size=10, opacity=0.35),
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
        fig_w.add_annotation(
            text="Actual > Expected",
            x=0.15, y=0.85, xref="paper", yref="paper",
            showarrow=False, font=dict(size=11, color="#999"),
        )
        fig_w.add_annotation(
            text="Actual < Expected",
            x=0.85, y=0.15, xref="paper", yref="paper",
            showarrow=False, font=dict(size=11, color="#999"),
        )
        fig_w.update_layout(
            title="Expected vs Actual Weight",
            xaxis_title="Expected Billable Weight (lbs)",
            yaxis_title="Actual Billed Weight (lbs)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        apply_chart_layout(fig_w)
        st.plotly_chart(fig_w, use_container_width=True)

    # Weight difference distribution
    st.markdown("**Weight Difference Distribution**")
    clipped = diff_w[(diff_w > -10) & (diff_w < 10)]

    wd_bin_size = 0.2  # clean 0.2 lbs bins, 0 is always a bin edge
    neg_wd = clipped[clipped < 0]
    zero_wd = clipped[clipped == 0]
    pos_wd = clipped[clipped >= 0]

    fig_wd = go.Figure()
    if len(neg_wd) > 0:
        fig_wd.add_trace(go.Histogram(
            x=neg_wd,
            xbins=dict(start=-10, end=0, size=wd_bin_size),
            marker=dict(color="#3498db", line=dict(color="white", width=0.5)),
            opacity=0.8,
            name="Shipments",
            showlegend=False,
            hovertemplate="Diff: %{x:.1f} lbs<br>Count: %{y:,}<extra></extra>",
        ))
    # Exact matches shown as annotation (no separate bar)
    if len(pos_wd) > 0:
        fig_wd.add_trace(go.Histogram(
            x=pos_wd,
            xbins=dict(start=0, end=10, size=wd_bin_size),
            marker=dict(color="#3498db", line=dict(color="white", width=0.5)),
            opacity=0.8,
            name="Shipments",
            showlegend=False,
            hovertemplate="Diff: %{x:.1f} lbs<br>Count: %{y:,}<extra></extra>",
        ))
    if len(zero_wd) > 0:
        zero_pct = len(zero_wd) / len(clipped) * 100 if len(clipped) > 0 else 0
        fig_wd.add_annotation(
            x=0, y=1, xref="x", yref="paper",
            text=(
                "<span style='background:#2c3e50;color:#fff;"
                "padding:4px 6px;border-radius:6px;'>"
                f"Exact match: {len(zero_wd):,} ({zero_pct:.1f}%)</span>"
            ),
            showarrow=False,
            yanchor="bottom",
        )
    fig_wd.update_layout(
        title="Weight Difference Distribution (clipped to +/-10 lbs)",
        xaxis_title="Weight Difference (Actual - Expected) lbs",
        yaxis_title="Count",
        barmode="overlay",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    apply_chart_layout(fig_wd)
    st.plotly_chart(fig_wd, use_container_width=True)
else:
    st.info("No valid weight data for comparison.")
