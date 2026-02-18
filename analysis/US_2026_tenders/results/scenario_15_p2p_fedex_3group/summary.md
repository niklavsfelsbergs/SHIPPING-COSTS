# Scenario 15: 3-Group Static Rules for P2P + FedEx

## Overview
Implementable version of S14 using 3 static group rules.
FedEx at 16% earned discount,
undiscounted spend constrained >= $5.1M.

## Rules
- Light:  P2P US zone -> P2P US if wt <= 3 lbs | non-P2P US -> P2P US2 if wt <= 2 lbs | else FedEx
- Medium: P2P US zone -> P2P US if wt <= 21 lbs | non-P2P US -> P2P US2 if wt <= 2 lbs | else FedEx
- Heavy:  FedEx always

## Results
- Total: $4,537,888.76 (-24.0% vs S1)
- FedEx undiscounted: $5,222,850 (margin: $+122,850)