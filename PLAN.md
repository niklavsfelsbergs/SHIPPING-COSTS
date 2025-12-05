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
├── database/                         # Shared across all carriers
│   ├── __init__.py                   # Connection, pull_data, push_data
│   └── pass.txt                      # Password file (gitignored)
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
    │   ├── __init__.py                      # Exports all surcharges + auto-inferred groupings
    │   ├── base.py                          # Surcharge base class
    │   ├── over_maximum_limits.py           # OML
    │   ├── large_package.py                 # LPS
    │   ├── additional_handling.py           # AHS
    │   ├── delivery_area.py                 # DAS
    │   ├── extended_delivery_area.py        # EDAS
    │   ├── residential.py                   # RES
    │   ├── demand_residential.py            # DEM_RES
    │   ├── demand_additional_handling.py    # DEM_AHS
    │   ├── demand_large_package.py          # DEM_LPS
    │   └── demand_over_maximum_limits.py    # DEM_OML
    │
    ├── pipeline/
    │   ├── __init__.py
    │   ├── load_inputs.py            # load_rates(), load_zones()
    │   ├── load_shipments.py         # SQL query to DB
    │   ├── supplement_shipments.py   # Dimensions, zones, billable weight
    │   ├── infer_surcharges.py       # Apply surcharge conditions
    │   └── calculator.py             # Orchestrates everything
    │
    ├── maintenance/
    │   ├── README.md
    │   └── generate_zones.py
    │
    └── scripts/
        ├── calculate_expected.py
        └── calculate_actuals.py
```

---

## Surcharge Design

### Base Class

```python
# surcharges/base.py
from abc import ABC, abstractmethod
import polars as pl


class Surcharge(ABC):
    """
    Base class for all surcharges.

    Required:
        name: Short code (e.g., "AHS", "DEM_RES")
        list_price: Published rate before discount
        discount: Decimal (0.70 = 70% off)
        allocation_type: "deterministic" or "allocated"

    Optional:
        priority_group: For mutually exclusive surcharges ("dimensional", "delivery")
        priority: Order within priority_group (1 = highest)
        min_billable_weight: Minimum billable weight when surcharge applies
        period_start: (month, day) tuple for demand period start
        period_end: (month, day) tuple for demand period end
        allocation_rate: Required if allocation_type="allocated" (e.g., 0.95)
    """

    # Required
    name: str
    list_price: float
    discount: float
    allocation_type: str

    # Optional
    priority_group: str | None = None
    priority: int | None = None
    min_billable_weight: int | None = None
    period_start: tuple[int, int] | None = None  # (month, day)
    period_end: tuple[int, int] | None = None    # (month, day)
    allocation_rate: float | None = None

    @classmethod
    def cost(cls) -> float:
        """Final cost after discount."""
        return cls.list_price * (1 - cls.discount)

    @classmethod
    def in_period(cls, month: int, day: int) -> bool:
        """Check if a date (month, day) falls within the surcharge period."""
        if cls.period_start is None or cls.period_end is None:
            return True  # No period restriction

        ship = (month, day)
        start = cls.period_start
        end = cls.period_end

        if start <= end:
            # Normal range (e.g., Mar 1 to Jun 30)
            return start <= ship <= end
        else:
            # Crosses year boundary (e.g., Sept 27 to Jan 16)
            return ship >= start or ship <= end

    @classmethod
    @abstractmethod
    def conditions(cls) -> pl.Expr:
        """Polars expression for when this surcharge triggers."""
        pass
```

### Attribute Reference

| Attribute | Required | Description |
|-----------|----------|-------------|
| `name` | Yes | Short code (e.g., "AHS") |
| `list_price` | Yes | Published rate before discount |
| `discount` | Yes | Decimal (0.70 = 70% off) |
| `allocation_type` | Yes | "deterministic" or "allocated" |
| `priority_group` | No | Only for mutually exclusive surcharges |
| `priority` | No | Order within priority_group (1 = highest) |
| `min_billable_weight` | No | Minimum billable weight when surcharge applies |
| `period_start` | No | (month, day) tuple for demand period start |
| `period_end` | No | (month, day) tuple for demand period end |
| `allocation_rate` | No | Required if allocation_type="allocated" |
| `conditions()` | Yes | Polars expression for trigger condition |

### Priority Groups (Mutual Exclusivity)

| Group | Surcharges | Logic |
|-------|------------|-------|
| `"dimensional"` | OML, LPS, AHS | Only highest priority applies (OML=1, LPS=2, AHS=3) |
| `"delivery"` | EDAS, DAS | Only one applies (EDAS=1, DAS=2) |

Surcharges without a priority_group are not mutually exclusive.

### Example: Deterministic Surcharge (AHS)

```python
# surcharges/ahs.py
import polars as pl
from .base import Surcharge


class AHS(Surcharge):
    """
    Additional Handling Surcharge

    Triggers when package exceeds weight, dimension, or volume thresholds.
    Contract: 70% discount, min billable weight 30 lbs
    """

    name = "AHS"
    list_price = 32.00
    discount = 0.70
    allocation_type = "deterministic"

    priority_group = "dimensional"
    priority = 3  # After OML (1), LPS (2)

    min_billable_weight = 30

    # Thresholds
    weight_threshold = 50
    longest_threshold = 48
    second_longest_threshold = 30
    cubic_threshold = 8640

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("weight_lbs").round(0) > cls.weight_threshold) |
            (pl.col("longest_side_in").round(0) > cls.longest_threshold) |
            (pl.col("second_longest_in").round(0) > cls.second_longest_threshold) |
            (pl.col("cubic_in").round(0) > cls.cubic_threshold)
        )
```

### Example: Allocated Surcharge (RES)

```python
# surcharges/res.py
import polars as pl
from .base import Surcharge


class RES(Surcharge):
    """
    Residential Surcharge (Allocated)

    Applied to ~95% of shipments based on historical data.
    Cannot predict per-shipment if residential or commercial.
    """

    name = "RES"
    list_price = 6.10
    discount = 0.90
    allocation_type = "allocated"
    allocation_rate = 0.95

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.lit(True)  # Always applies (allocated)
```

### Example: Demand Surcharge (DEM_AHS)

```python
# surcharges/demand_ahs.py
import polars as pl
from .base import Surcharge


class DEM_AHS(Surcharge):
    """
    Demand Additional Handling Surcharge

    Applied during peak season when AHS also applies.
    Period: Sept 27 - Jan 16 (year-agnostic)
    """

    name = "DEM_AHS"
    list_price = 11.00
    discount = 0.50
    allocation_type = "deterministic"

    period_start = (9, 27)   # Sept 27
    period_end = (1, 16)     # Jan 16

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("surcharge_ahs")  # Requires AHS to be triggered
```

### Example: Allocated Demand Surcharge (DEM_RES)

```python
# surcharges/demand_res.py
import polars as pl
from .base import Surcharge


class DEM_RES(Surcharge):
    """
    Demand Residential Surcharge (Allocated)

    Applied during residential demand period at 95% rate.
    Period: Oct 25 - Jan 16 (year-agnostic)
    """

    name = "DEM_RES"
    list_price = 1.00
    discount = 0.50
    allocation_type = "allocated"
    allocation_rate = 0.95

    period_start = (10, 25)  # Oct 25
    period_end = (1, 16)     # Jan 16

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.lit(True)  # Always applies during period (allocated)
```

### Surcharges __init__.py

Groupings are inferred automatically from surcharge class attributes:

```python
# surcharges/__init__.py
from .base import Surcharge
from .oml import OML
from .lps import LPS
from .ahs import AHS
from .das import DAS
from .edas import EDAS
from .res import RES
from .demand_res import DEM_RES
from .demand_ahs import DEM_AHS
from .demand_lps import DEM_LPS
from .demand_oml import DEM_OML

# All surcharges
ALL = [OML, LPS, AHS, DAS, EDAS, RES, DEM_RES, DEM_AHS, DEM_LPS, DEM_OML]


def get_by_priority_group(group: str) -> list[type[Surcharge]]:
    """Get surcharges in a priority group, sorted by priority (lowest number first)."""
    return sorted(
        [s for s in ALL if s.priority_group == group],
        key=lambda s: s.priority
    )


# Auto-inferred groupings
DIMENSIONAL = get_by_priority_group("dimensional")  # [OML, LPS, AHS]
DELIVERY = get_by_priority_group("delivery")        # [EDAS, DAS]
ALLOCATED = [s for s in ALL if s.allocation_type == "allocated"]
DEMAND = [s for s in ALL if s.period_start is not None]
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
"""
Billable Weight Configuration

Contract: DIM Factor 250 (standard OnTrac is 139)
Last updated: 2025-12-05
"""

DIM_FACTOR = 250          # Cubic inches per pound
DIM_THRESHOLD = 1728      # Min cubic inches to apply DIM weight (12x12x12)
```

### fuel.py

```python
# data/fuel.py
"""
Fuel Surcharge

Applied as percentage of subtotal (base + surcharges).
Updated weekly from ontrac.com/surcharges.

Last updated: 2025-12-05
"""

LIST_RATE = 0.195         # 19.5%
DISCOUNT = 0.35           # 35% contract discount
RATE = LIST_RATE * (1 - DISCOUNT)
```

---

## Pipeline Flow

```python
# Full calculation pipeline
df = load_shipments(start_date, end_date)
df = supplement_shipments(df)      # Dimensions, zones, billable weight
df = infer_surcharges(df)          # Apply all surcharge conditions
df = calculate_costs(df)           # Base rate + surcharge costs + fuel + total
```

### supplement_shipments.py

1. Calculate dimensions: `cubic_in`, `longest_side_in`, `second_longest_in`, `length_plus_girth`
2. Look up zones from zones.csv: `shipping_zone`, `das_zone`
3. Calculate billable weight using DIM_FACTOR and DIM_THRESHOLD

### infer_surcharges.py

1. For each priority_group, apply conditions in priority order (highest first)
2. Track which surcharge was applied to enforce mutual exclusivity
3. Apply min_billable_weight adjustments
4. Check period_start/period_end for demand surcharges against ship date (month, day only)
5. Output: `surcharge_oml`, `surcharge_lps`, `surcharge_ahs`, etc. (boolean columns)

### calculator.py

1. Look up base rate from base_rates.csv by zone + billable weight
2. Calculate cost for each surcharge based on flags
3. Handle allocated surcharges: `cost = surcharge.cost() * surcharge.allocation_rate`
4. Sum subtotal
5. Apply fuel surcharge
6. Calculate total
7. Stamp `calculator_version` from VERSION

---

## Implementation Parts

### Part 1: Foundation
- [x] `database/__init__.py` (shared across carriers)
- [x] `database/pass.txt`
- [x] `ontrac/version.py`
- [x] `.gitignore`

### Part 2: Data
- [x] `data/base_rates.csv` (copied from V1, removed date columns)
- [x] `data/zones.csv` (copied from V1)
- [x] `data/billable_weight.py`
- [x] `data/fuel.py`
- [x] `data/contracts/` folder structure (current/ and archive/)

### Part 3: Surcharges
- [x] `surcharges/base.py`
- [x] `surcharges/__init__.py`
- [x] `surcharges/over_maximum_limits.py`
- [x] `surcharges/large_package.py`
- [x] `surcharges/additional_handling.py`
- [x] `surcharges/delivery_area.py`
- [x] `surcharges/extended_delivery_area.py`
- [x] `surcharges/residential.py`
- [x] `surcharges/demand_residential.py`
- [x] `surcharges/demand_additional_handling.py`
- [x] `surcharges/demand_large_package.py`
- [x] `surcharges/demand_over_maximum_limits.py`

### Part 4: Pipeline
- [x] `pipeline/__init__.py`
- [ ] `pipeline/columns.py` (TODO: document all columns - database, calculated, surcharge flags)
- [x] `pipeline/load_inputs.py`
- [x] `pipeline/load_pcs_shipments.py` + `pipeline/sql/load_pcs_shipments.sql`
- [x] `pipeline/supplement_shipments.py`
- [x] `pipeline/calculate.py` (combined surcharge inference + cost calculation)

### Part 5: Maintenance
- [ ] `maintenance/README.md`
- [ ] `maintenance/generate_zones.py`

### Part 6: Scripts
- [ ] `scripts/calculate_expected.py`
- [ ] `scripts/calculate_actuals.py`

---

## Workflow for Updates

### Rate Change

1. Update `data/base_rates.csv` with new rates
2. Update `version.py`: `VERSION = "2025.07.01"`
3. Commit: `git commit -m "Rate update effective 2025-07-01 (+3% average)"`

### Surcharge Change (e.g., AHS discount 70% → 75%)

1. Edit `surcharges/ahs.py`: `discount = 0.75`
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

---

## Output Columns

After `calculator.py`:

| Column | Description |
|--------|-------------|
| `cost_base` | Base shipping rate |
| `cost_oml` | OML surcharge (if applicable) |
| `cost_lps` | LPS surcharge (if applicable) |
| `cost_ahs` | AHS surcharge (if applicable) |
| `cost_das` | DAS surcharge (if applicable) |
| `cost_edas` | EDAS surcharge (if applicable) |
| `cost_res` | RES surcharge (allocated) |
| `cost_dem_res` | Demand RES (allocated, if in period) |
| `cost_dem_ahs` | Demand AHS (if AHS + in period) |
| `cost_dem_lps` | Demand LPS (if LPS + in period) |
| `cost_dem_oml` | Demand OML (if OML + in period) |
| `cost_subtotal` | Sum before fuel |
| `cost_fuel` | Fuel surcharge |
| `cost_total` | Final total |
| `calculator_version` | Version stamp |
