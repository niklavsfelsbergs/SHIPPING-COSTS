"""
Compare Expected to Actual Costs
================================

Compares expected shipping costs to actual invoice costs and generates an HTML report.

Usage:
    python -m carriers.fedex.scripts.compare_expected_to_actuals
    python -m carriers.fedex.scripts.compare_expected_to_actuals --invoice 26D0I70116
    python -m carriers.fedex.scripts.compare_expected_to_actuals --date_from 2025-12-01 --date_to 2025-12-31
    python -m carriers.fedex.scripts.compare_expected_to_actuals --output report.html
"""

import argparse
from pathlib import Path
from datetime import datetime

import polars as pl

from shared.database import pull_data


# =============================================================================
# CONFIGURATION
# =============================================================================

EXPECTED_TABLE = "shipping_costs.expected_shipping_costs_fedex"
ACTUAL_TABLE = "shipping_costs.actual_shipping_costs_fedex"

SQL_DIR = Path(__file__).parent / "sql"
OUTPUT_DIR = Path(__file__).parent / "output" / "accuracy_reports"

# Deterministic surcharges (have specific triggering conditions)
DETERMINISTIC_SURCHARGES = [
    ("surcharge_ahs", "actual_ahs", "AHS"),
    ("surcharge_ahs_weight", "actual_ahs_weight", "AHS-Weight"),
    ("surcharge_oversize", "actual_oversize", "Oversize"),
    ("surcharge_das", "actual_das", "DAS"),
    ("surcharge_residential", "actual_residential", "Residential"),
]

# Cost positions to compare (expected column -> actual column -> label)
COST_POSITIONS = [
    ("cost_base_rate", "actual_base", "Base"),
    ("cost_ahs", "actual_ahs", "AHS"),
    ("cost_ahs_weight", "actual_ahs_weight", "AHS-Weight"),
    ("cost_oversize", "actual_oversize", "Oversize"),
    ("cost_das", "actual_das", "DAS"),
    ("cost_residential", "actual_residential", "Residential"),
    ("cost_dem_base", "actual_dem_base", "DEM-Base"),
    ("cost_dem_ahs", "actual_dem_ahs", "DEM-AHS"),
    ("cost_dem_oversize", "actual_dem_oversize", "DEM-Oversize"),
    (None, "actual_dem_residential", "DEM-Residential"),  # Expected not in table
    ("cost_fuel", "actual_fuel", "Fuel"),
    ("cost_performance_pricing", "actual_performance_pricing", "Perf. Pricing"),
    ("cost_earned_discount", "actual_earned_discount", "Earned Discount"),
    ("cost_grace_discount", "actual_grace_discount", "Grace Discount"),
]


# =============================================================================
# DATA LOADING
# =============================================================================

def load_comparison_data(
    invoice: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> pl.DataFrame:
    """Load joined expected/actual data with optional filters."""
    query_template = (SQL_DIR / "comparison_base.sql").read_text()

    # Build filter clauses
    invoice_filter = f"AND a.invoice_number = '{invoice}'" if invoice else ""
    date_from_filter = f"AND a.invoice_date >= '{date_from}'" if date_from else ""
    date_to_filter = f"AND a.invoice_date <= '{date_to}'" if date_to else ""

    query = query_template.format(
        invoice_filter=invoice_filter,
        date_from_filter=date_from_filter,
        date_to_filter=date_to_filter,
    )

    # Use Pandas as intermediate to handle Redshift decimal types
    df_pandas = pull_data(query, as_polars=False)
    df = pl.from_pandas(df_pandas)

    # Cast cost columns to Float64 (they may come as strings or objects)
    cost_cols = [
        "cost_base_rate", "cost_performance_pricing", "cost_earned_discount",
        "cost_grace_discount", "cost_ahs", "cost_ahs_weight", "cost_oversize",
        "cost_das", "cost_residential", "cost_dem_base", "cost_dem_ahs",
        "cost_dem_oversize", "cost_fuel", "cost_total",
        "actual_base", "actual_performance_pricing", "actual_earned_discount",
        "actual_grace_discount", "actual_ahs", "actual_ahs_weight", "actual_oversize",
        "actual_das", "actual_residential", "actual_dem_base", "actual_dem_ahs",
        "actual_dem_oversize", "actual_dem_residential", "actual_fuel",
        "actual_net_charge", "actual_unpredictable",
    ]
    for col in cost_cols:
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(pl.Float64, strict=False))

    return df


def get_match_rate_data(
    invoice: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Get counts for match rate calculation."""
    # Build filter for actuals
    actual_filters = []
    if invoice:
        actual_filters.append(f"invoice_number = '{invoice}'")
    if date_from:
        actual_filters.append(f"invoice_date >= '{date_from}'")
    if date_to:
        actual_filters.append(f"invoice_date <= '{date_to}'")

    actual_where = "WHERE " + " AND ".join(actual_filters) if actual_filters else ""

    # Count distinct orderids in filtered actuals
    if actual_where:
        actual_orderids_query = f"""
            SELECT COUNT(DISTINCT pcs_orderid) as cnt
            FROM {ACTUAL_TABLE}
            {actual_where}
        """
    else:
        actual_orderids_query = f"SELECT COUNT(DISTINCT pcs_orderid) as cnt FROM {ACTUAL_TABLE}"

    # Count expected orders that have matching actuals
    if actual_where:
        matched_query = f"""
            SELECT COUNT(DISTINCT e.pcs_orderid) as cnt
            FROM {EXPECTED_TABLE} e
            INNER JOIN {ACTUAL_TABLE} a ON e.pcs_orderid = a.pcs_orderid
            {actual_where.replace('WHERE', 'WHERE 1=1 AND')}
        """
    else:
        matched_query = f"""
            SELECT COUNT(DISTINCT e.pcs_orderid) as cnt
            FROM {EXPECTED_TABLE} e
            INNER JOIN {ACTUAL_TABLE} a ON e.pcs_orderid = a.pcs_orderid
        """

    # Total expected in same date range
    total_expected_query = f"SELECT COUNT(*) as cnt FROM {EXPECTED_TABLE}"

    # Use Pandas as intermediate to handle Redshift decimal types
    actual_count = int(pull_data(actual_orderids_query, as_polars=False)["cnt"].iloc[0])
    matched_count = int(pull_data(matched_query, as_polars=False)["cnt"].iloc[0])
    total_expected = int(pull_data(total_expected_query, as_polars=False)["cnt"].iloc[0])

    return {
        "actual_orderids": actual_count,
        "matched_orderids": matched_count,
        "total_expected": total_expected,
    }


# =============================================================================
# METRIC CALCULATIONS
# =============================================================================

def calc_portfolio_summary(df: pl.DataFrame, match_data: dict) -> dict:
    """Calculate overall portfolio accuracy metrics."""
    if len(df) == 0:
        return {
            "total_expected": 0,
            "total_actual": 0,
            "variance_dollars": 0,
            "variance_pct": 0,
            "order_count": 0,
            "match_rate": 0,
        }

    total_expected = df["cost_total"].sum()
    total_actual = df["actual_net_charge"].sum()
    variance_dollars = total_actual - total_expected
    variance_pct = (variance_dollars / total_expected * 100) if total_expected != 0 else 0

    match_rate = (
        match_data["matched_orderids"] / match_data["actual_orderids"] * 100
        if match_data["actual_orderids"] > 0 else 0
    )

    return {
        "total_expected": total_expected,
        "total_actual": total_actual,
        "variance_dollars": variance_dollars,
        "variance_pct": variance_pct,
        "order_count": len(df),
        "matched_orderids": match_data["matched_orderids"],
        "actual_orderids": match_data["actual_orderids"],
        "match_rate": match_rate,
    }


def calc_cost_position_accuracy(df: pl.DataFrame) -> list[dict]:
    """Calculate accuracy for each cost position."""
    results = []

    for exp_col, act_col, label in COST_POSITIONS:
        # Handle cases where expected column doesn't exist
        if exp_col is None:
            expected = 0
        else:
            expected = df[exp_col].fill_null(0).sum()

        actual = df[act_col].fill_null(0).sum()
        variance_dollars = actual - expected
        variance_pct = (variance_dollars / expected * 100) if expected != 0 else (
            float('inf') if actual != 0 else 0
        )

        results.append({
            "position": label,
            "expected": expected,
            "actual": actual,
            "variance_dollars": variance_dollars,
            "variance_pct": variance_pct,
        })

    # Add unpredictable charges row (FedEx-specific)
    unpredictable = df["actual_unpredictable"].fill_null(0).sum()
    results.append({
        "position": "Unpredictable",
        "expected": None,  # N/A
        "actual": unpredictable,
        "variance_dollars": None,  # N/A
        "variance_pct": None,  # N/A
    })

    # Add TOTAL row
    total_expected = df["cost_total"].sum()
    total_actual = df["actual_net_charge"].sum()
    total_variance = total_actual - total_expected
    total_variance_pct = (total_variance / total_expected * 100) if total_expected != 0 else 0

    results.append({
        "position": "TOTAL",
        "expected": total_expected,
        "actual": total_actual,
        "variance_dollars": total_variance,
        "variance_pct": total_variance_pct,
    })

    return results


def calc_zone_accuracy(df: pl.DataFrame) -> dict:
    """Calculate zone accuracy metrics."""
    if len(df) == 0:
        return {"match_rate": 0, "mismatches": [], "mismatch_cost_impact": 0}

    # Handle zone comparison - normalize both to integers
    # actual_zone may have leading zeros (e.g., "04" vs 4)
    df_with_match = df.with_columns([
        pl.col("shipping_zone").cast(pl.Int64).alias("expected_zone_int"),
        pl.col("actual_zone").cast(pl.Int64, strict=False).alias("actual_zone_int"),
    ]).with_columns(
        (pl.col("expected_zone_int") == pl.col("actual_zone_int")).alias("zone_match")
    )

    matches = df_with_match["zone_match"].sum()
    total = len(df_with_match)
    match_rate = matches / total * 100 if total > 0 else 0

    # Mismatch breakdown
    mismatches_df = (
        df_with_match
        .filter(~pl.col("zone_match"))
        .group_by(["expected_zone_int", "actual_zone_int"])
        .agg([
            pl.len().alias("count"),
            (pl.col("actual_net_charge") - pl.col("cost_total")).sum().alias("cost_impact"),
        ])
        .sort("count", descending=True)
    )

    mismatches = []
    if len(mismatches_df) > 0:
        for row in mismatches_df.to_dicts():
            mismatches.append({
                "shipping_zone": row["expected_zone_int"],
                "actual_zone": row["actual_zone_int"],
                "count": row["count"],
                "cost_impact": row["cost_impact"],
            })

    # Total cost impact of mismatches
    mismatch_cost_impact = (
        df_with_match
        .filter(~pl.col("zone_match"))
        .select((pl.col("actual_net_charge") - pl.col("cost_total")).sum())
        .item()
    ) if len(df_with_match.filter(~pl.col("zone_match"))) > 0 else 0

    # Zone direction counts (using already-computed integer columns)
    df_zone_diff = df_with_match.filter(~pl.col("zone_match"))

    zone_too_high = 0
    zone_too_low = 0
    if len(df_zone_diff) > 0:
        df_valid_zones = df_zone_diff.filter(
            pl.col("expected_zone_int").is_not_null() & pl.col("actual_zone_int").is_not_null()
        )
        if len(df_valid_zones) > 0:
            zone_too_high = df_valid_zones.filter(
                pl.col("expected_zone_int") > pl.col("actual_zone_int")
            ).height
            zone_too_low = df_valid_zones.filter(
                pl.col("expected_zone_int") < pl.col("actual_zone_int")
            ).height

    return {
        "match_rate": match_rate,
        "matches": matches,
        "total": total,
        "mismatches": mismatches,
        "mismatch_cost_impact": mismatch_cost_impact,
        "zone_too_high": zone_too_high,
        "zone_too_low": zone_too_low,
    }


def calc_weight_accuracy(df: pl.DataFrame) -> dict:
    """Calculate weight accuracy metrics."""
    if len(df) == 0:
        return {"avg_diff": 0, "match_rate": 0, "total": 0}

    # Filter out nulls
    df_valid = df.filter(
        pl.col("billable_weight_lbs").is_not_null() &
        pl.col("actual_rated_weight_lbs").is_not_null()
    )

    if len(df_valid) == 0:
        return {"avg_diff": 0, "match_rate": 0, "total": 0}

    df_with_diff = df_valid.with_columns(
        (pl.col("actual_rated_weight_lbs") - pl.col("billable_weight_lbs")).alias("weight_diff")
    )

    avg_diff = df_with_diff["weight_diff"].mean()

    # Match within tolerance (0.5 lbs)
    tolerance = 0.5
    matches = df_with_diff.filter(pl.col("weight_diff").abs() <= tolerance).height
    match_rate = matches / len(df_with_diff) * 100 if len(df_with_diff) > 0 else 0

    return {
        "avg_diff": avg_diff,
        "match_rate": match_rate,
        "matches": matches,
        "total": len(df_with_diff),
        "tolerance": tolerance,
    }


def calc_surcharge_detection(df: pl.DataFrame) -> list[dict]:
    """Calculate surcharge detection accuracy for deterministic surcharges."""
    results = []

    for flag_col, actual_col, label in DETERMINISTIC_SURCHARGES:
        # Expected flag (boolean)
        expected_flag = df[flag_col].fill_null(False)
        # Actual charged (amount > 0)
        actual_charged = df[actual_col].fill_null(0) > 0

        true_positive = (expected_flag & actual_charged).sum()
        false_positive = (expected_flag & ~actual_charged).sum()
        false_negative = (~expected_flag & actual_charged).sum()
        true_negative = (~expected_flag & ~actual_charged).sum()

        precision = (
            true_positive / (true_positive + false_positive) * 100
            if (true_positive + false_positive) > 0 else 100
        )
        recall = (
            true_positive / (true_positive + false_negative) * 100
            if (true_positive + false_negative) > 0 else 100
        )

        results.append({
            "surcharge": label,
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "true_negative": true_negative,
            "precision": precision,
            "recall": recall,
        })

    return results


def calc_state_zone_analysis(df: pl.DataFrame) -> list[dict]:
    """
    Analyze zone accuracy by US state.

    For each state, calculates:
    - Total shipments
    - Zone match rate (expected == actual)
    - % with smaller expected zone (expected < actual)
    - % with bigger expected zone (expected > actual)
    - Base cost variance
    """
    if len(df) == 0:
        return []

    # Add zone comparison columns - normalize to integers to handle "04" vs 4
    df_with_compare = df.with_columns([
        pl.col("shipping_zone").cast(pl.Int64).alias("expected_zone_int"),
        pl.col("actual_zone").cast(pl.Int64, strict=False).alias("actual_zone_int"),
    ]).with_columns([
        (pl.col("expected_zone_int") == pl.col("actual_zone_int")).alias("zone_match"),
        (pl.col("expected_zone_int") < pl.col("actual_zone_int")).alias("zone_smaller"),
        (pl.col("expected_zone_int") > pl.col("actual_zone_int")).alias("zone_bigger"),
    ])

    # Group by state
    state_stats = (
        df_with_compare
        .group_by("shipping_region")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("zone_match").fill_null(False).sum().alias("zone_matches"),
            pl.col("zone_smaller").fill_null(False).sum().alias("zone_smaller_count"),
            pl.col("zone_bigger").fill_null(False).sum().alias("zone_bigger_count"),
            pl.col("cost_base_rate").fill_null(0).sum().alias("expected_base"),
            pl.col("actual_base").fill_null(0).sum().alias("actual_base"),
        ])
        .with_columns([
            (pl.col("zone_matches") / pl.col("shipment_count") * 100).alias("match_rate"),
            (pl.col("zone_smaller_count") / pl.col("shipment_count") * 100).alias("smaller_pct"),
            (pl.col("zone_bigger_count") / pl.col("shipment_count") * 100).alias("bigger_pct"),
            (pl.col("actual_base") - pl.col("expected_base")).alias("base_variance"),
        ])
        .sort("shipment_count", descending=True)
    )

    return state_stats.to_dicts()


def calc_base_cost_by_zone(df: pl.DataFrame) -> list[dict]:
    """
    Compare base costs grouped by zone (expected vs actual).

    Shows the base cost variance per zone to identify where rate
    differences are coming from.
    """
    if len(df) == 0:
        return []

    # Analysis by expected zone
    expected_zone_stats = (
        df
        .group_by("shipping_zone")
        .agg([
            pl.len().alias("shipment_count"),
            pl.col("cost_base_rate").fill_null(0).sum().alias("expected_base"),
            pl.col("actual_base").fill_null(0).sum().alias("actual_base"),
            pl.col("cost_base_rate").fill_null(0).mean().alias("avg_expected_base"),
            pl.col("actual_base").fill_null(0).mean().alias("avg_actual_base"),
        ])
        .with_columns([
            (pl.col("actual_base") - pl.col("expected_base")).alias("base_variance"),
            ((pl.col("actual_base") - pl.col("expected_base")) / pl.col("expected_base") * 100).alias("variance_pct"),
            (pl.col("avg_actual_base") - pl.col("avg_expected_base")).alias("avg_variance"),
        ])
        .sort("shipping_zone")
    )

    return expected_zone_stats.to_dicts()


def calc_unpredictable_summary(df: pl.DataFrame) -> dict:
    """Calculate summary of unpredictable charges (FedEx-specific)."""
    if len(df) == 0:
        return {"total": 0, "order_count": 0, "avg_per_order": 0}

    unpredictable_total = df["actual_unpredictable"].fill_null(0).sum()
    orders_with_unpredictable = df.filter(
        pl.col("actual_unpredictable").fill_null(0) > 0
    ).height

    avg_per_order = (
        unpredictable_total / orders_with_unpredictable
        if orders_with_unpredictable > 0 else 0
    )

    return {
        "total": unpredictable_total,
        "order_count": orders_with_unpredictable,
        "avg_per_order": avg_per_order,
    }


def calc_outliers(df: pl.DataFrame, top_n: int = 20) -> dict:
    """Find orders with largest variances."""
    if len(df) == 0:
        return {"by_dollars": [], "by_percent": []}

    df_with_variance = df.with_columns([
        (pl.col("actual_net_charge") - pl.col("cost_total")).alias("variance_dollars"),
        (
            (pl.col("actual_net_charge") - pl.col("cost_total")) / pl.col("cost_total") * 100
        ).alias("variance_pct"),
        pl.col("shipping_zone").cast(pl.Int64).alias("expected_zone_int"),
        pl.col("actual_zone").cast(pl.Int64, strict=False).alias("actual_zone_int"),
    ])

    # Top by absolute dollars
    by_dollars = (
        df_with_variance
        .select([
            "pcs_orderid", "pcs_ordernumber", "actual_trackingnumber",
            "cost_total", "actual_net_charge", "variance_dollars", "variance_pct",
            "expected_zone_int", "actual_zone_int",
        ])
        .sort(pl.col("variance_dollars").abs(), descending=True)
        .head(top_n)
        .to_dicts()
    )

    # Top by percentage (exclude very small expected values)
    by_percent = (
        df_with_variance
        .filter(pl.col("cost_total") > 1)  # Avoid division issues
        .select([
            "pcs_orderid", "pcs_ordernumber", "actual_trackingnumber",
            "cost_total", "actual_net_charge", "variance_dollars", "variance_pct",
            "expected_zone_int", "actual_zone_int",
        ])
        .sort(pl.col("variance_pct").abs(), descending=True)
        .head(top_n)
        .to_dicts()
    )

    return {"by_dollars": by_dollars, "by_percent": by_percent}


# =============================================================================
# HTML REPORT GENERATION
# =============================================================================

def format_currency(value: float | None) -> str:
    """Format number as currency."""
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def format_percent(value: float | None) -> str:
    """Format number as percentage."""
    if value is None:
        return "N/A"
    if value == float('inf'):
        return "+Inf%"
    return f"{value:+.2f}%"


def variance_class(value: float | None) -> str:
    """CSS class for variance coloring."""
    if value is None:
        return ""
    if value > 0.01:
        return "negative"  # Actual > Expected = bad (overpaying)
    elif value < -0.01:
        return "positive"  # Actual < Expected = good (underpaying)
    return ""


def generate_html_report(
    portfolio: dict,
    cost_positions: list[dict],
    zone_accuracy: dict,
    weight_accuracy: dict,
    surcharge_detection: list[dict],
    outliers: dict,
    filters: dict,
    state_zone_analysis: list[dict],
    base_cost_by_zone: list[dict],
    unpredictable_summary: dict,
) -> str:
    """Generate the full HTML report."""

    # Build filter description
    filter_parts = []
    if filters.get("invoice"):
        filter_parts.append(f"Invoice: {filters['invoice']}")
    if filters.get("date_from"):
        filter_parts.append(f"From: {filters['date_from']}")
    if filters.get("date_to"):
        filter_parts.append(f"To: {filters['date_to']}")
    filter_desc = " | ".join(filter_parts) if filter_parts else "No filters applied"

    # Cost positions table rows
    cost_rows = ""
    for pos in cost_positions:
        var_class = variance_class(pos["variance_dollars"]) if pos["variance_dollars"] is not None else ""
        is_total = pos["position"] == "TOTAL"
        is_unpredictable = pos["position"] == "Unpredictable"
        row_style = 'style="font-weight: bold; background-color: #f0f0f0;"' if is_total else ""
        if is_unpredictable:
            row_style = 'style="background-color: #fff3cd;"'

        expected_str = format_currency(pos['expected']) if pos['expected'] is not None else "N/A"
        variance_dollars_str = format_currency(pos['variance_dollars']) if pos['variance_dollars'] is not None else "N/A"
        variance_pct_str = format_percent(pos['variance_pct']) if pos['variance_pct'] is not None else "N/A"

        cost_rows += f"""
        <tr {row_style}>
            <td style="text-align: left;">{pos['position']}</td>
            <td>{expected_str}</td>
            <td>{format_currency(pos['actual'])}</td>
            <td class="{var_class}">{variance_dollars_str}</td>
            <td class="{var_class}">{variance_pct_str}</td>
        </tr>
        """

    # Zone mismatches table
    zone_mismatch_rows = ""
    for m in zone_accuracy.get("mismatches", [])[:10]:
        zone_mismatch_rows += f"""
        <tr>
            <td>{m['shipping_zone']}</td>
            <td>{m['actual_zone']}</td>
            <td>{m['count']:,}</td>
            <td class="{variance_class(m['cost_impact'])}">{format_currency(m['cost_impact'])}</td>
        </tr>
        """

    # Surcharge detection table
    surcharge_rows = ""
    for s in surcharge_detection:
        surcharge_rows += f"""
        <tr>
            <td style="text-align: left;">{s['surcharge']}</td>
            <td>{s['true_positive']:,}</td>
            <td>{s['false_positive']:,}</td>
            <td>{s['false_negative']:,}</td>
            <td>{s['true_negative']:,}</td>
            <td>{s['precision']:.1f}%</td>
            <td>{s['recall']:.1f}%</td>
        </tr>
        """

    # State zone analysis table
    state_zone_rows = ""
    for s in state_zone_analysis:
        match_class = "positive" if s['match_rate'] >= 95 else ("negative" if s['match_rate'] < 80 else "")
        var_class = variance_class(s['base_variance'])
        state_zone_rows += f"""
        <tr>
            <td style="text-align: left;">{s['shipping_region'] or 'Unknown'}</td>
            <td>{s['shipment_count']:,}</td>
            <td class="{match_class}">{s['match_rate']:.1f}%</td>
            <td>{s['smaller_pct']:.1f}%</td>
            <td>{s['bigger_pct']:.1f}%</td>
            <td>{format_currency(s['expected_base'])}</td>
            <td>{format_currency(s['actual_base'])}</td>
            <td class="{var_class}">{format_currency(s['base_variance'])}</td>
        </tr>
        """

    # Base cost by zone table
    base_zone_rows = ""
    for z in base_cost_by_zone:
        var_class = variance_class(z['base_variance'])
        base_zone_rows += f"""
        <tr>
            <td>{z['shipping_zone']}</td>
            <td>{z['shipment_count']:,}</td>
            <td>{format_currency(z['expected_base'])}</td>
            <td>{format_currency(z['actual_base'])}</td>
            <td class="{var_class}">{format_currency(z['base_variance'])}</td>
            <td class="{var_class}">{format_percent(z['variance_pct'])}</td>
            <td>{format_currency(z['avg_expected_base'])}</td>
            <td>{format_currency(z['avg_actual_base'])}</td>
            <td class="{var_class}">{format_currency(z['avg_variance'])}</td>
        </tr>
        """

    # Outliers by dollars
    outlier_dollar_rows = ""
    for o in outliers.get("by_dollars", []):
        var_class = variance_class(o["variance_dollars"])
        outlier_dollar_rows += f"""
        <tr>
            <td>{o['pcs_orderid']}</td>
            <td>{o['actual_trackingnumber'] or '-'}</td>
            <td>{format_currency(o['cost_total'])}</td>
            <td>{format_currency(o['actual_net_charge'])}</td>
            <td class="{var_class}">{format_currency(o['variance_dollars'])}</td>
            <td>{o['expected_zone_int']}</td>
            <td>{o['actual_zone_int']}</td>
        </tr>
        """

    # Outliers by percent
    outlier_pct_rows = ""
    for o in outliers.get("by_percent", []):
        var_class = variance_class(o["variance_pct"])
        outlier_pct_rows += f"""
        <tr>
            <td>{o['pcs_orderid']}</td>
            <td>{o['actual_trackingnumber'] or '-'}</td>
            <td>{format_currency(o['cost_total'])}</td>
            <td>{format_currency(o['actual_net_charge'])}</td>
            <td class="{var_class}">{format_percent(o['variance_pct'])}</td>
            <td>{o['expected_zone_int']}</td>
            <td>{o['actual_zone_int']}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>FedEx Cost Comparison Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 40px;
            color: #333;
            line-height: 1.6;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #4d148c;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 40px;
            border-bottom: 2px solid #bdc3c7;
            padding-bottom: 5px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            font-size: 14px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px 12px;
            text-align: right;
        }}
        th {{
            background-color: #4d148c;
            color: white;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        tr:hover {{
            background-color: #e8f4f8;
        }}
        .positive {{
            color: #27ae60;
            font-weight: 600;
        }}
        .negative {{
            color: #e74c3c;
            font-weight: 600;
        }}
        .summary-box {{
            background: linear-gradient(135deg, #4d148c 0%, #ff6200 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        .summary-item {{
            text-align: center;
        }}
        .summary-value {{
            font-size: 28px;
            font-weight: bold;
        }}
        .summary-label {{
            font-size: 12px;
            opacity: 0.9;
            text-transform: uppercase;
        }}
        .meta {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        .section {{
            margin-top: 50px;
        }}
        .accuracy-box {{
            display: inline-block;
            padding: 15px 25px;
            background: #ecf0f1;
            border-radius: 8px;
            margin: 10px 10px 10px 0;
        }}
        .accuracy-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .accuracy-label {{
            font-size: 12px;
            color: #7f8c8d;
        }}
        .warning-box {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
        }}
        .warning-box h4 {{
            margin: 0 0 10px 0;
            color: #856404;
        }}
    </style>
</head>
<body>
    <h1>FedEx Expected vs Actual Cost Comparison</h1>
    <p class="meta">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p class="meta">Filters: {filter_desc}</p>

    <!-- Portfolio Summary -->
    <div class="summary-box">
        <div class="summary-item">
            <div class="summary-value">{format_currency(portfolio['total_expected'])}</div>
            <div class="summary-label">Expected Total</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">{format_currency(portfolio['total_actual'])}</div>
            <div class="summary-label">Actual Total</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">{format_currency(portfolio['variance_dollars'])}</div>
            <div class="summary-label">Variance ($)</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">{format_percent(portfolio['variance_pct'])}</div>
            <div class="summary-label">Variance (%)</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">{portfolio['order_count']:,}</div>
            <div class="summary-label">Orders Compared</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">{portfolio['match_rate']:.1f}%</div>
            <div class="summary-label">Match Rate</div>
        </div>
    </div>

    <!-- Cost Position Accuracy -->
    <div class="section">
        <h2>Cost Position Accuracy</h2>
        <table>
            <thead>
                <tr>
                    <th style="text-align: left;">Position</th>
                    <th>Expected</th>
                    <th>Actual</th>
                    <th>Variance ($)</th>
                    <th>Variance (%)</th>
                </tr>
            </thead>
            <tbody>
                {cost_rows}
            </tbody>
        </table>
    </div>

    <!-- Unpredictable Charges Summary -->
    <div class="section">
        <h2>Unpredictable Charges Summary</h2>
        <div class="warning-box">
            <h4>Note: Unpredictable charges include taxes, signatures, address corrections, etc.</h4>
            <p>These charges cannot be predicted from shipment data alone and are tracked separately.</p>
        </div>
        <div>
            <div class="accuracy-box">
                <div class="accuracy-value">{format_currency(unpredictable_summary['total'])}</div>
                <div class="accuracy-label">Total Unpredictable</div>
            </div>
            <div class="accuracy-box">
                <div class="accuracy-value">{unpredictable_summary['order_count']:,}</div>
                <div class="accuracy-label">Orders with Unpredictable</div>
            </div>
            <div class="accuracy-box">
                <div class="accuracy-value">{format_currency(unpredictable_summary['avg_per_order'])}</div>
                <div class="accuracy-label">Avg per Affected Order</div>
            </div>
        </div>
    </div>

    <!-- Zone Accuracy -->
    <div class="section">
        <h2>Zone Accuracy</h2>
        <div>
            <div class="accuracy-box">
                <div class="accuracy-value">{zone_accuracy['match_rate']:.1f}%</div>
                <div class="accuracy-label">Zone Match Rate</div>
            </div>
            <div class="accuracy-box">
                <div class="accuracy-value">{zone_accuracy.get('matches', 0):,} / {zone_accuracy.get('total', 0):,}</div>
                <div class="accuracy-label">Matches / Total</div>
            </div>
            <div class="accuracy-box">
                <div class="accuracy-value">{format_currency(zone_accuracy.get('mismatch_cost_impact', 0))}</div>
                <div class="accuracy-label">Mismatch Cost Impact</div>
            </div>
            <div class="accuracy-box">
                <div class="accuracy-value">{zone_accuracy.get('zone_too_high', 0):,}</div>
                <div class="accuracy-label">Zone Too High</div>
            </div>
            <div class="accuracy-box">
                <div class="accuracy-value">{zone_accuracy.get('zone_too_low', 0):,}</div>
                <div class="accuracy-label">Zone Too Low</div>
            </div>
        </div>

        {"<h3>Zone Mismatches (Top 10)</h3>" if zone_mismatch_rows else "<p>No zone mismatches found.</p>"}
        {f'''<table>
            <thead>
                <tr>
                    <th>Expected Zone</th>
                    <th>Actual Zone</th>
                    <th>Count</th>
                    <th>Cost Impact</th>
                </tr>
            </thead>
            <tbody>
                {zone_mismatch_rows}
            </tbody>
        </table>''' if zone_mismatch_rows else ''}
    </div>

    <!-- Weight Accuracy -->
    <div class="section">
        <h2>Weight Accuracy</h2>
        <div>
            <div class="accuracy-box">
                <div class="accuracy-value">{weight_accuracy['match_rate']:.1f}%</div>
                <div class="accuracy-label">Match Rate (within {weight_accuracy.get('tolerance', 0.5)} lbs)</div>
            </div>
            <div class="accuracy-box">
                <div class="accuracy-value">{weight_accuracy['avg_diff']:+.2f} lbs</div>
                <div class="accuracy-label">Avg Difference (Actual - Expected)</div>
            </div>
            <div class="accuracy-box">
                <div class="accuracy-value">{weight_accuracy.get('matches', 0):,} / {weight_accuracy.get('total', 0):,}</div>
                <div class="accuracy-label">Matches / Total</div>
            </div>
        </div>
    </div>

    <!-- Surcharge Detection -->
    <div class="section">
        <h2>Deterministic Surcharge Detection</h2>
        <p class="meta">TP: Expected AND charged | FP: Expected but NOT charged | FN: NOT expected but charged | TN: NOT expected AND NOT charged</p>
        <table>
            <thead>
                <tr>
                    <th style="text-align: left;">Surcharge</th>
                    <th>TP</th>
                    <th>FP</th>
                    <th>FN</th>
                    <th>TN</th>
                    <th>Precision</th>
                    <th>Recall</th>
                </tr>
            </thead>
            <tbody>
                {surcharge_rows}
            </tbody>
        </table>
    </div>

    <!-- Base Cost by Zone -->
    <div class="section">
        <h2>Base Cost Analysis by Zone</h2>
        <p class="meta">Compares expected vs actual base rates grouped by expected zone. Helps identify if rate card differences are zone-specific.</p>
        <table>
            <thead>
                <tr>
                    <th>Zone</th>
                    <th>Shipments</th>
                    <th>Expected Base</th>
                    <th>Actual Base</th>
                    <th>Variance ($)</th>
                    <th>Variance (%)</th>
                    <th>Avg Expected</th>
                    <th>Avg Actual</th>
                    <th>Avg Variance</th>
                </tr>
            </thead>
            <tbody>
                {base_zone_rows if base_zone_rows else '<tr><td colspan="9">No data</td></tr>'}
            </tbody>
        </table>
    </div>

    <!-- State Zone Analysis -->
    <div class="section">
        <h2>Zone Accuracy by State</h2>
        <p class="meta">Zone match analysis per US state. "Smaller" means expected zone &lt; actual zone (we underestimated distance). "Bigger" means expected zone &gt; actual zone (we overestimated).</p>
        <table>
            <thead>
                <tr>
                    <th style="text-align: left;">State</th>
                    <th>Shipments</th>
                    <th>Zone Match</th>
                    <th>Smaller Zone</th>
                    <th>Bigger Zone</th>
                    <th>Expected Base</th>
                    <th>Actual Base</th>
                    <th>Base Variance</th>
                </tr>
            </thead>
            <tbody>
                {state_zone_rows if state_zone_rows else '<tr><td colspan="8">No data</td></tr>'}
            </tbody>
        </table>
    </div>

    <!-- Outliers -->
    <div class="section">
        <h2>Outliers - Top 20 by Absolute Variance</h2>
        <table>
            <thead>
                <tr>
                    <th>Order ID</th>
                    <th>Tracking #</th>
                    <th>Expected</th>
                    <th>Actual</th>
                    <th>Variance ($)</th>
                    <th>Exp Zone</th>
                    <th>Act Zone</th>
                </tr>
            </thead>
            <tbody>
                {outlier_dollar_rows if outlier_dollar_rows else '<tr><td colspan="7">No data</td></tr>'}
            </tbody>
        </table>

        <h2>Outliers - Top 20 by Percentage Variance</h2>
        <table>
            <thead>
                <tr>
                    <th>Order ID</th>
                    <th>Tracking #</th>
                    <th>Expected</th>
                    <th>Actual</th>
                    <th>Variance (%)</th>
                    <th>Exp Zone</th>
                    <th>Act Zone</th>
                </tr>
            </thead>
            <tbody>
                {outlier_pct_rows if outlier_pct_rows else '<tr><td colspan="7">No data</td></tr>'}
            </tbody>
        </table>
    </div>

</body>
</html>
"""
    return html


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Compare expected vs actual FedEx shipping costs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m carriers.fedex.scripts.compare_expected_to_actuals
  python -m carriers.fedex.scripts.compare_expected_to_actuals --invoice 26D0I70116
  python -m carriers.fedex.scripts.compare_expected_to_actuals --date_from 2025-01-01 --date_to 2025-01-31
  python -m carriers.fedex.scripts.compare_expected_to_actuals --output my_report.html
        """
    )

    parser.add_argument(
        "--invoice",
        type=str,
        default=None,
        help="Filter by specific invoice number"
    )
    parser.add_argument(
        "--date_from",
        type=str,
        default=None,
        help="Filter by invoice_date >= date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--date_to",
        type=str,
        default=None,
        help="Filter by invoice_date <= date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output HTML filename (default: comparison_report_YYYYMMDD_HHMMSS.html)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("FEDEX EXPECTED VS ACTUAL COST COMPARISON")
    print("=" * 60)

    # Load data
    print("\nLoading comparison data...")
    df = load_comparison_data(
        invoice=args.invoice,
        date_from=args.date_from,
        date_to=args.date_to,
    )
    print(f"  Loaded {len(df):,} matched order records")

    if len(df) == 0:
        print("\nNo matched data found for the given filters.")
        print("Make sure both expected and actual tables have data for the specified criteria.")
        return

    # Get match rate data
    print("Calculating match rate...")
    match_data = get_match_rate_data(
        invoice=args.invoice,
        date_from=args.date_from,
        date_to=args.date_to,
    )

    # Calculate metrics
    print("Calculating metrics...")
    portfolio = calc_portfolio_summary(df, match_data)
    cost_positions = calc_cost_position_accuracy(df)
    zone_accuracy = calc_zone_accuracy(df)
    weight_accuracy = calc_weight_accuracy(df)
    surcharge_detection = calc_surcharge_detection(df)
    outliers = calc_outliers(df)
    state_zone_analysis = calc_state_zone_analysis(df)
    base_cost_by_zone = calc_base_cost_by_zone(df)
    unpredictable_summary = calc_unpredictable_summary(df)

    # Generate report
    print("Generating HTML report...")
    filters = {
        "invoice": args.invoice,
        "date_from": args.date_from,
        "date_to": args.date_to,
    }
    html = generate_html_report(
        portfolio=portfolio,
        cost_positions=cost_positions,
        zone_accuracy=zone_accuracy,
        weight_accuracy=weight_accuracy,
        surcharge_detection=surcharge_detection,
        outliers=outliers,
        filters=filters,
        state_zone_analysis=state_zone_analysis,
        base_cost_by_zone=base_cost_by_zone,
        unpredictable_summary=unpredictable_summary,
    )

    # Save report
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.output:
        output_path = OUTPUT_DIR / args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"comparison_report_{timestamp}.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"\nReport saved to: {output_path.absolute()}")

    # Print summary to console
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Orders compared:     {portfolio['order_count']:,}")
    print(f"Expected total:      {format_currency(portfolio['total_expected'])}")
    print(f"Actual total:        {format_currency(portfolio['total_actual'])}")
    print(f"Variance:            {format_currency(portfolio['variance_dollars'])} ({portfolio['variance_pct']:+.2f}%)")
    print(f"Match rate:          {portfolio['match_rate']:.1f}%")
    print(f"Zone match rate:     {zone_accuracy['match_rate']:.1f}%")
    print(f"Weight match rate:   {weight_accuracy['match_rate']:.1f}%")
    print(f"Unpredictable total: {format_currency(unpredictable_summary['total'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
