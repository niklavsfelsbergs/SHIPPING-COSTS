# S15 Validation Plan: P2P + FedEx 3-Group Routing

## Why S15

Scenario 15 replaces the current 4-carrier mix (OnTrac, USPS, FedEx, DHL) with a 2-relationship setup (P2P + FedEx) using 3 simple static routing rules. Estimated annual savings: **$1.43M (-24.0%)** vs the current mix.

### Decision Drivers

1. **Eliminate USPS** — operationally desired, not a preferred carrier relationship.
2. **Eliminate OnTrac** — regional carrier adds complexity. We don't want 2 regional carriers in the mix.
3. **Reduce carrier count to 2** — P2P (PFAP + PFA/PFS) and FedEx. Simpler operations, fewer integrations, fewer invoice reconciliations.
4. **Preserve FedEx relationship** — S15 maintains the 16% earned discount by keeping FedEx undiscounted spend above $5.1M. No penalty cost, no relationship damage.
5. **P2P offers a one-to-many model** — P2P manages the underlying carrier relationships. We get a single contract, single invoice, single point of contact for multiple last-mile carriers.
6. **P2P has a simple cost structure** — base rate by zone and weight, minimal surcharges. Easy to validate, easy to forecast.

### S15 Results Summary

| Metric                        | Value                |
|-------------------------------|----------------------|
| Total annual cost             | $4,537,889           |
| Savings vs S1 (current mix)  | $1,433,859 (-24.0%)  |
| vs 2025 actuals (Nov+Dec)    | -28.7%               |
| Carrier relationships         | 2 (P2P, FedEx)       |
| SPE rules                     | 3 group rules + 1 ZIP list |
| FedEx earned discount         | 16%                  |
| FedEx undiscounted spend      | $5,222,850           |
| FedEx $5M penalty margin      | $222,850             |
| FedEx 16% tier margin ($4.5M) | $722,850             |

### Routing Rules

| Group  | P2P US zone (38,599 ZIPs)     | Other zones                  |
|--------|-------------------------------|------------------------------|
| Light  | PFAP if ceil(wt) <= 3 lbs     | PFA/PFS if ceil(wt) <= 2 lbs |
| Medium | PFAP if ceil(wt) <= 21 lbs    | PFA/PFS if ceil(wt) <= 2 lbs |
| Heavy  | FedEx                         | FedEx                        |

Everything not routed to P2P goes to FedEx. Light = 20 package types (64.6%), Medium = 18 (21.7%), Heavy = 16 (13.7%).

### Carrier Split

| Carrier | Shipments | Share  | Cost         | Avg Cost |
|---------|-----------|--------|--------------|----------|
| PFAP    | 223,002   | 40.0%  | $1,011,433   | $4.54    |
| PFA     | 36,147    | 6.5%   | $208,660     | $5.77    |
| PFS     | 89,347    | 16.0%  | $543,634     | $6.09    |
| FedEx   | 209,517   | 37.5%  | $2,774,162   | $13.24   |
| **Total** | **558,013** | **100%** | **$4,537,889** | |

### Comparison to Alternatives

| Scenario                          | Cost         | vs S1    | Carriers | Why not                                    |
|-----------------------------------|--------------|----------|:--------:|--------------------------------------------|
| S7 Optimal per-shipment           | $4,433,040   | -25.8%   | 3        | Requires USPS + 353K routing assignments   |
| S11 3-Group with USPS             | $4,516,218   | -24.4%   | 3        | Requires USPS relationship                 |
| **S15 3-Group P2P+FedEx**         | **$4,537,889** | **-24.0%** | **2** | **Selected**                             |
| S14 P2P+FedEx per-shipment       | $4,858,916   | -18.6%   | 2        | 187K forced switches, complex rules        |
| S13 P2P+FedEx unconstrained      | $4,942,666   | -17.2%   | 2        | Loses FedEx 16% earned discount            |

S15 is only $22K/year more than S11 (the best 3-carrier implementable option) while eliminating the USPS relationship entirely.

---

## Validation Checklist

### V1. FedEx calculation accuracy

**Question:** Are our FedEx calculated costs in line with what FedEx actually invoices?

**Why it matters:** FedEx represents 37.5% of S15 shipments and 61% of cost ($2.77M). If our calculator over- or underestimates, the savings projection is wrong.

**How to validate:**
- Compare our FedEx calculator output against recent FedEx invoices (last 3-6 months)
- Focus on: base rate, fuel surcharge, DAS, residential, AHS, demand surcharges
- Current FedEx calculator accuracy: base rates +0.08% (HD), 0.00% (SmartPost) — but surcharges are still in development
- Key risk: SmartPost rates have been corrected in 2026 rate tables (Ground Economy pricing). Verify SmartPost invoices match the new rate structure.

**Status:** [ ] Not started

---

### V2. FedEx undiscounted spend threshold

**Question:** Does our calculated FedEx undiscounted spend really clear the $5M penalty threshold?

**Why it matters:** If actual undiscounted spend falls below $5M, we face a **$500K penalty**. Our model shows $5.22M undiscounted ($222K margin), but this relies on our rate-to-undiscounted conversion being correct.

**How to validate:**
- Request FedEx undiscounted list prices for a sample of recent shipments
- Compare our formula: `undiscounted = base_rate / 0.37` (where 0.37 = 1 - 0.45 PP - 0.18 earned)
- Verify the 0.45 performance pricing discount and 0.18 baked earned discount factors match the contract
- Check if there are FedEx cost components we're missing that count toward or against the undiscounted threshold (e.g., surcharges — do they count toward the $5M?)
- Run a monthly breakdown: does every month individually contribute enough, or is there seasonal risk?

**Status:** [ ] Not started

---

### V3. P2P peak surcharges

**Question:** Do P2P US and P2P US2 have peak/demand surcharges during holiday periods?

**Why it matters:** Our P2P calculators include zero peak surcharges because none are listed in the rate cards. If P2P charges peak surcharges (Nov-Jan, like FedEx/USPS), our P2P costs are underestimated — especially in the highest-volume months.

**How to validate:**
- Ask P2P directly: "Are there any peak/demand/holiday surcharges applied to PFAP, PFA, or PFS during Q4?"
- If yes: get the surcharge schedule, update calculators, rerun S15
- Note: Nov+Dec represent ~31% of annual volume. Even a $0.50/ship peak surcharge would add ~$53K to annual cost.

**Status:** [ ] Not started

---

### V4. P2P US coverage stability

**Question:** Will the 38,599 P2P US (PFAP) ZIP codes remain stable?

**Why it matters:** PFAP is the cheapest carrier ($4.54 avg) handling 40% of shipments. If ZIP coverage shrinks, shipments fall to PFA/PFS ($5.77-6.09) or FedEx ($13.24), increasing costs significantly. The routing rules are built around this ZIP list.

**How to validate:**
- Ask P2P: How often does the PFAP coverage zone change? Is it contractually locked?
- Get history: Has coverage expanded or contracted in the past 12 months?
- Stress test: What happens to S15 total cost if PFAP loses 10% of ZIPs? 20%?

**Status:** [ ] Not started

---

### V5. P2P US2 coverage and service selection

**Question:** Are all 93,100 P2P US2 ZIPs actually serviceable, and is the PFA vs PFS service selection stable?

**Why it matters:** P2P US2 handles 22.5% of shipments. The PFA/PFS service selection is done at the (packagetype, weight_bracket) group level. If P2P changes service availability or pricing, the group-level selection could shift.

**How to validate:**
- Confirm 93,100 ZIP coverage is contractually guaranteed
- Confirm PFA and PFS service availability per zone (PFA: zones 1-8, PFS: zones 1-9)
- Verify that the remote zone surcharge waiver is contractual (currently waived per contract)
- Confirm DIM factor 166 for both services

**Status:** [ ] Not started

---

### V6. P2P US2 rate competitiveness above 2 lbs

**Question:** Is P2P US2 truly uncompetitive above 2 lbs, or are we leaving money on the table?

**Why it matters:** S15 only uses P2P US2 for packages up to 2 lbs outside PFAP zones. The brute-force optimization confirms this is optimal, but it's worth understanding why — and whether P2P US2 rate improvements could change the cutoff.

**How to validate:**
- Compare P2P US2 rates vs FedEx at 16% earned for 3-5 lb packages across zones 3-7
- Check if P2P has mentioned upcoming rate adjustments for PFA/PFS
- If P2P US2 becomes competitive at 3 lbs, the unconstrained S15 cost would drop (but may need higher FedEx threshold enforcement)

**Status:** [ ] Not started

---

### V7. FedEx contract terms for volume reduction

**Question:** What happens to the FedEx contract if we reduce volume from ~274K shipments (current) to ~210K (S15)?

**Why it matters:** S15 reduces FedEx shipment count by 23% while maintaining undiscounted spend above $5M. FedEx may have contractual terms about volume changes, notice periods, or rate adjustments triggered by volume shifts.

**How to validate:**
- Review FedEx contract for minimum volume commitments (shipment count, not just spend)
- Check if the earned discount tiers are purely spend-based or also volume-based
- Confirm the $5M penalty threshold and $4.5M earned discount threshold are correct for 2026
- Ask: Does FedEx require advance notice of significant volume changes?

**Status:** [ ] Not started

---

### V8. OnTrac and USPS contract exit

**Question:** What are the exit terms for OnTrac and USPS?

**Why it matters:** S15 eliminates both carriers. OnTrac has a 279K/year minimum volume commitment (5,365/week x 52). USPS has a 140K/year minimum (35K/quarter). Breaking these commitments may have financial penalties.

**How to validate:**
- Review OnTrac contract: penalty for early termination or volume shortfall?
- Review USPS contract: penalty for dropping below Tier 1 quarterly minimum?
- Calculate net savings: S15 savings ($1.43M) minus any exit penalties
- Timeline: When do current contracts expire? Can we align the transition?

**Status:** [ ] Not started

---

### V9. Seasonal FedEx threshold risk

**Question:** Does the $5.1M FedEx undiscounted threshold hold across seasonal volume patterns?

**Why it matters:** Annual aggregate is $5.22M, but if Q1 or Q3 volumes dip significantly, the rolling/quarterly undiscounted spend could fall below $5M temporarily. Need to understand if the $5M penalty is annual, quarterly, or rolling.

**How to validate:**
- Clarify with FedEx: Is the $5M threshold measured annually, quarterly, or on a rolling basis?
- Run monthly FedEx undiscounted spend projection using S15 routing on 2025 monthly volumes
- Identify the lowest-volume quarter and check if it individually risks the threshold (if quarterly measurement)
- If needed, adjust the threshold buffer from $5.1M to $5.3M and measure cost impact

**Status:** [ ] Not started

---

### V10. SPE implementation feasibility

**Question:** Can the 3 routing rules + ZIP list be configured in PCS/SPE?

**Why it matters:** S15's value depends on PCS being able to route shipments based on (package type group, weight ceiling, destination ZIP list). If SPE can't support this logic, we'd need a workaround.

**How to validate:**
- Confirm SPE can handle: IF zip IN list AND ceil(weight) <= X THEN carrier Y
- Confirm SPE can map package types to groups (Light/Medium/Heavy)
- Test with a small batch: route 100 shipments through the new rules, verify correct carrier selection
- Identify any SPE limitations (e.g., max ZIP list size, weight rounding behavior)

**Status:** [ ] Not started

---

### V11. P2P invoice reconciliation capability

**Question:** Can we validate P2P invoices against our calculator?

**Why it matters:** The shipping cost validation system (this repository) needs to extend to P2P US and P2P US2. If P2P invoice format is incompatible or we can't match shipments, we lose cost control visibility.

**How to validate:**
- Request sample P2P invoice (PFAP, PFA, PFS)
- Map invoice fields to our calculator output columns
- Build upload_actuals and compare_expected_to_actuals for P2P (similar to existing OnTrac/USPS/FedEx)
- Target accuracy: < 1% variance between calculated and invoiced

**Status:** [ ] Not started

---

### V12. Transit time and service level impact

**Question:** Are P2P transit times acceptable compared to current carriers?

**Why it matters:** Cost savings are meaningless if delivery times degrade and impact customer satisfaction. P2P routes through various last-mile carriers — transit times may vary by region.

**How to validate:**
- Request P2P transit time guarantees/SLAs by zone
- Compare against current carrier transit times (OnTrac: 1-3 days West, USPS: 2-5 days, FedEx: 2-7 days)
- Focus on the 40% of shipments moving from current carriers to PFAP — are these getting slower?
- Check P2P's track record: on-time delivery rate, damage rate, claims process

**Status:** [ ] Not started

---

## Validation Priority

| Priority | Item | Risk if skipped | Effort |
|:--------:|------|-----------------|--------|
| **P1** | V1 FedEx calculation accuracy | Wrong savings estimate | Medium |
| **P1** | V2 FedEx undiscounted threshold | $500K penalty | Medium |
| **P1** | V3 P2P peak surcharges | Underestimated P2P cost | Low |
| **P1** | V9 Seasonal threshold risk | $500K penalty in low quarter | Medium |
| **P2** | V7 FedEx contract terms | Unexpected exit costs | Low |
| **P2** | V8 OnTrac/USPS exit terms | Unexpected exit penalties | Low |
| **P2** | V4 PFAP coverage stability | Cost increase if ZIPs lost | Low |
| **P2** | V10 SPE implementation | Can't implement the rules | Medium |
| **P3** | V5 P2P US2 coverage/service | Minor cost variance | Low |
| **P3** | V6 P2P US2 rate competitiveness | Missed optimization | Low |
| **P3** | V11 P2P invoice reconciliation | No cost control | Medium |
| **P3** | V12 Transit times | Service degradation | Low |

**P1 items should be resolved before committing to S15.** P2 items should be clarified before implementation. P3 items can be addressed during or after rollout.

---

## Decision Gate

Proceed with S15 implementation if:

- [ ] V1: FedEx calculator variance < 2% vs invoices
- [ ] V2: FedEx undiscounted spend formula confirmed against actual list prices
- [ ] V3: P2P peak surcharges are zero OR accounted for in updated model
- [ ] V9: FedEx $5M threshold measurement period confirmed AND seasonal risk acceptable

If any P1 validation fails, rerun S15 with corrected inputs before committing.

---

*Created: February 2026*
*Data basis: 558,013 shipments (2025 volumes), 2026 rate cards*
*S15 total: $4,537,889 (-24.0% vs S1 current mix $5,971,748)*
