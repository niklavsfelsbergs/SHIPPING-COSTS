# Scenario 15: 3-Group Static Rules for P2P + FedEx

## Overview
Implementable version of S14 using 3 static weight-group rules.
FedEx HD at 16% earned discount, SP at 4%,
undiscounted spend constrained >= $5.1M.

## Rules

| Group  | Weight     | Package Types | Shipments | P2P US Zone                     | Other Zone                     |
|--------|------------|---------------|-----------|----------------------------------|--------------------------------|
| Light  | <= 3 lbs   | 20            | 350,835   | P2P US if wt <= 3 lbs           | P2P US2 if wt <= 1 lbs, else FedEx |
| Medium | 3-21 lbs   | 18            | 116,561   | P2P US if wt <= 21 lbs          | P2P US2 if wt <= 2 lbs, else FedEx |
| Heavy  | > 21 lbs   | 15            | 72,521    | FedEx always                     | FedEx always                   |

**Routing codes:** PFAP = P2P US (preferred), PFA = P2P US (any weight in P2P US zone), PFS = P2P US2 (small weight fallback), FEDEX = FedEx

## Results
- Total shipments: 539,917
- Current mix (S1): $6,072,061.73
- S15 3-Group: $5,099,098.80
- **Difference vs S1: -$972,962.93 (-16.0%)**
- Avg per shipment: $9.44 (vs $11.25 current)

## FedEx Earned Discount
- FedEx HD earned discount: **16%**
- FedEx SP earned discount: **4%**
- FedEx undiscounted spend: $5,133,405.60 (HD: $3,680,643.16 + SP: $1,452,762.44)
- FedEx undiscounted threshold: $5,100,000
- **Margin above threshold: $33,405.60** (MET)

## Carrier Selection

| Carrier  | Shipments | Share  | Total Cost     | Avg Cost |
|----------|-----------|--------|----------------|----------|
| FEDEX    | 255,971   | 47.4%  | $3,745,233.85  | $14.63   |
| P2P_US   | 216,075   | 40.0%  | $978,249.46    | $4.53    |
| P2P_US2  | 67,871    | 12.6%  | $375,615.49    | $5.53    |

### FedEx HD/SP Split
| Service    | Shipments | Share of FedEx | Total Cost     | Avg Cost |
|------------|-----------|----------------|----------------|----------|
| FEDEX_HD   | 152,438   | 59.5%          | $2,697,191.64  | $17.69   |
| FEDEX_SP   | 103,533   | 40.5%          | $1,048,042.21  | $10.12   |

## Cross-Scenario Comparison

| Scenario | Description               | Total Cost     | vs S1     |
|----------|---------------------------|----------------|-----------|
| S1       | Current mix               | $6,072,061.73  | --        |
| S13      | P2P+FedEx@0% earned       | $5,178,925.65  | -14.7%    |
| **S15**  | **3-Group static rules**  | **$5,099,098.80** | **-16.0%** |
| S14      | P2P+FedEx@16% constrained | $4,944,679.84  | -18.6%    |

- **S15 vs S13:** -$79,826.85 better (static rules + 16% earned beats unconstrained 0% earned)
- **S15 vs S14:** +$154,418.96 worse (simplification cost of static rules vs per-shipment optimization)

## Key Findings
1. Static 3-group rules achieve **-16.0% vs current mix** ($973K savings) -- close to S14's optimal -18.6%
2. The simplification cost vs S14 (per-shipment optimal) is only $154,419 (3.1% of S14's total)
3. FedEx undiscounted spend of $5,133,406 comfortably meets the $5.1M threshold with $33K margin
4. P2P handles 52.6% of shipments (40.0% P2P US + 12.6% P2P US2) at much lower avg cost ($4.53/$5.53 vs FedEx $14.63)
5. Heavy packages (>21 lbs) all go to FedEx -- P2P is not competitive for heavy items
6. Light packages benefit most from P2P, with P2P US at $4.53 avg for shipments under 3 lbs
7. This is the **recommended implementable scenario** -- simple rules that operations can follow without per-shipment cost optimization

---
*Generated: February 2026*
*Data Period: 2025 shipment volumes with 2026 calculated rates*
*Dataset: Matched-only (539,917 shipments)*
