# FedEx Rate Increase Analysis - January 2026

**Analysis Date:** February 2, 2026
**Data Period:** June 2025 - January 2026
**Total Shipments Analyzed:** 51,918

---

## Executive Summary

**CONFIRMED:** FedEx implemented a systematic base rate increase effective January 1, 2026.

### Key Findings

- **138 of 140** rate cards (98.6%) that appeared in both December 2025 and January 2026 increased
- **100% of changes were increases** - zero decreases
- **Average rate increase: 5.93%** (range: 4.49% to 6.71%)
- **Median rate increase: 5.85%**
- **Overall impact: +22.83%** increase in average base rate per shipment
- **Median impact: +35.83%** increase in median base rate per shipment

---

## Methodology

### Analysis Approach

1. **Data Structure Discovery**
   - Confirmed FedEx uses a deterministic rate card: `base_rate = f(service, zone, rated_weight)`
   - No natural variation in base rates within the same rate card combination
   - Rate cards showed 0% standard deviation within comparable groups in December 2025

2. **Comparative Analysis**
   - Compared base rates for identical service+zone+weight combinations between December 2025 and January 2026
   - 140 rate cards appeared in both periods with sufficient volume (≥5 shipments per period)

3. **Impact Assessment**
   - Analyzed 50,272 December shipments vs 1,646 January shipments
   - Measured both rate card-level changes and actual shipment-level impacts

### Why Natural Variation Was Ruled Out

FedEx's pricing structure is completely deterministic:
- For any given service + zone + rated_weight combination, there is exactly one base rate in effect at any point in time
- Within December 2025, groups with 10+ shipments showed 0 standard deviation in base rates
- This confirms that FedEx does not have variable pricing - they use a fixed rate card

**Implication:** ANY systematic change in base rates between periods indicates a rate increase, not random variation.

---

## Detailed Findings

### Rate Card Changes (Dec 2025 → Jan 2026)

| Metric | Value |
|--------|-------|
| Rate cards in both periods | 140 |
| Rate cards that changed | 138 (98.6%) |
| Rate cards unchanged | 2 (1.4%) |
| Rate cards with increases | 138 (100% of changes) |
| Rate cards with decreases | 0 (0%) |

### Increase Statistics

| Statistic | Percentage | Dollar Amount |
|-----------|------------|---------------|
| Average | 5.93% | $1.66 |
| Median | 5.85% | - |
| Minimum | 4.49% | - |
| Maximum | 6.71% | - |

### Examples of Largest Increases

| Service | Zone | Weight (lbs) | Dec Rate | Jan Rate | % Change | $ Change |
|---------|------|--------------|----------|----------|----------|----------|
| Home Delivery | 07 | 12.0 | $25.65 | $27.37 | +6.71% | +$1.72 |
| Home Delivery | 09 | 40.0 | $192.09 | $204.96 | +6.70% | +$12.87 |
| Home Delivery | 17 | 40.0 | $192.09 | $204.96 | +6.70% | +$12.87 |
| Home Delivery | 09 | 14.0 | $96.01 | $102.44 | +6.70% | +$6.43 |
| Home Delivery | 07 | 20.0 | $36.62 | $39.07 | +6.69% | +$2.45 |

### Examples of Smallest Increases

| Service | Zone | Weight (lbs) | Dec Rate | Jan Rate | % Change | $ Change |
|---------|------|--------------|----------|----------|----------|----------|
| Home Delivery | 04 | 1.0 | $12.69 | $13.26 | +4.49% | +$0.57 |
| Home Delivery | 03 | 1.0 | $11.65 | $12.21 | +4.81% | +$0.56 |
| Home Delivery | 03 | 47.0 | $34.58 | $36.41 | +5.29% | +$1.83 |
| Home Delivery | 02 | 40.0 | $25.44 | $26.79 | +5.31% | +$1.35 |
| Home Delivery | 03 | 41.0 | $32.38 | $34.10 | +5.31% | +$1.72 |

---

## Breakdown by Dimension

### By Service Type

| Service | Rate Cards | Avg % Change | Avg $ Change | Dec Shipments | Jan Shipments |
|---------|-----------|--------------|--------------|---------------|---------------|
| Home Delivery | 128 | 5.94% | $1.65 | 5,777 | 1,612 |
| Ground Economy | 10 | 5.74% | $1.70 | 76 | 15 |

### By Zone

| Zone | Rate Cards | Avg % Change | Median % Change | Avg $ Change |
|------|-----------|--------------|-----------------|--------------|
| 02 | 13 | 5.94% | 5.82% | $1.12 |
| 03 | 21 | 5.88% | 5.81% | $1.22 |
| 04 | 29 | 5.83% | 5.51% | $1.31 |
| 05 | 25 | 5.92% | 5.52% | $1.46 |
| 06 | 18 | 5.94% | 5.52% | $1.40 |
| 07 | 12 | 5.96% | 5.53% | $1.85 |
| 08 | 9 | 5.95% | 5.88% | $3.03 |
| 09 | 4 | 6.42% | 6.70% | $6.99 |
| 17 | 2 | 6.56% | 6.56% | $10.20 |

**Pattern:** Higher zones (farther distances) show slightly higher percentage increases and significantly higher dollar increases.

### By Weight Bracket

| Weight Bracket | Rate Cards | Avg % Change | Median % Change | Avg $ Change |
|----------------|-----------|--------------|-----------------|--------------|
| 0-5 lbs | 41 | 5.68% | 5.77% | $1.06 |
| 5-10 lbs | 26 | 5.66% | 5.52% | $1.11 |
| 10-20 lbs | 40 | **6.46%** | **6.49%** | $1.50 |
| 20-50 lbs | 25 | 5.73% | 5.51% | $2.80 |
| 50+ lbs | 6 | 6.05% | 6.00% | $4.35 |

**Pattern:** The 10-20 lbs bracket saw the largest percentage increases (6.46% average). Heavier shipments saw larger dollar increases.

---

## Impact on Actual Shipments

### December 2025

- **Shipments:** 50,272
- **Total base charges:** $1,242,885.22
- **Average per shipment:** $24.72
- **Median per shipment:** $18.17

### January 2026

- **Shipments:** 1,646
- **Total base charges:** $49,986.00
- **Average per shipment:** $30.37
- **Median per shipment:** $24.68

### Changes

- **Average base rate:** +22.83%
- **Median base rate:** +35.83%

**Note:** The higher shipment-level impact (+22.83%) compared to the rate card average (+5.93%) is explained by:
1. **Shipment mix effects:** January had heavier average shipments (24.5 lbs vs 13.6 lbs in December)
2. **Weight distribution:** The correlation between weight change and rate change was 0.652, indicating heavier packages naturally cost more
3. **Sample size:** Only 1,646 January shipments vs 50,272 in December may create sampling bias

---

## Evidence for Rate Increase vs. Natural Variation

### Strong Evidence for Rate Increase

1. **Deterministic Pricing Structure**
   - FedEx uses fixed rate cards with zero natural variation
   - Standard deviation within rate card groups = $0.00 in December 2025
   - Any change must be deliberate, not random

2. **Systematic Increases**
   - 98.6% of rate cards changed
   - 100% of changes were increases
   - Increases fall within tight range (4.49% to 6.71%)

3. **Uniform Pattern**
   - All services affected (Home Delivery and Ground Economy)
   - All zones affected (02 through 17)
   - All weight ranges affected (1 lb to 90+ lbs)

4. **Timing**
   - Change occurred precisely at January 1, 2026
   - Consistent with annual rate increase timing

### No Evidence for Natural Variation

- **Zero standard deviation** in December rate cards
- **Zero decreases** among changed rate cards
- **Narrow range** of increases (4.49% to 6.71%) - too uniform to be random

---

## Conclusions

### Primary Conclusion

**FedEx implemented a base rate increase of approximately 5.9% effective January 1, 2026.**

This is a systematic, across-the-board rate increase affecting:
- Both Home Delivery and Ground Economy services
- All zones (02 through 17)
- All weight brackets (1 lb to 90+ lbs)
- 98.6% of rate cards

### Rate Increase Characteristics

1. **Magnitude:** 4.49% to 6.71%, averaging 5.93%
2. **Uniformity:** Tight clustering around 5.9% indicates a deliberate, percentage-based increase
3. **Timing:** Effective January 1, 2026 (typical for carrier annual increases)
4. **Scope:** Nearly universal - only 2 of 140 rate cards unchanged

### Business Impact

For businesses shipping with FedEx:
- **Expected cost increase:** ~5.9% on base rates
- **Actual impact:** May be higher due to mix effects (heavier shipments cost more)
- **Planning:** Should budget for ongoing ~6% annual increases

---

## Appendix: Technical Notes

### Data Quality

- **Completeness:** 51,918 shipments with complete actual_base data
- **Coverage:** June 2025 through January 2026
- **Comparison window:** December 2025 (50,272 shipments) vs January 2026 (1,646 shipments)

### Rate Card Definition

A "rate card" is defined as a unique combination of:
- `rate_service` (e.g., "Home Delivery", "Ground Economy")
- `actual_zone` (e.g., "02", "05", "17")
- `actual_rated_weight_lbs` (e.g., 1.0, 6.0, 40.0)

### Limitations

1. **January sample size:** Only 1,646 shipments in January vs 50,272 in December
2. **Mix effects:** January shipments were heavier on average (24.5 lbs vs 13.6 lbs)
3. **Partial month:** January data only covers January 1-23, 2026
4. **Peak season:** December includes peak surcharges which may affect comparisons

### Files Generated

- `analyze_rate_increase.py` - Initial analysis identifying rate changes
- `analyze_rate_variation.py` - Natural variation analysis
- `investigate_base_rates.py` - Rate card structure investigation
- `final_rate_increase_report.py` - Comprehensive final report
- `RATE_INCREASE_ANALYSIS.md` - This document

---

**Analysis conducted by:** Claude Code
**Date:** February 2, 2026
**Data source:** `carriers/fedex/dashboard/data/comparison.parquet`
