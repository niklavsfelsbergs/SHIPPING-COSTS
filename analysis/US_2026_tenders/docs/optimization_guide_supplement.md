1. Data foundation: 
    1. We have the parquet files. We need to join them in a unified dataset. Lets make a script for that in 2025_calculated_costs. 
    2. Lets assume for now the parquet files are with 2026 rates. I want to put together the logic for optimization, I will later update the files with actual 2026 calculations.
2. Scenario 1: Sounds good
3. Scenario 2: Sounds good
4. Scenario 3: The earned discount tiers are in fedex_agreement.md - we only care about ground and home.
    1. Performance discount is included in the undiscounted_rates as we did not know how they are actually splir
5. Scenario 4:
    1. sounds good
    2. Approaches:
        1. I think greedy _ adjustment makes the most sense
        2. lets use annual totals for simplicity
6. Scenario 5:
    1. no volume commitments
    2. geographic constraints are included with a penalty cost
    3. no service levels, just simple calculation
7. Implementation questions:
    1. We need to optimize by: packagetype, zip code, weight bracket in 1lb increments
    2. annual totals
    3. geographic contraints are included with a pentaly cost which should make them unoptimal
    4. Yes, in the multiple carrier split we need to consider the different tiers
8. Suggested implementation order:
    1. Makes sense. But we have to make it repeatable for when I update the costs



Section 2:
1. Data foundation:
    1. Lets first create a joined dataset on shipment level. Then do the summarized dataset. Question: What would be the cost for each group? The average? We should have a column for both averages and totals
2. Phase 2: soundsgood
3. Other phases sound good

Key questions:

1. You will investigate the paruqet files when we get to it, but there is packagetype, pcs_shippingprovider for the actual carrier. Each separate file calculates the cost for the specific carrier for all us shipments. So for the actual carrier dataset have to use usps, fedex, ontrac files where the pcs_shippingprovider matches with the files carrier.
2. Lets for now just calculate the earned discount on top of the base and performance (performance is 0 for now). Note this as something that has to be clarified in the fedex meeting.
3. This is also handled by the penalty cost