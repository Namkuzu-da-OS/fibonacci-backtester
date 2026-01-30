# Fibonacci Backtester

A backtesting system for **DiNapoli Levels** - a Fibonacci-based trading methodology from Joe DiNapoli's book "Trading with DiNapoli Levels".

## What This Tests

This system validates DiNapoli's Fibonacci methodology on real market data:

| Concept | Description |
|---------|-------------|
| **Fibnodes** | .382 (F3) and .618 (F5) retracement levels for support/resistance |
| **Objective Points** | COP, OP, XOP expansion targets for profit-taking |
| **Confluence** | When Fibnodes from different reactions align (strongest S/R) |
| **Agreement** | When a Fibnode and Objective Point align |

## Key Formulas (from DiNapoli)

### Fibnodes (Retracements)
```
F3 = B - 0.382(B - A)
F5 = B - 0.618(B - A)
```
Where B = Focus Number (swing extreme), A = Reaction point

### Objective Points (Expansions)
**Critical: Calculate from Point C, NOT Point B!**
```
COP = 0.618(B - A) + C
OP  = (B - A) + C
XOP = 1.618(B - A) + C
```

## Installation

```bash
pip install requests
```

## Usage

### Run a Backtest
```bash
python backtest.py SPY
python backtest.py QQQ
python backtest.py AAPL
```

### See Concrete Example
```bash
python test_example.py SPY
```

### Use in Code
```python
from schwab_client import SchwabClient
from dinapoli import DiNapoliCalculator, SwingPoint

# Calculate Fibnodes
calc = DiNapoliCalculator()
focus = 100.0  # Recent high
reactions = [SwingPoint(price=90.0, index=0, is_high=False)]

fibnodes = calc.calculate_fibnodes(focus, reactions, is_uptrend=True)
for fn in fibnodes:
    print(f"{fn.ratio}: ${fn.price:.2f}")
```

## Sample Backtest Results

| Metric | SPY | QQQ | AAPL |
|--------|-----|-----|------|
| F3 Held | 97.0% | 90.9% | 86.4% |
| F5 Held | 94.7% | 81.2% | 90.9% |
| **Confluence Held** | **100%** | **100%** | **100%** |
| OP Reached | 54.5% | 55.6% | 41.7% |

**Key Finding:** Confluence areas show 100% hold rate across all tested symbols, validating DiNapoli's claim that Confluence is the strongest form of support/resistance.

## Files

| File | Purpose |
|------|---------|
| `dinapoli.py` | Core DiNapoli calculations |
| `schwab_client.py` | API client for market data |
| `backtest.py` | Backtesting engine |
| `test_example.py` | Step-by-step example |
| `RnD/Research.html` | Interactive learning guide |
| `RnD/extracted_text/` | Full book text for reference |

## Requirements

- Python 3.8+
- Access to a market data API (configured for local Schwab server)

## Configuration

Update the API endpoint in `schwab_client.py`:
```python
def __init__(self, base_url: str = "http://YOUR-SERVER:8000"):
```

## References

- "Trading with DiNapoli Levels" by Joe DiNapoli
- Research documentation in `RnD/` folder

## License

For educational purposes only. Not financial advice.
