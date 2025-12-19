# Complete Guide to Credit Default Swap Pricing

## A Journey from First Principles to Expert-Level Implementation

---

## Table of Contents

1. [Introduction: What is a Credit Default Swap?](#1-introduction-what-is-a-credit-default-swap)
2. [The Fundamental Pricing Equation](#2-the-fundamental-pricing-equation)
3. [Discount Curves: The Time Value of Money](#3-discount-curves-the-time-value-of-money)
4. [Credit Curves: Modeling Default Risk](#4-credit-curves-modeling-default-risk)
5. [The Fee Leg: Premium Payments](#5-the-fee-leg-premium-payments)
6. [The Contingent Leg: Protection Payments](#6-the-contingent-leg-protection-payments)
7. [Schedule Generation and Day Count Conventions](#7-schedule-generation-and-day-count-conventions)
8. [Putting It All Together: Full CDS Pricing](#8-putting-it-all-together-full-cds-pricing)
9. [Risk Sensitivities: CS01 and DV01](#9-risk-sensitivities-cs01-and-dv01)
10. [Upfront Payments and Par Spread](#10-upfront-payments-and-par-spread)
11. [Worked Examples with Complete Calculations](#11-worked-examples-with-complete-calculations)
12. [Appendix: ISDA Standard Model Details](#appendix-isda-standard-model-details)

---

## 1. Introduction: What is a Credit Default Swap?

A **Credit Default Swap (CDS)** is a financial derivative that transfers credit risk from one party to another. Think of it as insurance against a company (the "reference entity") failing to pay its debts.

### The Two Parties

| Party | Role | Cash Flows |
|-------|------|------------|
| **Protection Buyer** | Seeks insurance against default | Pays periodic premiums (fee leg) |
| **Protection Seller** | Provides the insurance | Pays compensation if default occurs |

### The Two Scenarios

**Scenario 1: No Default**
```
Protection Buyer ───[Premium Payments]───► Protection Seller
                 ◄───────[Nothing]───────
```

**Scenario 2: Default Occurs**
```
Protection Buyer ───[Premium Payments (until default)]───► Protection Seller
                 ◄───────[(1 - Recovery) × Notional]───────
```

### Key Terms

| Term | Definition | Typical Value |
|------|------------|---------------|
| **Notional** | Face value of protection | $10,000,000 |
| **Coupon Rate** | Annual premium rate | 100 bps or 500 bps |
| **Par Spread** | Fair premium for the credit risk | Market determined |
| **Recovery Rate** | % of notional recovered in default | 40% (standard) |
| **Maturity** | Contract end date | 5 years (standard) |

---

## 2. The Fundamental Pricing Equation

The value of a CDS is the difference between what you receive and what you pay. From the **protection buyer's perspective**:

$$\boxed{\text{CDS Value} = \text{Protection Leg PV} - \text{Fee Leg PV}}$$

At inception, if priced at the par spread:

$$\text{Protection Leg PV} = \text{Fee Leg PV}$$

### Clean vs. Dirty Price

Like bonds, CDS have accrued interest between payment dates:

$$\text{PV}_{\text{dirty}} = \text{PV}_{\text{clean}} + \text{Accrued Interest}$$

The **clean price** is quoted in the market; the **dirty price** is what actually settles.

### The Par Spread Relationship

The **par spread** $s$ is the coupon rate that makes the CDS value zero at inception:

$$s = \frac{\text{Protection Leg PV}}{\text{Risky Annuity} \times N}$$

where $N$ is the notional and the **Risky Annuity** (RPV01) is the present value of receiving 1 basis point of premium.

---

## 3. Discount Curves: The Time Value of Money

Before pricing credit risk, we need to understand how to discount future cash flows.

### Zero Rates and Discount Factors

A **zero rate** $r(t)$ is the continuously compounded rate for borrowing/lending from today to time $t$.

$$\boxed{DF(t) = e^{-r(t) \cdot t}}$$

| Time $t$ | Zero Rate $r(t)$ | Discount Factor $DF(t)$ |
|----------|------------------|-------------------------|
| 1 year | 2.5% | $e^{-0.025 \times 1} = 0.9753$ |
| 3 years | 2.9% | $e^{-0.029 \times 3} = 0.9166$ |
| 5 years | 3.0% | $e^{-0.030 \times 5} = 0.8607$ |

### Forward Rates

The **forward rate** $f(t_1, t_2)$ is the implied rate between two future times:

$$f(t_1, t_2) = \frac{r(t_2) \cdot t_2 - r(t_1) \cdot t_1}{t_2 - t_1}$$

Equivalently, using discount factors:

$$f(t_1, t_2) = -\frac{\ln\left(\frac{DF(t_2)}{DF(t_1)}\right)}{t_2 - t_1}$$

### Bootstrapping Zero Curves from Swap Rates

Market swap rates are bootstrapped into zero rates using:

**For money market rates (< 1Y):**
$$DF = \frac{1}{1 + r_{MM} \times t_{MM}}$$
$$r_{\text{zero}} = -\frac{\ln(DF)}{t}$$

**For swap rates (≥ 1Y):** Solve iteratively such that the swap prices at par:
$$\sum_{i=1}^{n} c \cdot \tau_i \cdot DF_i + DF_n = 1$$

where $c$ is the swap rate and $\tau_i$ is the year fraction for period $i$.

### Example: Bootstrap Calculation

Given 1-year swap rate = 2.5%, 2-year swap rate = 2.8%:

**Step 1:** 1-year zero rate
$$DF_1 = \frac{1}{1 + 0.025 \times 1} = 0.9756$$
$$r_1 = -\frac{\ln(0.9756)}{1} = 0.0247$$

**Step 2:** 2-year zero rate (semi-annual payments)
$$0.028 \times 0.5 \times DF_{0.5} + 0.028 \times 0.5 \times DF_1 + DF_2 = 1$$
Solve for $r_2$ such that $DF_2 = e^{-r_2 \times 2}$

---

## 4. Credit Curves: Modeling Default Risk

### The Hazard Rate Model

The **hazard rate** $\lambda(t)$ represents the instantaneous probability of default at time $t$, conditional on survival to that point.

$$\lambda(t) = \lim_{\Delta t \to 0} \frac{P(\text{default in } [t, t+\Delta t] \mid \text{survival to } t)}{\Delta t}$$

### Survival Probability

The **survival probability** $Q(t)$ is the probability of no default by time $t$:

$$\boxed{Q(t) = e^{-\int_0^t \lambda(u) \, du}}$$

For piecewise constant hazard rates (flat forward):
$$Q(t) = e^{-h(t) \cdot t}$$

where $h(t)$ is the average hazard rate from 0 to $t$.

### Default Probability

The **cumulative default probability** is simply:
$$PD(t) = 1 - Q(t)$$

### Forward Survival and Hazard Rates

**Forward survival probability** from $t_1$ to $t_2$:
$$Q(t_1, t_2) = \frac{Q(t_2)}{Q(t_1)}$$

**Forward hazard rate**:
$$\lambda(t_1, t_2) = -\frac{\ln(Q(t_1, t_2))}{t_2 - t_1}$$

### Relationship Between Spread and Hazard Rate

For a rough approximation:
$$\lambda \approx \frac{\text{spread}}{1 - R}$$

where $R$ is the recovery rate. This gives the intuition that higher spreads imply higher default risk.

### Example: Credit Curve

| Time | CDS Spread | Hazard Rate | Survival Prob | Default Prob |
|------|------------|-------------|---------------|--------------|
| 1Y | 100 bps | 1.67% | 98.34% | 1.66% |
| 3Y | 150 bps | 2.50% | 92.77% | 7.23% |
| 5Y | 200 bps | 3.33% | 84.65% | 15.35% |

*(Using Recovery = 40%)*

---

## 5. The Fee Leg: Premium Payments

The fee leg represents the stream of premium payments from the protection buyer.

### Fee Leg Present Value Formula

$$\boxed{\text{Fee Leg PV} = \underbrace{\sum_{i=1}^{n} c \cdot N \cdot \tau_i \cdot Q(t_i) \cdot DF(t_i)}_{\text{Regular Payments}} + \underbrace{\text{Accrual on Default PV}}_{\text{Expected Accrued}}}$$

where:
- $c$ = coupon rate
- $N$ = notional
- $\tau_i$ = year fraction for period $i$ (ACT/360)
- $Q(t_i)$ = survival probability at period end
- $DF(t_i)$ = discount factor at payment date

### Regular Coupon Payments

For each coupon period $i$:

$$\text{Coupon PV}_i = c \times N \times \tau_i \times Q(t_i) \times DF(t_i)$$

The coupon is weighted by:
1. **Survival probability**: Only paid if reference entity survives
2. **Discount factor**: Time value of money

### Accrual on Default

If default occurs mid-period, the protection buyer pays accrued premium to that point:

$$\text{Accrual PV} = \int_{t_{i-1}}^{t_i} \text{Accrued}(u) \times \lambda(u) \times Q(u) \times DF(u) \, du$$

The ISDA model uses numerical integration with Taylor expansion for stability:

For each sub-interval:
$$\lambda' = \ln(Q_0) - \ln(Q_1)$$
$$f' = \ln(DF_0) - \ln(DF_1)$$
$$x = \lambda' + f'$$

If $|x| > 10^{-4}$:
$$PV = \frac{\lambda' \cdot \text{AccRate} \cdot Q_0 \cdot DF_0}{x^2} \left[(t_0 + \frac{\Delta t}{x}) - (t_1 + \frac{\Delta t}{x}) \cdot \frac{Q_1}{Q_0} \cdot \frac{DF_1}{DF_0}\right]$$

Otherwise, use Taylor expansion for numerical stability.

### Risky Annuity (RPV01)

The **risky annuity** is the fee leg PV per unit of spread:

$$\text{RPV01} = \frac{\partial(\text{Fee Leg PV})}{\partial c} \approx \frac{\text{Fee Leg PV}(c=1\text{bp})}{1\text{bp}}$$

This measures the present value of receiving 1 basis point of premium over the life of the CDS.

---

## 6. The Contingent Leg: Protection Payments

The contingent (protection) leg pays $(1-R) \times N$ upon default.

### Protection Leg Present Value Formula

$$\boxed{\text{Protection Leg PV} = (1-R) \times N \times \int_0^T \lambda(t) \times Q(t) \times DF(t) \, dt}$$

Breaking this down:
- $(1-R) \times N$ = Loss Given Default
- $\lambda(t) \times Q(t) \, dt$ = Probability of default in $[t, t+dt]$
- $DF(t)$ = Present value factor

### Numerical Integration

The integral is computed numerically over sub-intervals. For each sub-interval $[t_0, t_1]$:

$$\lambda' = \ln(Q(t_0)) - \ln(Q(t_1))$$
$$f' = \ln(DF(t_0)) - \ln(DF(t_1))$$
$$x = \lambda' + f'$$

If $|x| > 10^{-4}$:
$$PV_{\text{sub}} = \text{LGD} \times \frac{\lambda'}{x} \times (1 - e^{-x}) \times Q(t_0) \times DF(t_0)$$

For small $x$, use Taylor expansion:
$$\frac{1 - e^{-x}}{x} \approx 1 - \frac{x}{2} + \frac{x^2}{6} - \frac{x^3}{24} + \frac{x^4}{120}$$

### Intuition

The protection leg value increases with:
1. **Higher default probability** (larger $\lambda$)
2. **Lower recovery rate** (larger loss given default)
3. **Lower interest rates** (less discounting of future protection)

---

## 7. Schedule Generation and Day Count Conventions

### CDS Payment Schedule

Standard CDS use **quarterly payments** with schedules generated **backward from maturity**:

```
Maturity: Dec 20, 2026
         ◄────3M────◄────3M────◄────3M────◄─── ...
Sep 20   Jun 20     Mar 20     Dec 20
 2026     2026       2026       2025
```

### IMM Dates

CDS typically mature on **IMM dates**: March 20, June 20, September 20, December 20.

The accrual start date is the **previous IMM date** before the trade date.

### Day Count Conventions

| Convention | Formula | Usage |
|------------|---------|-------|
| **ACT/360** | $\frac{\text{Actual Days}}{360}$ | CDS accruals |
| **ACT/365F** | $\frac{\text{Actual Days}}{365}$ | Curve time calculations |
| **30/360** | $\frac{360 \times \Delta Y + 30 \times \Delta M + \Delta D}{360}$ | Swap fixed legs |

### Business Day Conventions

| Convention | Rule |
|------------|------|
| **Following** | Move to next business day |
| **Modified Following** | Move to next business day, unless it crosses month boundary (then previous) |
| **Preceding** | Move to previous business day |

### Example Schedule

Trade Date: August 31, 2022
Maturity: December 20, 2026
Accrual Start: June 20, 2022 (previous IMM)

| Period | Accrual Start | Accrual End | Payment Date | Year Fraction |
|--------|---------------|-------------|--------------|---------------|
| 1 | Jun 20, 2022 | Sep 20, 2022 | Sep 20, 2022 | 92/360 = 0.2556 |
| 2 | Sep 20, 2022 | Dec 20, 2022 | Dec 20, 2022 | 91/360 = 0.2528 |
| 3 | Dec 20, 2022 | Mar 20, 2023 | Mar 20, 2023 | 90/360 = 0.2500 |
| ... | ... | ... | ... | ... |

---

## 8. Putting It All Together: Full CDS Pricing

### Step-by-Step Pricing Algorithm

```
1. BUILD DISCOUNT CURVE
   └── Bootstrap zero rates from swap rates

2. BUILD CREDIT CURVE
   └── Bootstrap hazard rates from par spread

3. GENERATE PAYMENT SCHEDULE
   └── Quarterly periods from accrual start to maturity

4. CALCULATE FEE LEG PV
   └── Sum regular coupons + accrual on default

5. CALCULATE PROTECTION LEG PV
   └── Integrate default probability × loss × discount

6. COMPUTE CDS VALUE
   └── PV = Protection Leg - Fee Leg (for buyer)

7. CALCULATE GREEKS
   └── CS01, DV01 via bump-and-reprice
```

### The Complete Pricing Formula

For a protection **buyer**:

$$\text{PV}_{\text{dirty}} = \text{Protection PV} - \text{Fee PV}$$
$$\text{PV}_{\text{clean}} = \text{PV}_{\text{dirty}} - \text{Accrued Interest}$$

For a protection **seller** (signs reversed):

$$\text{PV}_{\text{dirty}} = \text{Fee PV} - \text{Protection PV}$$
$$\text{PV}_{\text{clean}} = \text{PV}_{\text{dirty}} + \text{Accrued Interest}$$

### Accrued Interest Calculation

$$\text{Accrued} = N \times c \times \frac{\text{Days since period start}}{360}$$

ISDA convention: Accrued is calculated to the **step-in date** (trade date + 1).

---

## 9. Risk Sensitivities: CS01 and DV01

### CS01: Credit Spread Sensitivity

**CS01** measures the P&L impact of a 1 basis point change in credit spreads:

$$\text{CS01} = \text{PV}(h + 1\text{bp}) - \text{PV}(h)$$

where $h$ represents the hazard rate curve.

**Interpretation:**
- Protection buyer with positive CS01: Profits when spreads widen
- Protection seller with positive CS01: Profits when spreads tighten

**Approximation:**
$$\text{CS01} \approx -\text{RPV01} \times N$$

### DV01: Interest Rate Sensitivity

**DV01** measures the P&L impact of a 1 basis point parallel shift in rates:

$$\text{DV01} = \text{PV}(r + 1\text{bp}) - \text{PV}(r)$$

CDS typically have **small DV01** because:
- Fee leg and protection leg are both discounted
- Rate effects partially offset

### Bump-and-Reprice Implementation

```python
def compute_cs01(base_pv, credit_curve, bump=0.0001):
    # Bump hazard rates up by 1bp
    original_rates = credit_curve.hazard_rates.copy()
    credit_curve.hazard_rates += bump

    # Reprice
    bumped_pv = calculate_pv()

    # Restore
    credit_curve.hazard_rates = original_rates

    return bumped_pv - base_pv
```

### Example CS01 Calculation

| Maturity | Notional | CS01 | CS01 per $1MM |
|----------|----------|------|---------------|
| 1Y | $10MM | $950 | $95 |
| 3Y | $10MM | $2,800 | $280 |
| 5Y | $10MM | $4,500 | $450 |

---

## 10. Upfront Payments and Par Spread

### Standard CDS Trading

Modern CDS trade with **fixed coupons** (100 bps or 500 bps). The difference between the fair spread and the coupon is settled **upfront**.

### Upfront from Spread

If market spread $>$ coupon: Protection buyer **pays** upfront
If market spread $<$ coupon: Protection buyer **receives** upfront

$$\text{Upfront} \approx (s - c) \times \text{RPV01} \times N$$

More precisely:
$$\text{Upfront}_{\text{clean}} = \text{Protection PV} - \text{Fee PV}$$

### Spread from Upfront

Given an upfront payment, we can back out the implied spread using root finding:

$$\text{Find } s \text{ such that: Protection PV}(s) - \text{Fee PV}(c) = \text{Upfront}$$

### Par Spread Calculation

The **par spread** is the spread that makes the upfront zero:

$$s_{\text{par}} = \frac{\text{Protection PV}}{\text{RPV01} \times N}$$

### Example: Upfront Calculation

Given:
- Par spread: 200 bps
- Coupon: 100 bps
- RPV01: 4.25 per $1MM
- Notional: $10MM

$$\text{Upfront} \approx (0.0200 - 0.0100) \times 4.25 \times 10 = -\$425,000$$

The buyer pays $425,000 upfront (negative from buyer's perspective).

---

## 11. Worked Examples with Complete Calculations

### Example 1: Basic CDS Pricing

**Given:**
- Trade Date: August 31, 2022
- Maturity: December 20, 2026 (~4.3 years)
- Notional: $10,000,000
- Par Spread: 65 bps (0.0065)
- Coupon: 100 bps (0.0100)
- Recovery Rate: 40%

**Step 1: Build Discount Curve**

From swap rates:
| Tenor | Rate | Zero Rate | DF |
|-------|------|-----------|-----|
| 1Y | 1.76% | 1.75% | 0.9827 |
| 3Y | 2.69% | 2.67% | 0.9229 |
| 5Y | 2.86% | 2.83% | 0.8680 |

**Step 2: Build Credit Curve**

Bootstrap hazard rate from par spread:
$$h \approx \frac{0.0065}{1 - 0.40} = 0.0108 \text{ (1.08%)}$$

Survival probabilities:
| Time | Survival Q(t) |
|------|---------------|
| 1Y | 98.93% |
| 3Y | 96.81% |
| 5Y | 94.73% |

**Step 3: Fee Leg PV**

With 100 bps coupon, quarterly payments:
$$\text{Fee PV} = \sum_{i} 0.01 \times 10MM \times \tau_i \times Q_i \times DF_i$$
$$\approx \$406,000$$

**Step 4: Protection Leg PV**

$$\text{Protection PV} = 0.60 \times 10MM \times \int_0^T \lambda Q \cdot DF \, dt$$
$$\approx \$268,000$$

**Step 5: CDS Value (Buy Protection)**

$$\text{PV}_{\text{dirty}} = \$268,000 - \$406,000 = -\$138,000$$

The protection buyer owes $138,000 because the coupon (100 bps) exceeds the par spread (65 bps).

**Step 6: Clean Price**

Assuming 72 days accrued:
$$\text{Accrued} = 10MM \times 0.01 \times \frac{72}{360} = \$20,000$$
$$\text{PV}_{\text{clean}} = -\$138,000 - \$20,000 = -\$158,000$$

---

### Example 2: Spread Sensitivity Analysis

How does PV change with different spreads?

| Spread | Protection PV | Fee PV | Net PV (Buy) | Upfront % |
|--------|---------------|--------|--------------|-----------|
| 50 bps | $204,000 | $406,000 | -$202,000 | -2.02% |
| 100 bps | $406,000 | $406,000 | $0 | 0.00% |
| 150 bps | $604,000 | $406,000 | +$198,000 | +1.98% |
| 200 bps | $798,000 | $406,000 | +$392,000 | +3.92% |

**Key Insight:** At par spread = coupon, the CDS value is zero.

---

### Example 3: Recovery Rate Impact

How does recovery rate affect pricing?

For 200 bps spread, 100 bps coupon:

| Recovery | Protection PV | Net PV (Buy) | Change |
|----------|---------------|--------------|--------|
| 20% | $1,064,000 | +$658,000 | +68% |
| 40% | $798,000 | +$392,000 | baseline |
| 60% | $532,000 | +$126,000 | -68% |

**Key Insight:** Lower recovery = higher protection value = better for buyer.

---

### Example 4: Complete Numerical Walkthrough

Let's trace through the exact calculations for a single coupon period.

**Period:** Sep 20, 2022 to Dec 20, 2022 (91 days)

**Given:**
- $Q(0.25) = 0.9973$ (survival at period start)
- $Q(0.50) = 0.9946$ (survival at period end)
- $DF(0.50) = 0.9900$ (discount at payment)
- $\tau = 91/360 = 0.2528$
- $N = \$10,000,000$
- $c = 0.01$

**Regular Coupon PV:**
$$\text{Coupon PV} = 0.01 \times 10MM \times 0.2528 \times 0.9946 \times 0.9900$$
$$= \$100,000 \times 0.2528 \times 0.9847 = \$24,897$$

**Protection Leg Contribution:**

For this period, integrating default probability:
$$\lambda' = \ln(0.9973) - \ln(0.9946) = 0.0027$$
$$\text{LGD} = 0.60 \times 10MM = \$6,000,000$$

$$\text{Prot PV}_{\text{period}} = \$6MM \times 0.0027 \times 0.9973 \times 0.9900 \approx \$16,000$$

---

## Appendix: ISDA Standard Model Details

### A.1 Flat Forward Interpolation

The ISDA model uses **flat forward** interpolation for curves:

Between curve points $t_i$ and $t_{i+1}$:
$$r(t) = \frac{r_i \cdot t_i + f_i \cdot (t - t_i)}{t}$$

where $f_i = \frac{r_{i+1} \cdot t_{i+1} - r_i \cdot t_i}{t_{i+1} - t_i}$ is the forward rate.

### A.2 Protection Start Convention

ISDA standard: Protection starts at the **beginning** of the protection period. This means:
- Survival observations use date - 1 day
- Protection covers the accrual start date itself

### A.3 Step-in Date

The **step-in date** is trade date + 1 business day. This is when:
- Protection effectively begins
- Accrued interest is calculated to

### A.4 Taylor Expansion for Numerical Stability

When $|\lambda + r| < 10^{-4}$, direct calculation loses precision. The Taylor expansion:

$$\frac{1 - e^{-x}}{x} = 1 - \frac{x}{2} + \frac{x^2}{6} - \frac{x^3}{24} + \frac{x^4}{120} + O(x^5)$$

### A.5 Brent's Method for Bootstrapping

Credit curves are bootstrapped using Brent's root-finding method:
- Combines bisection, secant, and inverse quadratic interpolation
- Guaranteed convergence with superlinear speed
- Tolerance: $10^{-14}$

### A.6 Complete Fee Leg Formula (ISDA)

$$\text{Fee PV} = \sum_{i=1}^{n} c \cdot N \cdot \tau_i \cdot Q(t_i^{obs}) \cdot DF(t_i^{pay}) + \sum_{i=1}^{n} \text{AOD}_i$$

where:
- $t_i^{obs}$ = observation date (accrual end - 1 day for non-final periods)
- $t_i^{pay}$ = adjusted payment date
- $\text{AOD}_i$ = accrual on default for period $i$

### A.7 Complete Protection Leg Formula (ISDA)

$$\text{Prot PV} = (1-R) \cdot N \cdot \sum_{j=1}^{m} \frac{\lambda_j}{x_j}(1 - e^{-x_j}) \cdot Q_j^{start} \cdot DF_j^{start}$$

where the sum is over integration sub-intervals with:
- $\lambda_j = \ln(Q_j^{start}) - \ln(Q_j^{end})$
- $x_j = \lambda_j + f_j$ (with $f_j$ being the forward rate contribution)

---

## Summary

CDS pricing combines:
1. **Interest rate modeling** via zero curves
2. **Credit risk modeling** via hazard rates and survival probabilities
3. **Careful date handling** per ISDA conventions
4. **Numerical integration** with stability considerations

The key equations to remember:

| Component | Formula |
|-----------|---------|
| Discount Factor | $DF(t) = e^{-r(t) \cdot t}$ |
| Survival Probability | $Q(t) = e^{-h(t) \cdot t}$ |
| Fee Leg PV | $\sum c \cdot N \cdot \tau \cdot Q \cdot DF + \text{AOD}$ |
| Protection PV | $(1-R) \cdot N \cdot \int \lambda \cdot Q \cdot DF \, dt$ |
| CDS Value (Buy) | $\text{Protection PV} - \text{Fee PV}$ |
| Par Spread | $s = \frac{\text{Protection PV}}{\text{RPV01} \times N}$ |

---

## 12. Practical Code Examples Using This Library

This section demonstrates how to use the accompanying Python library to implement everything discussed above.

### 12.1 Basic CDS Pricing

```python
from isda import CDSPricer

# Market data: swap curve
trade_date = '08/31/2022'
swap_rates = [
    0.002979, 0.006419, 0.01165, 0.017617, 0.024417, 0.026917,
    0.028, 0.028583, 0.029083, 0.02945, 0.029917, 0.030167,
    0.030417, 0.031417, 0.0305, 0.028917,
]
swap_tenors = [
    '1M', '3M', '6M', '1Y', '2Y', '3Y', '4Y', '5Y',
    '6Y', '7Y', '8Y', '9Y', '10Y', '15Y', '20Y', '30Y',
]

# Create pricer
pricer = CDSPricer(
    trade_date=trade_date,
    swap_rates=swap_rates,
    swap_tenors=swap_tenors,
)

# Price a 5-year CDS
result = pricer.price_cds(
    maturity_date='12/20/2026',
    par_spread=0.0065,      # 65 bps
    coupon_rate=100,        # 100 bps
    notional=10_000_000,
    recovery_rate=0.40,
    is_buy_protection=True,
)

print(f"PV (Dirty):  ${result.pv_dirty:,.2f}")
print(f"PV (Clean):  ${result.pv_clean:,.2f}")
print(f"Accrued:     ${result.accrued_interest:,.2f}")
print(f"CS01:        ${result.cs01:,.2f}")
print(f"DV01:        ${result.dv01:,.2f}")
print(f"Par Spread:  {result.par_spread * 10000:.2f} bps")
```

### 12.2 Building Curves Directly

```python
from isda import ZeroCurve, CreditCurve, bootstrap_zero_curve, bootstrap_credit_curve
from isda import parse_date

trade_date = parse_date('08/31/2022')

# Bootstrap zero curve from swap rates
zero_curve = bootstrap_zero_curve(
    base_date=trade_date,
    swap_rates=swap_rates,
    swap_tenors=swap_tenors,
)

# Extract discount factors
print("Discount Factors:")
for t in [1.0, 2.0, 3.0, 5.0]:
    df = zero_curve.discount_factor(t)
    rate = zero_curve.rate(t)
    print(f"  t={t}Y: DF={df:.6f}, Zero Rate={rate*100:.4f}%")

# Bootstrap credit curve from CDS spreads
cds_spreads = [0.0080, 0.0120, 0.0150, 0.0170, 0.0185]
cds_tenors = ['1Y', '2Y', '3Y', '5Y', '7Y']

credit_curve = bootstrap_credit_curve(
    base_date=trade_date,
    par_spreads=cds_spreads,
    spread_tenors=cds_tenors,
    zero_curve=zero_curve,
    recovery_rate=0.40,
)

# Extract survival probabilities
print("\nSurvival Probabilities:")
for t in [1.0, 2.0, 3.0, 5.0]:
    q = credit_curve.survival_probability(t)
    pd = credit_curve.default_probability(t)
    print(f"  t={t}Y: Survival={q*100:.4f}%, Default={pd*100:.4f}%")
```

### 12.3 Computing Upfront Payments

```python
# Compute upfront from spread
maturity = '12/20/2026'
notional = 10_000_000

# Different spread levels vs 100 bps coupon
for spread_bps in [50, 100, 150, 200]:
    spread = spread_bps / 10000

    dirty, clean, accrued = pricer.compute_upfront(
        maturity_date=maturity,
        par_spread=spread,
        coupon_rate=100,
        notional=notional,
        recovery_rate=0.40,
    )

    print(f"Spread={spread_bps}bp: Upfront=${dirty:+,.0f} ({dirty/notional*100:+.2f}%)")

# Recover spread from upfront
recovered_spread = pricer.compute_spread_from_upfront(
    maturity_date=maturity,
    upfront_charge=-0.05,  # 5% paid by buyer (as fraction)
    coupon_rate=100,
    notional=notional,
    recovery_rate=0.40,
    is_clean=False,
)
print(f"\n5% upfront implies spread: {recovered_spread * 10000:.2f} bps")
```

### 12.4 Leg-Level Calculations

```python
from isda.fee_leg import fee_leg_pv, risky_annuity, calculate_accrued_interest
from isda.contingent_leg import contingent_leg_pv
from isda.schedule import generate_cds_schedule
from isda.imm import previous_imm_date
from isda.enums import PaymentFrequency, DayCountConvention, BadDayConvention

# Generate schedule
accrual_start = previous_imm_date(trade_date)
maturity = parse_date('12/20/2026')

schedule = generate_cds_schedule(
    accrual_start=accrual_start,
    maturity=maturity,
    frequency=PaymentFrequency.QUARTERLY,
    day_count=DayCountConvention.ACT_360,
    bad_day=BadDayConvention.MODIFIED_FOLLOWING,
)

print("Payment Schedule:")
for i, period in enumerate(schedule.periods[:5]):
    print(f"  Period {i+1}: {period.accrual_start} to {period.accrual_end}, "
          f"YF={period.year_fraction:.4f}")

# Calculate fee leg PV
fee_pv = fee_leg_pv(
    value_date=trade_date,
    schedule=schedule,
    coupon_rate=0.01,
    discount_curve=zero_curve,
    credit_curve=credit_curve,
    notional=10_000_000,
)
print(f"\nFee Leg PV: ${fee_pv:,.2f}")

# Calculate protection leg PV
prot_pv = contingent_leg_pv(
    value_date=trade_date,
    maturity_date=maturity,
    discount_curve=zero_curve,
    credit_curve=credit_curve,
    recovery_rate=0.40,
    notional=10_000_000,
)
print(f"Protection Leg PV: ${prot_pv:,.2f}")

# Calculate risky annuity
rpv01 = risky_annuity(
    value_date=trade_date,
    schedule=schedule,
    discount_curve=zero_curve,
    credit_curve=credit_curve,
)
print(f"Risky Annuity (per $1): {rpv01:.6f}")
print(f"Risky Annuity (per $1MM): {rpv01 * 1_000_000:.2f}")
```

### 12.5 Analyzing Credit Quality Impact

```python
import math

# Compare survival across credit qualities
recovery = 0.40
spreads = {
    'Investment Grade (50bp)': 0.0050,
    'BBB (150bp)': 0.0150,
    'High Yield (500bp)': 0.0500,
    'Distressed (1500bp)': 0.1500,
}

print("Credit Quality Impact (5-Year Horizon):")
print("-" * 60)
print(f"{'Quality':<30} {'Spread':>10} {'Survival':>10} {'Default':>10}")
print("-" * 60)

for name, spread in spreads.items():
    # Approximate hazard rate
    hazard = spread / (1 - recovery)
    surv_5y = math.exp(-hazard * 5)
    default_5y = 1 - surv_5y

    print(f"{name:<30} {spread*10000:>8.0f}bp {surv_5y*100:>9.2f}% {default_5y*100:>9.2f}%")
```

### 12.6 Risk Sensitivity Analysis

```python
# Compare CS01 across maturities
maturities = [
    ('12/20/2023', '1Y'),
    ('12/20/2024', '2Y'),
    ('12/20/2025', '3Y'),
    ('12/20/2026', '4Y'),
    ('12/20/2027', '5Y'),
]

notional = 10_000_000

print("CS01 by Maturity:")
print("-" * 50)
print(f"{'Maturity':<12} {'PV Clean':>14} {'CS01':>12} {'CS01/MM':>12}")
print("-" * 50)

for mat_date, tenor in maturities:
    result = pricer.price_cds(
        maturity_date=mat_date,
        par_spread=0.0100,
        coupon_rate=100,
        notional=notional,
        recovery_rate=0.40,
        is_buy_protection=True,
    )

    cs01_per_mm = result.cs01 / notional * 1_000_000
    print(f"{tenor:<12} ${result.pv_clean:>12,.0f} ${result.cs01:>10,.0f} ${cs01_per_mm:>10,.0f}")
```

### 12.7 Complete Module Reference

| Module | Key Functions/Classes | Purpose |
|--------|----------------------|---------|
| `isda.pricer` | `CDSPricer` | High-level pricing API |
| `isda.cds` | `CDS`, `CDSContract`, `CDSPricingResult` | Core pricing engine |
| `isda.curves` | `ZeroCurve`, `CreditCurve` | Curve representations |
| `isda.zero_curve` | `bootstrap_zero_curve()` | Zero curve bootstrapping |
| `isda.credit_curve` | `bootstrap_credit_curve()` | Credit curve bootstrapping |
| `isda.fee_leg` | `fee_leg_pv()`, `risky_annuity()` | Premium leg calculations |
| `isda.contingent_leg` | `contingent_leg_pv()` | Protection leg calculations |
| `isda.schedule` | `CDSSchedule`, `generate_cds_schedule()` | Payment schedules |
| `isda.imm` | `next_imm_date()`, `previous_imm_date()` | IMM date utilities |
| `isda.dates` | `parse_date()`, `year_fraction()` | Date utilities |
| `isda.tenor` | `parse_tenor()`, `Tenor` | Tenor parsing |
| `isda.interpolation` | `flat_forward_interp()` | Curve interpolation |

---

## Quick Reference Card

### Key Formulas

| Calculation | Formula |
|-------------|---------|
| Discount Factor | `DF(t) = exp(-r(t) * t)` |
| Survival Probability | `Q(t) = exp(-h(t) * t)` |
| Default Probability | `PD(t) = 1 - Q(t)` |
| Hazard Rate (approx) | `h ≈ spread / (1 - R)` |
| Fee Leg PV | `Σ c × N × τ × Q × DF` |
| Protection PV | `(1-R) × N × ∫ λ × Q × DF dt` |
| Par Spread | `Protection PV / (RPV01 × N)` |
| Upfront (approx) | `(spread - coupon) × RPV01 × N` |

### Standard Conventions (ISDA)

| Parameter | Standard Value |
|-----------|----------------|
| Payment Frequency | Quarterly |
| Day Count (Accruals) | ACT/360 |
| Day Count (Curves) | ACT/365F |
| Business Day | Modified Following |
| Standard Coupons | 100 bps or 500 bps |
| Standard Recovery | 40% |
| Maturity Dates | IMM (Mar/Jun/Sep/Dec 20) |

---

*This guide is based on the ISDA CDS Standard Model implementation. For the complete source code, see the accompanying Python library.*
