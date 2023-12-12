## Swing failure automation

- Active price of asset (BTCUSDT) with websocket
- trigger price
- long / short
- (max loss in $ ?)

### when trade
- price goes above / below triger
- stays there x seconds
- max SL 2% otherwise cancel
- (minimum volume at high / low?)

### how trade
- distance between highest high starting the
- cross-over and trigger price == SL
- 2x distance SL == target with a minimum target == 0.5%
- tradingsize ← max loss when SL is hit