"""Cortex, a minimal, explicit agent loop you (and your coding agent) can read end
to end. This is the agent you ship: your PM chief-of-staff. You build it by
directing your coding agent (Claude Code / Cursor / Codex) to shape this file. You
never have to hand-write it.

Every bound the course talks about is visible right here in code, not buried in a
framework: the max-iteration counter, the cost cap, the revision cap, the
stop/escalate conditions, the auto-queue cap, and the absence of any publish tool.

Usage (ask your coding agent to run these for you, or run them yourself):
    python agent.py                # runs the happy-path task (weekly status update)
    python agent.py missing-data   # the stuck/escalate case
    python agent.py jailbreak       # the prompt-injection refusal case

Every run ends by showing the drafted status update in a FINAL STATUS UPDATE block
(or LAST DRAFT, held, if a bound trips), and saves it to run-output/. That file is
always a draft held for a human, it is never posted, there is no publish tool.

Requires OPENAI_API_KEY in your environment (see .env.example). Model and bounds
are read from env so you can tune them, that tuning is your M5 deliverable.

The loop is deliberately transparent (hand-written tool-calling on the openai
client) so a grader can see the machinery. Keep the bounds explicit if you rework it.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from openai import APITimeoutError, BadRequestError, OpenAI

import tools
from critic import review
from prompts import CORTEX_SYSTEM

try:  # load .env if python-dotenv is installed; harmless if it isn't
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Print UTF-8 everywhere: the Windows console defaults to cp1252, which crashes on
# characters like "≈" in the trace. A no-op on macOS/Linux.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

# --- Bounds (your M5 deliverable: tune these and justify them) ----------------
MODEL = os.environ.get("CORTEX_MODEL", "gpt-4o-mini")
MAX_ITERATIONS = int(os.environ.get("CORTEX_MAX_ITERATIONS", "8"))
MAX_REVISIONS = int(os.environ.get("CORTEX_MAX_REVISIONS", "2"))
COST_CAP_USD = float(os.environ.get("CORTEX_COST_CAP_USD", "0.50"))
MAX_QUEUE_ITEMS = int(os.environ.get("CORTEX_MAX_QUEUE_ITEMS", "10"))
# Rough $ per 1M tokens for your chosen model, set to match its pricing.
PRICE_IN = float(os.environ.get("CORTEX_PRICE_IN_PER_M", "0.15"))
PRICE_OUT = float(os.environ.get("CORTEX_PRICE_OUT_PER_M", "0.60"))
# M5 bounds: timeout per run / per model call, daily spend cap, churn alert.
RUN_TIMEOUT_S = float(os.environ.get("CORTEX_RUN_TIMEOUT_S", "90"))
CALL_TIMEOUT_S = float(os.environ.get("CORTEX_CALL_TIMEOUT_S", "40"))
DAILY_CAP_USD = float(os.environ.get("CORTEX_DAILY_CAP_USD", "1.00"))
CHURN_MULTIPLIER = float(os.environ.get("CORTEX_CHURN_MULTIPLIER", "3"))  # alert at > 3x median
CHURN_MIN_HISTORY = 5       # ...once there are this many runs; until then:
CHURN_FALLBACK_USD = 0.10
# M5 kill switch (soft layer): this file, or CORTEX_HALT=1, stops new and running loops.
HALT_FILE = Path(__file__).parent / "CORTEX_HALT"
# M5 context budget: estimated tokens sent per model call, and a size cap on any one
# tool result so a single huge document can't take over. Priority trimming (M4 order)
# is planned; today an over-budget call stops the run instead of crashing it.
CONTEXT_BUDGET_TOKENS = int(os.environ.get("CORTEX_CONTEXT_BUDGET_TOKENS", "32000"))
MAX_TOOL_RESULT_CHARS = int(os.environ.get("CORTEX_MAX_TOOL_RESULT_CHARS", "24000"))
# Loop Spec §3 stuck exit: a required pull failing this many times in a row = a tools problem.
MAX_PULL_FAILURES = 3
REQUIRED_PULLS = {"get_project", "get_activity"}
# Orchestration Map §5 tiered fail-action: these critic failures escalate at once;
# any other failed check (wrong_ids, untraceable_claim, story_off_prd) is revised.
ESCALATE_CHECKS = {"forbidden_commitment", "confidential_leak"}

# TEST ONLY (M3): CORTEX_SABOTAGE=metric|date injects one bad line into Cortex's
# first draft so we can prove the critic catches it. Never set this in a real run.
SABOTAGE = os.environ.get("CORTEX_SABOTAGE", "").strip().lower()
SABOTAGE_LINES = {
    "metric": "- Activation rate jumped to 58% this week, beating the quarterly target.",
    "date": "- Northstar GA is confirmed for 2026-11-15; we will announce it company-wide.",
}
# TEST ONLY (M4 grounding probe): CORTEX_WITHHOLD=get_activity hides that tool from
# Cortex for one run ("brain off"), without editing the tool lists. Comma-separated.
WITHHOLD = {t.strip() for t in os.environ.get("CORTEX_WITHHOLD", "").split(",") if t.strip()}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_project", "description": "Look up a project by its ID (status, flags, linked PRD).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {
        "name": "get_activity",
        "description": "Pull recent engineering activity for a project (merged PRs, open issues, Sev-1s).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {
        "name": "search_past_updates",
        "description": "Search previous status updates and decisions for tone and precedent.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_roadmap",
        "description": "Return the roadmap. Some items are flagged confidential/embargoed.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_norms", "description": "Return the team norms / PM playbook the agent must follow.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "propose_stories",
        "description": ("Queue a set of backlog stories for human approval (creates nothing; "
                        "rejected above the item cap, or if a story doesn't name the in-scope "
                        "PRD item it delivers)."),
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"},
            "stories": {"type": "array", "items": {
                "type": "object", "properties": {
                    "story": {"type": "string"},
                    "prd_item": {"type": "string",
                                 "description": "The in-scope PRD item this story delivers."}},
                "required": ["story", "prd_item"]}},
            "reason": {"type": "string"}}, "required": ["project_id", "stories"]}}},
]


class Bounds:
    """Tracks spend and trips the cost cap. This is enforced OUTSIDE the model."""

    def __init__(self):
        self.cost = 0.0

    def add(self, usage) -> None:
        self.cost += (usage.prompt_tokens * PRICE_IN
                      + usage.completion_tokens * PRICE_OUT) / 1_000_000

    def over_cap(self) -> bool:
        return self.cost >= COST_CAP_USD


OUTPUT_DIR = Path(__file__).parent / "run-output"


def banner(text: str) -> None:
    print(f"\n{'=' * 64}\n{text}\n{'=' * 64}")


def emit_deliverable(which: str, draft: str, *, accepted: bool,
                     reason: str, cost: float) -> None:
    """Surface AND persist Cortex's drafted status update so it can't get lost in
    the scroll-back. This is still a DRAFT held for human review, never a post,
    there is no publish tool, and an escalated run is held on purpose.

    Runs on every exit: an accepted pass prints the FINAL update; a bound trip or
    escalation prints the LAST draft it managed to write plus why it was held.
    """
    banner("FINAL STATUS UPDATE (draft, validator-approved, NOT posted)" if accepted
           else "LAST DRAFT (held, NOT posted, escalated to a human)")
    if draft.strip():
        print(draft.rstrip())
    else:
        print("(Cortex stopped before it produced a draft, nothing to show.)")
    if not accepted:
        print(f"\nWhy it was held: {reason}")

    if draft.strip():
        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"status-update-{which}.md"
        state = "accepted by validator" if accepted else "HELD, escalated"
        out.write_text(
            f"<!-- Cortex draft, {state}; NOT posted. Run cost ~ ${cost:.4f}. -->\n"
            f"<!-- {reason} -->\n\n{draft.rstrip()}\n", encoding="utf-8")
        print(f"\nSaved draft -> {out.relative_to(Path(__file__).parent)}  "
              f"(for your review, nothing was posted)")


def strip_marker(text: str) -> str:
    """Drop the DONE:/STUCK:/ESCALATE: marker so it doesn't end up in the saved draft."""
    return re.sub(r"^\s*(DONE|STUCK|ESCALATE):\s*", "", text, count=1)


def log_event(which: str, **fields) -> dict:
    """Append one line to run-output/run-log.jsonl and return it."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "task": which, **fields}
    with open(OUTPUT_DIR / "run-log.jsonl", "a", encoding="utf-8") as log:
        log.write(json.dumps(entry) + "\n")
    return entry


def past_runs() -> list[dict]:
    """Every finished run in the run log (entries that recorded how a run stopped)."""
    path = OUTPUT_DIR / "run-log.jsonl"
    if not path.exists():
        return []
    runs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "stop" in entry and "cost_usd" in entry:
            runs.append(entry)
    return runs


def spent_today() -> float:
    """Daily cap: total spend of today's finished runs (UTC), from the run log."""
    today = datetime.now(timezone.utc).date().isoformat()
    return sum(r["cost_usd"] for r in past_runs() if r["time"].startswith(today))


def halt_requested() -> bool:
    """Kill switch (soft layer): a CORTEX_HALT file next to agent.py, or CORTEX_HALT=1."""
    return HALT_FILE.exists() or os.environ.get("CORTEX_HALT", "") not in ("", "0")


def notify(which: str, kind: str, reason: str) -> None:
    """Simulated notification: stands in for Teams/Outlook until a connector is wired."""
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(OUTPUT_DIR / "notifications.log", "a", encoding="utf-8") as inbox:
        inbox.write(f"[{stamp}] {kind.upper()} task-{which}: {reason}\n")
    banner(f"NOTIFY HUMAN ({kind.upper()}): {reason}\n"
           f"(simulated, written to run-output/notifications.log)")


def finish(which: str, kind: str, draft: str, reason: str, cost: float) -> None:
    """Every run ends here with one of the Loop Spec exits: success (held at HITL),
    stuck (give up), escalate (a human must decide), or halted (kill switch).
    Each exit is written to the run log; anything but success also notifies the human."""
    emit_deliverable(which, strip_marker(draft), accepted=(kind == "success"),
                     reason=reason, cost=cost)

    history = [r["cost_usd"] for r in past_runs()[-20:] if r["cost_usd"] > 0]
    log_event(which, stop=kind, reason=reason, cost_usd=round(cost, 4))

    if kind != "success":
        notify(which, kind, reason)

    # Churn alert (soft): flag an unusually expensive run, don't stop it.
    if len(history) >= CHURN_MIN_HISTORY:
        threshold = CHURN_MULTIPLIER * statistics.median(history)
        basis = f"{CHURN_MULTIPLIER}x the median of the last {len(history)} runs"
    else:
        threshold, basis = CHURN_FALLBACK_USD, "the fallback (not enough run history yet)"
    if cost > threshold:
        reason = f"run cost ${cost:.4f} exceeds ${threshold:.4f} ({basis})"
        log_event(which, event="cost_alert", reason=reason, cost_usd=round(cost, 4))
        notify(which, "cost alert", reason)


def run(which: str = "happy") -> None:
    client = OpenAI(timeout=CALL_TIMEOUT_S, max_retries=1)
    bounds = Bounds()
    started = time.monotonic()
    task = tools.get_task(which)
    if "error" in task:
        print(task)
        return

    banner(f"CORTEX RUN, fixture: task-{which}  (auto-queue cap {MAX_QUEUE_ITEMS} items)")
    print(task["body"])

    # Refuse to start at all when the kill switch is on or today's budget is spent.
    if halt_requested():
        banner("KILL SWITCH ON, refusing to start.")
        finish(which, "halted", "", "kill switch on (CORTEX_HALT); run not started", 0.0)
        return
    already_spent = spent_today()
    if already_spent >= DAILY_CAP_USD:
        reason = f"daily cap ${DAILY_CAP_USD:.2f} reached (${already_spent:.4f} spent today)"
        banner(f"DAILY CAP, {reason}. Refusing to start.")
        finish(which, "stuck", "", reason, 0.0)
        return

    messages = [
        {"role": "system", "content": CORTEX_SYSTEM},
        {"role": "user", "content": f"PM task brief:\n\n{task['body']}"},
    ]
    source_log: list[str] = [task["body"]]
    revisions = 0
    last_draft = ""
    pull_failures = 0       # consecutive failed required pulls (stuck exit)
    stories_result = None   # latest propose_stories result (success check)
    requested_project = None    # project ID from get_project
    activity_projects = set()   # projects whose get_activity returned real data
    active_schemas = [s for s in TOOL_SCHEMAS if s["function"]["name"] not in WITHHOLD]
    if WITHHOLD:
        banner(f"WITHHELD (test only): {', '.join(sorted(WITHHOLD))} hidden from Cortex")
    sabotaged = False  # TEST ONLY: the sabotage line is injected once per run
    wants_stories = bool(re.search(r"\bstor(y|ies)\b", task["body"], re.IGNORECASE))

    for step in range(1, MAX_ITERATIONS + 1):
        if halt_requested():
            # Rollback: queued stories are only proposals held in this run; drop them.
            dropped = stories_result.get("count", 0) if stories_result else 0
            reason = (f"kill switch on (CORTEX_HALT) at step {step}; "
                      f"{dropped} unapproved queued stories discarded")
            banner(f"KILL SWITCH, {reason}.")
            finish(which, "halted", last_draft, reason, bounds.cost)
            return
        elapsed = time.monotonic() - started
        if elapsed > RUN_TIMEOUT_S:
            reason = f"run timeout {RUN_TIMEOUT_S:g}s hit after {elapsed:.0f}s"
            banner(f"BOUND TRIPPED, {reason}. Halting.")
            finish(which, "stuck", last_draft, reason, bounds.cost)
            return
        if bounds.over_cap():
            reason = f"cost cap ${COST_CAP_USD} hit at ${bounds.cost:.4f}"
            banner(f"BOUND TRIPPED, {reason}. Halting and escalating to a human.")
            finish(which, "escalate", last_draft, reason, bounds.cost)
            return
        if already_spent + bounds.cost >= DAILY_CAP_USD:
            reason = (f"daily cap ${DAILY_CAP_USD:.2f} hit "
                      f"(${already_spent + bounds.cost:.4f} spent today)")
            banner(f"BOUND TRIPPED, {reason}. Halting.")
            finish(which, "stuck", last_draft, reason, bounds.cost)
            return
        # Rough estimate (~4 chars per token) of what this call would send.
        est_tokens = sum(len(json.dumps(m, default=str)) for m in messages) // 4
        if est_tokens > CONTEXT_BUDGET_TOKENS:
            reason = (f"context budget exceeded (~{est_tokens} tokens > "
                      f"{CONTEXT_BUDGET_TOKENS}); required sources too large")
            banner(f"BOUND TRIPPED, {reason}. Halting.")
            finish(which, "stuck", last_draft, reason, bounds.cost)
            return

        try:
            resp = client.chat.completions.create(
                model=MODEL, messages=messages, tools=active_schemas)
        except APITimeoutError:
            reason = f"model call timed out after {CALL_TIMEOUT_S:g}s"
            banner(f"BOUND TRIPPED, {reason}. Halting.")
            finish(which, "stuck", last_draft, reason, bounds.cost)
            return
        except BadRequestError as exc:  # backstop: the model's own context limit
            if "context" not in str(exc).lower():
                raise
            reason = "model rejected the call: context window exceeded"
            banner(f"BOUND TRIPPED, {reason}. Halting.")
            finish(which, "stuck", last_draft, reason, bounds.cost)
            return
        bounds.add(resp.usage)
        msg = resp.choices[0].message

        if msg.tool_calls:
            messages.append(msg)
            for call in msg.tool_calls:
                fn = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                    result = tools.TOOLS[fn](**args)
                except Exception as exc:  # a broken tool call is a failed pull, not a crash
                    args, result = {}, {"error": f"tool_failed: {exc}"}
                source_log.append(f"{fn}({args}) -> {json.dumps(result)}")
                print(f"\n[step {step}] TOOL {fn}({args})")
                print(f"          -> {json.dumps(result)[:300]}")
                content = json.dumps(result)
                if len(content) > MAX_TOOL_RESULT_CHARS:
                    omitted = len(content) - MAX_TOOL_RESULT_CHARS
                    content = (content[:MAX_TOOL_RESULT_CHARS]
                               + f" ...[TRUNCATED: {omitted} chars omitted by the size cap]")
                    print(f"          (result truncated by the size cap: {omitted} chars omitted)")
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": content})

                if fn in REQUIRED_PULLS:
                    pull_failures = pull_failures + 1 if "error" in result else 0
                if fn == "propose_stories":
                    stories_result = result
                if fn == "get_project" and "error" not in result:
                    requested_project = result.get("project_id")
                # A truncated activity pull is partial data, not usable activity (M4:
                # priority-2 sources are never cut), so it can't satisfy the grading check.
                if (fn == "get_activity" and "error" not in result and result.get("activity")
                        and len(json.dumps(result)) <= MAX_TOOL_RESULT_CHARS):
                    activity_projects.add(result.get("project_id"))

            if pull_failures >= MAX_PULL_FAILURES:
                reason = f"required data pull failed {pull_failures}x in a row"
                banner(f"STUCK, {reason}. Giving up instead of guessing.")
                finish(which, "stuck", last_draft, reason, bounds.cost)
                return
            if stories_result and stories_result.get("error") == "batch_exceeds_queue_cap":
                reason = (f"story batch of {stories_result['count']} exceeds the "
                          f"queue cap of {stories_result['cap_items']}")
                banner(f"ESCALATE, {reason}. A human decides the batch.")
                finish(which, "escalate", last_draft, reason, bounds.cost)
                return
            continue

        # No tool calls => Cortex produced a proposed output.
        proposed = msg.content or ""
        last_draft = proposed
        print(f"\n[step {step}] PROPOSED OUTPUT:\n{proposed}")

        # Cortex chose a non-success exit itself: hold it, no critic needed.
        exit_marker = re.search(r"^\s*(STUCK|ESCALATE):\s*(.*)", proposed, re.MULTILINE)
        if exit_marker:
            kind = exit_marker.group(1).lower()
            reason = exit_marker.group(2).strip() or f"Cortex chose {kind.upper()}"
            banner(f"{kind.upper()}, Cortex stopped and handed off to a human.")
            finish(which, kind, proposed, reason, bounds.cost)
            return

        # Memory & Context §3 activity grading: no DONE without this week's activity
        # for the requested project. A draft without it is hollow, not done.
        if not activity_projects or (requested_project
                                     and requested_project not in activity_projects):
            reason = (f"no usable engineering activity pulled for "
                      f"{requested_project or 'the requested project'}; "
                      f"refusing to finish a draft that can't be grounded")
            banner(f"STUCK, {reason}.")
            finish(which, "stuck", proposed, reason, bounds.cost)
            return

        if SABOTAGE in SABOTAGE_LINES and not sabotaged:
            proposed = f"{proposed.rstrip()}\n{SABOTAGE_LINES[SABOTAGE]}"
            last_draft = proposed
            sabotaged = True
            banner(f"SABOTAGE (test only): injected a bad '{SABOTAGE}' line into the draft\n"
                   f"{SABOTAGE_LINES[SABOTAGE]}")

        # Validate the proposed output independently.
        banner("CRITIC, independent validation")
        try:
            verdict = review(client, MODEL, proposed, "\n".join(source_log))
        except APITimeoutError:
            reason = f"critic call timed out after {CALL_TIMEOUT_S:g}s"
            banner(f"BOUND TRIPPED, {reason}. Halting.")
            finish(which, "stuck", last_draft, reason, bounds.cost)
            return
        # Estimate critic spend too.
        bounds.cost += (verdict["_usage"]["prompt"] * PRICE_IN
                        + verdict["_usage"]["completion"] * PRICE_OUT) / 1_000_000
        print(json.dumps({k: v for k, v in verdict.items() if k != "_usage"}, indent=2))

        # Success (Loop Spec §3): critic pass AND the loop's own checks:
        # - if the task asked for stories (or any were proposed), propose_stories actually
        #   queued them; listing stories in the text is not the same as queueing them.
        # - the draft has a "Context used / excluded" section, so the PM approves the
        #   context together with the draft (M5 HITL checkpoint for "decide context").
        loop_problems = []
        if stories_result is None and wants_stories:
            loop_problems.append("the task asked for stories but propose_stories was never "
                                 "called, so nothing is queued; call it with the stories")
        elif stories_result is not None and stories_result.get("status") != "queued_for_approval":
            loop_problems.append("the proposed stories were not queued for approval: "
                                 f"{json.dumps(stories_result)}")
        if not re.search(r"context used", proposed, re.IGNORECASE):
            loop_problems.append("the draft has no 'Context used / excluded' section listing "
                                 "the items relied on and the items ignored (and why)")
        if verdict["verdict"] == "pass" and not loop_problems:
            banner(f"HITL CHECKPOINT, status update + any proposed stories queued for "
                   f"your review. Nothing posted, no commitments made. "
                   f"Run cost ≈ ${bounds.cost:.4f}")
            finish(which, "success", proposed, "validator passed", bounds.cost)
            return
        if loop_problems:
            print(f"\n-> loop check failed: {'; '.join(loop_problems)}")
            verdict["reasons"] = (verdict["reasons"] if verdict["verdict"] == "fail"
                                  else []) + loop_problems

        # Orchestration Map §5: every rejection is logged, not just how the run ended.
        log_event(which, event="rejection",
                  by="critic" if verdict["verdict"] == "fail" else "loop_check",
                  failed_checks=verdict["failed_checks"], reasons=verdict["reasons"],
                  revision=revisions)

        serious = ESCALATE_CHECKS.intersection(verdict["failed_checks"])
        if serious:
            reason = (f"critic failed {', '.join(sorted(serious))}: "
                      f"{'; '.join(verdict['reasons'])}")
            banner(f"ESCALATE, {', '.join(sorted(serious))}. No revision for this "
                   f"kind of failure, a human takes it from here.")
            finish(which, "escalate", last_draft, reason, bounds.cost)
            return

        if revisions >= MAX_REVISIONS:
            reason = f"validator rejected {MAX_REVISIONS}x (revision cap)"
            banner(f"REVISION CAP hit ({MAX_REVISIONS}). Escalating to a human "
                   f"instead of looping. Run cost ≈ ${bounds.cost:.4f}")
            finish(which, "escalate", last_draft, reason, bounds.cost)
            return

        revisions += 1
        print(f"\n-> sent back for revision {revisions}/{MAX_REVISIONS}")
        # Feed back the draft the critic actually judged (incl. any test-only sabotage line).
        messages.append({"role": "assistant", "content": proposed})
        messages.append({"role": "user", "content":
                         "A validator rejected that for these reasons: "
                         f"{verdict['reasons']}. Write the full corrected draft now and "
                         "start it with DONE:. Use ESCALATE: only if the problem needs "
                         "a human decision and can't be fixed by editing the draft."})

    banner(f"MAX ITERATIONS ({MAX_ITERATIONS}) reached without finishing. "
           f"Escalating. Run cost ≈ ${bounds.cost:.4f}")
    # Budget caps (iterations, revisions, per-run cost) escalate: Cortex ran out of
    # budget and a human decides. Infrastructure failures stay STUCK.
    finish(which, "escalate", last_draft,
           f"max iterations ({MAX_ITERATIONS}) reached", bounds.cost)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "happy")
