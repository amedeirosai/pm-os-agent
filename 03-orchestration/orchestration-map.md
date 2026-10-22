# Orchestration Map: Cortex PM Chief-of-Staff Agent

> Module 3 · Orchestration & Subagents, ★ Deliverable 3
>
> ✅ **What this validates:** nothing advances unchecked, by the end you'll have proven a justified topology, a roster, and a validator with a defined fail action.
>
> Builds on your M2 Loop Spec. Only split one agent into a team when there's a real reason, coordination has a cost.

## 1. Why split? (or why not)

**Cortex today:** a single agent, fired by a weekly and a biweekly cron plus a manual trigger, that pulls per-project data, drafts the status update and a proposed story ranking, and stops at the human review checkpoint with nothing posted.

**Decision: split exactly once, for an independent validator.** Everything else stays single-agent.

| Reason | Applies? | Why / why not |
|---|---|---|
| Separation of concerns | No | Both jobs use the same data and the same loop, and nothing would contaminate anything if one agent does both. |
| Parallelism | No | There's no time pressure that running agents side by side would relieve. |
| Independent validator | **Yes** | Cortex can't grade its own draft. Something outside the drafter has to check its claims. A human alone may have low capacity for a full check. |
| Context-window pressure | Not yet | Once we add connectors to the real tools, we'll be able to assess the risk of context overflow. If that happens, we could add a reader subagent later. |

## 2. Topology

**Pattern:** single agent + one subagent (the critic)

```
[Trigger: weekly/biweekly cron or manual]
   → [Cortex: pulls per-project data, drafts update + proposed stories]
        ├─ STUCK / ESCALATE ─────────────────────────────→ [Human: notified, draft held]
        └─ DONE → [Critic: checks A–E]
                    ├─ fail A/B/E → back to Cortex with reasons (max 2 revisions) → then STUCK → [Human]
                    ├─ fail C/D  → ESCALATE immediately ────────────────────────→ [Human]
                    └─ pass      → [PM review checkpoint] → held / queued, nothing posted
```

## 3. Roster

| Agent / subagent | Responsibility | Runs which Loop Spec |
|---|---|---|
| **Cortex** (chief of staff) | Pulls per-project data, drafts the status update and the proposed story ranking, decides DONE / STUCK / ESCALATE | The M2 loop (crons + manual hook) |
| **Critic** (validator) | Checks every DONE draft against checks A–E and returns pass/fail with reasons | No loop of its own: one call per draft, run inside Cortex's loop |

*Not agents:* the loop's code checks from M2 (stories actually queued, the queue cap, 3 failed pulls). They're plain code, not model calls.

## 4. Communication & hand-offs

Plain in-process Python function calls. No MCP or A2A.

- **Cortex → Critic:** the draft text + the source data (the raw tool results).
- **Critic → loop:** a JSON verdict, `{"verdict": "pass"|"fail", "reasons": [...]}`.
- **Loop → Cortex** (on revise): the critic's reasons, as a new message.
- **Loop → Human:** the saved draft in `run-output/`, plus a notification on STUCK or ESCALATE.

## 5. The validator

An independent critic (separate model call, own context; never sees Cortex's drafting conversation) checks every DONE draft before it reaches the PM. STUCK/ESCALATE outputs skip it and go straight to the human (M2).

- **What the critic checks** (all checkable against the pulled source data; chosen because they're easily and fast checkable):
  - **`wrong_ids`:** the update names the right project, and every PR/issue ID it cites exists in the pulled activity.
  - **`untraceable_claim`:** metrics, progress, and the status color all come from the pulled data; no invented numbers.
  - **`forbidden_commitment`:** no release date, ship commitment, launch gate, or "posted/sent" claim; status color matches the evidence (a sev-1 or `launch_hold` can't be reported Green).
  - **`confidential_leak`:** nothing marked CONFIDENTIAL, nothing from another project.
  - **`story_off_prd`:** each proposed story maps to an in-scope PRD item, they're in ranked order, and none is described as created in the backlog.
  - *Not checked:* tone/house style; that's too fuzzy for a gate and is left to the human spot-check.
- **Precision rule:** the critic flags a code only when it can quote the offending text from the draft (one problem, one code). Without it, the small model over-flagged an invented metric as a `forbidden_commitment` and escalated a fixable mistake.
- **Fail action (tiered):**
  - **`wrong_ids`, `untraceable_claim`, `story_off_prd` → revise.** These are drafting mistakes Cortex can usually fix with the critic's reasons.
  - **`forbidden_commitment`, `confidential_leak` → escalate immediately.** These go straight to a human.
  - Every failure is also **logged** to the run log.
- **Revision cap:** max **2** revisions, then **stuck + notify the human** (matches the M2 loop spec and `CORTEX_MAX_REVISIONS=2`). A single revision fixed the stories problem in M2, so two gives some margin.
- **Pass action:** the draft advances to the **PM review checkpoint** and is held there, never sent automatically (M1 action 9: no publish tool).

## 6. State: shared vs isolated

The critic sees just enough to do its job without getting biased.

- **Shared:** the per-project source data (raw tool results) and the draft. Both stay scoped to one project, following the M2 per-project state; no cross-project data enters either agent.
- **Isolated:**
  - The **critic never sees Cortex's conversation or instructions**: it gets the draft + source data in a fresh model call, so it doesn't inherit Cortex's blind spots.
  - **Cortex never sees the critic's reasoning**, only its conclusions (the `reasons` list) when a draft is sent back for revision.
- **Loop bookkeeping** (run log, dedupe keys, notifications) belongs to the loop, not to either agent.

## 7. Cost & latency budget

Measured on the simulated fixture data (gpt-4o-mini):

| Run | Model calls | Cost | Wall time |
|---|---|---|---|
| Clean, critic passes first time | ~3 Cortex + 1 critic | ~$0.02 | ~10–15 s |
| One revision | ~4–5 Cortex + 2 critic | ~$0.045–0.05 | ~20 s |
| Worst case at the revision cap (2 revisions → stuck) | ~5–6 Cortex + 3 critic | ~$0.07 (est.) | ~30 s |

- **What the validator adds:** 1 extra model call per draft (~3–5 s), costing about as much as one Cortex drafting call. Each revision adds one Cortex call + one critic call, more than doubling a clean run.
- **Latency:** irrelevant for a cron job nobody waits on; a draft reaches the PM within ~30 s even in the worst case.
- **Bound carried to M5:**
  - **Hard cap (unchanged):** $0.50 per run → stop, hold the draft, notify (stuck exit).
  - **Soft "churn alert":** flag a run that costs more than **3× the median of recent runs**, logged to the run log + notify, without stopping it. Until there are 5 runs of history (e.g. after adding a connector), fall back to a fixed **$0.10**. A relative rule stays meaningful once real connectors make normal runs bigger.
  - Repeated alerts + the logged rejection codes show *which* check keeps failing; that's a prompt fix, not just a cost problem.
