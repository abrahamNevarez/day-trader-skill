# Backtest results

Built 2026-10-29 from free Yahoo data. **Not financial advice. Past results do not predict future ones.**

Universe: US common stocks/ADRs from trader/universe.txt, price $5-$100 today, top 250 by average daily dollar volume over the last month. 250 symbols.

| setup | data | trades | win rate | loss rate | avg R (95% range) | P&L at $2 risk | trades a $100 / $2 account could take | their P&L | verdict |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 20-day closing-high breakout | daily, 2016-10-31 to now | 21914 | 44.3% | 55.6% | +0.050 (+0.032 to +0.068) | $+2181.17 | 15153 | $+1838.12 | no edge over the no-signal baseline (+0.069 R): the plus is just being long a rising market |
| bull flag | daily, 2016-10-31 to now | 7228 | 45.0% | 54.8% | +0.062 (+0.033 to +0.091) | $+901.97 | 4418 | $+685.61 | no edge over the no-signal baseline (+0.069 R): the plus is just being long a rising market |
| reclaimed the 20-day average | daily, 2016-10-31 to now | 22566 | 45.4% | 54.4% | +0.072 (+0.054 to +0.089) | $+3239.63 | 15126 | $+2536.67 | no edge over the no-signal baseline (+0.069 R): the plus is just being long a rising market |
| oversold bounce | daily, 2016-10-31 to now | 6137 | 46.8% | 53.0% | +0.069 (+0.039 to +0.099) | $+845.79 | 3834 | $+633.85 | no edge over the no-signal baseline (+0.069 R): the plus is just being long a rising market |
| baseline: no signal, every 5th day | daily, same rules | 104730 | 45.6% | | +0.069 (+0.059 to +0.079) | | | | the bar every setup must beat |
| opening-range breakout (15 min) | 5-min, 2026-08-06 to 2026-10-28 (59 sessions) | 7741 | 39.9% | 59.7% | -0.034 (-0.059 to -0.009) | $-525.32 | 7264 | $+26.03 | negative: loses money |

Win = exit above entry, loss = exit below. Every trade is counted, including several symbols on the same day.

## Data limits, plainly

- **Survivorship bias.** The universe is today's liquid stocks under $100. Companies that went bust or were delisted in the last 10 years are missing, and today's winners are over-represented. That flatters the daily long setups.
- **Price filter is today's price.** A stock under $100 today may have been above it years ago (and the reverse). Yahoo's daily bars are split-adjusted, so old prices are not what traded then.
- **Yahoo's 10y daily range** may start later for recent listings; 250 symbols had data, earliest bar 2016-10-31.
- **The ORB test is only 59 sessions** (Yahoo keeps about 60 days of 5-minute bars). That is one market regime; treat it as a small sample.
- **Overlapping trades.** Daily signals on many stocks cluster on the same days (one market move), so the 95% ranges are too narrow; the real uncertainty is wider.
- **The baseline row matters most.** It takes the same long trade with the same stop and target on every 5th day, no signal. Over a 10-year rising market that alone is positive. A setup only shows an edge if it beats the baseline, not zero.
- **The $ columns add up every signal.** A $100 account holds one position at a time, so it could never take thousands of overlapping trades; read the dollars as average R x $2, not as money a $100 account would have made.
- **No costs.** No spread, slippage or commissions. A one-cent spread on a $0.20 opening-range risk is 5% of R each way.
- **Fills are idealized.** Stops fill at the stop (or the open on a gap), targets at the target, and a bar that touches both counts as a stop.
- **The daily setups have no stop or target in the scanner.** The 1.5 x ATR stop, 2R target and 10-session limit were chosen here, before running, and were not tuned.
- **The $100 / $2 column shows the real problem for a small account:** most daily setups need a stop wider than $2 a share, so no whole share fits the $2 max loss.

