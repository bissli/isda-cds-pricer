# ISDA CDS Pricer

Pure Python implementation of the ISDA CDS Standard Model for pricing Credit Default Swaps.

## Installation

```bash
poetry install
```

## Usage

```python
from isda import CDSPricer

pricer = CDSPricer(
    trade_date='31/08/2022',
    swap_rates=[0.002979, 0.006419, ...],
    swap_tenors=['1M', '3M', '6M', '1Y', ...]
)

result = pricer.price_cds(
    maturity_date='20/12/2026',
    par_spread=0.0065,
    coupon_rate=100,  # bps
    notional=12_000_000,
    recovery_rate=0.4
)
```

## Testing

```bash
poetry run pytest
```

## Documentation

See the [CDS Pricing Guide](docs/CDS_PRICING_GUIDE.md) for a comprehensive guide covering CDS pricing from first principles to expert-level implementation.
