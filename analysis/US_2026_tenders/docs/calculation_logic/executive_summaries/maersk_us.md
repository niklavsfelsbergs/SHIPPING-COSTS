# Maersk US - Executive Summary

**Service:** Maersk US Ground (max 70 lbs)
**Origin:** Columbus only
**Status:** Early development - some surcharges not yet modeled

---

## How Shipping Cost Is Calculated

**Total Cost = Base Rate + Surcharges + Pickup Fee**

---

## Cost Components

### Base Rate
- Determined by destination zone (1-9) and package weight
- Zones are based on distance from Columbus - higher zones cost more
- Rates range from **$3.11** (lightest packages, Zone 1) to **$175.85** (70 lbs, Zone 9)
- **Important:** Rates increase dramatically at 30 lbs (e.g., Zone 5 jumps from $11.81 to $45.18)

### Weight Determination
- Billable weight is the greater of actual weight or dimensional weight
- Dimensional weight = package volume / 166
- Unlike some carriers, dimensional weight is **always** compared (no minimum size threshold)

### Pickup Fee
- **$0.04 per billable pound** (rounded up)
- Applies to every shipment

### Length Surcharges (mutually exclusive - only one applies)
- **Over 30 inches:** $4.00 - for packages with longest side exceeding 30"
- **21-30 inches:** $4.00 - for packages between 21" and 30" long

### Volume Surcharge
- **Large packages:** $18.00 - for packages exceeding 2 cubic feet (3,456 cubic inches)
- Can apply in addition to length surcharges (e.g., a 35" package over 2 cu ft pays both length and volume surcharges for **$22.00** in combined surcharges)

---

## What Is NOT Included

- **No fuel surcharge** - fuel costs are built into the base rate
- **Peak season surcharge** - not yet modeled
- **Residential delivery surcharge** - not yet modeled
- **Delivery area surcharges** - not yet modeled
- **Additional handling surcharges** - not yet modeled

---

## Example Cost Breakdown

**Package:** 35" x 11" x 10", 19 lbs actual weight, shipping to Los Angeles (Zone 8)

| Component | Amount |
|-----------|--------|
| Base rate (Zone 8, 24 lbs billable*) | $16.82 |
| Over 30" surcharge | $4.00 |
| Large package surcharge | $18.00 |
| Pickup fee (24 lbs x $0.04) | $0.96 |
| **Total** | **$39.78** |

*Dimensional weight (23.2 lbs) exceeds actual weight (19 lbs), so dimensional weight is used.

---

*Note: This carrier is in early development. Cost estimates may be incomplete due to unmodeled surcharges.*
