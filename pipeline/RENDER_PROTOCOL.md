# Render Protocol — lessons bought with free-tier calls, 2026-10-15

Read this before touching voices, renders, or the engine. Every rule below
cost a real mistake. Owner law sits above all of it: CLEAN VOICE (as-is,
no processing), $0 first, ears dispose.

## 1. Never render until validation passes (renders are not free to redo)
- Order: clean → validate_readout.py PASS → render. No exceptions.
- A killed background render wastes every call before it. Batch renders die
  to timeouts; run one file per command with unbuffered output.
- Background renders: launch with correct PYTHONPATH (cwd gotcha killed one
  run silently) and poll the log. `pkill -f` with a self-matching pattern
  hangs your own shell — use bracket patterns (`[g]rimm`).

## 2. Fish MCP facts
- Known ID → `get_voice`/`audio.voice`. Search NEVER finds IDs; direct REST 404s.
- `search_voices` page_size caps at 20. 25+ silently returns ZERO.
- Breadth = more queries (narrow brief + broad popularity sweep), never bigger pages.

## 3. Casting discipline
- PRESENT, never assign. Slates of 3–5 with samples; locks need a human
  reason recorded verbatim. A unilateral pick (even a good one) is a bug —
  its partials get deleted and the work redone.
- Anchors obey gender locks (they bypass the uses floor, nothing else).
- Tests assert behavior, never voice names (no "Adrian" hardcodes — read the
  live chair label).
- Stale snapshots lie: `casting/*.json` was archived 2026-10-15. Live engine
  + `voice-registry.json` are truth. Thesis `sounds_like` blocks are dead
  text — they feed nothing.
- Shelf, not adjectives: whisper+breathy retrieves the sensual shelf.
  Frost = witch/dark/mysterious. Veto the wrong genre explicitly.
- Narrators = narration voices; characters = character-voice tags.

## 4. Text path (what reaches the mic)
- Episodes render ONLY via render_pilot (parse strips `//` headers). Never
  prep-then-speak raw files by hand — headers get voiced.
- Gate + poison run PER CHUNK (a full readout is one segment; whole-segment
  gating can never pass).
- normalize() speaks: chapters/books cardinal ("chapter nine"), monarchs
  ordinal ("Henry the eighth"), `_italics_` stripped, `***` → [long pause].
  Fish tags are masked for processing, restored byte-identical for render.
- Watch list (audit found each once): Mr/Mrs/St titles, non-ascii (О, →),
  doubled words (real Gutenberg typos — fix the word, never rewrite),
  currency, `Part I` → "Part eye" trap, Psalm 23:1 colons.
- Sources lie about completeness: ~21k-word excerpts end mid-tale.
  Completeness check before promising hours. Truncation tails cut to last
  sentence; tale-boundary editing is editorial (damn routines), not mechanical.
- Inline quotes stay narrator-voiced until the splitter lands (in progress):
  explicit `said X` → speaker tags in the drama file (routine 02 owns
  splits); pronoun-only quotes stay narrator. Misattribution is worse than
  narrator-reading-all.

## 5. Voices as-is
- Channel pace 1.0 everywhere, expression off, no bed/SFX/loudnorm.
  Old saved formulas still carry stored expression — zero them on touch.
  Explicit owner direction ("slower") still obeys; defaults stay neutral.

## 6. Infra + hygiene
- Fish key: `characters/audition/.env` (600, gitignored). It has appeared in
  chat history — rotate in Fish dashboard.
- R2 S3 keys on box are dead (rotated Sept). CF_API_TOKEN works for the CF
  API (buckets listable) but cannot mint S3 keys. Owner minute needed:
  dash → R2 → API Tokens. Until then masters live in the voice bank.
- No `.bak` files, no /tmp scripts left behind. `git status` before done.
- Restarts: backend change → restart :8795 (kill by port, relaunch with
  DASH_PORT + YT_MODE=1, verify /api/health). Static files need none.
- Rule 1 stands: owner pushes. No commits without being asked.
