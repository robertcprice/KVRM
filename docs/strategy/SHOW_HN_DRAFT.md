# Show HN draft (post when ready — you post, not the repo)

**Title options (pick one, ≤80 chars):**

1. Show HN: KVRM – fail-closed action routing for AI systems (0% false-accept)
2. Show HN: A decision layer that can say "none of the above" and mean it
3. Show HN: KVRM – registry-constrained routing so models can't invent actions

**URL:** https://github.com/robertcprice/KVRM

**Body:**

I built KVRM because of a failure mode I kept hitting: any system where a
model's output triggers a real action (incident runbook, account suspension,
drone maneuver) will eventually meet an input it has no business acting on —
and a classifier answers anyway. It always answers. That's what it's for.

KVRM inverts this. Every decision is constrained to a versioned action
registry. Each action declares the input envelope it's valid for (a boolean
expression tree over features). An ensemble of six selectors proposes
candidates, a support gate drops any candidate whose envelope the input
doesn't satisfy, a validator checks the survivor against the live registry,
and only then does anything execute. Inputs that satisfy no envelope are
rejected or routed to an audited fallback — fail-closed, not best-guess.
Every decision logs its candidate scores, support evaluation, and the SHA-256
digest of the registry version it ran against.

Numbers (all regenerable from the repo): across 12 domains and 682 eval cases,
0/200 unsupported inputs executed (0.0% false-accept), 482/482 supported
inputs routed correctly. For contrast I ran small instruction-tuned models
(Qwen3.5, Gemma4) as structured-output selectors on the same cases: the best
one false-accepts 77% of unsupported inputs; one of them false-accepts 100%.
The ablations are the interesting part: remove the support gate and
correctness collapses to ~0.11–0.23 under confident-but-invalid evidence;
remove strict fallback validation and unsafe execution goes from 0% to 100%
on infeasible-handoff probes.

It's a plain Python library (MIT). `pip install -e kvrm-core/` gives you a
`kvrm` CLI — `kvrm init my-domain` scaffolds a working domain (just JSON, no
code), then `kvrm route/eval/explain` run the full pipeline on it. There's
also a small FastAPI server if you want it as a service with an audit log.

The obvious application right now is agent tool-calling: the registry is your
tool list, support specs are your preconditions, and the model never gets to
execute a tool the current state doesn't support. I'd genuinely like to hear
where this breaks — the eval domains are synthetic (that's documented), and
production traffic is the validation step I haven't done yet.

**First comment (post immediately after, pre-empts the obvious questions):**

A few things people will rightly poke at, answered up front:

- *"The domains are synthetic."* Yes — 12 eval packs built to probe the
  architecture (supported/unsupported splits, boundary perturbations,
  multi-step chains, registry-evolution probes). The claim is about the
  architecture's fail-closed properties, not about having solved SOC triage.
- *"Isn't this just a rules engine?"* The support specs are rules; the
  selection isn't. Rules alone can't rank among multiple valid actions or
  generalize near boundaries — that's what the selector ensemble + evidence
  fusion does. The novelty claim is the ordering: selection is subordinate to
  support gating and validation, so prediction quality can't compromise the
  safety contract.
- *"0% false-accept seems too clean."* It's a structural property, not a
  model accuracy: an action outside its envelope cannot pass the gate, by
  construction. The fuzz suite (400 randomized/garbage inputs per run)
  enforces exactly this invariant in CI.
