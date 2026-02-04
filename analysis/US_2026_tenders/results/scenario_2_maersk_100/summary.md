# Scenario 2: 100% Maersk

## Executive Summary

This scenario calculates the total shipping cost if 100% of US shipment volume were routed to Maersk US, a carrier not currently used in the production system. Using the `maersk_cost_total` column from the aggregated dataset, we find that **Maersk would cost $6.44M vs the current mix of $6.22M, representing a 3.6% ($226K) increase**. While Maersk is competitive for lightweight packages (1-4 lbs), it becomes significantly more expensive for mid-to-heavy weight shipments due to high base rates and a dramatic rate jump at 30 lbs.

## Methodology

Maersk US shipping costs are calculated as:

**Cost = Base Rate + Surcharges + Pickup Fee**

Where:
- **Base Rate**: Determined by zone (1-9) and billable weight. Rates range from $3.11 (light, Zone 1) to $175.85 (heavy, Zone 9). A significant rate jump occurs at 30 lbs.
- **Billable Weight**: MAX(actual weight, dimensional weight), where DIM weight = cubic inches / 166. No threshold - DIM always compared.
- **Surcharges**:
  - NSL1: $4.00 for packages with longest side > 21" (mutually exclusive with NSL2)
  - NSL2: $4.00 for packages with longest side > 30"
  - NSD: $18.00 for packages > 3,456 cubic inches (2 cu ft)
  - NSL and NSD can stack
- **Pickup Fee**: $0.04 per billable pound (always applies)
- **No fuel surcharge** - included in base rates

## Results

### Total Cost

| Metric | Value |
|--------|-------|
| Total Shipments | 558,210 |
| Current Mix Total | $6,218,604.91 |
| 100% Maersk Total | $6,444,524.54 |
| **Difference** | **+$225,919.63 (+3.6%)** |
| Avg Cost/Shipment (Current) | $11.14 |
| Avg Cost/Shipment (Maersk) | $11.54 |

### Carrier Ranking

| Rank | Carrier | Total Cost | vs Current |
|------|---------|------------|------------|
| 1 | P2P | $5,778,874 | -7.1% |
| **2** | **Maersk** | **$6,444,525** | **+3.6%** |
| 3 | FedEx | $6,920,940 | +11.3% |
| 4 | USPS | $8,195,287 | +31.8% |
| 5 | OnTrac* | $102,989,854 | +1556.2% |

*OnTrac includes penalty costs for non-serviceable areas

### Cost by Weight Bracket

The 30 lb rate jump is a critical cost driver for Maersk:

| Weight Bracket | Shipments | % of Total | Current Avg | Maersk Avg | Difference |
|----------------|-----------|------------|-------------|------------|------------|
| 0-1 lbs | 145,692 | 26.1% | $7.18 | $6.01 | -$1.17 (-16%) |
| 1-2 lbs | 113,406 | 20.3% | $8.82 | $6.10 | -$2.72 (-31%) |
| 2-3 lbs | 96,358 | 17.3% | $10.29 | $8.11 | -$2.18 (-21%) |
| 3-4 lbs | 43,915 | 7.9% | $12.41 | $9.33 | -$3.07 (-25%) |
| 4-5 lbs | 41,170 | 7.4% | $12.52 | $12.59 | +$0.07 (+1%) |
| 5-10 lbs | 87,003 | 15.6% | $18.82 | $21.65 | +$2.83 (+15%) |
| 10-20 lbs | 22,543 | 4.0% | $25.06 | $42.31 | +$17.25 (+69%) |
| 20-30 lbs | 3,229 | 0.6% | $27.36 | $74.54 | +$47.18 (+172%) |
| **> 30 lbs** | **1,853** | **0.3%** | **$30.40** | **$99.85** | **+$69.45 (+228%)** |

**The 30 lb Rate Jump:**

| Zone | 29-30 lbs Rate | 30-31 lbs Rate | Increase |
|------|----------------|----------------|----------|
| Zone 1 | $7.61 | $22.40 | +$14.79 (+194%) |
| Zone 5 | $11.81 | $45.18 | +$33.37 (+283%) |
| Zone 8 | $20.36 | $73.60 | +$53.24 (+262%) |

While only 0.3% of shipments exceed 30 lbs, they represent 2.9% of Maersk's total cost.

### Cost by Zone

| Zone | Shipments | % of Total | Current Avg | Maersk Avg | Difference |
|------|-----------|------------|-------------|------------|------------|
| 1 | 4,324 | 0.8% | $10.58 | $8.94 | -$1.64 (-15%) |
| 2 | 21,008 | 3.8% | $9.61 | $8.56 | -$1.04 (-11%) |
| 3 | 57,922 | 10.4% | $10.21 | $9.31 | -$0.90 (-9%) |
| 4 | 194,107 | 34.8% | $10.90 | $10.29 | -$0.61 (-6%) |
| 5 | 132,065 | 23.7% | $11.87 | $11.59 | -$0.28 (-2%) |
| 6 | 38,038 | 6.8% | $12.98 | $13.01 | +$0.04 (+0%) |
| 7 | 35,763 | 6.4% | $15.00 | $14.89 | -$0.10 (-1%) |
| 8 | 73,230 | 13.1% | $14.68 | $14.48 | -$0.21 (-1%) |
| 9 | 1,753 | 0.3% | $39.41 | $40.43 | +$1.01 (+3%) |

Maersk is competitive or cheaper across most zones, with the largest advantage in nearby zones (1-4).

### Surcharge Breakdown

| Component | Total Cost | % of Total | Shipments Affected |
|-----------|------------|------------|-------------------|
| Base Rate | $4,233,509 | 65.7% | 100% |
| NSL2 (>30") | $516,260 | 8.0% | 129,065 (23.1%) |
| NSL1 (>21") | $417,944 | 6.5% | 104,486 (18.7%) |
| NSD (>2 cu ft) | $1,093,104 | 17.0% | 60,728 (10.9%) |
| Pickup Fee | $183,707 | 2.9% | 100% |

**Key Insight:** 41.8% of shipments trigger length surcharges (NSL1 or NSL2), and 10.9% trigger the volume surcharge (NSD). Surcharge overlap (NSL + NSD) affects 10.9% of shipments, adding $22 per package.

### Top Cost Drivers

**Package types where Maersk is EXPENSIVE:**

| Package Type | Shipments | Avg Weight | Current Avg | Maersk Avg | Diff |
|--------------|-----------|------------|-------------|------------|------|
| PIZZA BOX 42x32x2 (2x str) | 2,914 | 22.4 lbs | $34.46 | $92.26 | +168% |
| 21" Tube | 12,377 | 0.6 lbs | $7.74 | $9.61 | +81% |
| PIZZA BOX 12x8x1 | 55,898 | 0.7 lbs | $5.96 | $5.24 | +49% |
| MUG BOX 5x5x5 | 4,464 | 0.9 lbs | $5.85 | $4.64 | +48% |
| PIZZA BOX 42x32x2 | 24,864 | 8.9 lbs | $28.41 | $32.65 | +15% |

**Package types where Maersk is CHEAP:**

| Package Type | Shipments | Avg Weight | Current Avg | Maersk Avg | Diff |
|--------------|-----------|------------|-------------|------------|------|
| PIZZA BOX 40x30x1 | 21,026 | 3.3 lbs | $21.14 | $11.19 | -47% |
| PIZZA BOX 20x16x2 | 36,319 | 3.2 lbs | $9.56 | $6.30 | -34% |
| MIXPIX BOX | 3,239 | 1.3 lbs | $8.33 | $5.69 | -32% |
| PIZZA BOX 16x12x2 | 43,675 | 2.2 lbs | $8.82 | $6.10 | -31% |
| PIZZA BOX 20x16x1 | 117,217 | 1.3 lbs | $8.69 | $6.10 | -30% |
| MUG BOX 16x12x8 | 4,965 | 4.6 lbs | $10.09 | $7.23 | -28% |

## Key Findings

1. **Maersk is competitive for lightweight packages (1-4 lbs)**: These represent 72% of shipments and show 21-31% cost savings vs current mix.

2. **The 30 lb rate jump is devastating**: Base rates nearly triple at the 30 lb threshold across all zones. Fortunately, only 0.3% of shipments exceed this weight.

3. **Surcharges are significant**: 34.5% of total cost comes from surcharges (NSL1/NSL2/NSD/Pickup), with the $18 NSD surcharge being the largest individual contributor.

4. **Zone pricing is competitive**: Maersk matches or beats current carriers across most zones, with the biggest advantage in zones 1-4 (closer destinations).

5. **No fuel surcharge advantage**: Unlike competitors, Maersk has no separate fuel surcharge - this is built into base rates.

6. **Heavy/bulky packages are expensive**: Packages over 10 lbs or with large dimensions (triggering NSD) see 50-200%+ cost increases vs current mix.

## Recommendation

**Maersk should NOT be used as a 100% volume carrier.** At +3.6% vs current mix, it's more expensive overall.

However, Maersk could be valuable in a **selective routing strategy** for:
- Lightweight packages (1-4 lbs) - saves 21-31% vs current mix
- Packages under 21" longest dimension (avoids NSL surcharges)
- Nearby destinations (Zones 1-4) where Maersk has the best rates

**Avoid routing to Maersk:**
- Packages over 10 lbs (rates become uncompetitive)
- Large packages over 2 cubic feet (NSD surcharge adds $18)
- Packages approaching 30 lb threshold (massive rate jump)

**Potential use case:** If USPS volume commitments are met and additional capacity is needed, Maersk could serve as a secondary carrier for the lightweight package segment, potentially yielding $500K+ in annual savings on that subset alone.

---

*Analysis generated: February 2026*
*Data source: `shipments_aggregated.parquet` and `shipments_unified.parquet`*
*Script: `scenario_2_maersk_100.py`*
