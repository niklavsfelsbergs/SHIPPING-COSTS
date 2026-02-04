# Scenario 2: 100% Maersk

## Executive Summary

This scenario calculates the total shipping cost if 100% of US shipment volume were routed to Maersk US, a carrier not currently used in the production system. **Maersk would cost $6.44M vs the current mix of $6.39M, representing a 0.8% ($51K) increase**. While Maersk is competitive for lightweight packages (1-4 lbs), it becomes significantly more expensive for mid-to-heavy weight shipments due to high base rates and a dramatic rate jump at 30 lbs.

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

| Metric                        | Value                       |
|-------------------------------|-----------------------------|
| Total Shipments               | 558,210                     |
| Current Mix Total             | $6,389,595.72               |
| 100% Maersk Total             | $6,440,239.70               |
| **Difference**                | **+$50,643.98 (+0.8%)**     |
| Avg Cost/Shipment (Current)   | $11.45                      |
| Avg Cost/Shipment (Maersk)    | $11.54                      |

### Carrier Ranking (Full Coverage Only)

| Rank   | Carrier       | Serviceable   | Total Cost       | Avg Cost   |
|--------|---------------|---------------|------------------|------------|
| 1      | Current Mix   | 558,210       | $6,389,596       | $11.45     |
| 2      | Maersk        | 558,210       | $6,440,240       | $11.54     |
| 3      | FedEx         | 558,210       | $6,920,940       | $12.40     |
| 4      | USPS          | 558,210       | $8,195,287       | $14.68     |

*Note: OnTrac (64.6% coverage) and P2P (51.8% coverage) excluded - cannot service all shipments*

### Cost by Weight Bracket

The 30 lb rate jump is a critical cost driver for Maersk. The table below shows the breakdown between base rate and surcharges:

| Weight Bracket   | Shipments   | Current Avg   | Maersk Avg   | Base Rate   | Surcharges   | Diff %    |
|------------------|-------------|---------------|--------------|-------------|--------------|-----------|
| 0-1 lbs          | 145,692     | $6.80         | $6.01        | $5.47       | $0.54        | -12%      |
| 1-2 lbs          | 113,406     | $8.70         | $6.10        | $5.82       | $0.28        | -30%      |
| 2-3 lbs          | 96,358      | $10.13        | $8.11        | $6.11       | $2.00        | -20%      |
| 3-4 lbs          | 43,915      | $12.23        | $9.33        | $6.69       | $2.64        | -24%      |
| 4-5 lbs          | 41,170      | $12.39        | $12.59       | $7.67       | $4.92        | +2%       |
| 5-10 lbs         | 88,003      | $18.49        | $20.62       | $9.25       | $11.37       | +12%      |
| 10-20 lbs        | 24,071      | $24.75        | $36.93       | $17.88      | $19.05       | +49%      |
| 20-30 lbs        | 3,684       | $27.16        | $72.22       | $49.29      | $22.92       | +166%     |
| 30-70 lbs        | 1,853       | $33.36        | $99.86       | $75.61      | $24.25       | +199%     |
| **>70 lbs**      | **58**      | **$58.29**    | **$126.12**  | **$101.32** | **$24.80**   | **+116%** |

*Note: Shipments >70 lbs exceed Maersk's weight limit and are priced at the 70 lb rate (maximum available).*

**Key insight:** Surcharges stay relatively flat ($20-24) for heavier packages, while the **base rate** is the primary cost driver - jumping from $49 (20-30 lbs) to $76 (30-70 lbs) due to Maersk's 30 lb rate jump.

**The 30 lb Rate Jump:**

| Zone     | 29-30 lbs Rate   | 30-31 lbs Rate   | Increase              |
|----------|------------------|------------------|-----------------------|
| Zone 1   | $7.61            | $22.40           | +$14.79 (+194%)       |
| Zone 5   | $11.81           | $45.18           | +$33.37 (+283%)       |
| Zone 8   | $20.36           | $73.60           | +$53.24 (+262%)       |

While only 0.3% of shipments exceed 30 lbs, they represent 2.9% of Maersk's total cost.

### Cost by Zone

| Zone   | Shipments   | % of Total   | Current Avg   | Maersk Avg   | Difference        |
|--------|-------------|--------------|---------------|--------------|-------------------|
| 1      | 4,324       | 0.8%         | $9.59         | $8.94        | -$0.65 (-7%)      |
| 2      | 21,008      | 3.8%         | $9.34         | $8.56        | -$0.78 (-8%)      |
| 3      | 57,922      | 10.4%        | $9.89         | $9.31        | -$0.57 (-6%)      |
| 4      | 194,107     | 34.8%        | $10.44        | $10.29       | -$0.15 (-1%)      |
| 5      | 132,065     | 23.7%        | $11.40        | $11.59       | +$0.19 (+2%)      |
| 6      | 38,038      | 6.8%         | $12.54        | $13.01       | +$0.48 (+4%)      |
| 7      | 35,763      | 6.4%         | $13.84        | $14.89       | +$1.05 (+8%)      |
| 8      | 73,230      | 13.1%        | $13.76        | $14.48       | +$0.72 (+5%)      |
| 9      | 1,753       | 0.3%         | $38.67        | $40.43       | +$1.75 (+5%)      |

Maersk is cheaper in nearby zones (1-4) but more expensive in farther zones (5-9). The volume-weighted effect results in Maersk being +0.9% more expensive overall.

### Surcharge Breakdown

| Component         | Total Cost     | % of Total   | Shipments Affected   |
|-------------------|----------------|--------------|----------------------|
| Base Rate         | $4,233,509     | 65.7%        | 100%                 |
| NSL2 (>30")       | $516,260       | 8.0%         | 129,065 (23.1%)      |
| NSL1 (>21")       | $417,944       | 6.5%         | 104,486 (18.7%)      |
| NSD (>2 cu ft)    | $1,093,104     | 17.0%        | 60,728 (10.9%)       |
| Pickup Fee        | $183,707       | 2.9%         | 100%                 |

**Key Insight:** 41.8% of shipments trigger length surcharges (NSL1 or NSL2), and 10.9% trigger the volume surcharge (NSD). Surcharge overlap (NSL + NSD) affects 10.9% of shipments, adding $22 per package.

### Top Cost Drivers

**Package types where Maersk is EXPENSIVE:**

| Package Type                    | Shipments   | Avg Weight   | Current Avg   | Maersk Avg   | Diff    |
|---------------------------------|-------------|--------------|---------------|--------------|---------|
| PIZZA BOX 42x32x2 (2x str)      | 2,914       | 22.4 lbs     | $34.30        | $92.26       | +169%   |
| PIZZA BOX 42x32x2               | 24,864      | 8.9 lbs      | $28.35        | $32.65       | +15%    |

**Package types where Maersk is CHEAP:**

| Package Type                    | Shipments   | Avg Weight   | Current Avg   | Maersk Avg   | Diff    |
|---------------------------------|-------------|--------------|---------------|--------------|---------|
| PIZZA BOX 40x30x1               | 21,026      | 3.3 lbs      | $20.82        | $11.19       | -46%    |
| PIZZA BOX 20x16x2               | 36,319      | 3.2 lbs      | $9.43         | $6.30        | -33%    |
| PIZZA BOX 16x12x2               | 43,675      | 2.2 lbs      | $8.64         | $6.10        | -29%    |
| PIZZA BOX 20x16x1               | 117,217     | 1.3 lbs      | $8.56         | $6.10        | -29%    |

## Key Findings

1. **Maersk is slightly more expensive than current mix** (+0.8%, +$51K) for full volume.

2. **Maersk is competitive for lightweight packages (1-4 lbs)**: These represent 72% of shipments and show 15-31% cost savings vs current mix.

3. **The 30 lb rate jump is devastating**: Base rates nearly triple at the 30 lb threshold across all zones. Fortunately, only 0.3% of shipments exceed this weight.

4. **Surcharges are significant**: 34.3% of total cost comes from surcharges (NSL1/NSL2/NSD/Pickup), with the $18 NSD surcharge being the largest individual contributor.

5. **Zone pricing varies**: Maersk is cheaper in nearby zones (1-4) but more expensive in farther zones (5-9). The volume in zones 5-9 (50% of shipments) drives the overall cost increase.

6. **No fuel surcharge advantage**: Unlike competitors, Maersk has no separate fuel surcharge - this is built into base rates.

## Recommendation

**Maersk is not recommended as a 100% volume carrier** at +0.8% vs current mix.

However, Maersk could be valuable in a **selective routing strategy** for:
- Lightweight packages (1-4 lbs) - saves 15-31% vs current mix
- Packages under 21" longest dimension (avoids NSL surcharges)
- Nearby destinations (Zones 1-4) where Maersk has the best rates

**Avoid routing to Maersk:**
- Packages over 10 lbs (rates become uncompetitive)
- Large packages over 2 cubic feet (NSD surcharge adds $18)
- Packages approaching 30 lb threshold (massive rate jump)

---

*Analysis generated: February 2026*
*Data source: `shipments_aggregated.parquet` and `shipments_unified.parquet`*
*Script: `scenario_2_maersk_100.py`*
