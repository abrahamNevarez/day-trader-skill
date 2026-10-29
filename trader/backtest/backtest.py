"""Backtest the scanner's setups on free Yahoo data. Python 3.8+, standard library only.

    python3 trader/backtest/backtest.py universe   # -> trader/backtest/universe.json
    python3 trader/backtest/backtest.py daily      # 10 years of daily bars
    python3 trader/backtest/backtest.py orb        # 60 days of 5-minute bars
    python3 trader/backtest/backtest.py report     # -> trader/backtest/RESULTS.md

Rules (fixed before looking at results):
  Daily setups use trader-scanner's own find_setups() on the closes up to the signal day.
    entry   next session's open
    stop    entry - 1.5 x ATR(14) of the signal day     (R = entry - stop)
    target  entry + 2R
    exit    stop or target intraday (stop first if one bar touches both; a gap through
            either fills at the open), else the close of the 10th session.
    One open trade per symbol per setup.
  Opening-range breakout: 15-minute range (first three 5-minute bars), entry at the close of
    the first later bar that closes above the range high and starts before 15:30, stop at the
    range midpoint, target 2R, else out at the close of the 15:50 bar (flat by 3:55 PM).
  No commissions, no slippage, no spread. Results are in R; "$2 risk" P&L = 2 x R.
  "Fits $100" counts only trades where whole shares = min(floor(2 / R), floor(100 / entry)) >= 1,
  and gives the dollar P&L of that many shares.
"""
import importlib.util
import json
import math
import os
import sys
import time
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("scan", os.path.join(ROOT, ".claude/skills/trader-scanner/scan.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

MAX_PRICE, MIN_PRICE, TOP_N = 100.0, 5.0, 250
RISK_USD, BUDGET = 2.0, 100.0
CACHE = os.path.join(HERE, "cache")


def out(name):
    return os.path.join(HERE, name)


def save(name, doc):
    with open(out(name), "w") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")


def cached_chart(sym, rng, interval):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "%s_%s_%s.json" % (sym, rng, interval))
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    time.sleep(S.PAUSE)
    text = S.yahoo_get(S.chart_path(sym, rng, interval))
    doc = json.loads(text)
    with open(p, "w") as f:
        json.dump(doc, f)
    return doc


def series(doc):
    res = (doc.get("chart") or {}).get("result") or []
    if not res:
        return None
    s = S.series_from_result(res[0])
    rows = []
    for i, t in enumerate(s["t"]):
        o, h, l, c = (s[k][i] if s[k] else None for k in ("o", "h", "l", "c"))
        if None in (t, o, h, l, c):
            continue
        rows.append((int(t), float(o), float(h), float(l), float(c), int((s["v"] or [0] * len(s["t"]))[i] or 0)))
    return rows


# ---------------------------------------------------------------- universe

def cmd_universe():
    syms = [line.split("|")[0] for line in open(os.path.join(ROOT, "trader/universe.txt")) if line.strip()]
    data, failed = S.fetch_spark(syms, "1mo", "1d", S.PAUSE)
    rows = []
    for sym, s in data.items():
        cl = [c for c in s["c"] if c is not None]
        if len(cl) < 15:
            continue
        price = (s.get("meta") or {}).get("regularMarketPrice") or cl[-1]
        vols = [v for v in (s.get("v") or []) if v]
        if not vols:
            vol = (s.get("meta") or {}).get("regularMarketVolume") or 0
            vols = [vol]
        dv = price * sum(vols) / len(vols)
        if MIN_PRICE <= price < MAX_PRICE:
            rows.append({"symbol": sym, "price": round(price, 2), "dollar_volume": round(dv)})
    rows.sort(key=lambda r: -r["dollar_volume"])
    pick = rows[:TOP_N]
    save("universe.json", {"built": datetime.datetime.utcnow().isoformat() + "Z",
                           "rule": "US common stocks/ADRs from trader/universe.txt, price $%g-$%g today, top %d by average daily dollar volume over the last month" % (MIN_PRICE, MAX_PRICE, TOP_N),
                           "candidates": len(rows), "fetched": len(data), "failed": len(failed), "symbols": pick})
    print("universe: %d of %d priced $%g-$%g; kept the %d most traded" % (len(rows), len(data), MIN_PRICE, MAX_PRICE, len(pick)))


def universe():
    with open(out("universe.json")) as f:
        return [r["symbol"] for r in json.load(f)["symbols"]]


# ---------------------------------------------------------------- daily

def atr(rows, i, n=14):
    trs = []
    for k in range(i - n + 1, i + 1):
        _, _, h, l, _, _ = rows[k]
        pc = rows[k - 1][4]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / n


def fits(entry, risk):
    if risk <= 0:
        return 0
    return max(0, min(int(math.floor(RISK_USD / risk + 1e-9)), int(math.floor(BUDGET / entry + 1e-9))))


def daily_trades(sym, rows, hold=10, look=100):
    trades = []
    busy = {}  # setup -> index the open trade exits on
    for i in range(look, len(rows) - 1):
        closes = [r[4] for r in rows[i - look + 1:i + 1]]
        tags, _ = S.find_setups(closes)
        if not tags:
            continue
        a = atr(rows, i)
        e_i = i + 1
        entry = rows[e_i][1]
        risk = 1.5 * a
        if risk <= 0 or entry <= 0:
            continue
        stop, target = entry - risk, entry + 2 * risk
        exit_px, exit_i, why = None, None, None
        for k in range(e_i, min(e_i + hold, len(rows))):
            _, o, h, l, c, _ = rows[k]
            if k > e_i and o <= stop:
                exit_px, why = o, "stop (gap)"
            elif k > e_i and o >= target:
                exit_px, why = o, "target (gap)"
            elif l <= stop:
                exit_px, why = stop, "stop"
            elif h >= target:
                exit_px, why = target, "target"
            if exit_px is not None:
                exit_i = k
                break
        if exit_px is None:
            exit_i = min(e_i + hold, len(rows)) - 1
            if exit_i - e_i + 1 < hold and exit_i == len(rows) - 1:
                continue  # still open at the end of the data
            exit_px, why = rows[exit_i][4], "time"
        for tag in tags:
            if busy.get(tag, -1) >= i:
                continue
            busy[tag] = exit_i
            r = (exit_px - entry) / risk
            sh = fits(entry, risk)
            trades.append({"symbol": sym, "setup": tag, "date": datetime.datetime.utcfromtimestamp(rows[e_i][0]).date().isoformat(),
                           "entry": round(entry, 4), "stop": round(stop, 4), "target": round(target, 4),
                           "exit": round(exit_px, 4), "why": why, "r": round(r, 4), "shares_fit": sh,
                           "pnl_fit": round(sh * (exit_px - entry), 4)})
    return trades


def cmd_daily():
    syms = universe()
    allt, bad, span = [], [], {}
    for n, sym in enumerate(syms):
        try:
            rows = series(cached_chart(sym, "10y", "1d"))
        except Exception as e:
            bad.append("%s: %s" % (sym, e))
            continue
        if not rows or len(rows) < 150:
            bad.append("%s: too few bars" % sym)
            continue
        span[sym] = (datetime.datetime.utcfromtimestamp(rows[0][0]).date().isoformat(), len(rows))
        allt += daily_trades(sym, rows)
        if (n + 1) % 25 == 0:
            print("  daily %d of %d" % (n + 1, len(syms)), file=sys.stderr)
    save("daily_trades.json", {"symbols": len(span), "failed": bad, "spans": span, "trades": allt})
    print("daily: %d trades on %d symbols (%d failed)" % (len(allt), len(span), len(bad)))


# ---------------------------------------------------------------- orb

def et(ts):
    return S.ts_to_eastern(ts)


def orb_trades(sym, rows):
    days = {}
    for r in rows:
        d = et(r[0])
        if datetime.time(9, 30) <= d.time() < datetime.time(16, 0):
            days.setdefault(d.date(), []).append(r)
    trades = []
    for day, bars in sorted(days.items()):
        bars.sort()
        if len(bars) < 70 or et(bars[0][0]).time() != datetime.time(9, 30):
            continue  # skip half days and holes
        orh = max(b[2] for b in bars[:3])
        orl = min(b[3] for b in bars[:3])
        mid = (orh + orl) / 2
        e = None
        for k in range(3, len(bars)):
            if et(bars[k][0]).time() >= datetime.time(15, 30):
                break
            if bars[k][4] > orh:
                e = k
                break
        if e is None:
            continue
        entry = bars[e][4]
        risk = entry - mid
        if risk <= 0:
            continue
        stop, target = mid, entry + 2 * risk
        exit_px, why, when = None, None, None
        for k in range(e + 1, len(bars)):
            t = et(bars[k][0]).time()
            if t >= datetime.time(15, 55):
                break
            _, o, h, l, c, _ = bars[k]
            if l <= stop:
                exit_px, why = (o if o < stop else stop), "stop"
            elif h >= target:
                exit_px, why = (o if o > target else target), "target"
            if exit_px is not None:
                when = t
                break
            exit_px_flat, when_flat = c, t
        if exit_px is None:
            last = [b for b in bars if et(b[0]).time() < datetime.time(15, 55)][-1]
            exit_px, why, when = last[4], "flat 3:55", et(last[0]).time()
        sh = fits(entry, risk)
        trades.append({"symbol": sym, "date": day.isoformat(), "entry_time": (et(bars[e][0]) + datetime.timedelta(minutes=5)).strftime("%H:%M"),
                       "entry": round(entry, 4), "stop": round(stop, 4), "target": round(target, 4),
                       "exit": round(exit_px, 4), "why": why, "r": round((exit_px - entry) / risk, 4),
                       "shares_fit": sh, "pnl_fit": round(sh * (exit_px - entry), 4)})
    return trades


def cmd_orb():
    syms = universe()
    allt, bad, days = [], [], set()
    for n, sym in enumerate(syms):
        try:
            rows = series(cached_chart(sym, "60d", "5m"))
        except Exception as e:
            bad.append("%s: %s" % (sym, e))
            continue
        if not rows:
            bad.append("%s: no bars" % sym)
            continue
        t = orb_trades(sym, rows)
        days.update(x["date"] for x in t)
        allt += t
        if (n + 1) % 25 == 0:
            print("  orb %d of %d" % (n + 1, len(syms)), file=sys.stderr)
    save("orb_trades.json", {"failed": bad, "sessions": sorted(days), "trades": allt})
    print("orb: %d trades over %d sessions (%d failed)" % (len(allt), len(days), len(bad)))


# ---------------------------------------------------------------- report

def stats(trades):
    n = len(trades)
    if not n:
        return None
    rs = [t["r"] for t in trades]
    w = sum(1 for r in rs if r > 0)
    l = sum(1 for r in rs if r < 0)
    avg = sum(rs) / n
    sd = math.sqrt(sum((r - avg) ** 2 for r in rs) / (n - 1)) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else 0.0
    fit = [t for t in trades if t["shares_fit"] >= 1]
    return {"trades": n, "wins": w, "losses": l, "win_rate": w / n, "loss_rate": l / n, "avg_r": avg,
            "ci95": (avg - 1.96 * se, avg + 1.96 * se), "pnl_2usd": 2 * sum(rs),
            "fit_trades": len(fit), "fit_pnl": sum(t["pnl_fit"] for t in fit),
            "fit_avg_r": (sum(t["r"] for t in fit) / len(fit)) if fit else None}


def verdict(s):
    lo, hi = s["ci95"]
    if lo > 0:
        return "positive, and the 95% range stays above zero (before costs)"
    if hi < 0:
        return "negative: loses money"
    return "no edge: the 95% range includes zero"


def cmd_report():
    lines = []
    d = json.load(open(out("daily_trades.json")))
    o = json.load(open(out("orb_trades.json")))
    u = json.load(open(out("universe.json")))
    first = min(v[0] for v in d["spans"].values())
    lines += ["# Backtest results", "",
              "Built %s from free Yahoo data. **Not financial advice. Past results do not predict future ones.**" % u["built"][:10], "",
              "Universe: %s. %d symbols." % (u["rule"], len(u["symbols"])), "",
              "| setup | data | trades | win rate | loss rate | avg R (95%% range) | P&L at $2 risk | trades a $100 / $2 account could take | their P&L | verdict |",
              "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |"]
    rows = []
    for key, label in S.SETUPS:
        if key == "oversold":
            continue  # the user asked for the bounce, not plain RSI<30
        rows.append((label, "daily, %s to now" % first, [t for t in d["trades"] if t["setup"] == key]))
    rows.append(("opening-range breakout (15 min)", "5-min, %s to %s (%d sessions)" % (o["sessions"][0], o["sessions"][-1], len(o["sessions"])), o["trades"]))
    summary = {}
    for label, data, tr in rows:
        s = stats(tr)
        summary[label] = s
        if not s:
            lines.append("| %s | %s | 0 | | | | | | | |" % (label, data))
            continue
        lines.append("| %s | %s | %d | %.1f%% | %.1f%% | %+.3f (%+.3f to %+.3f) | $%+.2f | %d | $%+.2f | %s |" % (
            label, data, s["trades"], 100 * s["win_rate"], 100 * s["loss_rate"], s["avg_r"], s["ci95"][0], s["ci95"][1],
            s["pnl_2usd"], s["fit_trades"], s["fit_pnl"], verdict(s)))
    lines += ["", "Win = exit above entry, loss = exit below. Every trade is counted, including several symbols on the same day.", "",
              "## Data limits, plainly", "",
              "- **Survivorship bias.** The universe is today's liquid stocks under $100. Companies that went bust or were delisted in the last 10 years are missing, and today's winners are over-represented. That flatters the daily long setups.",
              "- **Price filter is today's price.** A stock under $100 today may have been above it years ago (and the reverse). Yahoo's daily bars are split-adjusted, so old prices are not what traded then.",
              "- **Yahoo's 10y daily range** may start later for recent listings; %d symbols had data, earliest bar %s." % (d["symbols"], first),
              "- **The ORB test is only %d sessions** (Yahoo keeps about 60 days of 5-minute bars). That is one market regime; treat it as a small sample." % len(o["sessions"]),
              "- **No costs.** No spread, slippage or commissions. A one-cent spread on a $0.20 opening-range risk is 5% of R each way.",
              "- **Fills are idealized.** Stops fill at the stop (or the open on a gap), targets at the target, and a bar that touches both counts as a stop.",
              "- **The daily setups have no stop or target in the scanner.** The 1.5 x ATR stop, 2R target and 10-session limit were chosen here, before running, and were not tuned.",
              "- **The $100 / $2 column shows the real problem for a small account:** most daily setups need a stop wider than $2 a share, so no whole share fits the $2 max loss.",
              ""]
    save("summary.json", summary)
    with open(out("RESULTS.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    {"universe": cmd_universe, "daily": cmd_daily, "orb": cmd_orb, "report": cmd_report}[sys.argv[1]]()
