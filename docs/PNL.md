# P&L Worked Example

This document traces the exact arithmetic performed by `calculate_position()`
in `domain/pnl.py` for a three-trade sequence, then shows the `pledger pnl`
output that results.

## Trades

| # | Direction | Quantity | Price | Date |
|---|-----------|----------|-------|------|
| 1 | BUY       | 100      | 10.00 | 2024-01-10 |
| 2 | BUY       |  50      | 16.00 | 2024-01-20 |
| 3 | SELL      | 120      | 20.00 | 2024-02-01 |

## Step-by-step calculation

### Trade 1 — BUY 100 @ 10.00

```
new_quantity  = 0 + 100 = 100
average_cost  = (0 × 0 + 100 × 10.00) / 100
              = 1 000.00 / 100
              = 10.00

holding = 100 units @ avg cost 10.00
```

### Trade 2 — BUY 50 @ 16.00

The new trade value is blended into the running average:

```
new_quantity  = 100 + 50 = 150
average_cost  = (100 × 10.00 + 50 × 16.00) / 150
              = (1 000.00 + 800.00) / 150
              = 1 800.00 / 150
              = 12.00

holding = 150 units @ avg cost 12.00
```

### Trade 3 — SELL 120 @ 20.00

A sell does not change the average cost. Realized P&L is the spread between
sell price and average cost, multiplied by quantity sold:

```
realized_pnl += (20.00 - 12.00) × 120
             += 8.00 × 120
             += 960.00

quantity = 150 - 120 = 30

holding = 30 units @ avg cost 12.00
realized P&L = 960.00
```

## Final position

| Field         | Value  |
|---------------|--------|
| Quantity      | 30     |
| Average cost  | 12.00  |
| Cost basis    | 360.00 |
| Realized P&L  | 960.00 |

## Unrealized P&L at mark price 22.00

```
unrealized_pnl = (22.00 - 12.00) × 30
               = 10.00 × 30
               = 300.00

total_pnl = 960.00 + 300.00 = 1 260.00
```

## CLI output

```
$ pledger pnl --portfolio "AP7 Demo" --mark SINCH=22.00

 Symbol  Qty  Avg Cost  Cost Basis  Realized P&L  Unrealized P&L  Total P&L
 ────────────────────────────────────────────────────────────────────────────
 SINCH    30     12.00      360.00        960.00          300.00    1260.00
 ────────────────────────────────────────────────────────────────────────────
 TOTAL                               960.00          300.00    1260.00
```

Realized P&L (960.00) is rendered in green; unrealized (300.00) likewise.
If `--mark SINCH=22.00` is omitted, both unrealized and total columns show
`n/a` — never zero, which would be misleading.

## Why the average cost does not change on a sell

This is a property of the weighted average method (genomsnittsmetoden). The
cost of the remaining 30 units is still 12.00 per unit — that is what was paid
for them. A subsequent BUY at any price would blend into this 12.00 basis
naturally via the weighted-average formula.

Contrast with FIFO: under FIFO, selling 120 units would consume all 100 units
from trade 1 (cost 10.00) plus 20 units from trade 2 (cost 16.00), giving a
realized P&L of `(20−10)×100 + (20−16)×20 = 1 000 + 80 = 1 080`. The
remaining 30 units would carry the cost from trade 2: 16.00 each. The two
methods produce different realized P&L figures from the same trades.
