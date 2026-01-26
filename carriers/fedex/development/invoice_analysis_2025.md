# FedEx Invoice Analysis (2025-01-01 onwards)

## Summary

| Metric | Value |
|--------|-------|
| Total Shipments | 297,637 |
| Total Invoices | 256 |
| Total Net Charges | $4,611,546 |
| Total Transportation (List) | $6,235,797 |
| **Effective Discount Rate** | **26.1%** |

## Cost Composition

| Component | Amount | % of Net |
|-----------|--------|----------|
| Implied Base Charge | $6,257,161 | 135.7% |
| Total Surcharges | $1,861,388 | 40.4% |
| Total Discounts | -$3,511,930 | -76.1% |
| **Net Charges** | **$4,611,546** | **100%** |

---

## Service Type Breakdown

| Service | Shipments | % of Total | Net Charges | Avg/Shipment |
|---------|-----------|------------|-------------|--------------|
| **Home Delivery** | 177,852 | 59.8% | $3,320,775 | $18.67 |
| **SmartPost** | 117,567 | 39.5% | $1,188,989 | $10.11 |
| Ground (various) | 1,714 | 0.6% | $34,220 | $19.97 |
| Express (2Day, Priority, etc.) | 504 | 0.2% | $67,576 | $134.08 |

**Key insight**: 99.3% of volume is Home Delivery + SmartPost. Express services are negligible.

---

## Surcharges Analysis (Positive Charges)

### Top Surcharges by Total Amount

| Rank | Charge Description | Occurrences | Total Amount | Avg Amount | % of Surcharges |
|------|-------------------|-------------|--------------|------------|-----------------|
| 1 | **Fuel Surcharge** | 297,798 | $561,289 | $1.88 | 30.2% |
| 2 | **Residential** | 178,391 | $372,981 | $2.09 | 20.0% |
| 3 | **AHS - Dimensions** | 35,864 | $296,063 | $8.26 | 15.9% |
| 4 | **DAS Resi** | 38,709 | $84,446 | $2.18 | 4.5% |
| 5 | **Demand-Residential Del.** | 14,557 | $81,916 | $5.63 | 4.4% |
| 6 | **DAS Extended Resi** | 24,608 | $71,898 | $2.92 | 3.9% |
| 7 | **Delivery Area Surcharge (Extended)** | 18,609 | $70,051 | $3.76 | 3.8% |
| 8 | **Extended Delivery Area Surcharge** | 24,463 | $69,179 | $2.83 | 3.7% |
| 9 | **Oversize Charge** | 533 | $64,612 | $121.22 | 3.5% |
| 10 | **USPS Non-Mach Surcharge** | 10,775 | $50,747 | $4.71 | 2.7% |
| 11 | **Demand-Add'l Handling** | 10,315 | $46,503 | $4.51 | 2.5% |
| 12 | **DAS Remote Residential** | 3,175 | $28,010 | $8.82 | 1.5% |
| 13 | **Demand Surcharge** | 60,809 | $14,018 | $0.23 | 0.8% |
| 14 | **Address Correction** | 1,122 | $13,466 | $12.00 | 0.7% |
| 15 | **Demand-Oversize** | 172 | $8,513 | $49.49 | 0.5% |
| 16 | **AHS - Weight** | 239 | $5,724 | $23.95 | 0.3% |
| 17 | **DAS Alaska Resi** | 124 | $5,520 | $44.51 | 0.3% |
| 18 | **DAS Hawaii Resi** | 200 | $2,879 | $14.40 | 0.2% |

**Top 5 surcharges account for 75% of all surcharge costs.**

---

## Discounts Analysis (Negative Charges)

| Discount Type | Occurrences | Total Amount | Avg Amount |
|---------------|-------------|--------------|------------|
| **Performance Pricing** | 296,169 | -$2,797,543 | -$9.45 |
| **Earned Discount** | 163,756 | -$410,615 | -$2.51 |
| **Grace Discount** | 89,545 | -$224,221 | -$2.50 |
| **Discount** | 677 | -$79,551 | -$117.51 |

**Performance Pricing is the main contracted discount (80% of all discounts).**

---

## Surcharge Categories for Implementation

### 1. FUEL SURCHARGE
- Applied to nearly all shipments (297,798 / 297,637 = 100%)
- Average: $1.88 per shipment
- Likely percentage-based on base rate

### 2. RESIDENTIAL DELIVERY
- 178,391 occurrences (60% of shipments)
- Flat fee: ~$1.94 - $5.95 (mostly $2.09 avg)
- Aligns with Home Delivery service count

### 3. ADDITIONAL HANDLING (AHS)
Two types:
- **AHS - Dimensions**: 35,864 occurrences, $5.50 - $10.19 (avg $8.26)
- **AHS - Weight**: 239 occurrences, $18.75 - $27.50 (avg $23.95)
- **Add'l Handling-Dimension**: 80 occurrences (different naming?)
- **Add'l Handling-Weight**: 27 occurrences
- **Add'l Handling-Packaging**: 9 occurrences

### 4. DELIVERY AREA SURCHARGES (DAS)
Multiple tiers:
- **DAS Resi**: $2.18 avg (38,709 occurrences)
- **DAS Extended Resi**: $2.92 avg (24,608 occurrences)
- **DAS Remote Residential**: $8.82 avg (3,175 occurrences)
- **DAS Alaska Resi**: $44.51 avg (124 occurrences)
- **DAS Hawaii Resi**: $14.40 avg (200 occurrences)
- Commercial variants exist but are rare (<100 total)

Also separately named:
- **Delivery Area Surcharge (Extended)**: $3.76 avg
- **Extended Delivery Area Surcharge**: $2.83 avg
- **Delivery Area Surcharge Alaska/Hawaii**: small volumes

### 5. OVERSIZE CHARGE
- 533 occurrences, $75.25 - $167.75 (avg $121.22)
- High per-package cost, relatively rare

### 6. DEMAND/PEAK SURCHARGES
Seasonal surcharges:
- **Demand-Residential Del.**: $5.00 - $7.10 (14,557 occurrences)
- **Demand-Add'l Handling**: $3.88 - $10.00 (10,315 occurrences)
- **Demand Surcharge**: $0.00 - $24.50 (60,809 occurrences) - variable/tiered
- **Demand-Oversize**: $42.25 - $54.25 (172 occurrences)
- **Demand-Unauthorized**: $450 (1 occurrence)

### 7. SMARTPOST-SPECIFIC
- **USPS Non-Mach Surcharge**: $3.27 - $8.30 (10,775 occurrences)
  - Only applies to SmartPost shipments
  - ~9% of SmartPost volume triggers this

### 8. OTHER SURCHARGES (Low Priority)
- **Address Correction**: $11.25 - $12.75 (1,122 occurrences)
- **Weekly Service Chg**: $21.50 - $23.00 (62 occurrences)
- **Unauthorized Package**: $1,250 (1 occurrence)
- Various signature, pickup, and international charges

---

## Zero-Dollar Charges (Informational)

These appear in invoices but don't affect cost:
- **Delivery and Returns**: 117,567 occurrences (SmartPost marker)
- **Weekday Delivery**: 542 occurrences
- **Courier Pickup Charge**: 233 occurrences
- **Hold for Pickup**: 3 occurrences

---

## Implementation Priority

Based on financial impact and occurrence frequency:

### Must Implement (>$50K impact)
1. Fuel Surcharge ($561K)
2. Residential ($373K)
3. AHS - Dimensions ($296K)
4. DAS Resi ($84K)
5. Demand-Residential ($82K)
6. DAS Extended Resi ($72K)
7. Extended Delivery Area Surcharge ($70K)
8. Oversize Charge ($65K)
9. USPS Non-Mach Surcharge ($51K) - SmartPost only

### Should Implement ($10K-$50K impact)
10. Demand-Add'l Handling ($47K)
11. DAS Remote Residential ($28K)
12. Demand Surcharge ($14K)
13. Address Correction ($13K)

### Nice to Have (<$10K impact)
- Demand-Oversize
- AHS - Weight
- DAS Alaska/Hawaii variants
- Various other minor surcharges

### Discounts (for validation)
- Performance Pricing (main discount)
- Earned Discount
- Grace Discount

---

## Questions to Resolve

1. **Service scope**: Should we calculate for both Home Delivery AND SmartPost, or focus on one?
2. **SmartPost complexity**: SmartPost uses USPS for final delivery - does zone/rate structure differ?
3. **DAS naming inconsistency**: Multiple names for similar surcharges (DAS Extended Resi vs Extended Delivery Area Surcharge) - are these the same?
4. **Fuel surcharge calculation**: Is it a flat rate or percentage? Need rate card to confirm.
5. **Demand period dates**: What are the exact date ranges for demand/peak surcharges?
6. **AHS thresholds**: What dimension/weight thresholds trigger AHS?
