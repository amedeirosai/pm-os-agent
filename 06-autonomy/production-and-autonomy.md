# Production & Autonomy: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 5, how you'd ship it, govern it, and widen trust over time
>
> ✅ **What this validates:** you can ship it, govern it, and widen trust deliberately, by the end you'll have proven an autonomy dial, a Trust Ladder rung with its eval gate, and a governance plan.

## Autonomy Dial by segment

_Autonomy is a product decision per user, not one global setting._ The dial sets how many below-the-line steps still pause for a human for that user; it does **not** move the M1 agent line. Posting a company-wide update stays human-only for everyone.

| Segment | Desired autonomy | Why |
|---|---|---|
| **The PM who owns Cortex** (me) | **Supervised** | Built it and knows its failure modes; reviews every draft at the HITL checkpoint, while the spot-checked steps (pulling data, drafting) run unattended on the cron. |
| **A covering or new PM** (running Cortex while I'm away, or new to the team) | **Assisted** | Doesn't know Cortex's blind spots yet (the stories slip, a roadmap standing in for missing activity), so every step, including the "Context used / excluded" list, gets reviewed. |
| **The eng lead receiving the stories** | **Assisted** | Stories always land as proposals the team sizes, splits, and adds technical dependencies to; nothing enters their backlog without them. |
| **Stakeholder / SME** | **Assisted** | Confirms the scope and validates that the proposed user stories align with their requirements before they're committed to a sprint. |

## Trust Ladder

- **Current rung: Assisted.** Cortex produces outputs on request and a human reviews everything. Validated on simulated fixtures only; the weekly/biweekly crons are designed but not wired, and no real ADO / Teams / SharePoint data has gone through it yet.
- **Next rung: Supervised:** the crons turned on; I approve at the HITL checkpoints instead of reviewing every step.
- **Eval gate to reach Supervised** (count-based: at one run a week, percentages just mean "all of them"):
  1. **Offline, on every change:** replay set **R1–R6 at 100%** (M5 §5), and **EV-7 fixed** (a date request escalates, never STUCK, never a date).
  2. **Shadow on real data for 4 consecutive weeks** once the real tools are plugged in (Cortex runs; I still write the real update): **4/4** status runs and **2/2** stories runs pass **EV-1 + EV-4** (grounded, critic pass, stories within the PRD), with **≤ 1** human fact correction per run, and the **stories slip (EV-2) in ≤ 1 of the 4** status runs.
  3. **Clean incident record for those 4 weeks** (below).
- **What counts as an incident:** any confidential leak · any stated release date or ship commitment · any hollow DONE (a draft passed without its sources) · any write or post outside an approval. **Not incidents:** ESCALATE and STUCK exits, which are the system working as designed.
- **Incident record so far** (all on fixtures, none reached a real audience):
  - **0** posts, writes, or commitments outside approval: there is no tool to make them.
  - Caught **in testing and fixed:** the "Context used / excluded" list named the confidential projects Orbit and Pulsar (M5); the critic misread "now live" as a commitment and over-flagged an invented metric as one (M3, M5); a hollow draft built from roadmap narrative when activity was withheld (M4, now STUCK).
  - **Open:** EV-7 still fails (a GA-date request ends STUCK instead of ESCALATE), part of the gate above.

## Deployment plan

- **Runtime: serverless scheduled functions.** Two timer triggers (weekly status, biweekly stories) plus an HTTP trigger for the manual run. Cortex is a short, bounded job (≤ 90 s, a few model calls) that runs a few times a month, so there's no server to keep alive, and the schedule can be disabled in one place.
- **Operator / on-call owner:** **me, as PM.** I own the prompts, bounds, evals, and the review checkpoint. **Escalation to Ed and Trevor**, the eng partners for my two product teams, for build or tool failures and the hard kill switch.
- **Rollback** (smallest step first): drop the dial one rung → set the halt flag (soft kill) → revert the prompt / agent version (the model version is pinned) → disable a misbehaving tool → revoke keys/tokens and disable the schedule (hard kill).
- **Monitoring:** a weekly review of the run log, watching:
  - replay / eval pass rate in CI (R1–R6, EV-1..EV-8)
  - escalate / stuck rate, and rejection codes that keep repeating
  - cost per run, daily spend, and churn alerts
  - trust-incident count
  - stories-slip rate (EV-2)

## ROI metrics (beyond adoption & tokens)

| Metric | Target | How captured |
|---|---|---|
| **Outcome: PM time per update cycle** (weekly leadership update + sprint story prep) | **3–4 hours of review**, down from a **2–3 day** manual baseline (~80–90% less PM time) | Log my review time per run during the 4-week shadow; compare against the manual baseline |
| **Cost-to-serve: $ per approved update** | **≤ $0.10** model spend per approved draft, including revisions and failed runs (today ~$0.02–0.05 per run) | Sum `cost_usd` from the run log ÷ number of drafts I approved |
| **Trust incidents** | **0 per month** (definition in the Trust Ladder: leaks, stated dates, hollow DONEs, writes outside approval; ESCALATE/STUCK don't count) | Incident log reviewed weekly alongside the run log |
| **Story acceptance** | **≥ 70%** of proposed stories kept by Ed's and Trevor's teams (split or with dependencies added still counts as kept) | Track each queued story's outcome at sprint planning: kept / split / discarded |

## Widen-autonomy decision rule

_Stated in advance; applied per segment, one rung at a time._

**Turn the dial up one notch for a segment when all of these hold:**
1. **Gate still green:** replay set R1–R6 at 100% and EV-1..EV-8 passing on the current version (any prompt, tool, or model change resets this).
2. **4 consecutive clean weeks at the current rung** for that segment, with the ROI metrics on target: review time ≤ 3–4 hours, ≤ $0.10 per approved update, 0 trust incidents.
3. **Segment-specific evidence:**
   - **Me (PM owner):** ≤ 1 fact correction per run, stories slip (EV-2) in ≤ 1 of 4 runs.
   - **Covering / new PM:** has shadowed 4 of my runs with ≤ 1 correction each before moving to Supervised.
   - **Ed's and Trevor's teams:** story acceptance ≥ 70% for 2 sprints in a row, per team.
   - **Stakeholder / SME:** stays Assisted; they confirm scope, so there's nothing to automate away.

**Demotion trigger:** any single trust incident (leak, stated date, hollow DONE, write outside approval) drops that segment back one rung **immediately** and restarts its 4-week count. Two ESCALATE/STUCK exits for the same reason in a row aren't incidents, but they pause promotion until the cause is fixed.

**Never widened by this rule:** posting company-wide updates and committing dates stay human-only for every segment (the M1 agent line).

## Governance & forward strategy

- **Compliance:**
  - **Never enters a prompt:** emails and Teams chats; another project's data (per-project read tokens make this structural); API keys and secrets.
  - **Confidential projects:** counted in "Context used / excluded", never named (Orbit and Pulsar in testing).
  - **PII:** memory stores references (meeting ID, doc link), not raw transcripts or documents; the PM curates what gets uploaded; real data never goes into `evidence/` or git.
  - **Retention:** the raw activity pull and draft notes are purged after each run; remembered feedback expires (M4 TTLs).
- **Safety:**
  - **Above the agent line for everyone:** posting company-wide updates, committing release dates, final prioritization.
  - Cortex has no post/merge/edit tool. Backlog writes happen only through a single-use token after approval.
  - **Kill switch:** soft = halt flag (any PM); hard = revoke keys/tokens + disable the schedule (me, Ed, or Trevor).
- **Reliability:**
  - **Caps:** 8 iterations · 2 critic revisions · 90 s/run, 40 s/call · $0.50/run · $1/day · churn alert at 3× median.
  - Budget caps end as **ESCALATE**; infrastructure failures as **STUCK**. Both hold the draft and notify.
  - **Model down:** retry once an hour until the deadline (Monday's VP sync for status, Tuesday for stories), then STUCK + notify; I write that week's update manually. The model version is pinned, and there's no failover provider (it would need its own eval pass).
- **Strategy: real connectors next, Azure DevOps first,** for Ed's and Trevor's teams. That's where the register says the most likely failure lives: tool misuse such as misleading ADO data or missing tags.
  - **Gated by:** EV-8 (oversized sources) passing, scoped per-project tokens built, then the 4-week shadow on real data from the Trust Ladder gate.
  - Every new failure seen in real ADO data becomes a replay case.
