---
name: autopilot
description: Use when you want to drive a ticket end-to-end UNATTENDED from a fresh worktree and walk away — fetch the ticket, plan, build, verify, review, open a PR, and resolve review feedback in the same live session via non-LLM waits — with no human available to answer questions or approve gates.
---

# Autopilot

## Overview

Take a ticket from a fresh git worktree all the way to a green, feedback-resolved PR **with no human present**. You open a worktree, invoke this skill, and walk away from the keyboard.

**This runs entirely in THIS session — keep it open (laptop on). It does not run remotely.** The advantage is full in-session context. The feedback loop uses **non-LLM waits** (like waiting on a compile or deploy) so it costs nothing while idle and wakes only when the PR actually changes. Because it's the same session, it inherits your git/`gh` auth and working tree — there is nothing remote to provision.

**Tickets are descriptive by design.** Autopilot assumes the ticket fully specifies scope. It NEVER invents or reconstructs scope. An unreadable or empty ticket is an error condition — halt and report, don't guess.

**Core insight — the Autopilot Contract:** Invoking this skill IS standing approval for every interactive gate in the normal workflow (plan approval, scope confirmation, ship confirmation, "track time?"). In autopilot you **never pause to ask**. You decide from evidence, log the decision, and proceed.

**Violating the letter (pausing for a gate) violates the spirit (the human explicitly asked for unattended delivery).**

The one non-negotiable rule: **NEVER BLOCK ON A QUESTION.** If you would normally ask the human something, instead pick the best-supported option, record it under `Assumptions & Risks` (the PR section, see Phase 6), and continue.

## When to Use

- The human said some form of "run my whole workflow on this ticket and walk away."
- You're in a worktree on a ticket branch and no one is available to answer.

**When NOT to use:**
- The human is present and wants interactive brainstorming/approval → run the normal workflow (`superpowers:brainstorming` → `writing-plans` → etc.).
- The change requires irreversible/outward-facing actions beyond opening a PR (deploy, prod data, sending external mail) → those still need explicit human go-ahead; autopilot stops at the PR.

## The Pipeline

Run these phases in order. Each maps to an existing skill — use it, don't reinvent it. The delegated `superpowers` skills have their own human-review checkpoints; **autopilot overrides them** — when a sub-skill would pause for approval, apply the Autopilot Contract instead (decide, log, proceed).

| Phase | Do | Skill / tool |
|-------|-----|--------------|
| 0 Preflight | confirm worktree+branch, read project CLAUDE.md, start timer | `git`, plane scripts |
| 1 Understand | fetch ticket (authoritative scope), read nearest code patterns, derive requirements | Plane API (below), `superpowers:brainstorming` lens (answer your own questions) |
| 2 Plan | written, provisional plan honoring architecture rules | `superpowers:writing-plans` (+ `systematic-debugging` for bug tickets) |
| 3 Build | TDD, subagent-driven, parallelize independent tasks | `superpowers:subagent-driven-development`, `test-driven-development`, `dispatching-parallel-agents` |
| 4 Verify | run the project's verification gate, fix root causes | `superpowers:verification-before-completion` |
| 5 Review | self-review + apply findings with rigor | `superpowers:requesting-code-review` / `/review`; `/cso` or `security-review` for security surfaces; `/codex` for high-stakes; `receiving-code-review` |
| 6 Ship | commit, push, open PR with Assumptions & Risks section | `commit-push-pr` |
| 7 Feedback loop | non-LLM wait for PR change, then resolve in-session; repeat until quiet | `Monitor` (or background `Bash` poll) + `pr-feedback-resolver` |
| 8 Wind down | stop timer, post final status | plane scripts |

### Phase 0 — Preflight

1. `git branch --show-current` + `git status`. You must be on a non-default branch whose name carries a ticket id (e.g. `REBAR-613-...`). **Legitimate halt #1 (of two — the other is an unreadable/empty ticket, Phase 1):** if you're on `main`/`master` or cannot identify a ticket, you don't know what to build — stop and leave a note. These are the *only* halts; everything else is decide-log-proceed.
2. Read the project `CLAUDE.md` (root + the relevant service's). It owns the **exact** verification-gate commands, architecture rules, and review routing. Defer to it over any defaults here.
3. Start the timer (do **not** prompt): `bash ~/.claude/skills/plane-time-tracking/scripts/start-timer.sh`. Exit 0 = tracking; exit 2/3 = log and proceed without tracking.

### Phase 1 — Understand (this replaces interactive brainstorming)

**Fetch the ticket from Plane.** Config is `~/.claude/.plane` (`workspace_slug`, `api_url`, `api_key_env` — the *name* of the env var holding the key, e.g. `PLANE_API_KEY`). Auth header is `X-API-Key: $PLANE_API_KEY`. (Verified live against `plane.actualreality.ai`, 2026-06-08.)

You already have the IDs: **Phase 0's `start-timer.sh` prints `Resolved <ID> -> <issue_uuid>`, `Project: <project_uuid>`, and the issue title.** Reuse those — don't re-scan. Then:
- If a Plane MCP/read tool exists (`ToolSearch` for "plane"), prefer it.
- Else GET the issue detail: `GET {api_url}/api/v1/workspaces/{workspace_slug}/projects/{project_uuid}/issues/{issue_uuid}/`.
  - **Read `description_html` and strip the tags — that is where the body lives.** `description_stripped` and `description` are often EMPTY even on a fully-specified ticket; do not treat an empty `description_stripped` as "no description."
  - Comments: `GET .../issues/{issue_uuid}/comments/` (read `comment_stripped`).
- Fallback if you only have the identifier (timer skipped): two hops — `GET .../projects/` match `identifier`, then `GET .../projects/{id}/issues/` match `sequence_id`.
- **If the read genuinely fails or the ticket body is truly empty: HALT and report (legitimate halt #2 of two).** Tickets are descriptive by design, so a blank/unreadable ticket means something is wrong (wrong id, API failure, wrong worktree) — **never reconstruct scope from the branch name, memory, or commits.** Reconstructed scope is invented scope; an unattended agent inventing scope is the worst failure mode. Stop, say exactly what failed, and wait. (Memory and nearest-code reading are for project *conventions* only — never as a substitute for the ticket's scope.)

**Scope discipline (critical for open-ended tickets).** Build only what the ticket's acceptance criteria require. When you resolve an unknown by judgment, pick the *narrowest* defensible option and log it — do not expand scope because "while I'm here." Capture adjacent improvements as a "Follow-ups" list in the PR, not as code. An unattended agent with no human to bound it is the most likely thing to ship a sprawling PR.

Then read relevant memory, the nearest existing code in the same layer (follow its shape), and recent related work. Apply the `superpowers:brainstorming` lens — but **answer its questions yourself from evidence** and log each judgment call. Do not wait for a human.

### Phase 2–6 — Plan → Ship

- **Plan** is provisional. There is no approval gate. Honor the project's layered architecture and "reference existing patterns" rule. Summarize the plan in the PR later.
- **Build** TDD-first for services/domain/handlers. Atomic conventional commits.
- **Verify** by running the project's gate and reading the full output. Fix root causes, not tests. If one issue resists 3+ honest attempts, log it under `RISKS`, route around it, and keep going — never silently bail.
- **Review**, apply findings, re-run the gate. Run the security pass (`/cso` / `security-review`) whenever the change touches auth, secrets, or what gets written to logs/spans/telemetry — observability work routinely risks leaking tokens/PII into span attributes, so treat instrumentation as a security surface by default.
- **Ship** via `commit-push-pr`, PR targeting the default integration branch (`main` here). The PR body **MUST** contain:

  ```
  ## Assumptions & Risks
  - <every judgment call made while unattended: the provisional plan, scope interpretations where the ticket left a detail open, unresolved tradeoffs, anything you'd normally have asked about. NOT reconstructed scope — a ticket too blank to scope is a HALT, not a logged assumption.>
  ```

  Post the same list as a comment on the Plane ticket. **Never merge.**

### Phase 7 — Feedback loop (in-session, non-LLM wait)

Stay in **this** session and loop. Each cycle is: **wait cheaply → wake on change → resolve → re-arm.** Do NOT poll with LLM turns and do NOT offload to a remote/cron routine — both throw away the in-session context that makes this fast.

**The wait must be non-LLM** — the same way you'd wait on a long compile or a deploy: a blocking watch that burns zero tokens while idle and returns only when the PR state actually changes. Use the **`Monitor`** tool with an until-condition, or a **`Bash` background poll** (`run_in_background`) that exits — and thereby re-invokes you — when the condition trips. Sleep-in-foreground is not a wait; it just blocks. The wake condition is: **new review comment/thread since last seen, OR CI rollup finished (pass/fail).**

Detect via these — but mind the field surfaces:
- `gh pr view <n> --json comments,reviews,reviewDecision,statusCheckRollup` — valid `gh pr view` fields. **`reviewThreads` is NOT a `gh pr view` field** (it errors with "Unknown JSON field"). For inline/resolvable review threads use `gh api graphql` (the `pullRequest.reviewThreads` connection) or `gh pr checks <n>`.
- **Validate every poll command once, inline, before backgrounding it** (run it raw and confirm non-empty JSON). A wrong `--json` field makes the command fail on *every* poll.

**The poll MUST surface failure, never swallow it.** A background poll that treats an empty/errored result as "nothing changed → sleep" will silently die on a bad field or a `gh`/network outage and never wake you — the loop looks alive but is dead. Always:
- Count consecutive failed polls and **exit (wake yourself) after N≈6 consecutive failures** with a clear "API unreachable / command broken" message, instead of looping forever.
- Treat "fetch succeeded but empty" and "fetch failed" as distinct — only a *successful* read with an unchanged state counts as "no change."

Each time the wait wakes you:

1. Run `pr-feedback-resolver` on the PR — in this session, with full context: evaluate each human/AI comment against the codebase + pinned-version docs, implement fixes (TDD) or dismiss with evidence, reply, resolve threads, re-run the verification gate, push.
2. For **strategic** disagreements: `pr-feedback-resolver`'s escalate-and-wait becomes **best-judgment + log** — decide, append rationale to the PR/ticket, proceed. Only items genuinely impossible to decide stay unresolved, flagged in the `Assumptions & Risks` note.
3. Then **re-arm the wait** and repeat. **Exit the loop** when EITHER:
   - 0 unresolved review threads AND CI green AND no new comments since the last pass; OR
   - a **safety cap** trips — max **8 passes** or **24h** elapsed, OR the *same* comment/thread has recurred across **3** passes without converging (a loop you can't win). "Until quiet" must never mean "forever" — an active bot reviewer can post every cycle.
4. On exit (either path), fire a notification via `PushNotification` **and** post a closing comment on the PR + Plane ticket summarizing: what shipped, the assumptions/risks, which exit condition fired, and any human-only leftovers.

### Phase 8 — Wind down

Only after the Phase 7 loop has exited, stop the timer with a concise summary: `bash ~/.claude/skills/plane-time-tracking/scripts/stop-timer.sh "<what shipped>"`. The timer runs for the whole session, including the (cheap, idle) waits.

## Definition of Done

The in-session feedback loop has hit an exit condition — EITHER a **clean exit** (PR open, CI-green, all *actionable* threads resolved, only logged human-strategic items remain) OR a **safety-cap exit** (8 passes / 24h / non-converging loop), with the unfinished state spelled out in `Assumptions & Risks` and the notification. Timer stopped; final notification sent. **You never merge and never deploy.**

## Red Flags — STOP rationalizing

These are the exact paralysis points an agent hits without this skill:

| Thought | Reality |
|---------|---------|
| "I can't both never-pause AND follow the workflow's approval gates" | Autopilot = the human pre-approved every gate. Proceeding IS following the workflow. |
| "Plan approval / scope confirmation is a HARD STOP" | The *plan* needs no approval — it's provisional, logged in the PR, build on it. *Scope* is fixed by the ticket: if it's clear, build; if it's blank/unreadable, HALT — never invent it. |
| "I should ask the human to confirm X" | No human is present. Decide from evidence, log under Assumptions & Risks, proceed. |
| "Should I track time? I need a yes/no first" | Autopilot auto-starts and auto-stops the timer. Never prompt. |
| "I'm not sure a loop can run after I leave, so I'll do one pass" | Stay in-session and wait with `Monitor`/background `Bash` (non-LLM, zero tokens idle). Re-arm and repeat until an exit condition. |
| "The ticket is blank, I'll figure out the scope myself" | NEVER. Tickets are descriptive by design — a blank one means something's wrong. Halt and report; reconstructed scope is invented scope. |
| "I'll cron/remote it so it survives my laptop closing" | Not the model. It runs in this session; keep it open. Remote adds an auth/checkout failure surface for no benefit here. |
| "Strategic feedback needs the human; leave the thread open" | Best-judgment + log to PR/ticket, then proceed. Only truly un-decidable items stay open. |
| "I'll merge to close it out / deploy to finish" | Never. Stop at a green, feedback-resolved PR. |
| "A test won't pass; I'll relax it / skip the gate" | Fix the root cause, or log it under RISKS and route around. Never fake the gate. |

## Common Mistakes

- Prompting for anything → blocks the whole point. Decide and log.
- Opening the PR without the `Assumptions & Risks` section → the human loses the audit trail of every unattended decision.
- Doing one feedback pass instead of waiting (non-LLM) and looping in-session → "until there's none left" never happens.
- Polling the PR with LLM turns instead of a `Monitor`/background-`Bash` wait → burns tokens for nothing while idle.
- A background watcher that swallows poll failures (empty/errored result → sleep) → it dies silently on a bad `--json` field (e.g. `reviewThreads` on `gh pr view`) or a `gh`/network outage and never wakes you; the loop looks alive but is dead. Validate the poll command inline first, and exit-to-wake after ~6 consecutive failed polls.
- Silently dropping a failing test or scope item → log it; silence reads as "done."
