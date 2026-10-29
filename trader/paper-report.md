# Paper trading report: Thursday 2026-10-29

**PAPER TRADING ONLY.** No broker was connected and no order was placed. Fills are simulated at free, delayed Yahoo quotes. These are not real results.

Session started at 2:50 PM New York time, so only the last 40 minutes of the entry window (cutoff 3:30 PM) were available.

| ticker | entry (ET) | entry $ | stop | target | exit (ET) | exit $ | result | P&L |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| CMCSA | 2:58 PM | 22.19 | 21.91 | 22.75 | 3:55 PM (flat by close) | 22.225 | win | +$0.14 |

Shares: 4 (the $100 cap bound, not the $2 max loss; the risk at the stop was $1.12). Risk check: PASS. Time Machine: 97% neither stop nor target by 3:55, average R -0.03 (a coin flip).

Totals: 1 trade, 1 win, 0 losses, win rate 100% (on one trade, meaningless). Ending balance: $100.14 from $100.00.

Why only one trade: 4 shares of CMCSA used $88.76 of the $100, so nothing else could be bought while it was open, and it stayed open past the 3:30 PM entry cutoff.

Full log: trader/paper-log.json. Backtest: trader/backtest/RESULTS.md.
