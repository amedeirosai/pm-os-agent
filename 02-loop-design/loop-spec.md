# Loop Spec: Cortex PM Chief-of-Staff Agent

> Module 2 · Loop Engineering, ★ Deliverable 2
>
> ✅ **What this validates:** the agent knows when to run and when to stop, by the end you'll have proven a one-page Loop Spec with a trigger, a definition of "done," and explicit stop conditions.
>
> Your one-page blueprint for how the work you handed to the agent (M1) actually *runs*.
> An agent is just a prompt that fires itself, this spec says when it fires, what "done" means, and what it needs to do the job. Living document; refine as the course progresses.

## 1. Trigger & loop type

**Chosen type:** cron (primary, two schedules) + hook (manual backup)

- **Weekly cron**, Monday morning before the VP sync → assemble the leadership status update.
- **Biweekly cron**, Tuesday morning, the day before sprint planning → propose the next sprint's stories (capped).
- **Manual hook** → an ad-hoc update on demand.

**Why:** each job runs on the rhythm the work actually follows: weekly leadership comms, biweekly sprints. The manual trigger covers anything in between.

**Ruled out:**
- **Heartbeat:** overkill for this process, wasted budget.
- **Goal:** not always applicable and more complex to define. Cortex's real finish line is a human's approval at the HITL checkpoint, which it can't loop its way to on its own.

**Dedupe:** one draft per project per period (e.g. `P-NORTH / status / 2026-W42`, `P-NORTH / stories / Sprint 25`). A repeat trigger in the same period points to the existing draft instead of creating a second one. A manual run can deliberately replace it.

## 2. Goal / definition of done

Two jobs, each with its own finish line. Cortex never updates the backlog or posts anything in this first version.

- **Status run (weekly):** a leadership status update, grounded in the pulled activity, is drafted, passes the critic, and is held at the HITL checkpoint. Nothing is posted.
- **Stories run (biweekly):** up to 10 stories with a *proposed* ranking are queued for approval. Nothing is created in the backlog; a human approves the ranking (M1: prioritization is HITL required).

## 3. Stop conditions

| Condition | What it looks like (detectable) | What happens |
|---|---|---|
| **Success** | All of: critic returns `"verdict": "pass"`; draft saved to `run-output/`; for the stories run, `propose_stories` returned `queued_for_approval` with ≤ 10 items. | Stop at the HITL checkpoint. Draft + stories held for human review; nothing posted. |
| **Stuck / give up** | Any of: a required data pull (project/activity) fails 3 times in a row · required data is missing or empty · critic rejects twice (revision cap) · 8 iterations or $0.50 spent without success. | Stop, log the reason, hold the last draft, and **always notify the human**. |
| **Escalate to human** | Any of: a security vulnerability in the pulled data · confidential or cross-project content would enter the draft · a sev-1 issue or `launch_hold` flag · the draft states a release date or ship commitment · the story batch exceeds the cap of 10 · a jailbreak attempt (task tries to make Cortex post, commit, or ignore its rules). | Stop, hold the draft, notify the human with the reason. Ties to M1 HITL checkpoints: actions 1, 5, 6→7, 8, 9. |

## 4. State

**Scope: per-project.** Each project's state lives in its own space. A run for one project can only read that project's state, plus the shared team norms and the *shareable* parts of the roadmap. This enforces the cross-project guardrail from M1 (action 1) structurally, not just by instruction.

- **Persists across runs:** roadmap, team norms, decision log, past updates, and human decisions/feedback from previous HITL checkpoints (e.g. items marked as noise).
- **Loop bookkeeping:** dedupe keys (e.g. `P-NORTH / status / 2026-W42`) and a run log (what fired, which stop condition ended the run, and why), which feeds the human notification on stuck/escalate.
- **Purged after each run:** the raw activity pull and draft working notes.
- **Later:** a human-curated shared layer where I can deliberately add cross-project items (e.g. a dependency between two teams). How remembered feedback expires is decided in M4.

## 5. The five things a loop can lean on

_`state` is always-on. `connectors` only if you already have one wired (e.g. a Jira key or Google MCP), otherwise just note it as a plan. `skills`, `subagents`, `work tree` scale with autonomy; "not needed yet, because…" is a valid answer._

| Component | For Cortex |
|---|---|
| **Work tree** (isolated workspace per run, a git worktree) | Not needed yet, because Cortex doesn't edit code or files beyond saving its draft to `run-output/`. |
| **Skills** (reusable capabilities) | Not needed yet, because Cortex has one recipe per job. Later candidate: a reusable "status update in our team's format" skill shared across projects. |
| **Plugins / connectors** (tools & access, optional if you don't have one yet) | **Planned:** Azure DevOps or Jira (backlog/board), SharePoint, Teams (meeting transcripts), Outlook, intranet/roadmaps/announcements, Miro. **Today:** simulated fixture data in `00-build/fixtures/` stands in for them. |
| **Subagents** (independent check when the loop can't grade itself) | The critic already acts as one: an independent model call validates each draft, so Cortex never grades itself. Full design in M3 `orchestration-map.md`. |
| **State tracking** | Per-project state (see §4): persisted reference data + human feedback, dedupe keys, run log. |

> Context plan (M4) and the hand-off to bounds & evals (M5) come in later modules, you'll add them to their own deliverables then, not here.

## Link to live loop

[`00-build/agent.py`](../00-build/agent.py)
