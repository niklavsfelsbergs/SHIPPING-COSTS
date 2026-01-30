"""
OnTrac Analytics Dashboard
==========================

Multi-page Streamlit app for analyzing OnTrac shipping cost data.

Prerequisites:
    python -m carriers.ontrac.dashboard.export_data   # export data from Redshift

Run with:
    streamlit run carriers/ontrac/dashboard/OnTrac.py
"""

import streamlit as st

from carriers.ontrac.dashboard.data import init_page, join_grain_note

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="OnTrac Expected Cost Calculation",
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

st.title("OnTrac Expected Cost Calculation")
st.markdown(
    "Interactive dashboard for analyzing expected vs actual OnTrac shipping costs. "
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
    st.caption("KPIs, time series, cost breakdown")

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
    st.caption("Billing anomalies, surcharge surprises, trend monitoring")

with col4:
    st.page_link(
        "pages/4_Cost_Drivers.py",
        label="Cost Drivers",
        icon="💰",
    )
    st.caption("Surcharge frequency, dimensional analysis, geography, weight")

st.info(
    "Data loaded from local parquet snapshot. "
    "To refresh, run: `python -m carriers.ontrac.dashboard.export_data`"
)

note = join_grain_note(prepared_df)
if note:
    st.info(note)
