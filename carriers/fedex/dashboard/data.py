"""
Dashboard Data Layer
====================

Layered caching architecture:
  1. load_raw()          — reads parquet from disk (cached, no TTL)
  2. prepare_df()        — adds derived columns (cached on df hash)
  3. get_filtered_df()   — applies sidebar filters (cached on filter params)

Pages call get_filtered_df() directly — no session_state bus.

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
COST_POSITIONS = [
    ("cost_base_rate", "actual_base", "Base Rate"),
    ("cost_performance_pricing", "actual_performance_pricing", "Performance Pricing"),
    ("cost_earned_discount", "actual_earned_discount", "Earned Discount"),
    ("cost_grace_discount", "actual_grace_discount", "Grace Discount"),
    ("cost_ahs", "actual_ahs", "AHS"),
    ("cost_ahs_weight", "actual_ahs_weight", "AHS-Weight"),
    ("cost_oversize", "actual_oversize", "Oversize"),
    ("cost_das", "actual_das", "DAS"),
    ("cost_residential", "actual_residential", "Residential"),
    ("cost_dem_base", "actual_dem_base", "DEM-Base"),
    ("cost_dem_ahs", "actual_dem_ahs", "DEM-AHS"),
    ("cost_dem_oversize", "actual_dem_oversize", "DEM-Oversize"),
    ("cost_fuel", "actual_fuel", "Fuel"),
    ("cost_discount", "actual_discount", "Other Discount"),
    ("cost_unpredictable", "actual_unpredictable", "Unpredictable"),
    ("cost_total", "actual_net_charge", "TOTAL"),
]

DETERMINISTIC_SURCHARGES = ["ahs", "ahs_weight", "oversize", "das", "residential"]

SURCHARGE_COST_COLS = [
    "cost_ahs", "cost_ahs_weight", "cost_oversize", "cost_das",
    "cost_residential", "cost_dem_base", "cost_dem_ahs", "cost_dem_oversize",
]

WEIGHT_BRACKETS = [
    (0, 1, "0-1 lbs"),
    (1, 5, "1-5 lbs"),
    (5, 10, "5-10 lbs"),
    (10, 20, "10-20 lbs"),
    (20, 50, "20-50 lbs"),
    (50, 100, "50-100 lbs"),
    (100, float("inf"), "100+ lbs"),
]

# Charge types available for include/exclude filtering
# Maps label → (expected_col, actual_col)
CHARGE_TYPES = {
    "AHS": ("cost_ahs", "actual_ahs"),
    "AHS-Weight": ("cost_ahs_weight", "actual_ahs_weight"),
    "Oversize": ("cost_oversize", "actual_oversize"),
    "DAS": ("cost_das", "actual_das"),
    "Residential": ("cost_residential", "actual_residential"),
    "DEM-Base": ("cost_dem_base", "actual_dem_base"),
    "DEM-AHS": ("cost_dem_ahs", "actual_dem_ahs"),
    "DEM-Oversize": ("cost_dem_oversize", "actual_dem_oversize"),
    "Other Discount": ("cost_discount", "actual_discount"),
    "Unpredictable": ("cost_unpredictable", "actual_unpredictable"),
}
ALL_CHARGE_LABELS = list(CHARGE_TYPES.keys())

# Cost positions available for zeroing-out in analysis
# Maps label → (expected_col, actual_col)
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
        "actual invoice row (e.g., 1 expected row + 5 actual rows = 5 joined rows). "
        "Interpret totals at the shipment/line-item grain."
    )


# =============================================================================
# LAYER 1 — Raw data from disk (cached, never re-reads during session)
# =============================================================================

@st.cache_data(ttl=None)
def load_raw(_file_mtime: float = 0) -> pl.DataFrame:
    """Load comparison dataset from parquet. Cached for entire session."""
    path = DATA_DIR / "comparison.parquet"
    if not path.exists():
        st.error(
            f"Data file not found: {path}\n\n"
            "Run `python -m carriers.fedex.dashboard.export_data` first."
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
# LAYER 2 — Prepared data with derived columns (cached on df identity)
# =============================================================================

@st.cache_data
def prepare_df(df: pl.DataFrame, grain: str = "line") -> pl.DataFrame:
    """Add all derived columns. Cached — only recomputes if raw df changes."""
    # Cast Decimal columns to Float64 (Redshift exports Decimal; Polars
    # aggregations like .mean() break on Decimal dtype)
    decimal_cols = [c for c in df.columns if str(df[c].dtype).startswith("Decimal")]
    if decimal_cols:
        df = df.with_columns([pl.col(c).cast(pl.Float64) for c in decimal_cols])

    # Cast zone columns to string for consistent comparison (actual_zone comes as String from Redshift)
    if "shipping_zone" in df.columns:
        df = df.with_columns(pl.col("shipping_zone").cast(pl.String))
    if "actual_zone" in df.columns:
        df = df.with_columns(pl.col("actual_zone").cast(pl.String))

    # Normalize zones for comparison (remove leading zeros, keep letters as-is)
    if "shipping_zone" in df.columns:
        df = df.with_columns(
            pl.col("shipping_zone")
                .str.strip_chars_start("0")
                .fill_null("")
                .alias("shipping_zone_normalized")
        )
        # Handle edge case where zone was "0" -> becomes empty string
        df = df.with_columns(
            pl.when(pl.col("shipping_zone_normalized") == "")
            .then(pl.col("shipping_zone"))
            .otherwise(pl.col("shipping_zone_normalized"))
            .alias("shipping_zone_normalized")
        )

    if "actual_zone" in df.columns:
        df = df.with_columns(
            pl.col("actual_zone")
                .str.strip_chars_start("0")
                .fill_null("")
                .alias("actual_zone_normalized")
        )
        # Handle edge case where zone was "0" -> becomes empty string
        df = df.with_columns(
            pl.when(pl.col("actual_zone_normalized") == "")
            .then(pl.col("actual_zone"))
            .otherwise(pl.col("actual_zone_normalized"))
            .alias("actual_zone_normalized")
        )

    # Service type segment
    if "rate_service" in df.columns:
        df = df.with_columns(
            pl.col("rate_service").fill_null("Unknown").alias("service_type")
        )
    else:
        df = df.with_columns(pl.lit("Unknown").alias("service_type"))

    # Net base calculation (Base Rate + PP + Earned + Grace)
    df = df.with_columns(
        (
            pl.col("cost_base_rate") +
            pl.col("cost_performance_pricing") +
            pl.col("cost_earned_discount") +
            pl.col("cost_grace_discount")
        ).alias("cost_net_base"),
        (
            pl.col("actual_base") +
            pl.col("actual_performance_pricing").fill_null(0) +
            pl.col("actual_earned_discount").fill_null(0) +
            pl.col("actual_grace_discount").fill_null(0)
        ).alias("actual_net_base"),
    )

    # Add cost_unpredictable and cost_discount columns (always 0 - we can't predict these)
    df = df.with_columns([
        pl.lit(0.0).alias("cost_unpredictable"),
        pl.lit(0.0).alias("cost_discount"),
    ])

    # SmartPost anomaly flag (10+ lbs)
    df = df.with_columns(
        (
            (pl.col("service_type") == "Ground Economy") &
            (pl.col("billable_weight_lbs") >= 10)
        ).alias("smartpost_anomaly")
    )

    # Deviation
    df = df.with_columns(
        (pl.col("actual_net_charge") - pl.col("cost_total")).alias("deviation"),
        pl.when(pl.col("cost_total") != 0)
        .then((pl.col("actual_net_charge") - pl.col("cost_total")) / pl.col("cost_total") * 100)
        .otherwise(0.0)
        .alias("deviation_pct"),
    )

    # Error source segment
    surcharge_correct = (
        (pl.col("surcharge_ahs").fill_null(False) == (pl.col("actual_ahs").fill_null(0) > 0))
        & (pl.col("surcharge_ahs_weight").fill_null(False) == (pl.col("actual_ahs_weight").fill_null(0) > 0))
        & (pl.col("surcharge_oversize").fill_null(False) == (pl.col("actual_oversize").fill_null(0) > 0))
        & (pl.col("surcharge_das").fill_null(False) == (pl.col("actual_das").fill_null(0) > 0))
        & (pl.col("surcharge_residential").fill_null(False) == (pl.col("actual_residential").fill_null(0) > 0))
    )
    # Use normalized zones for comparison if available
    if "shipping_zone_normalized" in df.columns and "actual_zone_normalized" in df.columns:
        zone_matches = pl.col("shipping_zone_normalized") == pl.col("actual_zone_normalized")
    elif "shipping_zone" in df.columns and "actual_zone" in df.columns:
        zone_matches = pl.col("shipping_zone") == pl.col("actual_zone")
    else:
        zone_matches = pl.lit(True)  # Default to match if zones don't exist

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

    # Zone match (use normalized zones if available, otherwise use raw zones)
    if "shipping_zone_normalized" in df.columns and "actual_zone_normalized" in df.columns:
        df = df.with_columns(
            (pl.col("shipping_zone_normalized") == pl.col("actual_zone_normalized")).alias("zone_match"),
        )
    elif "shipping_zone" in df.columns and "actual_zone" in df.columns:
        df = df.with_columns(
            (pl.col("shipping_zone") == pl.col("actual_zone")).alias("zone_match"),
        )
    else:
        df = df.with_columns(pl.lit(False).alias("zone_match"))

    return df


@st.cache_data
def aggregate_shipments(df: pl.DataFrame) -> pl.DataFrame:
    """Aggregate actuals to shipment-level (pcs_orderid)."""
    base_cols = [
        "pcs_ordernumber", "latest_trackingnumber",
        "pcs_created", "ship_date", "production_site",
        "shipping_zip_code", "shipping_region", "shipping_zone", "billable_weight_lbs",
        "length_in", "width_in", "height_in", "weight_lbs",
        "cubic_in", "longest_side_in", "second_longest_in",
        "dim_weight_lbs", "uses_dim_weight",
    ]

    if "packagetype" in df.columns:
        base_cols.append("packagetype")
    if "rate_service" in df.columns:
        base_cols.append("rate_service")
    if "service_type" in df.columns:
        base_cols.append("service_type")

    expected_flag_cols = [c for c in df.columns if c.startswith("surcharge_")]
    expected_cost_cols = [c for c in df.columns if c.startswith("cost_")]
    actual_sum_cols = [
        c for c in df.columns
        if c.startswith("actual_") and c not in {
            "actual_zone", "actual_rated_weight_lbs", "actual_trackingnumber"
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
        agg_exprs.append(pl.col("actual_trackingnumber").sort_by("invoice_date").first())
    if "invoice_number" in df.columns:
        agg_exprs.append(pl.col("invoice_number").sort_by("invoice_date").first())
        agg_exprs.append(pl.col("invoice_number").unique().alias("invoice_numbers"))
    if "invoice_date" in df.columns:
        agg_exprs.append(pl.col("invoice_date").min().alias("invoice_date"))
    if "actual_zone" in df.columns:
        agg_exprs.append(pl.col("actual_zone").drop_nulls().mode().first().alias("actual_zone"))
    if "actual_rated_weight_lbs" in df.columns:
        agg_exprs.append(pl.col("actual_rated_weight_lbs").max())

    for col in actual_sum_cols:
        agg_exprs.append(pl.col(col).sum())

    if "smartpost_anomaly" in df.columns:
        agg_exprs.append(pl.col("smartpost_anomaly").max())

    return df.group_by(PRIMARY_KEY).agg(agg_exprs)


@st.cache_data
def load_shipment_df(_file_mtime: float = 0) -> pl.DataFrame:
    """Load shipment-level dataset aggregated by pcs_orderid."""
    raw_df = load_raw(_file_mtime=_file_mtime)
    ship_df = aggregate_shipments(raw_df)
    return prepare_df(ship_df, grain="shipment")


# =============================================================================
# LAYER 3 — Filtered data (cached on filter parameters)
# =============================================================================

@st.cache_data
def get_filtered_df(
    _prepared_df: pl.DataFrame,
    date_from: date | None = None,
    date_to: date | None = None,
    date_col: str = "ship_date",
    sites: tuple[str, ...] | None = None,
    services: tuple[str, ...] | None = None,
    zones: tuple[str, ...] | None = None,
    invoices: tuple[str, ...] = (),
    actual_charges: tuple[str, ...] = (),
    charges: tuple[str, ...] = (),
    positions: tuple[str, ...] = (),
    weight_min: float | None = None,
    weight_max: float | None = None,
    weight_type: str = "Expected",
    grain: str = "line",
) -> pl.DataFrame:
    """
    Apply sidebar filters and return result.

    Cached on filter parameter values — changing a chart tab or scrolling
    does NOT re-filter. Only changing a sidebar filter does.

    Args use tuple (hashable) instead of list for cache compatibility.
    """
    df = _prepared_df

    if date_from is not None:
        df = df.filter(pl.col(date_col) >= pl.lit(date_from).cast(pl.Date))
    if date_to is not None:
        df = df.filter(pl.col(date_col) <= pl.lit(date_to).cast(pl.Date))
    if sites:
        df = df.filter(pl.col("production_site").is_in(list(sites)))
    if services:
        df = df.filter(pl.col("service_type").is_in(list(services)))
    if zones:
        df = df.filter(pl.col("shipping_zone").is_in(list(zones)))

    # Weight filter - use correct column based on type
    weight_col = "billable_weight_lbs" if weight_type == "Expected" else "actual_rated_weight_lbs"
    if weight_min is not None and weight_col in df.columns:
        df = df.filter(pl.col(weight_col) >= weight_min)
    if weight_max is not None and weight_col in df.columns:
        df = df.filter(pl.col(weight_col) <= weight_max)

    if invoices:
        if "invoice_numbers" in df.columns:
            invoice_list = list(invoices)
            df = df.filter(
                pl.col("invoice_numbers")
                .list.eval(pl.element().is_in(invoice_list))
                .list.any()
            )
        else:
            df = df.filter(pl.col("invoice_number").is_in(list(invoices)))

    # Actual charge filter: show only shipments with specific actual charges
    if actual_charges:
        act_cols = [
            CHARGE_TYPES[label][1]
            for label in actual_charges
            if label in CHARGE_TYPES and CHARGE_TYPES[label][1] in df.columns
        ]
        if act_cols:
            df = df.filter(
                pl.any_horizontal([pl.col(c).fill_null(0) > 0 for c in act_cols])
            )

    # Shipment charges: unchecked = exclude shipments with that charge
    # in either expected or actual.
    excluded_charges = set(ALL_CHARGE_LABELS) - set(charges)
    for label in excluded_charges:
        exp_col, act_col = CHARGE_TYPES[label]
        # Only filter if both columns exist in dataframe
        if exp_col in df.columns and act_col in df.columns:
            df = df.filter(
                (pl.col(exp_col).fill_null(0) <= 0) & (pl.col(act_col).fill_null(0) <= 0)
            )

    # Cost positions: unchecked = zero out on both sides.
    excluded_pos = set(ALL_POSITION_LABELS) - set(positions)
    if excluded_pos:
        # Calculate adjustment amounts before zeroing
        exp_adjustments = []
        act_adjustments = []
        zero_exprs = []

        for label in excluded_pos:
            exp_col, act_col = COST_POSITION_MAP[label]
            exp_adjustments.append(pl.col(exp_col).fill_null(0))
            act_adjustments.append(pl.col(act_col).fill_null(0))
            zero_exprs.append(pl.lit(0.0).alias(exp_col))
            zero_exprs.append(pl.lit(0.0).alias(act_col))

        # Subtract zeroed amounts from original totals (preserves precision)
        df = df.with_columns([
            (pl.col("cost_total") - pl.sum_horizontal(*exp_adjustments)).alias("cost_total"),
            (pl.col("actual_net_charge") - pl.sum_horizontal(*act_adjustments)).alias("actual_net_charge"),
        ])

        # Now zero out the component columns
        df = df.with_columns(zero_exprs)

        # Recalculate deviation from new totals
        df = df.with_columns(
            (pl.col("actual_net_charge") - pl.col("cost_total")).alias("deviation"),
        )
        df = df.with_columns(
            pl.when(pl.col("cost_total") != 0)
            .then(pl.col("deviation") / pl.col("cost_total") * 100)
            .otherwise(0.0)
            .alias("deviation_pct"),
        )

    return df


# =============================================================================
# PAGE INIT — shared sidebar + data loading for all pages
# =============================================================================

def init_page() -> tuple[pl.DataFrame, dict, pl.DataFrame]:
    """
    Load data, render sidebar filters, return (prepared_df, match_rate_data, filtered_df).

    Call at the top of every page (including app.py) so the sidebar filters
    appear regardless of which page the user navigates to.
    """
    # Get file modification time to bust cache when data changes
    comparison_path = DATA_DIR / "comparison.parquet"
    file_mtime = comparison_path.stat().st_mtime if comparison_path.exists() else 0

    raw_df = load_raw(_file_mtime=file_mtime)
    prepared_df = prepare_df(raw_df, grain="line")
    match_rate_data = load_match_rate()

    _render_sidebar(prepared_df)

    date_label = st.session_state.get("filter_time_axis", "Invoice Date")
    date_col = "invoice_date" if date_label == "Invoice Date" else "ship_date"

    filtered_df = get_filtered_df(
        prepared_df,
        date_from=st.session_state.get("filter_date_from"),
        date_to=st.session_state.get("filter_date_to"),
        date_col=date_col,
        sites=st.session_state.get("filter_sites"),
        services=st.session_state.get("filter_services"),
        zones=st.session_state.get("filter_zones"),
        invoices=st.session_state.get("filter_invoices", ()),
        actual_charges=st.session_state.get("filter_actual_charges", ()),
        charges=st.session_state.get("filter_charges", tuple(ALL_CHARGE_LABELS)),
        positions=st.session_state.get("filter_positions", tuple(ALL_POSITION_LABELS)),
        weight_min=st.session_state.get("filter_weight_min"),
        weight_max=st.session_state.get("filter_weight_max"),
        weight_type=st.session_state.get("filter_weight_type", "Expected"),
        grain="line",
    )

    return prepared_df, match_rate_data, filtered_df


def get_filtered_shipments() -> pl.DataFrame:
    """Return shipment-level data filtered by current sidebar settings."""
    # Get file modification time to bust cache when data changes
    comparison_path = DATA_DIR / "comparison.parquet"
    file_mtime = comparison_path.stat().st_mtime if comparison_path.exists() else 0

    ship_df = load_shipment_df(_file_mtime=file_mtime)
    date_label = st.session_state.get("filter_time_axis", "Invoice Date")
    date_col = "invoice_date" if date_label == "Invoice Date" else "ship_date"
    return get_filtered_df(
        ship_df,
        date_from=st.session_state.get("filter_date_from"),
        date_to=st.session_state.get("filter_date_to"),
        date_col=date_col,
        sites=st.session_state.get("filter_sites"),
        services=st.session_state.get("filter_services"),
        zones=st.session_state.get("filter_zones"),
        invoices=st.session_state.get("filter_invoices", ()),
        charges=st.session_state.get("filter_charges", tuple(ALL_CHARGE_LABELS)),
        positions=st.session_state.get("filter_positions", tuple(ALL_POSITION_LABELS)),
        weight_min=st.session_state.get("filter_weight_min"),
        weight_max=st.session_state.get("filter_weight_max"),
        weight_type=st.session_state.get("filter_weight_type", "Expected"),
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
    expanded_key = f"_expanded_{key_prefix}"  # Track expander state across pages

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

    # Sync from widget keys and mark expander as "should stay open"
    for opt in options:
        wkey = f"{key_prefix}_{opt}"
        if wkey in st.session_state and st.session_state[wkey] != saved[opt]:
            st.session_state[expanded_key] = True  # Persist open state
            saved[opt] = st.session_state[wkey]

    n_selected = sum(saved[opt] for opt in options)

    def _set_all(target):
        st.session_state[f"{key_prefix}__bulk"] = True
        s = st.session_state[state_key]
        for o in options:
            s[o] = target
            st.session_state[f"{key_prefix}_{o}"] = target

    # Keep open if All/None button was just clicked
    if st.session_state.pop(f"{key_prefix}__bulk", False):
        st.session_state[expanded_key] = True  # Persist open state

    # Use persisted state for expanded parameter
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
    # Use separate filter key for persistence
    time_axis_options = ["Invoice Date", "Ship Date"]
    if "filter_time_axis" not in st.session_state:
        st.session_state["filter_time_axis"] = "Invoice Date"  # default

    time_axis_idx = time_axis_options.index(st.session_state["filter_time_axis"])
    selected_time_axis = st.sidebar.radio(
        "Time axis",
        time_axis_options,
        index=time_axis_idx,
        horizontal=True,
        key="sidebar_date_col",
    )
    st.session_state["filter_time_axis"] = selected_time_axis

    # Time grain for time-series charts
    time_grain_options = ["Daily", "Weekly", "Monthly"]
    if "filter_time_grain" not in st.session_state:
        st.session_state["filter_time_grain"] = "Daily"

    time_grain_idx = time_grain_options.index(st.session_state["filter_time_grain"])
    selected_time_grain = st.sidebar.radio(
        "Time grain",
        time_grain_options,
        index=time_grain_idx,
        horizontal=True,
        key="sidebar_time_grain",
    )
    st.session_state["filter_time_grain"] = selected_time_grain

    # Date range (depends on selected date column)
    date_label = st.session_state.get("filter_time_axis", "Invoice Date")
    date_col = "invoice_date" if date_label == "Invoice Date" else "ship_date"
    if date_col in prepared_df.columns:
        date_series = prepared_df[date_col].cast(pl.Date)
        min_date = date_series.min()
        max_date = date_series.max()
    else:
        min_date, max_date = None, None

    if min_date is not None and max_date is not None:
        # Reset dates when switching between invoice_date and ship_date
        last_date_col = st.session_state.get("_last_date_col")
        if last_date_col != date_col:
            fixed_from = date(2025, 12, 1)
            fixed_to = date(2025, 12, 31)
            default_from = max(min_date, fixed_from)
            default_to = min(max_date, fixed_to)
            if default_from > default_to:
                default_from = min_date
                default_to = max_date
            st.session_state["filter_date_from"] = default_from
            st.session_state["filter_date_to"] = default_to
            st.session_state["_last_date_col"] = date_col

        # Initialize date range in session state if not set
        if "filter_date_from" not in st.session_state or "filter_date_to" not in st.session_state:
            fixed_from = date(2025, 12, 1)
            fixed_to = date(2025, 12, 31)
            default_from = max(min_date, fixed_from)
            default_to = min(max_date, fixed_to)
            if default_from > default_to:
                default_from = min_date
                default_to = max_date
            st.session_state["filter_date_from"] = default_from
            st.session_state["filter_date_to"] = default_to
            st.session_state["_last_date_col"] = date_col

        # Use session state values (preserves user selection across reruns)
        current_from = st.session_state["filter_date_from"]
        current_to = st.session_state["filter_date_to"]

        # Use wide date range to allow any dates
        date_range = st.sidebar.date_input(
            f"{date_label} Range",
            value=(current_from, current_to),
            min_value=date(2020, 1, 1),
            max_value=date(2030, 12, 31),
            key="sidebar_date_range",
        )

        # Update session state when user changes the date
        if isinstance(date_range, tuple) and len(date_range) == 2:
            st.session_state["filter_date_from"] = date_range[0]
            st.session_state["filter_date_to"] = date_range[1]
        elif isinstance(date_range, tuple) and len(date_range) == 1:
            st.session_state["filter_date_from"] = date_range[0]
            st.session_state["filter_date_to"] = date_range[0]
    else:
        st.sidebar.warning("No data loaded.")

    # Weight range filter
    st.sidebar.caption("Filter by weight")

    # Weight type toggle
    weight_type_options = ["Expected", "Actual"]
    if "filter_weight_type" not in st.session_state:
        st.session_state["filter_weight_type"] = "Expected"

    selected_weight_type = st.sidebar.selectbox(
        "Weight type",
        weight_type_options,
        index=weight_type_options.index(st.session_state["filter_weight_type"]),
        key="sidebar_weight_type",
    )
    st.session_state["filter_weight_type"] = selected_weight_type

    # Determine which column to use
    weight_col = "billable_weight_lbs" if selected_weight_type == "Expected" else "actual_rated_weight_lbs"

    if weight_col in prepared_df.columns:
        weight_data = prepared_df[weight_col].drop_nulls()
        if len(weight_data) > 0:
            data_min_weight = float(weight_data.min())
            data_max_weight = float(weight_data.max())

            # Initialize weight range to data bounds when switching types or first time
            if "filter_weight_min" not in st.session_state or \
               st.session_state.get("_last_weight_type") != selected_weight_type:
                st.session_state["filter_weight_min"] = data_min_weight
                st.session_state["filter_weight_max"] = data_max_weight
                st.session_state["_last_weight_type"] = selected_weight_type

            col1, col2 = st.sidebar.columns(2)
            with col1:
                weight_min = st.number_input(
                    "Min weight (lbs)",
                    min_value=0.0,
                    max_value=999.0,
                    value=st.session_state["filter_weight_min"],
                    step=1.0,
                    key="sidebar_weight_min",
                )
                st.session_state["filter_weight_min"] = weight_min

            with col2:
                weight_max = st.number_input(
                    "Max weight (lbs)",
                    min_value=0.0,
                    max_value=999.0,
                    value=st.session_state["filter_weight_max"],
                    step=1.0,
                    key="sidebar_weight_max",
                )
                st.session_state["filter_weight_max"] = weight_max

    # Metric mode
    metric_mode_options = ["Total", "Average per shipment"]
    if "filter_metric_mode" not in st.session_state:
        st.session_state["filter_metric_mode"] = "Total"

    def _on_metric_mode_change():
        st.session_state["filter_metric_mode"] = st.session_state["sidebar_metric_mode"]

    metric_mode_idx = metric_mode_options.index(st.session_state["filter_metric_mode"])
    st.sidebar.radio(
        "Metric mode",
        metric_mode_options,
        index=metric_mode_idx,
        horizontal=True,
        key="sidebar_metric_mode",
        on_change=_on_metric_mode_change,
    )

    # Production site
    all_sites = sorted(prepared_df["production_site"].drop_nulls().unique().to_list())
    selected_sites = _checkbox_dropdown(
        "Production site", all_sites, default_checked=True, key_prefix="site"
    )
    st.session_state["filter_sites"] = tuple(selected_sites)

    # Service type
    all_services = sorted(prepared_df["service_type"].drop_nulls().unique().to_list())
    selected_services = _checkbox_dropdown(
        "Service Type", all_services, default_checked=True, key_prefix="service"
    )
    st.session_state["filter_services"] = tuple(selected_services)

    # Zone filter
    if "shipping_zone" in prepared_df.columns:
        all_zones = sorted(prepared_df["shipping_zone"].drop_nulls().unique().to_list())
        selected_zones = _checkbox_dropdown(
            "Shipping Zone", all_zones, default_checked=True, key_prefix="zone"
        )
        st.session_state["filter_zones"] = tuple(selected_zones)
    else:
        st.session_state["filter_zones"] = ()

    # Invoice filter — with search bar and scrollable list
    all_invoices = sorted(
        prepared_df["invoice_number"].drop_nulls().unique().to_list(),
        reverse=True,
    )
    inv_state_key = "_persist_inv"
    if inv_state_key not in st.session_state:
        st.session_state[inv_state_key] = {inv: True for inv in all_invoices}
    inv_saved = st.session_state[inv_state_key]
    for inv in all_invoices:
        if inv not in inv_saved:
            inv_saved[inv] = True

    # Sync from widget keys
    inv_keep_open = False
    for inv in all_invoices:
        wkey = f"inv_{inv}"
        if wkey in st.session_state and st.session_state[wkey] != inv_saved[inv]:
            inv_keep_open = True
            inv_saved[inv] = st.session_state[wkey]

    n_inv_selected = sum(inv_saved[inv] for inv in all_invoices)

    def _set_all_inv(target):
        st.session_state["inv__bulk"] = True
        s = st.session_state[inv_state_key]
        for i in all_invoices:
            s[i] = target
            wkey = f"inv_{i}"
            if wkey in st.session_state:
                st.session_state[wkey] = target

    if st.session_state.pop("inv__bulk", False):
        inv_keep_open = True

    with st.sidebar.expander(
        f"Invoice number ({n_inv_selected}/{len(all_invoices)})",
        expanded=inv_keep_open,
    ):
        search = st.text_input(
            "Search", key="inv_search", placeholder="Type to filter...",
            label_visibility="collapsed",
        )
        col_a, col_b = st.columns(2)
        col_a.button("All", key="inv__btn_all", use_container_width=True,
                      on_click=_set_all_inv, args=(True,))
        col_b.button("None", key="inv__btn_none", use_container_width=True,
                      on_click=_set_all_inv, args=(False,))
        display_invoices = (
            [inv for inv in all_invoices if search.upper() in inv.upper()]
            if search else all_invoices
        )
        with st.container(height=200):
            for inv in display_invoices:
                wkey = f"inv_{inv}"
                if wkey in st.session_state:
                    val = st.checkbox(inv, key=wkey)
                else:
                    val = st.checkbox(inv, value=inv_saved[inv], key=wkey)
                inv_saved[inv] = val

    st.session_state[inv_state_key] = inv_saved
    selected_invoices = [inv for inv in all_invoices if inv_saved[inv]]
    st.session_state["filter_invoices"] = tuple(selected_invoices)

    # --- Shipment Charges ---
    st.sidebar.caption("Optional: filter to shipments with specific actual charges")
    st.sidebar.multiselect(
        "Actual charge filter",
        ALL_CHARGE_LABELS,
        default=[],
        key="filter_actual_charges",
    )

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
    total_act = df["actual_net_charge"].sum()
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
    Reusable drilldown drawer: dimension selector → filtered table → CSV download.

    Call from any page after a chart/section to let users slice and export.
    """
    if len(df) == 0:
        return

    default_cols = [
        "pcs_orderid", "pcs_ordernumber", "invoice_number",
        "ship_date", "production_site", "service_type", "shipping_zone", "actual_zone",
        "billable_weight_lbs", "cost_total", "actual_net_charge", "deviation",
    ]
    display_cols = columns or default_cols
    available = [c for c in display_cols if c in df.columns]

    with st.expander(f"Drilldown: {label} ({len(df):,} rows)"):
        # Dimension selector
        dim_options = ["(none)"] + [
            c for c in ["production_site", "service_type", "shipping_zone", "error_source", "weight_bracket"]
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
    """Apply consistent layout settings to prevent label cutoff."""
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)

    # Extra top margin when legend is above plot (y=1.02 pattern)
    top_margin = 80 if has_legend else 50

    fig.update_layout(
        margin=dict(l=10, r=10 + extra_right, t=top_margin, b=10),
        autosize=True,
    )
    return fig
