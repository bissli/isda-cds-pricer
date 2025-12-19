# ISDA CDS Standard Model - Examples

These examples demonstrate the Python ISDA CDS Standard Model library.

## Running Examples

Make sure you have the library installed, then run any example:

```bash
poetry run python examples_py/01_basic_pricing.py
```

## Example Files

### 01_basic_pricing.py
**Basic CDS Pricing**

Covers fundamental CDS pricing concepts:
- Creating a CDSPricer with market data
- Pricing buy and sell protection positions
- Present value components (dirty PV, clean PV, accrued interest)
- Risk metrics (CS01, DV01)
- Comparing different maturities

### 02_upfront_calculations.py
**Upfront and Spread Calculations**

Demonstrates upfront payment mechanics:
- Computing upfront from par spread
- Computing spread from upfront charge
- Round-trip validation
- Impact of coupon rates (100 vs 500 bps)
- Recovery rate effects

### 03_risk_sensitivities.py
**Risk Sensitivities (CS01 and DV01)**

Key risk metrics for portfolio management:
- CS01: Credit spread sensitivity
- DV01: Interest rate sensitivity
- Risk across different spread levels
- Risk across different maturities
- Portfolio aggregation examples
- P&L estimation from spread moves

### 04_curves.py
**Curve Building and Analysis**

Understanding interest rate and credit curves:
- Bootstrapping zero curves from swap rates
- Extracting discount factors
- Forward rate calculation
- Bootstrapping credit curves from CDS spreads
- Survival and default probabilities
- Hazard rate analysis

### 05_dates_and_calendar.py
**Date Utilities and Calendar Functions**

Date handling for CDS calculations:
- Parsing dates from multiple formats
- Year fraction calculations (day count conventions)
- Business day checks
- Bad day conventions (Following, Modified Following)
- Date arithmetic (add days, months, years)
- Custom calendars with holidays

### 06_imm_dates.py
**IMM Dates for CDS**

IMM date mechanics for standardized CDS:
- What constitutes an IMM date
- Finding next and previous IMM dates
- IMM dates for standard tenors
- Generating IMM date vectors
- On-the-run vs off-the-run contracts
- Year-end IMM date behavior

### 07_schedules.py
**CDS Payment Schedules**

Understanding the fee leg of a CDS:
- Quarterly payment schedules
- Stub period handling
- Different payment frequencies
- Accrued interest calculations
- Payment date business day adjustments
- Working with schedule objects

## Output Format

All examples display dates in MM/DD/YYYY format for clarity.

## Library Coverage

These examples cover the main functionality of the library:

| Module | Example Coverage |
|--------|------------------|
| CDSPricer | 01, 02, 03 |
| Curves (ZeroCurve, CreditCurve) | 04 |
| Date utilities | 05, 06 |
| Calendar | 05 |
| IMM dates | 06 |
| Schedules | 07 |
| Day count conventions | 04, 05 |
| Bad day conventions | 05 |
