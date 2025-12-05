# OnTrac Shipping Cost Calculator - Implementation Plan

## Core Principle

**Git is the version control system.** The repository only reflects current reality. Historical versions are tracked through git commits, not through date-versioned configurations.

- Single `VERSION` constant at repository root
- Each calculation stamps `calculator_version` on output
- To recalculate historical period: `git checkout <commit>` and run

---

## Directory Structure

```
SHIPPING-COSTS/
├── shared/                           # Shared across all carriers
│   ├── database/
│   │   ├── __init__.py               # Connection, pull_data, push_data
│   │   └── pass.txt                  # Password file (gitignored)
│   └── sql/
│       ├── pcs_shipments.sql         # PCS shipments query
│       └── get_tracking_numbers.sql  # Tracking number lookup
│
├── tests/
│   ├── test_pipeline.py              # Unit tests for pipeline
│   ├── run_pipeline.py               # Run pipeline on mock data
│   └── data/                         # Mock shipment data
│
└── ontrac/
    ├── version.py                    # VERSION = "2025.12.05"
    │
    ├── data/
    │   ├── base_rates.csv            # Current rates only
    │   ├── zones.csv                 # Current zones only
    │   ├── billable_weight.py        # DIM_FACTOR, DIM_THRESHOLD
    │   ├── fuel.py                   # LIST_RATE, DISCOUNT, RATE
    │   └── contracts/
    │       ├── current/
    │       └── archive/
    │
    ├── surcharges/
    │   ├── __init__.py               # Exports all surcharges + BASE/DEPENDENT groups
    │   ├── base.py                   # Surcharge base class + in_period() helper
    │   ├── over_maximum_limits.py    # OML
    │   ├── large_package.py          # LPS
    │   ├── additional_handling.py    # AHS
    │   ├── delivery_area.py          # DAS
    │   ├── extended_delivery_area.py # EDAS
    │   ├── residential.py            # RES
    │   ├── demand_residential.py     # DEM_RES
    │   ├── demand_additional_handling.py    # DEM_AHS
    │   ├── demand_large_package.py          # DEM_LPS
    │   └── demand_over_maximum_limits.py    # DEM_OML
    │
    ├── loaders/                      # Source-specific data loaders
    │   ├── __init__.py
    │   └── pcs.py                    # load_pcs_shipments()
    │
    ├── core/                         # Source-agnostic calculation logic
    │   ├── __init__.py
    │   ├── columns.py                # Column schema definitions
    │   ├── inputs.py                 # load_rates(), load_zones(), FUEL_RATE
    │   ├── supplement.py             # Enrich with zones, dimensions, billable weight
    │   └── calculate.py              # Apply surcharges, calculate costs
    │
    ├── output/
    │   └── accuracy_reports/         # HTML comparison reports
    │
    └── scripts/
        ├── calculator.py             # Interactive CLI calculator
        ├── upload_expected.py        # Upload expected costs to DB
        ├── upload_actuals.py         # Upload actual invoice costs to DB
        ├── compare_expected_to_actuals.py  # Generate accuracy reports
        └── sql/
            ├── get_invoice_actuals.sql   # OnTrac invoice query
            └── comparison_base.sql       # Comparison join query
```

---

## Surcharge Design

### Base Class

```python
# surcharges/base.py
from abc import ABC
import polars as pl


def in_period(
    start: tuple[int, int],
    end: tuple[int, int],
    date_col: str = "ship_date"
) -> pl.Expr:
    """
    Check if date falls within a (month, day) period.
    Handles year boundary crossings (e.g., Sept 27 to Jan 16).
    """
    start_md = start[0] * 100 + start[1]
    end_md = end[0] * 100 + end[1]
    ship_md = (
        pl.col(date_col).dt.month().cast(pl.Int32) * 100 +
        pl.col(date_col).dt.day().cast(pl.Int32)
    )

    if start_md <= end_md:
        return (ship_md >= start_md) & (ship_md <= end_md)
    else:
        return (ship_md >= start_md) | (ship_md <= end_md)


class Surcharge(ABC):
    """
    Base class for all surcharges.

    Attributes:
        IDENTITY
            name            - Short code (e.g., "AHS", "DEM_RES")

        PRICING
            list_price      - Published rate before discount
            discount        - Decimal discount (0.70 = 70% off)
            is_allocated    - True if cost is spread across all shipments
            allocation_rate - Rate for allocated surcharges (e.g., 0.95)

        EXCLUSIVITY (for mutually exclusive surcharges)
            exclusivity_group - Group name (e.g., "dimensional", "delivery")
            priority          - Rank within group (1 = highest, wins ties)

        DEPENDENCIES
            depends_on      - Name of surcharge this depends on (e.g., "AHS")
            period_start    - (month, day) tuple for seasonal start
            period_end      - (month, day) tuple for seasonal end

        SIDE EFFECTS
            min_billable_weight - Minimum billable weight when triggered
    """

    # IDENTITY
    name: str

    # PRICING
    list_price: float
    discount: float
    is_allocated: bool = False
    allocation_rate: float | None = None

    # EXCLUSIVITY
    exclusivity_group: str | None = None
    priority: int | None = None

    # DEPENDENCIES
    depends_on: str | None = None
    period_start: tuple[int, int] | None = None
    period_end: tuple[int, int] | None = None

    # SIDE EFFECTS
    min_billable_weight: int | None = None

    @classmethod
    def net_price(cls) -> float:
        """Price after discount, before allocation."""
        return cls.list_price * (1 - cls.discount)

    @classmethod
    def cost(cls) -> float:
        """Cost per shipment (net_price * allocation_rate if allocated)."""
        if cls.is_allocated:
            return cls.net_price() * cls.allocation_rate
        return cls.net_price()

    @classmethod
    def conditions(cls) -> pl.Expr:
        """
        Polars expression for when this surcharge triggers.
        Default returns True (for allocated surcharges).
        Override for deterministic surcharges with specific conditions.
        """
        return pl.lit(True)
```

### Attribute Reference

| Attribute | Required | Description |
|-----------|----------|-------------|
| `name` | Yes | Short code (e.g., "AHS") |
| `list_price` | Yes | Published rate before discount |
| `discount` | Yes | Decimal (0.70 = 70% off) |
| `is_allocated` | No | True if cost is spread across all shipments (default: False) |
| `allocation_rate` | No | Required if is_allocated=True (e.g., 0.95) |
| `exclusivity_group` | No | Only for mutually exclusive surcharges |
| `priority` | No | Rank within exclusivity_group (1 = highest) |
| `depends_on` | No | Name of surcharge this depends on |
| `period_start` | No | (month, day) tuple for demand period start |
| `period_end` | No | (month, day) tuple for demand period end |
| `min_billable_weight` | No | Minimum billable weight when surcharge applies |
| `conditions()` | No | Polars expression (default: True for allocated) |

### Exclusivity Groups (Mutual Exclusivity)

| Group | Surcharges | Logic |
|-------|------------|-------|
| `"dimensional"` | OML, LPS, AHS | Only highest priority applies (OML=1, LPS=2, AHS=3) |
| `"delivery"` | EDAS, DAS | Only one applies (EDAS=1, DAS=2) |

Surcharges without an exclusivity_group are applied independently.

### Processing Groups

Surcharges are processed in two phases:

| Phase | Group | Description |
|-------|-------|-------------|
| 1 | BASE | Surcharges that don't reference other surcharge flags |
| 2 | DEPENDENT | Surcharges that reference flags from phase 1 (via `depends_on`) |

Within each phase, surcharges with the same `exclusivity_group` compete - only the highest priority (lowest number) wins.

### Example: Deterministic Surcharge (AHS)

```python
# surcharges/additional_handling.py
import polars as pl
from .base import Surcharge


class AHS(Surcharge):
    """Additional Handling - requires extra handling due to size/weight."""

    # Identity
    name = "AHS"

    # Pricing (70% discount per Third Amendment)
    list_price = 32.00
    discount = 0.70

    # Exclusivity (dimensional: OML > LPS > AHS)
    exclusivity_group = "dimensional"
    priority = 3

    # Side effects (negotiated down from OnTrac standard of 40)
    min_billable_weight = 30

    # Thresholds
    WEIGHT_LBS = 50
    LONGEST_IN = 48
    SECOND_LONGEST_IN = 30
    CUBIC_IN = 8640

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("weight_lbs").round(0) > cls.WEIGHT_LBS) |
            (pl.col("longest_side_in").round(0) > cls.LONGEST_IN) |
            (pl.col("second_longest_in").round(0) > cls.SECOND_LONGEST_IN) |
            (pl.col("cubic_in").round(0) > cls.CUBIC_IN)
        )
```

### Example: Allocated Surcharge (RES)

```python
# surcharges/residential.py
from .base import Surcharge


class RES(Surcharge):
    """Residential - allocated at 95% based on historical residential rate."""

    # Identity
    name = "RES"

    # Pricing (90% discount, allocated at 95%)
    list_price = 6.10
    discount = 0.90
    is_allocated = True
    allocation_rate = 0.95

    # Uses default conditions() -> pl.lit(True)
```

### Example: Dependent Demand Surcharge (DEM_AHS)

```python
# surcharges/demand_additional_handling.py
import polars as pl
from .base import Surcharge, in_period


class DEM_AHS(Surcharge):
    """Demand Additional Handling - seasonal surcharge when AHS applies."""

    # Identity
    name = "DEM_AHS"

    # Pricing (50% discount per Second Amendment)
    list_price = 11.00
    discount = 0.50

    # Dependencies
    depends_on = "AHS"
    period_start = (9, 27)   # Sept 27
    period_end = (1, 16)     # Jan 16

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("surcharge_ahs") & in_period(cls.period_start, cls.period_end)
```

### Surcharges __init__.py

```python
# surcharges/__init__.py
from .base import Surcharge, in_period
from .over_maximum_limits import OML
from .large_package import LPS
from .additional_handling import AHS
from .delivery_area import DAS
from .extended_delivery_area import EDAS
from .residential import RES
from .demand_residential import DEM_RES
from .demand_additional_handling import DEM_AHS
from .demand_large_package import DEM_LPS
from .demand_over_maximum_limits import DEM_OML

# All surcharges
ALL = [OML, LPS, AHS, DAS, EDAS, RES, DEM_RES, DEM_AHS, DEM_LPS, DEM_OML]

# Processing groups
BASE = [s for s in ALL if s.depends_on is None]
# OnTrac: [OML, LPS, AHS, DAS, EDAS, RES]

DEPENDENT = [s for s in ALL if s.depends_on is not None]
# OnTrac: [DEM_RES, DEM_AHS, DEM_LPS, DEM_OML]


def get_exclusivity_group(group: str) -> list[type[Surcharge]]:
    """Get surcharges in an exclusivity group, sorted by priority."""
    return sorted(
        [s for s in ALL if s.exclusivity_group == group],
        key=lambda s: s.priority
    )


def get_unique_exclusivity_groups(surcharges: list) -> set[str]:
    """Get unique exclusivity group names from a list of surcharges."""
    return {s.exclusivity_group for s in surcharges if s.exclusivity_group is not None}
```

---

## Data Files

### base_rates.csv

Simple format - no date columns:

```csv
weight_lbs_lower,weight_lbs_upper,zone_2,zone_3,zone_4,zone_5,zone_6,zone_7,zone_8
0,1,4.00,4.00,4.21,4.39,4.54,4.62,4.68
1,2,4.00,4.41,4.81,4.92,5.13,5.35,5.42
...
```

### zones.csv

```csv
zip_code,shipping_state,phx_zone,cmh_zone,das
95613,California,4,5,EDAS
19711,Delaware,8,4,NO
...
```

### billable_weight.py

```python
# data/billable_weight.py
DIM_FACTOR = 250          # Cubic inches per pound
DIM_THRESHOLD = 1728      # Min cubic inches to apply DIM weight (12x12x12)
```

### fuel.py

```python
# data/fuel.py
LIST_RATE = 0.195         # 19.5%
DISCOUNT = 0.35           # 35% contract discount
RATE = LIST_RATE * (1 - DISCOUNT)
```

---

## Column Schema

Defined in `core/columns.py`:

### Required Input Columns (from any loader)

| Column | Description |
|--------|-------------|
| `ship_date` | Ship date (for demand period checks) |
| `production_site` | "Phoenix" or "Columbus" (for zone lookup) |
| `shipping_zip_code` | Destination ZIP code |
| `shipping_region` | Destination state/region |
| `length_in` | Package length (inches) |
| `width_in` | Package width (inches) |
| `height_in` | Package height (inches) |
| `weight_lbs` | Package weight (pounds) |

### PCS-Specific Columns (from PCS loader)

| Column | Description |
|--------|-------------|
| `pcs_ordernumber` | PCS order number |
| `pcs_orderid` | PCS order ID |
| `pcs_created` | PCS order creation date |
| `trackingnumber` | Carrier tracking number |
| `shop_ordernumber` | Shop reference number |
| `shipping_country` | Destination country name |

### Supplement Columns (added by supplement_shipments)

| Column | Description |
|--------|-------------|
| `cubic_in` | L x W x H (cubic inches) |
| `longest_side_in` | Longest dimension |
| `second_longest_in` | Second longest dimension |
| `length_plus_girth` | Longest + 2*(sum of other two) |
| `shipping_zone` | Shipping zone (2-8) |
| `das_zone` | DAS classification: "DAS", "EDAS", or "NO" |
| `dim_weight_lbs` | Dimensional weight |
| `uses_dim_weight` | True if dim weight > actual weight |
| `billable_weight_lbs` | Max of actual and dim weight |

### Output Columns (after calculate)

| Column | Description |
|--------|-------------|
| `surcharge_*` | Boolean flag for each surcharge |
| `cost_*` | Cost for each surcharge |
| `cost_base` | Base shipping rate |
| `cost_subtotal` | Sum before fuel |
| `cost_fuel` | Fuel surcharge |
| `cost_total` | Final total |
| `calculator_version` | Version stamp |

---

## Pipeline Flow

```python
# Full calculation pipeline
from ontrac.loaders import load_pcs_shipments
from ontrac.core import supplement_shipments, calculate

df = load_pcs_shipments(start_date, end_date)
df = supplement_shipments(df)    # Dimensions, zones, billable weight
df = calculate(df)               # Surcharges + costs
```

### supplement.py

1. Calculate dimensions: `cubic_in`, `longest_side_in`, `second_longest_in`, `length_plus_girth`
2. Look up zones from zones.csv: `shipping_zone`, `das_zone`
3. Calculate billable weight using DIM_FACTOR and DIM_THRESHOLD

### calculate.py

```python
def calculate(df: pl.DataFrame) -> pl.DataFrame:
    # Phase 1: Apply base surcharges (don't reference other surcharge flags)
    df = _apply_surcharges(df, BASE)

    # Phase 2: Apply dependent surcharges (reference flags from phase 1)
    df = _apply_surcharges(df, DEPENDENT)

    # Phase 3: Adjust billable weights based on triggered surcharges
    df = _apply_min_billable_weights(df)

    # Phase 4: Look up base shipping rate
    df = _lookup_base_rate(df)

    # Phase 5: Calculate costs
    df = _calculate_subtotal(df)
    df = _apply_fuel(df)
    df = _calculate_total(df)

    # Phase 6: Stamp version
    df = _stamp_version(df)

    return df
```

Within `_apply_surcharges`:
- Standalone surcharges (no exclusivity_group) are applied independently
- Exclusive surcharges (same exclusivity_group) compete - only highest priority wins

---

## Implementation Parts

### Part 1: Foundation
- [x] `shared/database/__init__.py` (shared across carriers)
- [x] `shared/database/pass.txt`
- [x] `ontrac/version.py`
- [x] `.gitignore`

### Part 2: Data
- [x] `data/base_rates.csv`
- [x] `data/zones.csv`
- [x] `data/billable_weight.py`
- [x] `data/fuel.py`
- [x] `data/contracts/` folder structure

### Part 3: Surcharges
- [x] `surcharges/base.py`
- [x] `surcharges/__init__.py`
- [x] All 10 surcharge files (OML, LPS, AHS, DAS, EDAS, RES, DEM_*)

### Part 4: Loaders
- [x] `loaders/__init__.py`
- [x] `loaders/pcs.py` + `shared/sql/pcs_shipments.sql`

### Part 5: Core Pipeline
- [x] `core/__init__.py`
- [x] `core/columns.py`
- [x] `core/inputs.py`
- [x] `core/supplement.py`
- [x] `core/calculate.py`

### Part 6: Tests
- [x] `tests/test_pipeline.py`
- [x] `tests/run_pipeline.py`
- [x] `tests/data/mock_shipments.csv`

### Part 7: Scripts
- [x] `scripts/calculator.py` - Interactive CLI calculator
- [x] `scripts/upload_expected.py` - Upload expected costs to Redshift
- [x] `scripts/upload_actuals.py` - Upload actual invoice costs to Redshift
- [x] `scripts/compare_expected_to_actuals.py` - Generate HTML accuracy reports

---

## Workflow for Updates

### Rate Change

1. Update `data/base_rates.csv` with new rates
2. Update `version.py`: `VERSION = "2025.07.01"`
3. Commit: `git commit -m "Rate update effective 2025-07-01 (+3% average)"`

### Surcharge Change (e.g., AHS discount 70% → 75%)

1. Edit `surcharges/additional_handling.py`: `discount = 0.75`
2. Update `version.py`: `VERSION = "2025.07.15"`
3. Commit: `git commit -m "AHS discount increased to 75% per Fourth Amendment"`

### Fuel Rate Change

1. Edit `data/fuel.py`: `LIST_RATE = 0.200`
2. Update `version.py`: `VERSION = "2025.12.09"`
3. Commit: `git commit -m "Fuel rate 19.5% → 20.0% (week of Dec 9)"`

### New Demand Season

1. Edit demand surcharge files with new period_start/period_end if dates changed
2. Update `version.py`
3. Commit: `git commit -m "Demand period dates updated for 2026-2027 season"`

### Historical Recalculation

```bash
git checkout v2025.11.15
python -m ontrac.scripts.calculate_expected --start-date 2025-11-01 --end-date 2025-11-30
git checkout main
```
