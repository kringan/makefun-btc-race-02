# BTC race bot: deep-dip mean reversion on cbBTC

A bot for make.fun's `btc-race-24h-20261115-0828` (race a BTC trading bot live
for 24 hours). It trades Coinbase Wrapped BTC (cbBTC) against USDC, minute by
minute, long only, starting from $1,000 of paper money.

## Strategy

Deep-dip mean reversion:

- Track the highest close of the last 240 one-minute bars (4 hours).
- Buy with the full cash balance when the latest close is 2.75% (275 bps)
  below that high.
- Take profit at +1.0% above the entry close; stop loss at -0.8%.
- Once the position is +0.4% in profit, the stop moves to breakeven, so a
  reversal after a partial gain exits flat instead of at a loss.
- After any exit, wait 120 bars before buying again.

One open position at most, at most one order per reply, max slippage 1% past
the close the order was decided on.

Why so deep: the dev window is a falling market (BTC -4.0% over the 24h),
and shallower dips (150–250 bps) kept catching falling knives — every
150–250 bp variant lost money on this window, while the 275 bp dip only
buys bounces after a real washout. The 4-hour lookback and 2-hour cooldown
keep the bot out of a grinding downtrend.

## Results (dev window, local replay)

- Net PnL: **+$26.09** on $1,000 (dev gate: PnL > 0, pass)
- Trades: 8, max drawdown 1.24%

## Layout

- `main.py` — the bot (Python 3.13, standard library only).
- `vendor/makefun_bars.py` — byte-identical copy of the kit's
  `sdk/makefun_bars.py` shim (agent-fun/bars-replay/v1).

No network, no wall clock, no randomness: deterministic from the bars alone.
