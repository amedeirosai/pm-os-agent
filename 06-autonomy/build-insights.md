# Build Insights: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 4, what you learned building it
>
> ✅ **What this validates:** you can reflect on what building it taught you, by the end you'll have proven the friction, the learning, and the aha that changes how you'd design your next agent.

## Friction

- **The critic was harder to tune than the agent.** Getting it to catch real problems without over-flagging took more iterations than anything else: it read an invented metric as a commitment, "now live" as a promise, and in the final M6 run it flagged "Status: Green" as untraceable and pushed a fixable draft into the revision cap. The fix wasn't a stricter prompt; it was a precision rule (quote the text, one problem = one code).
- **Cortex sounded most confident when it knew the least.** With engineering activity withheld, it rebuilt the week from last week's update and the roadmap, "rolling out" an email that had already merged. Only a plain code check (no usable activity → STUCK) stopped it; the prompt alone didn't.
- **"Listed" isn't "done."** In almost every run Cortex wrote stories into the draft without calling `propose_stories`. A loop check catches it every time, but it never stopped happening.

## Learning

1. **Enforce outside the model.** Every bound that held (iterations, cost, queue cap, PRD item per story, no post tool) is code, not instruction. The jailbreak failed because there is no tool to post, not because Cortex said no. The agent line lives in infrastructure, not in the prompt.
2. **Stop conditions are product decisions.** Choosing what is STUCK vs ESCALATE, what counts as an incident, and who gets notified shaped the agent more than the drafting prompt did.
3. **Evals are the spec.** Writing EV-1..EV-8 and the replay set forced me to say exactly what "good" looks like, and EV-7 still failing is the most honest thing in the deliverable.

## Aha moment

**Design for simplicity first, and widen the agent's scope later.** I came in thinking of agents as large orchestrations to build from scratch. Building Cortex showed me why that's backwards: every piece you add is something else to bound, evaluate, and debug. Even one extra subagent (the critic) took more tuning than the main agent. So Cortex stays one agent plus one validator; parallelism and a reader subagent are only "not yet," triggered by real evidence such as context pressure from real connectors. Autonomy works the same way: start at Assisted on one project, and widen only when the evals and the incident record earn it. Next time I'd start with the smallest loop that does the job and let the evidence pull in each new piece.

## What you'd do differently

- **Write the evals and the replay set in week one**, before tuning prompts, so every change is measured instead of eyeballed.
- **Start from real data shapes sooner.** Fixtures hid the problems I expect most (misleading ADO data, missing tags); I'd ingest a sanitized sample of my own sources early.
- **Keep confidential names out of everything from day one,** including the agent's own "what I excluded" notes, which leaked them in testing.
- **Fewer, sharper critic checks** with descriptive codes from the start, and a calibration set for the critic itself.
