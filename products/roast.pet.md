# roast.pet — kind: surface

Upload your pet, get roasted. Same roast-line functions, pet-flavored
front plus an Etsy storefront for distribution.

- Intent: the funniest pet product on the internet.
- In → out: pet pics + name → roast set / clip → delivered roast.
- Path: image observe → roast-line judges → L3 render → gated send.
  Storefront orders arrive as queue tasks with digits.
- Needs: setup.social (roast.pet web records — zone live, mail only
  today), roast-line (the engine), clip-farm (video roasts),
  influencer-ops patterns (order queue).
- Distribution: Etsy listing for the paid roast (keys `ETSY_KEYSTRING` /
  `ETSY_SHARED_SECRET` in the etsy vault), roast.pet site for upload +
  delivery. Same queue, same receipts, two doors.
- Implementation repo: `/home/ubuntu/etsysignal` — the pipeline already
  runs end to end: order → beats → FreakTown bundle → portrait → gift URL
  (`roast/pipeline.py`, demo `roast/demo_orders/buster-001/`). Ships photo
  QC + photo pipeline, roast compiler (order → FreakTown beats), gift page
  + card art, Remotion listing (`roast-pet-listing/`), and Pog persistent
  pet characters (bring them back for new sets, gifts, performances).
  Influence's job is the management plane around it: order queue with
  digits, spend/grant rails, receipts per roast, analytics back as reward.
- Status: pipeline live in-repo, zone live, etsy keys held. Next: web
  records, order queue wired to the pipeline, first receipted roast.
