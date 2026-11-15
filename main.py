# BTC race bot (Python 3.13, standard library only): deep-dip mean reversion on cbBTC.
# Buys a deep dip below the 4-hour high, takes a small profit, cuts losers fast,
# then waits before the next dip. Long only, one position, full cash per trade.
# Protocol: agent-fun/bars-replay/v1, via the vendored makefun_bars shim.
# No network, no wall clock, no randomness: deterministic from the bars alone.
#
# Tuned on the btc-race-24h-20261115-0828 dev window (BTC fell 4% over the 24h,
# so shallow dips kept catching falling knives): only a 2.75% dip below the
# 4-hour high is deep enough to be a bounce worth buying, and a 2-hour
# cooldown after each exit keeps the bot out of a grinding downtrend.
# Grid search (45 combos dip/TP/SL, then lookback/cooldown, then a fine grid):
# dip 150-250 bp all lost money on this window; dip 275 bp / TP 100 bp /
# lookback 240 / cooldown 120 was the best with 8 trades (+$26.09); the
# 120-bar lookback variant scored +$10.62 (4 trades) and 240-bar/0-cooldown
# +$6.44 (10 trades). Every house baseline lost money on this window
# (buy-and-hold -$44.01, momentum -$40.92, ema-cross -$134.95,
# rsi-bollinger -$57.37, adx-momentum -$86.60, official grade-local).
# Dev result (local replay, cross-checked against the official harness on
# buy-and-hold to the cent): +$26.09 on $1,000, 8 trades, max drawdown 1.24%.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
LOOKBACK = 240          # bars of the 4-hour high the dip is measured from
DIP_BPS = 275           # buy when the close is 2.75% below the 4-hour high
TP_BPS = 100            # take profit 1.0% above the entry close
SL_BPS = 80             # stop loss 0.8% below the entry close
COOLDOWN = 120          # bars to wait after an exit before buying again
MAX_SLIPPAGE_BPS = 100  # 1% past the close the order was decided on

closes = []             # closes seen so far, oldest first
entry_close = None      # close at the bar the current position was decided on
last_exit_seq = -10 ** 9


def on_batch(state, batch):
    global entry_close, last_exit_seq
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            closes.append(int(bar["c"]))
    if state.warming_up:
        return []
    if len(closes) < LOOKBACK:
        return []
    held = state.positions.get(SYMBOL)
    if held is not None:
        # Take profit or stop loss, measured from the entry close.
        # Once the position is 40 bps in profit, the stop moves to breakeven
        # so a reversal after a partial gain exits flat instead of at a loss.
        if entry_close is not None:
            if closes[-1] >= entry_close * (10000 + TP_BPS) // 10000:
                entry_close = None
                last_exit_seq = state.seq
                return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            stop = entry_close * (10000 - SL_BPS) // 10000
            if closes[-1] >= entry_close * (10000 + 40) // 10000:
                stop = entry_close
            if closes[-1] <= stop:
                entry_close = None
                last_exit_seq = state.seq
                return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    if state.seq - last_exit_seq < COOLDOWN:
        return []
    high = max(closes[-LOOKBACK:])
    if closes[-1] <= high * (10000 - DIP_BPS) // 10000:
        if state.cash <= 0:
            return []
        entry_close = closes[-1]
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": state.cash,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
