"""
Page 4: Cost Drivers
=====================

Understand what drives shipping costs: surcharge frequency, dimensional analysis,
zone/geography, and weight analysis.
"""

import polars as pl
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import numpy as np

from carriers.ontrac.dashboard.data import (
    SURCHARGE_COST_COLS,
    init_page,
    drilldown_section,
    format_currency,
)

st.set_page_config(page_title="Cost Drivers | OnTrac", layout="wide")
st.title("Cost Drivers")

# ---------------------------------------------------------------------------
prepared_df, match_data, df = init_page()

if len(df) == 0:
    st.warning("No data matches current filters.")
    st.stop()

total_shipments = len(df)


# ===========================================================================
# SECTION A — Surcharge Frequency & Cost Impact
# ===========================================================================

st.header("A. Surcharge Frequency & Cost Impact")

surcharge_info = [
    ("oml", "OML"), ("lps", "LPS"), ("ahs", "AHS"),
    ("das", "DAS"), ("edas", "EDAS"), ("res", "RES"),
    ("dem_oml", "DEM_OML"), ("dem_lps", "DEM_LPS"),
    ("dem_ahs", "DEM_AHS"), ("dem_res", "DEM_RES"),
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
    fig_f, ax_f = plt.subplots(figsize=(8, 5))
    labels = [d["Surcharge"] for d in freq_data]
    pcts = [d["pct"] for d in freq_data]
    colors = plt.cm.Set2(np.linspace(0, 1, len(labels)))
    bars = ax_f.barh(labels, pcts, color=colors)
    ax_f.set_xlabel("% of Shipments")
    ax_f.set_title("Surcharge Trigger Rate")
    ax_f.grid(axis="x", alpha=0.3)
    for bar, pct in zip(bars, pcts):
        if pct > 0.5:
            ax_f.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                      f"{pct:.1f}%", va="center", fontsize=9)
    ax_f.invert_yaxis()
    fig_f.tight_layout()
    st.pyplot(fig_f)
    plt.close(fig_f)

with right_a:
    st.markdown("**Total Cost Impact by Surcharge**")
    fig_c, ax_c = plt.subplots(figsize=(8, 5))
    costs = [d["total_cost"] for d in freq_data]
    ax_c.barh(labels, costs, color=colors)
    ax_c.set_xlabel("Total Cost ($)")
    ax_c.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_c.set_title("Total Cost by Surcharge")
    ax_c.grid(axis="x", alpha=0.3)
    ax_c.invert_yaxis()
    fig_c.tight_layout()
    st.pyplot(fig_c)
    plt.close(fig_c)

# Weekly surcharge trend
st.markdown("**Weekly Surcharge Trigger Trend**")

selected_surcharges = st.multiselect(
    "Select surcharges to display",
    [d["Surcharge"] for d in freq_data],
    default=["AHS", "LPS", "DAS", "RES"],
    key="surcharge_trend_select",
)

fig_st, ax_st = plt.subplots(figsize=(12, 4.5))
color_cycle = plt.cm.tab10(np.linspace(0, 1, 10))

date_col = st.session_state.get("sidebar_date_col", "billing_date")

for idx, item in enumerate(freq_data):
    if item["Surcharge"] not in selected_surcharges:
        continue
    cost_col = f"cost_{item['key']}"
    weekly = (
        df.with_columns(
            pl.col(date_col).cast(pl.Date).dt.truncate("1w").alias("week"),
            (pl.col(cost_col).fill_null(0) > 0).alias("triggered"),
        )
        .group_by("week")
        .agg([
            pl.len().alias("total"),
            pl.col("triggered").sum().alias("trig_count"),
        ])
        .with_columns(
            (pl.col("trig_count") / pl.col("total") * 100).alias("rate"),
        )
        .sort("week")
    )
    if len(weekly) > 0:
        w_pd = weekly.to_pandas()
        ax_st.plot(
            w_pd["week"], w_pd["rate"],
            label=item["Surcharge"],
            color=color_cycle[idx % 10],
            linewidth=1.5, marker="o", markersize=3,
        )

ax_st.set_ylabel("% of Shipments Triggered")
ax_st.set_title("Weekly Surcharge Frequency")
ax_st.legend(loc="upper right")
ax_st.grid(axis="y", alpha=0.3)
fig_st.autofmt_xdate()
fig_st.tight_layout()
st.pyplot(fig_st)
plt.close(fig_st)

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

    oml_flag = dim_df["surcharge_oml"].fill_null(False).to_numpy()
    lps_flag = dim_df["surcharge_lps"].fill_null(False).to_numpy()
    ahs_flag = dim_df["surcharge_ahs"].fill_null(False).to_numpy()

    cat_colors = np.full(len(dim_df), "#bdc3c7")
    cat_colors[ahs_flag] = "#f39c12"
    cat_colors[lps_flag] = "#e74c3c"
    cat_colors[oml_flag] = "#8e44ad"

    n = len(longest)
    if n > 5000:
        idx = np.random.choice(n, 5000, replace=False)
        longest_s, second_s, colors_s = longest[idx], second[idx], cat_colors[idx]
    else:
        longest_s, second_s, colors_s = longest, second, cat_colors

    fig_d, ax_d = plt.subplots(figsize=(10, 7))
    ax_d.scatter(longest_s, second_s, c=colors_s, alpha=0.4, s=10)

    ax_d.axhline(30, color="#f39c12", linestyle="--", linewidth=1.5, alpha=0.7, label="AHS: 2nd longest > 30\"")
    ax_d.axvline(48, color="#e74c3c", linestyle="--", linewidth=1.5, alpha=0.7, label="LPS: longest > 48\"")
    ax_d.axvline(72, color="#8e44ad", linestyle="--", linewidth=1.5, alpha=0.7, label="OML: longest > 72\"")

    legend_patches = [
        mpatches.Patch(color="#bdc3c7", label="No dim surcharge"),
        mpatches.Patch(color="#f39c12", label="AHS"),
        mpatches.Patch(color="#e74c3c", label="LPS"),
        mpatches.Patch(color="#8e44ad", label="OML"),
    ]
    ax_d.legend(handles=legend_patches, loc="upper left")
    ax_d.set_xlabel("Longest Side (in)")
    ax_d.set_ylabel("Second Longest Side (in)")
    ax_d.set_title("Package Dimensions with Surcharge Boundaries")
    ax_d.grid(alpha=0.3)
    fig_d.tight_layout()
    st.pyplot(fig_d)
    plt.close(fig_d)

    # Near-miss
    st.markdown("**Near-Miss Analysis** (within 1\" of surcharge threshold)")

    near_ahs = dim_df.filter((pl.col("second_longest_in") >= 29) & (pl.col("second_longest_in") < 30))
    near_lps = dim_df.filter((pl.col("longest_side_in") >= 47) & (pl.col("longest_side_in") < 48))
    near_oml = dim_df.filter((pl.col("longest_side_in") >= 71) & (pl.col("longest_side_in") < 72))

    nc1, nc2, nc3 = st.columns(3)
    nc1.metric("Near AHS (2nd longest 29-30\")", f"{len(near_ahs):,}")
    nc2.metric("Near LPS (longest 47-48\")", f"{len(near_lps):,}")
    nc3.metric("Near OML (longest 71-72\")", f"{len(near_oml):,}")

    # Potential savings
    st.markdown("**Potential Savings** — if packages were 1\" smaller")
    ahs_cost_per = float(df.filter(pl.col("cost_ahs") > 0)["cost_ahs"].mean()) if int((df["cost_ahs"].fill_null(0) > 0).sum()) > 0 else 0
    lps_cost_per = float(df.filter(pl.col("cost_lps") > 0)["cost_lps"].mean()) if int((df["cost_lps"].fill_null(0) > 0).sum()) > 0 else 0

    ahs_at_threshold = dim_df.filter(
        (pl.col("second_longest_in") >= 30) & (pl.col("second_longest_in") < 31)
        & (pl.col("surcharge_ahs").fill_null(False))
    )
    lps_at_threshold = dim_df.filter(
        (pl.col("longest_side_in") >= 48) & (pl.col("longest_side_in") < 49)
        & (pl.col("surcharge_lps").fill_null(False))
    )

    sc1, sc2 = st.columns(2)
    sc1.metric("AHS triggers at 30-31\"", f"{len(ahs_at_threshold):,}",
               help=f"Avg AHS cost: {format_currency(ahs_cost_per)}")
    sc2.metric("LPS triggers at 48-49\"", f"{len(lps_at_threshold):,}",
               help=f"Avg LPS cost: {format_currency(lps_cost_per)}")

    drilldown_section(ahs_at_threshold, "AHS Threshold Shipments (30-31\")", key_suffix="ahs_thresh")
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
        fig_sv, ax_sv = plt.subplots(figsize=(8, 6))
        ax_sv.barh(sv_pd["shipping_region"], sv_pd["count"], color="#3498db", alpha=0.85)
        ax_sv.set_xlabel("Shipments")
        ax_sv.set_title("Top 20 States by Volume")
        ax_sv.grid(axis="x", alpha=0.3)
        ax_sv.invert_yaxis()
        fig_sv.tight_layout()
        st.pyplot(fig_sv)
        plt.close(fig_sv)

with right_c:
    st.markdown("**Average Cost per Shipment by Zone**")
    zone_avg = (
        df.group_by("shipping_zone")
        .agg([
            pl.col("cost_total").mean().alias("avg_expected"),
            pl.col("actual_total").mean().alias("avg_actual"),
            pl.len().alias("count"),
        ])
        .sort("shipping_zone")
    )
    if len(zone_avg) > 0:
        za_pd = zone_avg.fill_null(0).to_pandas()
        fig_za, ax_za = plt.subplots(figsize=(8, 6))
        zones = za_pd["shipping_zone"].astype(str).tolist()
        x = np.arange(len(zones))
        w = 0.35
        ax_za.bar(x - w / 2, za_pd["avg_expected"], w, label="Expected", color="#3498db")
        ax_za.bar(x + w / 2, za_pd["avg_actual"], w, label="Actual", color="#e74c3c")
        ax_za.set_xticks(x)
        ax_za.set_xticklabels(zones)
        ax_za.set_xlabel("Zone")
        ax_za.set_ylabel("Avg Cost ($)")
        ax_za.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:.2f}"))
        ax_za.set_title("Average Cost per Shipment by Zone")
        ax_za.legend()
        ax_za.grid(axis="y", alpha=0.3)
        fig_za.tight_layout()
        st.pyplot(fig_za)
        plt.close(fig_za)

# Zone distribution by origin
st.markdown("**Zone Distribution by Origin**")
origin_zone = (
    df.group_by(["production_site", "shipping_zone"])
    .agg(pl.len().alias("count"))
    .sort(["production_site", "shipping_zone"])
)

sites_list = sorted(df["production_site"].drop_nulls().unique().to_list())
if len(sites_list) >= 1 and len(origin_zone) > 0:
    fig_oz, axes = plt.subplots(1, max(len(sites_list), 1),
                                 figsize=(5 * max(len(sites_list), 1), 4), sharey=True)
    if not isinstance(axes, np.ndarray):
        axes = [axes]

    for ax, site in zip(axes, sites_list):
        site_data = origin_zone.filter(pl.col("production_site") == site).to_pandas()
        if len(site_data) > 0:
            ax.bar(site_data["shipping_zone"].astype(str), site_data["count"], color="#3498db", alpha=0.85)
            ax.set_title(site)
            ax.set_xlabel("Zone")
            ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("Shipments")
    fig_oz.suptitle("Zone Distribution by Production Site", fontsize=13, fontweight="bold")
    fig_oz.tight_layout()
    st.pyplot(fig_oz)
    plt.close(fig_oz)

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
        fig_wh, ax_wh = plt.subplots(figsize=(8, 5))

        max_display = min(np.percentile(billable_wt, 99) * 1.2, 100)
        ax_wh.hist(actual_wt[actual_wt < max_display], bins=60, alpha=0.6,
                    color="#3498db", label="Actual Weight", edgecolor="white")
        ax_wh.hist(dim_wt[dim_wt < max_display], bins=60, alpha=0.5,
                    color="#e74c3c", label="DIM Weight", edgecolor="white")
        ax_wh.set_xlabel("Weight (lbs)")
        ax_wh.set_ylabel("Count")
        ax_wh.set_title("Actual vs DIM Weight Distribution")
        ax_wh.legend()
        ax_wh.grid(axis="y", alpha=0.3)
        fig_wh.tight_layout()
        st.pyplot(fig_wh)
        plt.close(fig_wh)

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

        fig_pie, ax_pie = plt.subplots(figsize=(6, 4))
        ax_pie.pie(
            [dim_pct, 100 - dim_pct],
            labels=["DIM Weight", "Actual Weight"],
            colors=["#e74c3c", "#3498db"],
            autopct="%1.1f%%",
            startangle=90,
        )
        ax_pie.set_title("Billable Weight Basis")
        fig_pie.tight_layout()
        st.pyplot(fig_pie)
        plt.close(fig_pie)

    drilldown_section(
        valid.filter(pl.col("uses_dim_weight").fill_null(False)),
        "DIM Weight Shipments",
        columns=[
            "pcs_orderid", "pcs_ordernumber", "packagetype",
            "weight_lbs", "dim_weight_lbs", "billable_weight_lbs",
            "longest_side_in", "second_longest_in", "cubic_in",
            "cost_total", "actual_total",
        ],
        key_suffix="dim_weight",
    )
else:
    st.info("No weight data available.")
