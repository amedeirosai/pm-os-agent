# Cortex, a PM Chief-of-Staff Agent

> A PM chief-of-staff agent, one agent plus an independent critic, that drafts my weekly leadership update and a PRD-scoped story batch from pulled project data, then stops at my review with nothing posted.

_Andreia Medeiros · Agentic Loops for PMs Cohort · October 2026_

Repo: https://github.com/amedeirosai/pm-os-agent

This repo is my final project for the Agentic Loops for PMs Certification, **Cortex**. Each module’s artifact lives in its own folder; this README is the dashboard and the pitch.

---

## Module artifacts

### M1 · The Agent Line
- **Agent-line map**: [`01-agent-line/agent-line-map.md`](01-agent-line/agent-line-map.md)

### M2 · Loop Engineering
- **Loop spec**: [`02-loop-design/loop-spec.md`](02-loop-design/loop-spec.md)

### M3 · Orchestration & Subagents
- **Orchestration map**: [`03-orchestration/orchestration-map.md`](03-orchestration/orchestration-map.md)

### M4 · Choose What Each Agent Step Is Allowed to See
- **Memory & context plan**: [`04-memory-context/memory-and-context.md`](04-memory-context/memory-and-context.md)

### M5 · Bounds & Evals
- **Bounds & evals**: [`05-bounds-evals/bounds-and-evals.md`](05-bounds-evals/bounds-and-evals.md)

### M6 · Autonomy & Production
- **Production & autonomy plan**: [`06-autonomy/production-and-autonomy.md`](06-autonomy/production-and-autonomy.md)
- **Prototype write-up**: [`06-autonomy/prototype.md`](06-autonomy/prototype.md)
- **Build insights**: [`06-autonomy/build-insights.md`](06-autonomy/build-insights.md)
- **Pitch deck**: [`06-autonomy/pitch.html`](06-autonomy/pitch.html)
- **Live agent**: [`00-build/agent.py`](00-build/agent.py)

---

## Ship plan

### Autonomy dial (per segment)
- **Me (PM owner):** Supervised. I built it and know its failure modes; I review every draft at the HITL checkpoint.
- **Covering / new PM:** Assisted. Doesn't know Cortex's blind spots yet; reviews every step, including "Context used / excluded".
- **Eng lead receiving the stories (Ed, Trevor):** Assisted. Stories land as proposals the team sizes, splits, and adds dependencies to.
- **Stakeholder / SME:** Assisted. Confirms scope and that stories match their requirements before a sprint.
- **For everyone:** posting company-wide updates and committing dates stay human-only.

### Trust Ladder rung + eval gate
- **Current rung:** Assisted (on request, human reviews everything, fixtures only, crons not wired).
- **Next rung:** Supervised.
- **Gate:** replay set R1–R6 at 100% and EV-7 fixed (date requests escalate) on every change; then 4 consecutive weeks of shadow runs on real data: 4/4 status runs and 2/2 stories runs pass EV-1 + EV-4, ≤ 1 fact correction per run, stories slip (EV-2) in ≤ 1 of 4 runs, and 0 trust incidents (confidential leak, stated date/commitment, hollow DONE, write/post outside approval).

### Deployment plan
- **Runtime:** serverless scheduled functions: two timer triggers (weekly status, biweekly stories) + an HTTP trigger for manual runs. Short, bounded jobs a few times a month.
- **Owner / on-call:** me (PM). Escalation: Ed and Trevor, eng partners for my two teams, for build/tool failures and the hard kill switch.
- **Rollback (smallest first):** drop the dial a rung → halt flag → revert prompt/version (model pinned) → disable a tool → revoke keys/tokens + disable the schedule.
- **Monitoring (weekly run-log review):** replay/eval pass rate in CI, escalate/stuck rate + repeating rejection codes, cost per run / daily / churn alerts, trust-incident count, stories-slip rate.

### ROI metrics + widen-autonomy rule
**ROI:**

- **Outcome:** PM time per update cycle: 3–4 hours of review, down from 2–3 days manual (~80–90% less). Captured by logging review time in the shadow weeks.
- **Cost-to-serve:** ≤ $0.10 per approved update (today ~$0.02–0.06 per run). Run-log cost ÷ approved drafts.
- **Trust incidents:** 0 per month. Incident log reviewed weekly.
- **Story acceptance:** ≥ 70% of proposed stories kept by Ed's and Trevor's teams (split / dependencies added still counts). Tracked at sprint planning.

**Widen-autonomy rule:**

- **Per segment, one rung at a time:** gate still green (R1–R6 100%, EV-1..EV-8 passing on the current version) + 4 consecutive clean weeks at the current rung with ROI on target + segment evidence (covering PM: shadowed 4 of my runs with ≤ 1 correction; eng teams: story acceptance ≥ 70% for 2 sprints). Any single trust incident drops that segment back a rung immediately and restarts its count.

### Governance & strategy
- **Compliance:** no emails or Teams chats in prompts; no cross-project data (per-project read tokens); confidential projects counted, never named; memory stores references, not raw transcripts; real data never in git.
- **Safety:** posting, committing dates, and final prioritization stay human-only; no post/merge/edit tool; backlog writes only via a single-use token after approval; kill switch soft (halt flag) and hard (revoke keys + disable schedule).
- **Reliability:** 8 iterations · 2 revisions · 90 s/run · $0.50/run · $1/day · churn alert at 3× median; budget caps ESCALATE, infra failures STUCK. Model down: retry hourly until the deadline, then STUCK + notify and I write it manually.
- **Strategy:** real connectors next, Azure DevOps first, gated by EV-8 + scoped tokens + the 4-week shadow.

---

## Build insights

- **Friction point.** The critic was harder to tune than the agent (over-flagging, fixed with a precision rule); Cortex was most confident when it knew the least (hollow draft from stale data, stopped only by a code check); stories "listed" but not queued in almost every run.
- **Key learning.** Enforce bounds outside the model; stop conditions are product decisions; evals are the spec.
- **Aha moment.** Design for simplicity first and widen scope later, instead of starting with a large orchestration. One agent + one critic, Assisted on one project, and let evidence pull in each new piece.

---

_Certification submission, Agentic Loops for PMs Certification._
