# Context Engineering & Memory: Cortex PM Chief-of-Staff Agent

> Module 4 · Context Engineering & Memory
>
> ✅ **What this validates:** the agent reasons on the right, safe inputs, by the end you'll have proven a context budget, per-source retrieve-vs-long-context decisions, and a memory map with risk mitigations.
>
> 🗂️ **How the lab maps to this file:** In **Part A** (before the lecture) you don't edit this file, you rough-draft on scratch, focused on the per-source calls in **section 2** plus a quick remember/forget + "how it rots" sketch. In **Part B** (after the lecture) you complete **all five sections**; the Lab Guide's guided builder writes this file for you to copy in and commit.

## 1. Context budget

Each loop iteration receives Cortex's system prompt plus what its tools return for **one project**:

- The task brief (whole) and the team norms (whole)
- The project record (`get_project`) and this week's activity for that project (`get_activity`)
- The roadmap section for that project only (`get_roadmap`)
- Recent past updates and decisions for that project (`search_past_updates`)

**Priority order** (if context must shrink, e.g. once real connectors bring in transcripts, cut from the bottom):

1. **Task brief + team norms:** the ask, and the rules Cortex is judged by. Never cut.
2. **Project record + this week's activity:** the facts every claim must trace to. Without them, the draft goes hollow (placeholders, stale numbers, re-proposed shipped work).
3. **Roadmap section:** direction and scope for stories, plus citable lines.
4. **Past updates:** tone and precedent only. Dropped first, since a draft without them is less polished but not wrong.

## 2. Retrieve vs. long-context: per source

For each data source, decide: **retrieve** (narrow a large/changing corpus to the relevant slice) or **long-context** (just include a bounded set you can reason over).

| Source | Size / volatility | Decision | Why (deciding factor) |
|---|---|---|---|
| **Engineering activity** (`get_activity`) | Small per week in the fixtures, large in real Azure DevOps/Jira; changes constantly | **Retrieve** (this project, this week) | **Volatility:** a live feed that has to be pulled fresh on every run, because last week's copy is already wrong. |
| **Past updates + decision log** (`search_past_updates`) | Grows every week, never shrinks; older entries go stale | **Retrieve** (recent, this project) | **Size** first: unbounded, so including all of it gets more expensive every week. **Volatility/staleness** second: old figures (e.g. "39%") become wrong. |
| **Roadmap** (`get_roadmap`) | Medium, slow-changing; contains CONFIDENTIAL items (Orbit, Pulsar) | **Retrieve** (requested project's section only) | **Citation / audit:** Cortex cites the specific roadmap line it relied on. Side effect: embargoed sections never enter the context. |
| **Team norms** (`get_norms`) | Small (~2 KB), changes rarely, must stay current | **Long-context** (whole document, read fresh every run) | **Size:** small and bounded, and every rule can apply to every run; retrieving a subset could miss the one rule needed. |
| **Task brief** (`get_task`) | One short document per run | **Long-context** (whole brief) | **Size:** short, bounded, and every line could be part of the ask. Note: it's **data, not instructions**, the one source users write freely, so injection attempts land here. |
| **Project record** (`get_project`) | One small record per project | **Retrieve** (keyed lookup by project ID) | **Citation / audit:** status, the `launch_hold` flag, and PRD scope must come from the exact record. |

## 3. Retrieval quality plan

Every **retrieve** source gets the moves its failure mode demands, so none is naive "fetch → stuff → hope". Long-context sources (team norms, task brief) are read whole and don't need them.

**What worries me most:** failures of information relevance (grading) and ignored flags, especially confidentiality. So **document grading is on every retrieved source**, and it runs *before* drafting.

**Lesson from the probe:** with activity withheld, Cortex took figures from the roadmap's narrative. Figures must come from activity only; narrative sources don't count as evidence for metrics. (The build now refuses to finish DONE without usable activity for the requested project → STUCK + notify.)

| Source | Failure mode | Routing | Grading | Reranking | Self-verification | Caching |
|---|---|---|---|---|---|---|
| **Engineering activity** | Empty/missing (the hollow draft), wrong project, last week's window | Later (once there are several systems: ADO / Jira / GitHub) | ✅ Non-empty, this project, this week; otherwise STUCK, not a hollow DONE | No (one project's week is small) | ✅ Every PR/issue ID and metric in the draft appears in what was retrieved (critic: `wrong_ids`, `untraceable_claim`) | ❌ **Explicitly no:** volatile, a cached copy is a stale copy |
| **Past updates + decision log** | Other projects returned, stale figures reused as current, too many results | Later (route date/launch questions to the decision log if the two split) | ✅ Keep this project + team-wide decisions only; drop the rest (closes the cross-project leak) | ✅ Most recent first, keep the top ~3 | ✅ Figures must come from this week's activity, never from a past update; past updates are for tone/precedent only | Optional (entries never change, but the file is tiny) |
| **Roadmap** (project section) | Confidential section slips through, wrong section (name vs ID), outdated roadmap | Folded into grading (ID → section) | ✅ Section matches the requested project; its label (SHAREABLE / INTERNAL / CONFIDENTIAL) fits the audience; CONFIDENTIAL → escalate, never draft | No (one section) | ✅ Critic `confidential_leak`; roadmap claims cite the section they came from | ✅ Yes, **invalidated on every new pull** (e.g. the pack that added Pulsar) |
| **Project record** | Project not found, flags ignored, status disagrees with the draft | No (one record by ID) | ✅ Missing → STUCK; `confidential` → stays out of company-wide updates; `launch_hold` → escalate the go/no-go, checked before drafting | No | ✅ Status color and scope match the flags and PRD (critic: `forbidden_commitment`, `story_off_prd`) | ❌ No: status and flags change mid-week (Vega's hold must never be served stale) |

## 4. Memory map (your PM brain)

**Rule:** Cortex never writes semantic or episodic memory itself; only humans do (by approving an update or ingesting a data pack). This keeps the M1 agent line intact for memory, not just actions.

| Memory type | What Cortex stores | Who can write it | Scope / TTL |
|---|---|---|---|
| **Working** (in-loop) | Pulled data, drafts, critic reasons, revision count | Cortex + loop | **This run.** Purged at run end; only the saved draft and run-log lines survive. |
| **Episodic** (past runs) | Approved past updates; the run log (stops, rejections, cost); human feedback from HITL checkpoints (e.g. "mark #825 as noise") | Humans approve updates; the loop writes the run log | Per project. Past updates: kept, but only the latest ~3 retrieved. Run log: ~90 days. **Feedback: expires on whichever comes first: new activity on the item, or 2 sprints**, so it keeps an expiration date on items with no activity and refreshes immediately the ones that have. |
| **Semantic** (durable facts/prefs) | Team norms, roadmap, decision log, project records | **Humans only, via ingest** | Until replaced by the next pull. The files are the source of truth; no separate copy to go stale. |
| **Shared** (across agents) | This run's source data + draft, shared by Cortex and the critic | Cortex writes; the critic **only reads** | This run only. The critic never writes to memory (M3 state split). |

**Not stored at all:** emails and Teams chat history. Meeting transcripts and SharePoint documents are stored as **references (links) only**, never raw copies. The PM decides whether a document is relevant and safe for Cortex, and adds it to the repo deliberately.

## 5. Memory risks & mitigations

**Most likely to bite first:** cross-project contamination, once all the real tools are plugged in.

| Risk | Where it bites Cortex | Mitigation |
|---|---|---|
| **Drift** | Approved updates become next week's tone precedent; if slightly-off drafts keep getting approved, the house style drifts. A model update can shift behavior overnight. | Retrieve only the latest ~3 human-approved updates; the critic judges against the **norms**, not past updates; a fixed eval set re-run on the same fixtures catches drift (M5); pin the model version. |
| **Poisoning** | Untrusted text treated as instructions or fact: an injection in the task brief, a PR title like "ignore your rules", or a bad data pack. | Cortex never writes semantic/episodic memory, only humans do; brief and data content is data, not instructions; new data packs are inspected before ingest. |
| **Staleness** | Old figures reused as current (the "39%" demo), a cached roadmap missing Pulsar, a noise mark hiding an item that changed. | Activity never cached; roadmap cache invalidated on every pull; figures only from this week's activity; feedback expires on new activity or after 2 sprints. |
| **Confidential / PII / retention** | Orbit/Pulsar leaking into a company-wide draft; real names and meeting content once Teams/Outlook/SharePoint are connected; traces committed to git. | Per-project scope and roadmap-section retrieval; `confidential` flags checked before drafting + critic `confidential_leak`; working memory purged each run; run log ~90 days; transcripts and SharePoint docs stored as links only; no emails or Teams chats stored; the PM curates what enters the repo; real data never goes into `evidence/` or git. |

> TTLs (run log ~90 days, feedback 2 sprints) become enforceable bounds in M5.
