---
name: copilot
description: Use when you want to drive a ticket from a worktree but stay at the keyboard and in the loop while building — you approve the plan, you make the scope/ambiguity calls, and you verify the running app (UI smoke test, backend Bruno run) before any PR. The attended counterpart to autopilot.
---

# Copilot

## Overview

Drive a ticket from a fresh worktree to a green PR **with the human present and in the loop while building.** Same pipeline as `autopilot`, but inverted at the gates: where autopilot decides-logs-proceeds, copilot **stops and hands the decision to the human.**

**Core insight — the Copilot Contract:** You are NOT unattended. The human is at the keyboard and explicitly chose to stay involved during the build. At the three checkpoints below you **STOP and wait for the human.** Pausing at these points is the entire purpose of this skill, not a failure to push through.

**The inverse of autopilot's failure mode is THIS skill's failure mode.** An agent carrying build momentum will rationalize skipping a gate ("the plan's obviously fine, I'll just build"). Don't. At a checkpoint, pausing IS the work.

**But don't over-pause either.** Between the three checkpoints, run the normal workflow at full speed. Do not manufacture extra confirmation prompts for trivial, reversible, well-evidenced decisions — that's noise, not involvement. The skill names exactly three gates; honor those, decide the rest yourself.

## When to Use

- You're at the keyboard, working a ticket from a worktree, and want to approve the plan, own the scope calls, and see the app actually run before a PR.
- You want autopilot's structure (worktree → ticket → TDD build → verify → review → ship) but with human checkpoints during the build.

**When NOT to use:**
- You want to walk away and have it driven unattended → use `autopilot`.
- A quick one-file change you can describe in a sentence → just do it, no ceremony.
- Net-new UI/design exploration → start with `ui-research-design` / `/design-shotgun`, then come back here to build.

## The Three Checkpoints

| # | Checkpoint | What you do | When |
|---|-----------|-------------|------|
| 1 | **Scope / ambiguity** | When the ticket leaves a detail open, **ASK the human** — do not pick the narrowest option and log it (that's autopilot's move). | Phase 1, whenever an open question surfaces |
| 2 | **Plan approval** | Present the written plan and **WAIT for explicit approval** before writing any build code. | End of Phase 2, before Phase 3 |
| 3 | **Pre-PR verification** | Prove it works to the human in the running app, then **WAIT for go-ahead** before committing/opening the PR. UI change → dev-up + browser smoke test. Backend change → Bruno run. | End of Phase 5, before Phase 6 |

## The Pipeline

Same phases as autopilot; the difference is the gates. Each phase maps to an existing skill — use it, don't reinvent it.

| Phase | Do | Skill / tool | Gate? |
|-------|-----|--------------|-------|
| 0 Preflight | confirm worktree+branch, read project CLAUDE.md, start timer | `git`, plane scripts | — |
| 1 Understand | fetch ticket (authoritative scope), read nearest code patterns | Plane API, `superpowers:brainstorming` | **① ask on ambiguity** |
| 2 Plan | written plan honoring architecture rules | `superpowers:writing-plans` (+ `systematic-debugging` for bugs) | **② approval** |
| 3 Build | TDD, subagent-driven, parallelize independent tasks | `superpowers:subagent-driven-development`, `test-driven-development`, `dispatching-parallel-agents` | — |
| 4 Verify | run the project's verification gate, fix root causes | `superpowers:verification-before-completion` | — |
| 5 Review | self-review + apply findings with rigor | `/review`; `/cso` / `security-review` for security surfaces; `/codex` for high-stakes; `receiving-code-review` | **③ verify in running app** |
| 6 Ship | commit, push, open PR | `commit-push-pr` | — |
| 7 Feedback | resolve review comments interactively | `pr-feedback-resolver` | — |
| 8 Wind down | stop timer | plane scripts | — |

### Phase 0 — Preflight

1. `git branch --show-current` + `git status`. Be on a non-default branch carrying a ticket id (e.g. `REBAR-613-...`). If you're on `main`/`master` or can't identify a ticket, ask the human which ticket/branch.
2. Read the project `CLAUDE.md` (root + relevant service). It owns the **exact** verification-gate commands, architecture rules, review routing, and the dev-up / test commands. Defer to it over any defaults here.
3. Start the timer: `bash ~/.claude/skills/plane-time-tracking/scripts/start-timer.sh`. Exit 0 = tracking; exit 2 = ask the human which issue; exit 3 = skip.

### Phase 1 — Understand → **Checkpoint ① (scope/ambiguity)**

Fetch the ticket from Plane (this is the authoritative scope). The fetch mechanics are identical to `autopilot`'s Phase 1 — config at `~/.claude/.plane`, auth `X-API-Key: $PLANE_API_KEY`, read `description_html` and strip tags (`description_stripped` is often empty even on a full ticket), comments via `.../comments/`. Prefer a Plane MCP tool if one exists (`ToolSearch` "plane"). If the ticket is unreadable or truly empty, halt and tell the human.

Then read relevant memory, the nearest existing code in the same layer (follow its shape), and recent related work.

**The gate:** whenever the ticket leaves a real decision open — a scope boundary, a UX detail, a tradeoff with no clear winner — **stop and ask the human.** Do not pick the narrowest option and log it; that's autopilot's contract, not yours. Batch related questions into one clear prompt rather than drip-feeding. Trivial, reversible, evidence-backed choices (naming, obvious pattern reuse) you still make yourself.

### Phase 2 — Plan → **Checkpoint ② (plan approval)**

Produce a written plan via `superpowers:writing-plans`, honoring the project's layered architecture and "reference existing patterns" rule. Then **present it and WAIT for explicit approval.** Do not write build code until the human approves. If they request changes, revise and re-present. This is a hard gate.

### Phases 3–4 — Build → Verify

- **Build** TDD-first for services/domain/handlers (`test-driven-development`). Atomic conventional commits. Parallelize genuinely independent tasks.
- **Verify** by running the project's gate (from CLAUDE.md) and reading full output. Fix root causes, not tests. Run these freely without pausing — they're between checkpoints.

### Phase 5 — Review → **Checkpoint ③ (verify in the running app)**

1. Self-review and apply findings (`/review`; security pass via `/cso` or `security-review` when the change touches auth, secrets, or what lands in logs/spans). Re-run the gate.
2. **Then prove it works to the human in the running app, and WAIT for go-ahead before any commit/PR:**
   - **UI change** → start the app and have the human smoke-test it. Find the dev-up command from the project (`CLAUDE.md` commands table, `package.json` scripts, a `scripts/dev*.sh`, or a Makefile target — commonly `bun run dev`). Start it (background it so the session stays free), surface the local URL, and tell the human exactly what to click. The `run` skill can launch and drive the app if useful.
   - **Backend change** → run the project's Bruno collection so the human can verify the endpoints. Bruno CLI: `bru run <collection-dir>` (look for a `bruno/` or `*.bru` collection in the repo; respect the env flag, e.g. `bru run ./bruno --env local`). Show the human the results.
   - **Both** → do both.
   - **Neither (pure refactor/internal)** → show the diff and verification output and ask for go-ahead.

Only after the human gives the go-ahead do you proceed to ship.

### Phase 6 — Ship

Commit and open the PR via `commit-push-pr`, targeting the default integration branch (`main` here). Summarize the plan, the scope decisions the human made, and how it was verified (UI smoke / Bruno results) in the PR body. **Never merge; never deploy** — those still need explicit human action.

### Phase 7 — Feedback

The human is present, so there is **no non-LLM wait loop** (that's autopilot). When review comments arrive, run `pr-feedback-resolver` interactively — escalate strategic/contradictory items and reviewer questions to the human rather than deciding them.

### Phase 8 — Wind down

Stop the timer with a concise summary: `bash ~/.claude/skills/plane-time-tracking/scripts/stop-timer.sh "<what shipped>"`.

## Red Flags — STOP and hand it to the human

| Thought | Reality |
|---------|---------|
| "The plan is obviously right, I'll just start building" | Plan approval is Checkpoint ②. Present it and wait. Build momentum is not approval. |
| "The ticket's a bit vague here but I'll pick the sensible option and note it" | That's autopilot's contract. In copilot, an open scope/UX call is Checkpoint ① — ask. |
| "Tests pass, I'll open the PR" | Green tests ≠ verified. Checkpoint ③: show it running (UI smoke / Bruno) and wait for go-ahead first. |
| "It's a UI change but the diff looks fine, skip the app" | Run the dev-up script and let the human see it. Looking fine in a diff is not a smoke test. |
| "I'll just merge to wrap it up" | Never merge or deploy. Stop at the PR. |
| "I should confirm this rename / obvious pattern choice too" | Over-pausing is noise. Only the three named checkpoints are gates; decide the rest yourself. |

## Common Mistakes

- Barreling past a checkpoint because the build had momentum → the three gates are the point; pausing is the work.
- Treating an open scope question as a decide-and-log (autopilot behavior) → ask the human.
- Opening the PR on green tests without showing the running app → Checkpoint ③ exists because tests-pass ≠ works.
- Pausing at every trivial decision → erodes trust and flow; honor exactly the three gates.
- Running the non-LLM feedback wait loop → that's autopilot. Here, resolve feedback interactively.
