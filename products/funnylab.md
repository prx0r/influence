# funnylab — kind: infra

The simulate-only comedy loop. No socials, no money, no humans. Feeds
lineages to autopilot and training signal to eval-api.

- Intent: get funnier every cycle for the price of inference.
- In → out: corpus + lineages → scored sets → reweighted lineages.
- Path: corpus → set.write → funny.score / lands Noul → rsi.reweight.
- Needs: pinned corpus (`jacob-burgess/killtony` @ `8f64531`,
  `/home/ubuntu/killtony-upstream`; prior art `/home/ubuntu/killella/data`).
- Feeds: freaktown-autopilot (lineages), eval-api (judge training pairs).
- Status: designed. Next: frozen eval cut, one lineage, first reweight receipt.
