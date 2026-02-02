"""
FedEx Analytics Dashboard
==========================

Multi-page Streamlit app for analyzing FedEx shipping cost data.

Prerequisites:
    python -m carriers.fedex.dashboard.export_data   # export data from Redshift

Run with:
    streamlit run carriers/fedex/dashboard/FedEx.py
"""

import streamlit as st

from carriers.fedex.dashboard.data import init_page, join_grain_note

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="FedEx Expected Cost Calculation",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    div[data-testid="stAlert"] p {
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# DATA + SIDEBAR FILTERS (shared via init_page)
# =============================================================================

prepared_df, match_rate_data, df = init_page()

# =============================================================================
# LANDING PAGE
# =============================================================================

st.title("FedEx Expected Cost Calculation")
st.markdown(
    "Interactive dashboard for analyzing expected vs actual FedEx shipping costs "
    "(Home Delivery and Ground Economy). "
    "Use the **sidebar** to filter data, then navigate to a page below."
)

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.page_link(
        "pages/1_Portfolio.py",
        label="Portfolio Overview",
        icon="📊",
    )
    st.caption("KPIs, time series, service comparison, cost breakdown")

with col2:
    st.page_link(
        "pages/2_Accuracy.py",
        label="Estimation Accuracy",
        icon="🎯",
    )
    st.caption("Deviation analysis, surcharge detection, zone & weight accuracy")

with col3:
    st.page_link(
        "pages/3_Anomalies.py",
        label="Anomaly Detection",
        icon="🔍",
    )
    st.caption("Billing anomalies, unpredictable charges, SmartPost 10+ lb issues")

with col4:
    st.page_link(
        "pages/4_Cost_Drivers.py",
        label="Cost Drivers",
        icon="💰",
    )
    st.caption("Service type, discount impact, DAS tiers, SmartPost weight cliff")

st.info(
    "Data loaded from local parquet snapshot. "
    "To refresh, run: `python -m carriers.fedex.dashboard.export_data`"
)

note = join_grain_note(prepared_df)
if note:
    st.info(note)
