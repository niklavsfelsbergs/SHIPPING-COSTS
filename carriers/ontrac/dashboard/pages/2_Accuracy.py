"""
Page 2: Estimation Accuracy
============================

Deep-dive into shipment-level estimation precision: deviation analysis,
surcharge detection accuracy, zone accuracy, and weight accuracy.
"""

import polars as pl
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
    fig, ax = plt.subplots(figsize=(12, 5))
    p1, p99 = np.percentile(devs, [1, 99])
    margin = max(abs(p1), abs(p99)) * 0.2
    lo, hi = p1 - margin, p99 + margin
    ax.hist(devs, bins=80, range=(lo, hi), color="#3498db", alpha=0.8, edgecolor="white", linewidth=0.5)
    ax.axvline(0, color="#2c3e50", linestyle="--", linewidth=1.5, label="Zero")
    mean_val = np.mean(devs)
    median_val = np.median(devs)
    ax.axvline(mean_val, color="#e74c3c", linestyle="--", linewidth=1.5, label=f"Mean: {mean_val:.2f}")
    ax.axvline(median_val, color="#27ae60", linestyle="--", linewidth=1.5, label=f"Median: {median_val:.2f}")
    ax.set_xlabel(dev_label, fontsize=11)
    ax.set_ylabel("Shipment Count", fontsize=11)
    ax.set_title(f"Deviation Distribution (n={len(devs):,})", fontsize=13, fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

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
    fig_e, ax_e = plt.subplots(figsize=(12, 5))
    all_devs_np = df["deviation"].drop_nulls().cast(pl.Float64).to_numpy()
    if len(all_devs_np) > 0:
        p1, p99 = np.percentile(all_devs_np, [1, 99])
        margin = max(abs(p1), abs(p99)) * 0.2
        lo, hi = p1 - margin, p99 + margin
        for seg_name, color in COLORS.items():
            seg_devs = df.filter(pl.col("error_source") == seg_name)["deviation"].drop_nulls().cast(pl.Float64).to_numpy()
            if len(seg_devs) > 0:
                ax_e.hist(seg_devs, bins=80, range=(lo, hi), color=color, alpha=0.5,
                          edgecolor="white", linewidth=0.3, label=f"{seg_name} (n={len(seg_devs):,})")
        ax_e.axvline(0, color="#2c3e50", linestyle="--", linewidth=1.5, alpha=0.7)
        ax_e.set_xlabel("Deviation ($)")
        ax_e.set_ylabel("Shipment Count")
        ax_e.set_title("Deviation by Error Source")
        ax_e.legend()
        ax_e.grid(axis="y", alpha=0.3)
        fig_e.tight_layout()
        st.pyplot(fig_e)
    plt.close(fig_e)

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

    fig_cm, ax_cm = plt.subplots(figsize=(8, 6))
    im = ax_cm.imshow(matrix, cmap="Blues", aspect="auto")
    ax_cm.set_xticks(range(len(all_zones)))
    ax_cm.set_yticks(range(len(all_zones)))
    ax_cm.set_xticklabels([str(z) for z in all_zones])
    ax_cm.set_yticklabels([str(z) for z in all_zones])
    ax_cm.set_xlabel("Actual Zone")
    ax_cm.set_ylabel("Expected Zone")
    ax_cm.set_title("Expected vs Actual Zone (count)")

    for i in range(len(all_zones)):
        for j in range(len(all_zones)):
            val = int(matrix[i][j])
            if val > 0:
                color = "white" if val > matrix.max() * 0.5 else "black"
                ax_cm.text(j, i, f"{val:,}", ha="center", va="center", fontsize=9, color=color)

    fig_cm.colorbar(im, ax=ax_cm, shrink=0.8)
    fig_cm.tight_layout()
    st.pyplot(fig_cm)
    plt.close(fig_cm)

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

    # Scatter plot
    st.markdown("**Expected vs Actual Billable Weight**")
    fig_w, ax_w = plt.subplots(figsize=(8, 6))

    n_pts = len(exp_w)
    if n_pts > 5000:
        idx = np.random.choice(n_pts, 5000, replace=False)
        px, py = exp_w[idx], act_w[idx]
    else:
        px, py = exp_w, act_w

    ax_w.scatter(px, py, alpha=0.3, s=8, color="#3498db")
    max_val = max(np.max(px), np.max(py)) * 1.05
    ax_w.plot([0, max_val], [0, max_val], color="#e74c3c", linestyle="--", linewidth=1.5, label="Perfect match")
    ax_w.set_xlabel("Expected Billable Weight (lbs)")
    ax_w.set_ylabel("Actual Billed Weight (lbs)")
    ax_w.set_title("Expected vs Actual Weight")
    ax_w.legend()
    ax_w.grid(alpha=0.3)
    fig_w.tight_layout()
    st.pyplot(fig_w)
    plt.close(fig_w)

    # Weight difference distribution
    st.markdown("**Weight Difference Distribution**")
    fig_wd, ax_wd = plt.subplots(figsize=(10, 4))
    clipped = diff_w[(diff_w > -10) & (diff_w < 10)]
    ax_wd.hist(clipped, bins=60, color="#3498db", alpha=0.8, edgecolor="white")
    ax_wd.axvline(0, color="#2c3e50", linestyle="--", linewidth=1.5)
    ax_wd.set_xlabel("Weight Difference (Actual - Expected) lbs")
    ax_wd.set_ylabel("Count")
    ax_wd.set_title("Weight Difference Distribution (clipped to +/-10 lbs)")
    ax_wd.grid(axis="y", alpha=0.3)
    fig_wd.tight_layout()
    st.pyplot(fig_wd)
    plt.close(fig_wd)
else:
    st.info("No valid weight data for comparison.")
