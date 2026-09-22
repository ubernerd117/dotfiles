---
name: review-incoming-prs
description: Scan the configured Slack PR-review channel for PRs tagged to me and run the full review workflow on each new one, mirroring my manual ritual (👀 on pickup; clean → approve + ✅; findings → REQUEST_CHANGES review + thread reply "See comments"). Time-tracks each review to its Plane ticket. Pick which project/repo to review by passing its key when summoning, e.g. `/review-incoming-prs example-project`.
---

You are running ONE poll cycle of the Slack-triggered PR-review loop. Discover from
Slack, review any *new* PRs, act on GitHub + Slack as me, then return so the `/loop`
wrapper can sleep. Do NOT loop inside this command. Process PRs **one at a time**
(so per-PR Plane timers never overlap).

## Configuration (read first — never hardcode)

Site-specific values live in `~/.claude/review-incoming-prs.config.json`, which is
**managed by this skill, not hand-edited**. A small helper reads/writes it deterministically:

```
CFG=~/.claude/skills/review-incoming-prs/scripts/config.py
```

The config holds a `projects` map; each entry is one repo with its own
`repo` / `plane` / `ui_gate` / `docs_sync` (and an optional `slack` channel override).
Slack identity (`my_user_id`) and `state_file` are global.

### Resolve the project (this cycle reviews exactly one)

**The project is the repo you summon in.** With no argument, the skill matches your current
repo to a configured project; an explicit argument overrides that. (Under `/loop`, the wrapped
command carries the argument too.) Resolve through the helper — it applies the channel fallback
and `~`-expansion:

A repo is identified by its **git common dir** (`git rev-parse --git-common-dir`), which is
stable whether you summon from the bare repo, a linked worktree, or a normal clone:

```bash
# explicit project name wins:
python3 "$CFG" effective "<project-arg>"

# otherwise resolve by the repo you're in (the helper realpath-normalizes, so an
# absolute common dir is all that's needed):
GITDIR="$(git rev-parse --git-common-dir 2>/dev/null)"
GITDIR="$(cd "$GITDIR" && pwd)"   # make absolute (--git-common-dir can be relative)
python3 "$CFG" effective --git-dir "$GITDIR"
```

- **exit 0** — prints the effective settings as flat JSON. Use those values directly. Proceed to Step 0.
- **exit 4** — no project matched (unknown name, or the current repo isn't configured yet). If you're inside a git repo, run **First-run setup** below for it, then re-run `effective`. If a name was given that doesn't exist, report it with the printed valid keys; don't fall back silently.
- **exit 3** — nothing to resolve (no name given and not inside a git repo). If the printed project list is non-empty, show it and ask which to use, then return. If it's empty, this is a brand-new install → ask the user to summon from inside the repo they want to review (so setup can detect it).

The fields returned by `effective` map to the bracketed names used throughout this skill:
`[channel_id]`, `[channel_name]`, `[my_user_id]`, `[git_dir]` (the git common dir — all git ops run via `git --git-dir=[git_dir]`), `[worktrees_dir]` (where review worktrees are created),
`[default_branch]`, `[owner]`/`[name]` (the GitHub repo), `[ticket_prefix]` (ticket regex
is `[ticket_prefix]-\d+`), `[ui_globs]`, `[docs_sync]`, and `[state_file]`
(shape `{"reviewed":{"<owner>/<repo>#<pr>":"<headSHA>"}}`, shared across projects).

### First-run setup (only when the project isn't configured yet)

Run this **from inside the repo you want to review** (the bare repo or any of its worktrees)
so detection works. Gather values, confirming each with the user, then persist — never invent:

1. **Detect from the repo** (Bash):
   - `git rev-parse --git-common-dir` → resolve to an absolute path → `git_common_dir` (the repo identity).
   - `git rev-parse --is-bare-repository` to confirm the layout.
   - `worktrees_dir`: where your worktrees live. Infer from `git worktree list --porcelain` — the parent directory of an existing non-bare linked worktree is your worktrees dir. If none exist yet, propose the parent of `git_common_dir` and confirm.
   - `gh repo view --json nameWithOwner,defaultBranchRef` → owner/name + default branch.
   - Scan a worktree for likely **UI-component dirs** (`**/components/`) and **docs dirs** (`**/docs/`) to propose `ui_gate.component_globs` and `docs_sync` mappings.
2. **Ask the user** for what can't be detected, showing detected values for confirmation:
   - Slack channel for this project (channel id + name). If they say "same as default" and a global channel exists, omit the per-project override.
   - Plane `ticket_prefix` — propose a guess from recent branch names
     (`git --git-dir=<git_common_dir> for-each-ref --sort=-committerdate --count=20 --format='%(refname:short)' refs/heads refs/remotes`) and confirm.
   - Confirm/edit the detected UI globs, docs-sync mappings, and the inferred `worktrees_dir` (either glob list may be empty).
3. **If `my_user_id` is not set yet** (very first setup ever): ask for the Slack member id and
   `python3 "$CFG" set slack.my_user_id <U…>`. Likewise set a global default channel if they want one
   (`set slack.channel_id` / `set slack.channel_name`).
4. **Persist the project** (deterministic write; the project key should be memorable — the repo name is a good default):
   ```bash
   python3 "$CFG" upsert-project <name> <<'JSON'
   { "slack": {"channel_id":"…","channel_name":"…"},        // omit slack to use the global default
     "repo": {"git_common_dir":"…","worktrees_dir":"…","default_branch":"…","owner":"…","name":"…"},
     "plane": {"ticket_prefix":"…"},
     "ui_gate": {"component_globs":[…]},
     "docs_sync": [{"code_glob":"…","docs_dir":"…","fallback_docs_dir":null}] }
   JSON
   ```
5. Confirm what was written, then re-run `effective` and continue the cycle.

**Slack tooling:** this skill calls `slack_read_channel`, `slack_add_reaction`, and
`slack_get_reactions`. Those come from a Slack MCP server that must be connected in
this session. If they are unavailable, report that and return — do not proceed.

## Guardrails (non-negotiable)
- **All verified feedback is blocking.** Any verified finding — any kind, any severity (low/nit included), code or doc-sync — routes to **`REQUEST_CHANGES`**. `COMMENTED` is used ONLY for the clean-but-UI case (Step 5). Never merge, never push/edit code.
- **Auto-approval requires BOTH** zero verified findings (after Step 4 — raw finder output does NOT count) **AND** the PR does not touch any UI component path in `[ui_globs]`. Only then: submit a GitHub `APPROVE` + ✅ (`white_check_mark`) Slack reaction. **UI-component work is NEVER auto-approved** (needs manual testing) even when clean — but app routes/pages, hooks, tRPC/BFF, and styles follow the normal process and CAN auto-approve. Any finding → `REQUEST_CHANGES`, never approve/✅.
- The bot's two reactions: **👀** on pickup (always), and **✅** only on a clean auto-approval. Never ✅ when there are findings.
- **One instance per PR (the cross-instance gate).** Before 👀 or any review work, acquire the local claim: `python3 "$CFG" claim "<owner>/<repo>#<n>"`. On **exit 5**, another instance owns it — skip the PR this cycle. This local lock — NOT the Slack 👀 — is what stops two running instances from reviewing the same PR, because both instances react as the *same* Slack user, so 👀 can't distinguish them. **Always release the claim** (`python3 "$CFG" release …`) when the PR is done, on every exit path.
- **No emojis in GitHub review bodies or inline comments** — keep all PR-facing text plain. (The Slack 👀/✅ reactions are a separate channel and are unaffected by this.)
- **Keep the main (loop) session lean — delegate all reading to subagents.** The main session must NOT read PR diffs or source files for analysis. It only orchestrates: dispatch agents, dedup their summaries, assemble the review payload from their structured returns, and post. ALL diff/source reading + verification happens inside subagents (Agent tool) whose isolated context is discarded once they return compact results. This is load-bearing for a loop: one main context is reused across many cycles, so inline reading compounds and bloats it.
- Everything posts as the authenticated user (me) — treat every reaction, review, approval, and reply as outward-facing and final.
- If anything is ambiguous or a step fails for one PR, skip it, note it in the cycle summary, and continue — never block the whole cycle. If a review step fails after 👀 was added, do NOT approve/comment/reply and do NOT record state; **release the claim** (`python3 "$CFG" release …`) and list it under "needs manual attention".

## Step 0 — Refresh the diff base
At the start of every cycle, fetch the latest base so PR reviews are computed against current `[default_branch]`:
```bash
git --git-dir=[git_dir] fetch origin [default_branch]
```
Each PR gets its own worktree (Step 2). The review diff is `origin/[default_branch]...HEAD`, three-dot, so a freshly-fetched base is all that's needed.

**Review worktrees are ordinary worktrees, kept and never auto-pruned.** Each is created in your normal worktrees dir (`[worktrees_dir]`), named after the PR's head branch — exactly like a worktree you'd make by hand — so you can `cd` in and inspect any PR. They accumulate by design — prune manually when you want (`git --git-dir=[git_dir] worktree remove [worktrees_dir]/<branch>`).

## Step 1 — Read the channel
`slack_read_channel` on `[channel_id]` (limit ~30). Keep a message as a candidate only if ALL hold:
1. It mentions me: contains `<@[my_user_id]`.
2. It contains a GitHub PR URL `github.com/<owner>/<repo>/pull/<number>` (raw, `<url>`, or `<url|text>`). Parse owner/repo/number.
3. It has **no 👀 (`eyes`) reaction at all** (if unsure, `slack_get_reactions` on its `ts`).

"No 👀 at all" is the don't-step-on-a-human guard: a message already carrying 👀 is either handled or one I'm reviewing manually — leave it. So the existing backlog (already 👀'd) is skipped → no first-run burst. **This 👀 check is a cheap pre-filter, not the cross-instance lock** — two instances polling at the same time both see no 👀 and would both proceed. The authoritative gate is the local claim in Step 2.1; selection here just trims obvious non-candidates.

Also drop: PRs authored by me, and drafts (`gh pr view <n> --repo <owner>/<repo> --json isDraft,author`).

If no candidates survive, report "No new PRs to review" and return.

## Step 2 — For each new PR (one at a time)

1. **Claim it — local lock FIRST, then 👀.** Run `python3 "$CFG" claim "<owner>/<repo>#<n>"`:
   - **exit 0** → you own this PR. Now add 👀 (`slack_add_reaction`, `name:"eyes"`, `[channel_id]`, message `ts`) and continue.
   - **exit 5** → another instance holds a live claim (it's reviewing this PR right now). **Skip this PR this cycle** — do NOT add 👀, do NOT review. Note it as "claimed by another instance" and move to the next candidate.

   The claim must come before 👀 and before any GitHub reads, so two overlapping cycles can't both pass into review. Stale claims older than 60 min are auto-reclaimed, so a crashed instance never blocks a PR permanently. Once claimed, you MUST release in step 8 on every exit path.
2. **Start the Plane timer.** Get the PR's ticket: `gh pr view <n> --repo <owner>/<repo> --json headRefName,title` and extract `[ticket_prefix]-\d+` from the branch name (preferred) or title.
   - If found: `bash ~/.claude/skills/plane-time-tracking/scripts/start-timer.sh <TICKET>` (stop any already-running timer first if the script reports one running).
   - If no ticket found: skip timer tracking for this PR and note it in the summary; still do the review.
3. **SHA guard:** `gh pr view <n> --repo <owner>/<repo> --json headRefOid`. If `reviewed["<owner>/<repo>#<n>"]` in `[state_file]` already equals this SHA, skip to step 6 (already reviewed at this commit; you'll still release the claim in step 8).
4. **Create (or refresh) an ordinary worktree for this PR's head branch** (works for forks). Get the branch name: `BR=$(gh pr view <n> --repo <owner>/<repo> --json headRefName -q .headRefName)`. The worktree dir is `[worktrees_dir]/$BR` (if `$BR` has slashes, that just nests dirs — same as a normal worktree). Then:
   ```bash
   git --git-dir=[git_dir] fetch origin "pull/<number>/head"
   SHA=$(git --git-dir=[git_dir] rev-parse FETCH_HEAD)   # resolve here: FETCH_HEAD is per-worktree, not visible from the new worktree
   if [ -d "[worktrees_dir]/$BR" ]; then
     # re-review (worktree exists, new commits): update it in place
     git -C "[worktrees_dir]/$BR" reset --hard "$SHA"
   else
     # first review: a normal branch-named worktree, no pr- prefix
     git --git-dir=[git_dir] worktree add -B "$BR" "[worktrees_dir]/$BR" "$SHA"
   fi
   ```
   (`$SHA` equals the PR's `headRefOid` from the Step 3 guard — using the resolved SHA avoids the per-worktree `FETCH_HEAD` pitfall.) Run the rest of the review from `[worktrees_dir]/$BR`. Leave the worktree in place when done.
5. **Run the review workflow** (all git/file reads happen inside the PR's worktree `[worktrees_dir]/$BR`; pass that path to every subagent as its working directory):
   - Scope (main session, cheap): run only `git -C [worktrees_dir]/$BR diff origin/[default_branch]...HEAD --stat` to see which files/areas changed — do NOT read the full diff or any source in the main session. Pick finder angles by change type:
     - **App code (Go/TS/Python):** line-by-line scan (incl. enclosing unchanged lines of touched functions), removed-behavior auditor, cross-file caller/callee tracer; plus reuse / simplification / efficiency / altitude.
     - **IaC / config (Terraform, YAML, Helm, compose, Dockerfiles):** config correctness (refs resolve, ports/endpoints, env wiring across layers), cross-file consistency + docs drift, security (exposed ports, secrets, over-broad IAM, TLS), reuse/duplication/altitude.
     - Mixed: both sets, scoped to relevant files.
   - **Fan out finders in parallel via the Agent tool (general-purpose) — mandatory, never inline.** Scale the count to the change: 1–2 finders for a tiny/simple PR, the full angle set for a large/complex one. Each finder runs `git -C [worktrees_dir]/$BR diff origin/[default_branch]...HEAD` and reads any files in that worktree IN ITS OWN context, returning ≤6 candidates as JSON `{file, line, summary, failure_scenario}`. The heavy reading stays in the subagents, not the main session.
   - **VERIFY in a subagent (critical — this gates approve-vs-comment).** Main dedups near-duplicate candidates by comparing their summaries only (cheap, no file reads). Then dispatch ONE verify subagent (Agent tool) with the deduped list: it opens the actual files, confirms/refutes each finding, **corrects line numbers** (finders routinely cite lines outside the file and invent failure modes — drop those), drops anything refuted by the code, and returns the final verified findings with exact `{path, line, side, body}` anchors ready to post. The main session does NOT open files. The returned verified list (cap ~10, correctness over cleanup) decides the next step.
   - **Documentation-sync check (same verify subagent).** For the area the PR touched, the verify agent also reads the matching docs and confirms they stay in sync with the implementation. Use the `[docs_sync]` mapping: for each entry whose `code_glob` the PR touched, read `docs_dir` (or `fallback_docs_dir` if `docs_dir` is absent). It flags two **doc-sync findings** (tag them clearly so routing can detect them):
     1. **Contradiction** — a doc states behavior/config/values the PR changes, so the doc is now stale/wrong. Anchor on the stale doc line (`side:"RIGHT"`), comment what the implementation now does.
     2. **Missing docs** — the PR introduces new behavior, env vars/flags, endpoints, or schema that should be documented but no doc was added/updated. Anchor on the implementation line that introduced it, comment which doc needs the addition.
     If no `[docs_sync]` entry matches the changed area (or neither `docs_dir` nor `fallback_docs_dir` exists), note "no docs scope" and skip the doc-gate — never fabricate.
   - **UI gate (main, from `--stat`):** `is_ui` = the diff touches any path matching a glob in `[ui_globs]`. ONLY those paths gate auto-approval. App routes/pages (they just import components), hooks, tRPC/BFF, and styles do NOT gate — they follow the normal review path and can auto-approve when clean.
   - **Branch on verified findings + UI gate:**
     - **≥1 verified finding (any kind, any severity — ALL feedback is blocking) → REQUEST_CHANGES.** Post one review via `gh api .../pulls/<number>/reviews --input <payload.json>` — `{commit_id:<headSHA>, event:"REQUEST_CHANGES", body:<overall summary; state that the listed feedback must be addressed before merge; for doc-sync findings, that docs must be updated/added to stay synced>, comments:[{path,line,side:"RIGHT",body:"**[Severity] …**"}]}`. Every comment line MUST be in the diff (prefer `+` lines; new files = any line; removed-only → `side:"LEFT"`) or the review is rejected. Then thread-reply `See comments`. Do NOT approve/✅.
     - **Zero findings AND `is_ui` is false → AUTO-APPROVE.** Submit `gh api --method POST /repos/<owner>/<repo>/pulls/<number>/reviews -f commit_id=<headSHA> -f event=APPROVE -f body="Reviewed — no issues found across <the angles run>. LGTM."` then add ✅ (`slack_add_reaction`, `name:"white_check_mark"`, the message `ts`).
     - **Zero findings BUT `is_ui` is true → COMMENTED, NO approval.** Frontend/UI/UX must be manually tested, so never auto-approve. Post a `COMMENTED` review with `body:"Reviewed — no automated issues found, but this touches the frontend/UI, so it needs manual UI/UX testing before approval. Not auto-approving."` (no inline comments needed). Then thread-reply `See comments`. No ✅, no approve.
6. **Stop the Plane timer** (if started in 2.2): `bash ~/.claude/skills/plane-time-tracking/scripts/stop-timer.sh "PR review: <owner>/<repo>#<n> — <approved | N comments posted>"`.
7. **Record state:** set `reviewed["<owner>/<repo>#<n>"] = "<headSHA>"` in `[state_file]` and write it back.
8. **Release the claim** (always, as the last per-PR action): `python3 "$CFG" release "<owner>/<repo>#<n>"`. Release on EVERY exit path once claimed — normal completion, the SHA-guard skip (step 3), and any mid-review failure — so the lock never outlives the work and the PR is claimable again on its next commit.

## Step 3 — Report
Lead with the project that ran (`[P]` and its `[channel_name]`). Compact summary: candidates found; for each reviewed PR — approved (✅) / request-changes / commented (manual-UI note) + the verified-findings count + that 👀 was added + timer ticket; skipped (reason — including "claimed by another instance" when the local lock was held); any "needs manual attention".

End every summary with a **Next loop** line. Compute it from the real schedule, not an assumption: call `CronList` to get the active loop job's cron expression (the one whose prompt invokes `/review-incoming-prs` for THIS project — match the project argument), run `date '+%H:%M %Z'` for the current time, work out the next matching fire, and print `- Next loop: ~H:MM<am/pm>` (prefix `~` because the scheduler adds small jitter). If no active cron job exists for this loop (e.g. a manual one-off run), print `- Next loop: — (no active schedule)`.

Then return — the loop sleeps until that time.
