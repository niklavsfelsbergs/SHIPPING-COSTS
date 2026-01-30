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
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
UNMATCHED_EXPECTED_PATH = DATA_DIR / "unmatched_expected.parquet"
UNMATCHED_ACTUAL_PATH = DATA_DIR / "unmatched_actual.parquet"

# Cost positions: (expected_col, actual_col, label)
COST_POSITIONS = [
    ("cost_base", "actual_base", "Base"),
    ("cost_oml", "actual_oml", "OML"),
    ("cost_lps", "actual_lps", "LPS"),
    ("cost_ahs", "actual_ahs", "AHS"),
    ("cost_das", "actual_das", "DAS"),
    ("cost_edas", "actual_edas", "EDAS"),
    ("cost_res", "actual_res", "RES"),
    ("cost_dem_oml", "actual_dem_oml", "DEM_OML"),
    ("cost_dem_lps", "actual_dem_lps", "DEM_LPS"),
    ("cost_dem_ahs", "actual_dem_ahs", "DEM_AHS"),
    ("cost_dem_res", "actual_dem_res", "DEM_RES"),
    ("cost_fuel", "actual_fuel", "Fuel"),
    ("cost_total", "actual_total", "TOTAL"),
]

DETERMINISTIC_SURCHARGES = ["oml", "lps", "ahs", "das", "edas"]

SURCHARGE_COST_COLS = [
    "cost_oml", "cost_lps", "cost_ahs", "cost_das", "cost_edas",
    "cost_res", "cost_dem_oml", "cost_dem_lps", "cost_dem_ahs", "cost_dem_res",
]

WEIGHT_BRACKETS = [
    (0, 1, "0-1 lbs"),
    (1, 5, "1-5 lbs"),
    (5, 10, "5-10 lbs"),
    (10, 20, "10-20 lbs"),
    (20, 50, "20-50 lbs"),
    (50, float("inf"), "50+ lbs"),
]

# Charge types available for include/exclude filtering
# Maps label → (expected_col, actual_col)
CHARGE_TYPES = {
    "OML": ("cost_oml", "actual_oml"),
    "LPS": ("cost_lps", "actual_lps"),
    "AHS": ("cost_ahs", "actual_ahs"),
    "DAS": ("cost_das", "actual_das"),
    "EDAS": ("cost_edas", "actual_edas"),
    "RES": ("cost_res", "actual_res"),
    "DEM_OML": ("cost_dem_oml", "actual_dem_oml"),
    "DEM_LPS": ("cost_dem_lps", "actual_dem_lps"),
    "DEM_AHS": ("cost_dem_ahs", "actual_dem_ahs"),
    "DEM_RES": ("cost_dem_res", "actual_dem_res"),
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


# =============================================================================
# LAYER 1 — Raw data from disk (cached, never re-reads during session)
# =============================================================================

@st.cache_data
def load_raw() -> pl.DataFrame:
    """Load comparison dataset from parquet. Cached for entire session."""
    path = DATA_DIR / "comparison.parquet"
    if not path.exists():
        st.error(
            f"Data file not found: {path}\n\n"
            "Run `python -m carriers.ontrac.dashboard.export_data` first."
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
def prepare_df(df: pl.DataFrame) -> pl.DataFrame:
    """Add all derived columns. Cached — only recomputes if raw df changes."""
    # PK uniqueness check
    n_unique = df[PRIMARY_KEY].n_unique()
    n_total = len(df)
    if n_unique != n_total:
        st.warning(
            f"Data grain issue: {n_total:,} rows but {n_unique:,} unique "
            f"{PRIMARY_KEY} values. Totals may double-count."
        )

    # Cast Decimal columns to Float64 (Redshift exports Decimal; Polars
    # aggregations like .mean() break on Decimal dtype)
    decimal_cols = [c for c in df.columns if str(df[c].dtype).startswith("Decimal")]
    if decimal_cols:
        df = df.with_columns([pl.col(c).cast(pl.Float64) for c in decimal_cols])

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
        (pl.col("surcharge_ahs").fill_null(False) == (pl.col("actual_ahs").fill_null(0) > 0))
        & (pl.col("surcharge_lps").fill_null(False) == (pl.col("actual_lps").fill_null(0) > 0))
        & (pl.col("surcharge_oml").fill_null(False) == (pl.col("actual_oml").fill_null(0) > 0))
        & (pl.col("surcharge_das").fill_null(False) == (pl.col("actual_das").fill_null(0) > 0))
        & (pl.col("surcharge_edas").fill_null(False) == (pl.col("actual_edas").fill_null(0) > 0))
    )
    zone_matches = pl.col("shipping_zone") == pl.col("actual_zone")

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

    # Zone match
    df = df.with_columns(
        (pl.col("shipping_zone") == pl.col("actual_zone")).alias("zone_match"),
    )

    return df


# =============================================================================
# LAYER 3 — Filtered data (cached on filter parameters)
# =============================================================================

@st.cache_data
def get_filtered_df(
    _prepared_df: pl.DataFrame,
    date_from: date | None = None,
    date_to: date | None = None,
    sites: tuple[str, ...] | None = None,
    invoices: tuple[str, ...] = (),
    charges: tuple[str, ...] = (),
    positions: tuple[str, ...] = (),
) -> pl.DataFrame:
    """
    Apply sidebar filters and return result.

    Cached on filter parameter values — changing a chart tab or scrolling
    does NOT re-filter. Only changing a sidebar filter does.

    Args use tuple (hashable) instead of list for cache compatibility.
    """
    df = _prepared_df

    if date_from is not None:
        df = df.filter(pl.col("ship_date") >= pl.lit(date_from).cast(pl.Date))
    if date_to is not None:
        df = df.filter(pl.col("ship_date") <= pl.lit(date_to).cast(pl.Date))
    if sites:
        df = df.filter(pl.col("production_site").is_in(list(sites)))
    if invoices:
        df = df.filter(pl.col("invoice_number").is_in(list(invoices)))

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
            zero_exprs.append(pl.lit(0.0).alias(act_col))

        df = df.with_columns(zero_exprs)
        # Recompute totals from remaining positions
        exp_cols = [exp for exp, _, lbl in COST_POSITIONS if lbl != "TOTAL"]
        act_cols = [act for _, act, lbl in COST_POSITIONS if lbl != "TOTAL"]
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
# PAGE INIT — shared sidebar + data loading for all pages
# =============================================================================

def init_page() -> tuple[pl.DataFrame, dict, pl.DataFrame]:
    """
    Load data, render sidebar filters, return (prepared_df, match_rate_data, filtered_df).

    Call at the top of every page (including app.py) so the sidebar filters
    appear regardless of which page the user navigates to.
    """
    raw_df = load_raw()
    prepared_df = prepare_df(raw_df)
    match_rate_data = load_match_rate()

    _render_sidebar(prepared_df)

    filtered_df = get_filtered_df(
        prepared_df,
        date_from=st.session_state.get("filter_date_from"),
        date_to=st.session_state.get("filter_date_to"),
        sites=st.session_state.get("filter_sites"),
        invoices=st.session_state.get("filter_invoices", ()),
        charges=st.session_state.get("filter_charges", tuple(ALL_CHARGE_LABELS)),
        positions=st.session_state.get("filter_positions", tuple(ALL_POSITION_LABELS)),
    )

    return prepared_df, match_rate_data, filtered_df


def _checkbox_dropdown(
    label: str,
    options: list[str],
    default_checked: bool = False,
    key_prefix: str = "",
) -> list[str]:
    """Expander with checkboxes, persisted via user-managed session_state dict."""
    state_key = f"_persist_{key_prefix}"

    # Initialise persistent dict on first ever run
    if state_key not in st.session_state:
        st.session_state[state_key] = {opt: default_checked for opt in options}
    saved = st.session_state[state_key]

    # Ensure new options get a default
    for opt in options:
        if opt not in saved:
            saved[opt] = default_checked

    # Sync from widget keys
    keep_open = False
    for opt in options:
        wkey = f"{key_prefix}_{opt}"
        if wkey in st.session_state and st.session_state[wkey] != saved[opt]:
            keep_open = True
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
        keep_open = True

    with st.sidebar.expander(f"{label} ({n_selected}/{len(options)})", expanded=keep_open):
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
    st.sidebar.title("OnTrac Analytics")
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")

    # Date range
    min_date = prepared_df["ship_date"].min()
    max_date = prepared_df["ship_date"].max()

    if min_date is not None and max_date is not None:
        default_from = max(min_date, max_date - timedelta(days=90))
        date_range = st.sidebar.date_input(
            "Ship date range",
            value=(default_from, max_date),
            min_value=min_date,
            max_value=max_date,
            key="sidebar_date_range",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            st.session_state["filter_date_from"] = date_range[0]
            st.session_state["filter_date_to"] = date_range[1]
        elif isinstance(date_range, tuple) and len(date_range) == 1:
            st.session_state["filter_date_from"] = date_range[0]
            st.session_state["filter_date_to"] = date_range[0]
    else:
        st.sidebar.warning("No data loaded.")

    # Production site
    all_sites = sorted(prepared_df["production_site"].drop_nulls().unique().to_list())
    selected_sites = _checkbox_dropdown(
        "Production site", all_sites, default_checked=True, key_prefix="site"
    )
    st.session_state["filter_sites"] = tuple(selected_sites)

    # Invoice filter — with search bar and scrollable list
    all_invoices = sorted(
        prepared_df["invoice_number"].drop_nulls().unique().to_list(),
        reverse=True,
    )
    inv_state_key = "_persist_inv"
    if inv_state_key not in st.session_state:
        st.session_state[inv_state_key] = {inv: False for inv in all_invoices}
    inv_saved = st.session_state[inv_state_key]
    for inv in all_invoices:
        if inv not in inv_saved:
            inv_saved[inv] = False

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
    st.sidebar.markdown("**Shipment Charges**")
    st.sidebar.caption("Uncheck to exclude shipments with that charge")

    selected_charges = _checkbox_dropdown(
        "Charges", ALL_CHARGE_LABELS, default_checked=True, key_prefix="chg"
    )
    st.session_state["filter_charges"] = tuple(selected_charges)

    # --- Cost Positions ---
    st.sidebar.markdown("**Cost Positions**")
    st.sidebar.caption("Uncheck to zero out a cost component")

    selected_positions = _checkbox_dropdown(
        "Positions", ALL_POSITION_LABELS, default_checked=True, key_prefix="pos"
    )
    st.session_state["filter_positions"] = tuple(selected_positions)

    # Date axis for time-series charts
    st.sidebar.radio(
        "Time axis",
        ["billing_date", "ship_date"],
        key="sidebar_date_col",
        horizontal=True,
    )

    # Filter summary
    st.sidebar.markdown("---")
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
# DRILLDOWN HELPER (suggestion #5 — consistent pattern across pages)
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
        "pcs_orderid", "pcs_ordernumber", "shop_ordernumber", "invoice_number",
        "ship_date", "production_site", "shipping_zone", "actual_zone",
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
