# Scenario 5: Optimal with P2P

## Executive Summary

This analysis evaluates adding P2P US as a fourth carrier option. **Key finding: P2P does NOT improve the optimal mix when OnTrac's contractual minimum must be met.** P2P captures most shipments in unconstrained assignment (75%), but meeting OnTrac's 279K minimum forces expensive penalty-cost assignments, resulting in **$22.5M higher cost** than Scenario 4.

**Recommendation:** Do not add P2P to the carrier mix while the OnTrac contractual minimum remains at 279K shipments.

## Methodology

### Algorithm: Greedy + Adjustment (4 Carriers)

1. **Initial Assignment**: For each group, assign to cheapest carrier among OnTrac, USPS, FedEx, and P2P
2. **Constraint Enforcement**: Shift volume to meet OnTrac (279K) and USPS (140K) minimums
3. **Priority**: Preserve P2P assignments where possible, shift from FedEx/USPS first
4. **FedEx Earned Discount**: Apply if threshold reached

### Constraints

| Carrier | Minimum           | Notes                               |
|---------|-------------------|-------------------------------------|
| OnTrac  | 279,080 shipments | Contractual (5,365/week × 52)       |
| USPS    | 140,000 shipments | Tier 1 (35K/quarter × 4)            |
| P2P     | None              | No volume commitment                |
| FedEx   | None              | Earned discount tiers apply         |

## Results

### Initial Greedy Assignment (Before Constraints)

| Carrier | Shipments | % of Total | Notes                           |
|---------|-----------|------------|---------------------------------|
| P2P     | 418,985   | 75.1%      | Cheapest for most segments      |
| FedEx   | 73,266    | 13.1%      | -                               |
| USPS    | 62,098    | 11.1%      | -                               |
| OnTrac  | 3,861     | 0.7%       | Only wins in core service area  |

P2P dominates because it has no geographic penalty costs and competitive base rates.

### After Constraint Enforcement

| Carrier   | Shipments | % of Total | Total Cost       |
|-----------|-----------|------------|------------------|
| OnTrac    | 279,080   | 50.0%      | $26,573,571.99   |
| P2P       | 279,130   | 50.0%      | $1,305,155.25    |
| USPS      | 0         | 0.0%       | $0.00            |
| FedEx     | 0         | 0.0%       | $0.00            |
| **Total** | **558,210** | **100%** | **$27,878,727.24** |

### Constraint Satisfaction

| Carrier | Actual    | Minimum   | Status            |
|---------|-----------|-----------|-------------------|
| OnTrac  | 279,080   | 279,080   | **MET**           |
| USPS    | 0         | 140,000   | **NOT MET**       |
| P2P     | 279,130   | 0         | N/A               |
| FedEx   | 0         | 0         | N/A               |

**Problem:** Meeting OnTrac's minimum consumes all non-P2P volume, leaving nothing for USPS.

### Comparison to Scenario 4

| Metric               | Scenario 4      | Scenario 5       | Difference     |
|----------------------|-----------------|------------------|----------------|
| Total Cost           | $5,389,973.56   | $27,878,727.24   | +$22,488,753   |
| OnTrac Volume        | 279,080         | 279,080          | 0              |
| USPS Volume          | 200,310         | 0                | -200,310       |
| FedEx Volume         | 78,820          | 0                | -78,820        |
| P2P Volume           | N/A             | 279,130          | N/A            |

## Analysis: Why P2P Makes Things Worse

### The OnTrac Penalty Cost Problem

OnTrac only serves the US West region. For shipments outside this area, a **penalty cost** is applied to make them non-optimal. When P2P is added:

1. P2P has no geographic restrictions → captures 75% of volume (cheapest everywhere)
2. OnTrac only naturally captures 3,861 shipments (0.7%) in its core area
3. To meet OnTrac's 279K minimum, 275K shipments must be **forced** to OnTrac
4. These forced shipments are outside OnTrac's service area → penalty pricing
5. OnTrac average cost jumps to **$95/shipment** (vs $4.68 for P2P)

### Without P2P (Scenario 4)

| Carrier | Natural Assignment | After Constraints | Avg Cost/Shipment |
|---------|-------------------|-------------------|-------------------|
| OnTrac  | 153,957           | 279,080           | $9.26             |
| USPS    | 296,087           | 200,310           | $7.44             |
| FedEx   | 108,166           | 78,820            | $16.69            |

USPS naturally captures 53% of volume, leaving more competitive shipments for OnTrac.

### With P2P (Scenario 5)

| Carrier | Natural Assignment | After Constraints | Avg Cost/Shipment |
|---------|-------------------|-------------------|-------------------|
| OnTrac  | 3,861             | 279,080           | **$95.24**        |
| P2P     | 418,985           | 279,130           | $4.68             |
| USPS    | 62,098            | 0                 | N/A               |
| FedEx   | 73,266            | 0                 | N/A               |

P2P captures all the "easy" shipments, forcing OnTrac to take expensive out-of-area volume.

## P2P Segment Analysis

Where P2P would be cheapest (if no constraints):

### By Weight Bracket

| Weight   | Shipments | P2P Avg    | Next Best Avg |
|----------|-----------|------------|---------------|
| 1 lb     | 67,114    | $4.68      | ~$7-9         |
| 2 lbs    | 84,558    | $4.68      | ~$7-9         |
| 3 lbs    | 57,596    | $4.68      | ~$8-10        |
| 4-10 lbs | 69,862    | $4.68      | ~$9-12        |

P2P's flat/low rates beat other carriers across most weight brackets.

### Cost Comparison (P2P Segments)

If the 279,130 P2P shipments went to other carriers:

| Carrier | Total Cost       | Avg/Shipment |
|---------|------------------|--------------|
| P2P     | $1,305,155       | $4.68        |
| USPS    | $2,723,277       | $9.76        |
| FedEx   | $3,111,835       | $11.15       |
| OnTrac  | $76,416,282      | $273.77*     |

*OnTrac penalty costs for out-of-area shipments.

## Key Findings

1. **P2P is not viable with current OnTrac commitment**: The 279K OnTrac minimum cannot be efficiently met when P2P captures most volume.

2. **P2P is genuinely cheap**: At $4.68/shipment average, P2P beats all other carriers in unconstrained scenarios.

3. **Constraint interaction is critical**: P2P only works if OnTrac's minimum is significantly reduced or eliminated.

4. **USPS minimum also fails**: With P2P + OnTrac constraints, no volume remains for USPS.

## Recommendations

### Do Not Add P2P Under Current Constraints

The OnTrac contractual minimum makes P2P counterproductive. Adding P2P would cost **$22.5M more** than the current optimized mix.

### If Considering P2P in the Future

| OnTrac Min | P2P Viability | Notes |
|------------|---------------|-------|
| 279K       | Not viable    | Current situation |
| 150K       | Marginal      | Still forces expensive assignments |
| 50K        | Viable        | P2P can capture most volume |
| 0          | Optimal       | Unconstrained: save $1.3M vs S4 |

### Alternative: Renegotiate OnTrac

If OnTrac minimum could be reduced to ~50K shipments (for their core West region), P2P could capture non-West volume efficiently.

---

*Analysis generated: February 2026*
*Data source: shipments_aggregated.parquet (558,210 shipments)*
*Note: P2P US is not currently used - this is a future assessment*
