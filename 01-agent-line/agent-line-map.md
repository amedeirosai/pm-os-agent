# Agent Line Map: Cortex PM Chief-of-Staff Agent

> Module 1 · The Agent Line
>
> ✅ **What this validates:** every risky action has a clear owner, by the end you'll have proven an above/below-the-line map with HITL checkpoints, scored on reversibility, blast radius, and measurability.

## The workflow, decision by decision

List every discrete decision or action in your agent's workflow, then score each one and place it **above** the line (a human owns it) or **below** (the agent owns it). Borderline calls get an HITL checkpoint.

| Decision / action | Reversibility (H/M/L) | Blast radius (H/M/L) | Measurability (H/M/L) | Above / Below | HITL? |
|---|---|---|---|---|---|
| Pull project state + activity | H | M | H | Below | spot-check |
| Decide relevant context | H | M | L | Above | required |
| Prioritize by customer value / criticality | M | M | L | Above | required |
| Draft the update | H | L | H | Below | spot-check |
| Decide tone/commitment level | L | H | M | Above | required + hard rule: no dates from Cortex |
| Flag at-risk/escalation | H | M | M | Below | spot-check + rule-based safety net |
| Choose what to escalate | L | H | M | Above | required |
| Propose a story batch (capped) | H | L | H | Below | spot-check |
| Post an update / approve a company-wide one | L | H | M | Above | human only (no publish tool for Cortex) |

## Agent anatomy (sketch)

- **Model:** `gpt-4o-mini` by default (cheap, fast, ~$0.02 per run). Escalate to a frontier model on hard judgment calls: when the update has escalation flags, a Red/Yellow status, or a critic rejection, the moments where a human checkpoint needs the best possible proposal.
- **Tools:** read-only lookups (`get_project`, `get_activity`, `search_past_updates`, `get_roadmap`, `get_norms`) plus `propose_stories` (queues stories for human approval, creates nothing, capped). **No publish tool**, by design.
- **Memory:** *Persist:* roadmap, team norms, decision log, past updates, and human decisions/feedback from previous checkpoints (e.g. items marked as noise). *Purge after each run:* the raw activity pull and draft working notes. Open question for M4: how remembered feedback expires so it doesn't go stale.
- **Loop:** _placeholder, defined in M2 loop-spec.md_
- **Bounds:** _placeholder, defined in M5 bounds-and-evals.md_
- **Evals:** _placeholder, defined in M5 bounds-and-evals.md_

## The golden rule, applied

1. **Pull project state + activity** sits **below** the line because it's easy to reverse (read-only), has a medium blast radius (cross-project leak risk), and is easy to verify. Deciding factor: **reversibility**, nothing is changed, and a spot-check costs little.
2. **Decide relevant context** sits **above** the line because it's easy to reverse, has a medium blast radius, and is hard to verify. Deciding factor: **measurability**, activity ≠ importance or value, and a human sees signals the data doesn't.
3. **Prioritize by customer value / criticality** sits **above** the line because it's moderately hard to reverse once the team starts building, has a medium blast radius, and is hard to verify. Deciding factor: **measurability**, whether the priorities were right only shows weeks later, so a human validates what gets built next.
4. **Draft the update** sits **below** the line because it's easy to reverse, has a low blast radius, and is easy to verify. Deciding factor: **blast radius**, it's a draft only and nothing leaves the building.
5. **Decide tone/commitment level** sits **above** the line because it's hard to reverse, has a high blast radius, and is only partly verifiable. Deciding factor: **blast radius**, a wrong call has high impact, and Cortex never decides release dates on its own.
6. **Flag at-risk/escalation** sits **below** the line because it's easy to reverse, has a medium blast radius, and is only partly verifiable. Deciding factor: **measurability**, missed flags are hard to see, so a rule-based safety net is more likely to catch them than human review, with a spot-check on top.
7. **Choose what to escalate** sits **above** the line because it's hard to reverse, has a high blast radius, and is only verifiable in hindsight. Deciding factor: **reversibility**, it's harder to fix if we make the wrong choice.
8. **Propose a story batch (capped)** sits **below** the line because it's easy to reverse, has a low blast radius, and is easy to verify. Deciding factor: **measurability**, the context and priorities feeding it are already human-validated, so I know what to expect and can check each story against them.
9. **Post an update / approve a company-wide one** sits **above** the line because it's hard to reverse, has a high blast radius, and is only verifiable after the damage is done. Deciding factor: **blast radius**, bad content can harm the product, company and brand, so Cortex never gets a publish tool (at least not until it's heavily evaluated).

## Hardest call

**Propose a story batch (capped): below the line, spot-check only.** My instinct was to make it HITL required. But once I moved *decide relevant context* and *prioritize by customer value* above the line, the story batch stopped being a decision for the human and became an **outcome** of decisions the human had already made. That contradicts what I would have thought before this exercise. Deciding axis: **measurability**, reversibility helps too, but because I've already validated the context and priorities, I know what to expect from the outcome and can check each story against them. Lesson: put humans on the decisions that shape the work, and the work itself can be automated.
