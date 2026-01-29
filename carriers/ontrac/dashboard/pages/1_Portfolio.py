"""
Page 1: Portfolio Overview
==========================

Executive overview with KPIs, time series, cost breakdown, and distribution snapshots.
"""

import polars as pl
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

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

    fig, ax1 = plt.subplots(figsize=(12, 4.5))
    ax1.plot(weekly_pd["week"], weekly_pd["Expected"], label="Expected", color="#3498db", linewidth=2)
    ax1.plot(weekly_pd["week"], weekly_pd["Actual"], label="Actual", color="#e74c3c", linewidth=2)
    ax1.fill_between(
        weekly_pd["week"], weekly_pd["Expected"], weekly_pd["Actual"],
        alpha=0.15, color="#e74c3c", label="Variance band",
    )
    ax1.set_ylabel("Total Cost ($)")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax1.legend(loc="upper left")
    ax1.grid(axis="y", alpha=0.3)
    ax1.set_title(f"Weekly Cost by {date_col}")
    fig.autofmt_xdate()
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
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

    x = np.arange(len(component_labels))
    width = 0.35

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.bar(x - width / 2, exp_values, width, label="Expected", color="#3498db", alpha=0.85)
    ax2.bar(x + width / 2, act_values, width, label="Actual", color="#e74c3c", alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels(component_labels, rotation=45, ha="right")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax2.legend()
    ax2.set_title("Cost Components: Expected vs Actual")
    ax2.grid(axis="y", alpha=0.3)
    fig2.tight_layout()
    st.pyplot(fig2)
    plt.close(fig2)

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
        fig3, ax3 = plt.subplots(figsize=(7, 4))
        zones = zc_pd["shipping_zone"].astype(str).tolist()
        counts = zc_pd["count"].tolist()
        ax3.bar(zones, counts, color="#3498db", alpha=0.85)
        ax3.set_xlabel("Zone")
        ax3.set_ylabel("Shipments")
        ax3.set_title("Shipment Count by Zone")
        ax3.grid(axis="y", alpha=0.3)
        for i, v in enumerate(counts):
            ax3.text(i, v + max(counts) * 0.01, f"{v:,}", ha="center", fontsize=9)
        fig3.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)

with right2:
    st.markdown("**Shipments by Production Site**")
    site_counts = (
        df.group_by("production_site")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    if len(site_counts) > 0:
        sc_pd = site_counts.to_pandas()
        fig4, ax4 = plt.subplots(figsize=(7, 4))
        ax4.bar(sc_pd["production_site"], sc_pd["count"], color="#27ae60", alpha=0.85)
        ax4.set_xlabel("Production Site")
        ax4.set_ylabel("Shipments")
        ax4.set_title("Shipment Count by Production Site")
        ax4.grid(axis="y", alpha=0.3)
        for i, v in enumerate(sc_pd["count"]):
            ax4.text(i, v + sc_pd["count"].max() * 0.01, f"{v:,}", ha="center", fontsize=9)
        fig4.tight_layout()
        st.pyplot(fig4)
        plt.close(fig4)

# Drilldown
drilldown_section(df, "Portfolio Data", key_suffix="portfolio")
