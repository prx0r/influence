# voiceagentfeedback — dev notes for the voice side

Upstream reviewed: `github.com/prx0r/voiceagent` @ `08f19c2` (10 commits, 2 days).
Reviewer: backend track (cmail + stevejobless). Date: 2026-09-10.

**Read in this order:** `01-review.md` → `02-security.md` → `03-integration.md` → `04-build-list.md`

**The one-line brief:** keep your repo as the conversation/retrieval/guard kernel;
keep all business state + telephony config on our side. Do not route production
callers until the P0s in `02-security.md` land — today a jailbreak and a gas-leak
call both depend on the LLM obeying the prompt.

**Pull these notes:** they live in `github.com/prx0r/cmail` under
`voiceagentfeedback/`. To work from them: `git pull` this repo, or copy the
folder into your checkout. Comment inline and push back — we'll read it here.
