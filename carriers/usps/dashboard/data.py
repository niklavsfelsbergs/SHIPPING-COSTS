"""
Dashboard Data Layer
====================

Layered caching architecture:
  1. load_raw()          - reads parquet from disk (cached, no TTL)
  2. prepare_df()        - adds derived columns (cached on df hash)
  3. get_filtered_df()   - applies sidebar filters (cached on filter params)

Pages call get_filtered_df() directly - no session_state bus.

Convention: Polars for all transforms. Convert to pandas only at plot time
via df.to_pandas() in page code.
"""

import json
from datetime import date, timedelta
from pathlib import Path

import polars as pl
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
UNMATCHED_EXPECTED_PATH = DATA_DIR / "unmatched_expected.parquet"
UNMATCHED_ACTUAL_PATH = DATA_DIR / "unmatched_actual.parquet"

# Cost positions: (expected_col, actual_col, label)
# Note: USPS actual_base includes peak, so we compare (cost_base + cost_peak) vs actual_base
COST_POSITIONS = [
    ("cost_base_with_peak", "actual_base", "Base"),  # Combined for comparison
    ("cost_nsl1", "actual_nsl1", "NSL1"),
    ("cost_nsl2", "actual_nsl2", "NSL2"),
    ("cost_nsv", "actual_noncompliance", "NSV"),  # NSV maps to noncompliance
    ("cost_total", "actual_total", "TOTAL"),
]

# Raw cost positions (for internal use where we need original columns)
COST_POSITIONS_RAW = [
    ("cost_base", "actual_base", "Base (raw)"),
    ("cost_nsl1", "actual_nsl1", "NSL1"),
    ("cost_nsl2", "actual_nsl2", "NSL2"),
    ("cost_nsv", "actual_noncompliance", "NSV"),
    ("cost_peak", None, "Peak"),
    ("cost_total", "actual_total", "TOTAL"),
]

DETERMINISTIC_SURCHARGES = ["nsl1", "nsl2"]  # NSV is noncompliance, different category

SURCHARGE_COST_COLS = [
    "cost_nsl1", "cost_nsl2", "cost_nsv", "cost_peak",
]

WEIGHT_BRACKETS = [
    (0, 1, "0-1 lbs"),
    (1, 5, "1-5 lbs"),
    (5, 10, "5-10 lbs"),
    (10, 20, "10-20 lbs"),
]

# Charge types available for include/exclude filtering
# Maps label -> (expected_col, actual_col)
CHARGE_TYPES = {
    "NSL1": ("cost_nsl1", "actual_nsl1"),
    "NSL2": ("cost_nsl2", "actual_nsl2"),
    "NSV": ("cost_nsv", "actual_noncompliance"),
}
ALL_CHARGE_LABELS = list(CHARGE_TYPES.keys())

# Cost positions available for zeroing-out in analysis
# Maps label -> (expected_col, actual_col)
COST_POSITION_MAP = {
    label: (exp_col, act_col)
    for exp_col, act_col, label in COST_POSITIONS
    if label != "TOTAL"
}
ALL_POSITION_LABELS = list(COST_POSITION_MAP.keys())

PRIMARY_KEY = "pcs_orderid"


def join_grain_note(df: pl.DataFrame) -> str | None:
    """Explain join grain when expected rows are duplicated across actual line items."""
    n_unique = df[PRIMARY_KEY].n_unique()
    n_total = len(df)
    if n_unique == n_total:
        return None
    return (
        f"Join grain note: {n_total:,} rows but {n_unique:,} unique "
        f"{PRIMARY_KEY} values. Expected rows are duplicated for each matching "
        "actual invoice row. Interpret totals at the shipment/line-item grain."
    )


# =============================================================================
# LAYER 1 - Raw data from disk (cached, never re-reads during session)
# =============================================================================

@st.cache_data
def load_raw() -> pl.DataFrame:
    """Load comparison dataset from parquet. Cached for entire session."""
    path = DATA_DIR / "comparison.parquet"
    if not path.exists():
        st.error(
            f"Data file not found: {path}\n\n"
            "Run `python -m carriers.usps.dashboard.export_data` first."
        )
        st.stop()
    return pl.read_parquet(path)


@st.cache_data
def load_match_rate() -> dict:
    """Load match rate counts from JSON. Cached for entire session."""
    path = DATA_DIR / "match_rate.json"
    if not path.exists():
        return {"actual_orderids": 0, "matched_orderids": 0}
    return json.loads(path.read_text())


@st.cache_data
def load_unmatched_expected() -> pl.DataFrame:
    """Load expected shipments without actuals (if exported)."""
    if not UNMATCHED_EXPECTED_PATH.exists():
        return pl.DataFrame()
    return pl.read_parquet(UNMATCHED_EXPECTED_PATH)


@st.cache_data
def load_unmatched_actual() -> pl.DataFrame:
    """Load actual shipments without expecteds (if exported)."""
    if not UNMATCHED_ACTUAL_PATH.exists():
        return pl.DataFrame()
    return pl.read_parquet(UNMATCHED_ACTUAL_PATH)


# =============================================================================
# LAYER 2 - Prepared data with derived columns (cached on df identity)
# =============================================================================

@st.cache_data
def prepare_df(df: pl.DataFrame, grain: str = "line") -> pl.DataFrame:
    """Add all derived columns. Cached - only recomputes if raw df changes."""
    # Cast Decimal columns to Float64 (Redshift exports Decimal; Polars
    # aggregations like .mean() break on Decimal dtype)
    decimal_cols = [c for c in df.columns if str(df[c].dtype).startswith("Decimal")]
    if decimal_cols:
        df = df.with_columns([pl.col(c).cast(pl.Float64) for c in decimal_cols])

    # Create combined base+peak column for comparison (USPS invoices include peak in base)
    df = df.with_columns(
        (pl.col("cost_base").fill_null(0) + pl.col("cost_peak").fill_null(0)).alias("cost_base_with_peak")
    )

    # Normalize zones for comparison
    # shipping_zone: '1*', '2', '2*', '3', etc. -> strip asterisk, keep as string
    # actual_zone: '01', '02', '03', etc. -> strip leading zeros
    df = df.with_columns([
        pl.col("shipping_zone")
            .str.replace(r"\*", "")
            .alias("shipping_zone_normalized"),
        pl.col("actual_zone")
            .str.strip_chars_start("0")
            .fill_null("")
            .alias("actual_zone_normalized"),
    ])
    # Handle edge case where actual_zone was "0" -> becomes empty string
    df = df.with_columns(
        pl.when(pl.col("actual_zone_normalized") == "")
        .then(pl.col("actual_zone"))
        .otherwise(pl.col("actual_zone_normalized"))
        .alias("actual_zone_normalized")
    )

    # Deviation
    df = df.with_columns(
        (pl.col("actual_total") - pl.col("cost_total")).alias("deviation"),
        pl.when(pl.col("cost_total") != 0)
        .then((pl.col("actual_total") - pl.col("cost_total")) / pl.col("cost_total") * 100)
        .otherwise(0.0)
        .alias("deviation_pct"),
    )

    # Error source segment
    surcharge_correct = (
        (pl.col("surcharge_nsl1").fill_null(False) == (pl.col("actual_nsl1").fill_null(0) > 0))
        & (pl.col("surcharge_nsl2").fill_null(False) == (pl.col("actual_nsl2").fill_null(0) > 0))
    )
    # Use normalized zones for comparison
    zone_matches = pl.col("shipping_zone_normalized") == pl.col("actual_zone_normalized")

    df = df.with_columns(
        pl.when(~surcharge_correct)
        .then(pl.lit("Surcharge mismatch"))
        .when(~zone_matches)
        .then(pl.lit("Zone mismatch only"))
        .otherwise(pl.lit("Clean match"))
        .alias("error_source"),
    )

    # Weight bracket
    expr = pl.lit("Unknown")
    for lower, upper, label in reversed(WEIGHT_BRACKETS):
        if upper == float("inf"):
            expr = (
                pl.when(pl.col("billable_weight_lbs") >= lower)
                .then(pl.lit(label))
                .otherwise(expr)
            )
        else:
            expr = (
                pl.when(
                    (pl.col("billable_weight_lbs") >= lower)
                    & (pl.col("billable_weight_lbs") < upper)
                )
                .then(pl.lit(label))
                .otherwise(expr)
            )
    df = df.with_columns(expr.alias("weight_bracket"))

    # Zone match (use normalized zones)
    df = df.with_columns(
        (pl.col("shipping_zone_normalized") == pl.col("actual_zone_normalized")).alias("zone_match"),
    )

    return df


@st.cache_data
def aggregate_shipments(df: pl.DataFrame) -> pl.DataFrame:
    """Aggregate actuals to shipment-level (pcs_orderid)."""
    base_cols = [
        "pcs_ordernumber", "shop_ordernumber", "latest_trackingnumber",
        "pcs_created", "ship_date", "production_site",
        "shipping_zip_code", "shipping_region", "shipping_country", "packagetype",
        "shipping_zone", "rate_zone", "billable_weight_lbs",
        "length_in", "width_in", "height_in", "weight_lbs",
        "cubic_in", "longest_side_in", "second_longest_in", "length_plus_girth",
        "dim_weight_lbs", "uses_dim_weight",
    ]

    expected_flag_cols = [c for c in df.columns if c.startswith("surcharge_")]
    expected_cost_cols = [c for c in df.columns if c.startswith("cost_")]
    actual_sum_cols = [
        c for c in df.columns
        if c.startswith("actual_") and c not in {
            "actual_zone", "actual_billed_weight_lbs", "actual_trackingnumber"
        }
    ]

    agg_exprs = []
    for col in base_cols:
        if col in df.columns:
            agg_exprs.append(pl.col(col).first())
    for col in expected_flag_cols:
        agg_exprs.append(pl.col(col).first())
    for col in expected_cost_cols:
        agg_exprs.append(pl.col(col).first())

    if "actual_trackingnumber" in df.columns:
        agg_exprs.append(pl.col("actual_trackingnumber").sort_by("billing_date").first())
    if "billing_date" in df.columns:
        agg_exprs.append(pl.col("billing_date").min().alias("billing_date"))
    if "actual_zone" in df.columns:
        agg_exprs.append(pl.col("actual_zone").drop_nulls().mode().first().alias("actual_zone"))
    if "actual_billed_weight_lbs" in df.columns:
        agg_exprs.append(pl.col("actual_billed_weight_lbs").max())
    if "has_adjustment" in df.columns:
        agg_exprs.append(pl.col("has_adjustment").max())

    for col in actual_sum_cols:
        agg_exprs.append(pl.col(col).sum())

    return df.group_by(PRIMARY_KEY).agg(agg_exprs)


@st.cache_data
def load_shipment_df() -> pl.DataFrame:
    """Load shipment-level dataset aggregated by pcs_orderid."""
    raw_df = load_raw()
    ship_df = aggregate_shipments(raw_df)
    return prepare_df(ship_df, grain="shipment")


# =============================================================================
# LAYER 3 - Filtered data (cached on filter parameters)
# =============================================================================

@st.cache_data
def get_filtered_df(
    _prepared_df: pl.DataFrame,
    date_from: date | None = None,
    date_to: date | None = None,
    date_col: str = "ship_date",
    sites: tuple[str, ...] | None = None,
    packagetypes: tuple[str, ...] | None = None,
    charges: tuple[str, ...] = (),
    positions: tuple[str, ...] = (),
    grain: str = "line",
) -> pl.DataFrame:
    """
    Apply sidebar filters and return result.

    Cached on filter parameter values - changing a chart tab or scrolling
    does NOT re-filter. Only changing a sidebar filter does.

    Args use tuple (hashable) instead of list for cache compatibility.
    """
    df = _prepared_df

    if date_from is not None:
        df = df.filter(pl.col(date_col).cast(pl.Date) >= date_from)
    if date_to is not None:
        df = df.filter(pl.col(date_col).cast(pl.Date) <= date_to)
    if sites:
        df = df.filter(pl.col("production_site").is_in(list(sites)))
    if packagetypes:
        df = df.filter(pl.col("packagetype").is_in(list(packagetypes)))

    # Shipment charges: unchecked = exclude shipments with that charge
    # in either expected or actual.
    excluded_charges = set(ALL_CHARGE_LABELS) - set(charges)
    for label in excluded_charges:
        exp_col, act_col = CHARGE_TYPES[label]
        df = df.filter(
            (pl.col(exp_col).fill_null(0) <= 0) & (pl.col(act_col).fill_null(0) <= 0)
        )

    # Cost positions: unchecked = zero out on both sides.
    excluded_pos = set(ALL_POSITION_LABELS) - set(positions)
    if excluded_pos:
        zero_exprs = []
        for label in excluded_pos:
            exp_col, act_col = COST_POSITION_MAP[label]
            zero_exprs.append(pl.lit(0.0).alias(exp_col))
            if act_col:
                zero_exprs.append(pl.lit(0.0).alias(act_col))

        df = df.with_columns(zero_exprs)
        # Recompute totals from remaining positions
        exp_cols = [exp for exp, _, lbl in COST_POSITIONS if lbl != "TOTAL"]
        act_cols = [act for _, act, lbl in COST_POSITIONS if lbl != "TOTAL" and act]
        df = df.with_columns(
            pl.sum_horizontal(*[pl.col(c) for c in exp_cols]).alias("cost_total"),
            pl.sum_horizontal(*[pl.col(c) for c in act_cols]).alias("actual_total"),
            (pl.sum_horizontal(*[pl.col(c) for c in act_cols])
             - pl.sum_horizontal(*[pl.col(c) for c in exp_cols])).alias("deviation"),
        )
        df = df.with_columns(
            pl.when(pl.col("cost_total") != 0)
            .then(pl.col("deviation") / pl.col("cost_total") * 100)
            .otherwise(0.0)
            .alias("deviation_pct"),
        )

    return df


# =============================================================================
# PAGE INIT - shared sidebar + data loading for all pages
# =============================================================================

def init_page() -> tuple[pl.DataFrame, dict, pl.DataFrame]:
    """
    Load data, render sidebar filters, return (prepared_df, match_rate_data, filtered_df).

    Call at the top of every page (including app.py) so the sidebar filters
    appear regardless of which page the user navigates to.
    """
    raw_df = load_raw()
    prepared_df = prepare_df(raw_df, grain="line")
    match_rate_data = load_match_rate()

    _render_sidebar(prepared_df)

    date_label = st.session_state.get("sidebar_date_col", "Ship Date")
    date_col = "billing_date" if date_label == "Billing Date" else "ship_date"

    filtered_df = get_filtered_df(
        prepared_df,
        date_from=st.session_state.get("filter_date_from"),
        date_to=st.session_state.get("filter_date_to"),
        date_col=date_col,
        sites=st.session_state.get("filter_sites"),
        packagetypes=st.session_state.get("filter_packagetypes"),
        charges=st.session_state.get("filter_charges", tuple(ALL_CHARGE_LABELS)),
        positions=st.session_state.get("filter_positions", tuple(ALL_POSITION_LABELS)),
        grain="line",
    )

    return prepared_df, match_rate_data, filtered_df


def get_filtered_shipments() -> pl.DataFrame:
    """Return shipment-level data filtered by current sidebar settings."""
    ship_df = load_shipment_df()
    date_label = st.session_state.get("sidebar_date_col", "Ship Date")
    date_col = "billing_date" if date_label == "Billing Date" else "ship_date"
    return get_filtered_df(
        ship_df,
        date_from=st.session_state.get("filter_date_from"),
        date_to=st.session_state.get("filter_date_to"),
        date_col=date_col,
        sites=st.session_state.get("filter_sites"),
        packagetypes=st.session_state.get("filter_packagetypes"),
        charges=st.session_state.get("filter_charges", tuple(ALL_CHARGE_LABELS)),
        positions=st.session_state.get("filter_positions", tuple(ALL_POSITION_LABELS)),
        grain="shipment",
    )


def _checkbox_dropdown(
    label: str,
    options: list[str],
    default_checked: bool = False,
    key_prefix: str = "",
) -> list[str]:
    """Expander with checkboxes, persisted via user-managed session_state dict."""
    state_key = f"_persist_{key_prefix}"
    expanded_key = f"_expanded_{key_prefix}"

    # Initialise persistent dict on first ever run
    if state_key not in st.session_state:
        st.session_state[state_key] = {opt: default_checked for opt in options}
    saved = st.session_state[state_key]

    # Initialize expanded state (default collapsed)
    if expanded_key not in st.session_state:
        st.session_state[expanded_key] = False

    # Ensure new options get a default
    for opt in options:
        if opt not in saved:
            saved[opt] = default_checked

    # Sync from widget keys - if user changed a checkbox, mark as should stay open
    for opt in options:
        wkey = f"{key_prefix}_{opt}"
        if wkey in st.session_state and st.session_state[wkey] != saved[opt]:
            st.session_state[expanded_key] = True
            saved[opt] = st.session_state[wkey]

    n_selected = sum(saved[opt] for opt in options)

    def _set_all(target):
        st.session_state[f"{key_prefix}__bulk"] = True
        s = st.session_state[state_key]
        for o in options:
            s[o] = target
            st.session_state[f"{key_prefix}_{o}"] = target

    # Also keep open if All/None button was just clicked
    if st.session_state.pop(f"{key_prefix}__bulk", False):
        st.session_state[expanded_key] = True

    with st.sidebar.expander(f"{label} ({n_selected}/{len(options)})", expanded=st.session_state[expanded_key]):
        col_a, col_b = st.columns(2)
        col_a.button("All", key=f"{key_prefix}__btn_all", use_container_width=True,
                      on_click=_set_all, args=(True,))
        col_b.button("None", key=f"{key_prefix}__btn_none", use_container_width=True,
                      on_click=_set_all, args=(False,))
        for opt in options:
            wkey = f"{key_prefix}_{opt}"
            if wkey in st.session_state:
                val = st.checkbox(opt, key=wkey)
            else:
                val = st.checkbox(opt, value=saved[opt], key=wkey)
            saved[opt] = val

    st.session_state[state_key] = saved
    return [opt for opt in options if saved[opt]]


def _render_sidebar(prepared_df: pl.DataFrame) -> None:
    """Render sidebar filters shared across all pages."""
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            min-width: 360px !important;
            max-width: 360px !important;
        }
        section[data-testid="stSidebar"] > div {
            min-width: 360px !important;
            max-width: 360px !important;
        }
        [data-testid="stSidebar"] .sidebar-divider {
            height: 2px;
            background: #b9acbb;
            opacity: 0.6;
            margin: 10px 0;
            width: 100%;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] > details {
            background: transparent;
            border: none;
            padding: 0;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] > details > summary {
            background: #a092a1;
            border: 1px solid #8e8190;
            border-radius: 6px;
            padding: 6px 8px;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] > details[open] > summary {
            border-bottom-left-radius: 0;
            border-bottom-right-radius: 0;
        }
        [data-testid="stSidebar"] [data-testid="stDateInput"] [data-baseweb="input"] {
            background: #a092a1;
            border: 1px solid #8e8190;
            border-radius: 6px;
        }
        [data-testid="stSidebar"] [data-testid="stDateInput"] [data-baseweb="input"] input {
            background: transparent;
            color: #ffffff;
        }
        [data-testid="stSidebar"] [data-testid="stDateInput"] [data-baseweb="input"] > div {
            background: transparent;
        }
        [data-testid="stSidebar"] [data-testid="stDateInput"] svg {
            color: #ffffff;
            fill: #ffffff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.subheader("Filters")

    # Time axis for time-series charts
    time_axis_options = ["Ship Date", "Billing Date"]
    if "filter_time_axis" not in st.session_state:
        st.session_state["filter_time_axis"] = "Ship Date"
    time_axis_idx = time_axis_options.index(st.session_state["filter_time_axis"])
    time_axis = st.sidebar.radio(
        "Time axis",
        time_axis_options,
        index=time_axis_idx,
        horizontal=True,
        key="sidebar_date_col",
    )
    st.session_state["filter_time_axis"] = time_axis

    # Time grain for time-series charts
    time_grain_options = ["Daily", "Weekly", "Monthly"]
    if "filter_time_grain" not in st.session_state:
        st.session_state["filter_time_grain"] = "Daily"
    time_grain_idx = time_grain_options.index(st.session_state["filter_time_grain"])
    time_grain = st.sidebar.radio(
        "Time grain",
        time_grain_options,
        index=time_grain_idx,
        horizontal=True,
        key="sidebar_time_grain",
    )
    st.session_state["filter_time_grain"] = time_grain

    # Date range (depends on selected date column)
    date_label = st.session_state.get("sidebar_date_col", "Ship Date")
    date_col = "billing_date" if date_label == "Billing Date" else "ship_date"
    if date_col in prepared_df.columns:
        date_series = prepared_df[date_col].cast(pl.Date)
        min_date = date_series.min()
        max_date = date_series.max()
    else:
        min_date, max_date = None, None

    if min_date is not None and max_date is not None:
        # Initialize filter values only on first load
        if "filter_date_from" not in st.session_state:
            fixed_from = date(2026, 1, 1)
            fixed_to = date(2026, 1, 31)
            st.session_state["filter_date_from"] = max(min_date, fixed_from)
            st.session_state["filter_date_to"] = min(max_date, fixed_to)
            if st.session_state["filter_date_from"] > st.session_state["filter_date_to"]:
                st.session_state["filter_date_from"] = min_date
                st.session_state["filter_date_to"] = max_date

        # Use persisted values for widget default
        current_from = st.session_state["filter_date_from"]
        current_to = st.session_state["filter_date_to"]
        # Clamp to valid range
        current_from = max(min_date, min(max_date, current_from))
        current_to = max(min_date, min(max_date, current_to))

        date_range = st.sidebar.date_input(
            f"{date_label} Range",
            value=(current_from, current_to),
            min_value=min_date,
            max_value=max_date,
        )
        # Only update when both dates are selected (len == 2)
        # When user is mid-selection (len == 1), keep previous values
        if isinstance(date_range, tuple) and len(date_range) == 2:
            st.session_state["filter_date_from"] = date_range[0]
            st.session_state["filter_date_to"] = date_range[1]
    else:
        st.sidebar.warning("No data loaded.")

    # Metric mode
    metric_options = ["Total", "Average per shipment"]
    if "filter_metric_mode" not in st.session_state:
        st.session_state["filter_metric_mode"] = "Total"
    metric_idx = metric_options.index(st.session_state["filter_metric_mode"])
    metric_mode = st.sidebar.radio(
        "Metric mode",
        metric_options,
        index=metric_idx,
        horizontal=True,
        key="metric_mode",
    )
    st.session_state["filter_metric_mode"] = metric_mode

    # Production site
    all_sites = sorted(prepared_df["production_site"].drop_nulls().unique().to_list())
    selected_sites = _checkbox_dropdown(
        "Production site", all_sites, default_checked=True, key_prefix="site"
    )
    st.session_state["filter_sites"] = tuple(selected_sites)

    # Package type
    all_packages = sorted(prepared_df["packagetype"].drop_nulls().unique().to_list())
    selected_packages = _checkbox_dropdown(
        "Package type", all_packages, default_checked=True, key_prefix="pkg"
    )
    st.session_state["filter_packagetypes"] = tuple(selected_packages)

    # --- Shipment Charges ---
    st.sidebar.caption("Uncheck to exclude shipments with that charge")

    selected_charges = _checkbox_dropdown(
        "Charges", ALL_CHARGE_LABELS, default_checked=True, key_prefix="chg"
    )
    st.session_state["filter_charges"] = tuple(selected_charges)

    # --- Cost Positions ---
    st.sidebar.caption("Uncheck to zero out a cost component")

    selected_positions = _checkbox_dropdown(
        "Positions", ALL_POSITION_LABELS, default_checked=True, key_prefix="pos"
    )
    st.session_state["filter_positions"] = tuple(selected_positions)

    # Filter summary
    st.sidebar.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)
    st.sidebar.metric("Total in dataset", f"{len(prepared_df):,}")


# =============================================================================
# STAT HELPERS
# =============================================================================

def calc_segment_stats(df: pl.DataFrame) -> dict:
    """Calculate summary stats for a segment of shipments."""
    n = len(df)
    if n == 0:
        return {
            "count": 0, "total_expected": 0, "total_actual": 0,
            "variance_dollars": 0, "variance_pct": 0,
            "mean_dev": 0, "median_dev": 0, "std_dev": 0, "mad": 0,
            "within_1": 0, "within_2": 0, "within_5": 0,
        }

    devs = df["deviation"]
    total_exp = df["cost_total"].sum()
    total_act = df["actual_total"].sum()
    var_d = total_act - total_exp
    abs_dev = devs.abs()

    return {
        "count": n,
        "total_expected": total_exp,
        "total_actual": total_act,
        "variance_dollars": var_d,
        "variance_pct": (var_d / total_exp * 100) if total_exp != 0 else 0,
        "mean_dev": devs.mean(),
        "median_dev": devs.median(),
        "std_dev": devs.std() if n > 1 else 0,
        "mad": abs_dev.mean(),
        "within_1": (abs_dev <= 1.0).sum() / n * 100,
        "within_2": (abs_dev <= 2.0).sum() / n * 100,
        "within_5": (abs_dev <= 5.0).sum() / n * 100,
    }


# =============================================================================
# DRILLDOWN HELPER
# =============================================================================

def drilldown_section(
    df: pl.DataFrame,
    label: str,
    columns: list[str] | None = None,
    max_rows: int = 200,
    key_suffix: str = "",
):
    """
    Reusable drilldown drawer: dimension selector -> filtered table -> CSV download.

    Call from any page after a chart/section to let users slice and export.
    """
    if len(df) == 0:
        return

    default_cols = [
        "pcs_orderid", "pcs_ordernumber", "shop_ordernumber",
        "ship_date", "production_site", "packagetype", "shipping_zone", "actual_zone",
        "shipping_zip_code", "billable_weight_lbs", "cost_total", "actual_total", "deviation",
    ]
    display_cols = columns or default_cols
    available = [c for c in display_cols if c in df.columns]

    with st.expander(f"Drilldown: {label} ({len(df):,} rows)"):
        # Dimension selector
        dim_options = ["(none)"] + [
            c for c in ["production_site", "shipping_zone", "packagetype", "error_source", "weight_bracket"]
            if c in df.columns
        ]
        dim = st.selectbox(
            "Slice by dimension",
            dim_options,
            key=f"drill_dim_{key_suffix}",
        )

        view_df = df
        if dim != "(none)":
            dim_values = sorted(df[dim].drop_nulls().unique().to_list())
            selected = st.selectbox(
                f"Select {dim}",
                dim_values,
                key=f"drill_val_{key_suffix}",
            )
            view_df = df.filter(pl.col(dim) == selected)

        st.dataframe(
            view_df.select(available).head(max_rows),
            use_container_width=True,
            hide_index=True,
        )

        # Download CSV
        csv = view_df.select(available).head(max_rows).to_pandas().to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            file_name=f"{label.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            key=f"drill_dl_{key_suffix}",
        )


# =============================================================================
# FORMAT HELPERS
# =============================================================================

def format_currency(value) -> str:
    if value is None:
        return "-"
    return f"${value:,.2f}"


def format_pct(value) -> str:
    if value is None:
        return "-"
    return f"{value:+.2f}%"


def apply_chart_layout(fig: go.Figure, extra_right: int = 0, has_legend: bool = True) -> go.Figure:
    """Apply consistent layout settings to prevent label cutoff.

    Args:
        fig: Plotly figure to update
        extra_right: Extra right margin for charts with outside text labels
        has_legend: If True, adds extra top margin for horizontal legend above plot
    """
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    # Extra top margin when legend is above plot (y=1.02 pattern)
    top_margin = 80 if has_legend else 50
    fig.update_layout(
        margin=dict(l=10, r=10 + extra_right, t=top_margin, b=10),
        autosize=True,
    )
    return fig
