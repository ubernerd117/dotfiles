---
description: Use when creating, refining, splitting, or reviewing a Plane ticket / work item / issue for Actual Reality work — including turning a spec, plan, brainstorm, bug report, or "we should also…" remark into tickets, choosing a priority, writing acceptance criteria, or deciding which board column a new ticket belongs in.
targets: [claude]
version: 1
---

# writing-tickets

Source of truth: [`docs/PROCESS.md`](../../docs/PROCESS.md) — the Engineering Process
handbook, sections 1–3. Plane is the source of truth for in-flight work: if work is
happening and there is no ticket, the team cannot see it, so it effectively is not
happening.

**Core test:** a ticket is finished when someone who was not in the conversation can pull
it and know when they are done. That someone may be a person or an agent (`/autopilot`,
`/copilot`). Write for that reader, not for yourself.

## When to use

- Any new task, bug, or idea that will take real work
- Chunking a spec or plan into board items
- Refining an Intake/Backlog item so it can move to Todo
- Reviewing tickets someone else (or an AI) drafted

**Not for:** the git/PR mechanics after a ticket exists (branch naming beyond the ID, PR
requirements, merge rules) — that is [`docs/GIT-WORKFLOW.md`](../../docs/GIT-WORKFLOW.md).

## Every ticket needs four things

| Field | Bar it has to clear |
|---|---|
| **Title** | Someone scanning the board knows what this is without opening it |
| **Description** | Context and scope: what, where, and why now |
| **Acceptance criteria** | Specific conditions that make this ticket finished |
| **Priority** | One of Urgent / High / Medium / Low, chosen deliberately |

An **estimate** is the fifth field, required only to leave Intake for Todo (see
Definition of ready).

Missing acceptance criteria is the single most common defect. They are what lets someone
else pick the ticket up, and what lets a reviewer tell whether the PR actually did the job.

## Pick the type

Three primary templates. Choosing correctly saves the next person from guessing what kind
of work this is.

- **Feature** — new capability, or an enhancement to something that exists.
- **Bug** — defect or regression. Must include steps to reproduce, plus expected vs actual.
- **Discovery (Spike)** — time-boxed research, prototyping, investigation. The deliverable
  is a decision or a written finding, **not** shipped code. Say the time box and where the
  finding lands.

If the ticket would need all three shapes, it is more than one ticket.

## Titles

Imperative, specific, no ticket ID (Plane adds it), no type prefix (the template says it).

```
✅ Add per-key spend caps to the gateway config
✅ Streaming responses drop the final chunk when the client disconnects
✅ Decide whether Presidio runs in-process or as a sidecar

❌ Spend caps                      (what about them?)
❌ Fix gateway bug                 (which bug?)
❌ Investigate performance issues  (of what? done when?)
```

## Acceptance criteria

Write conditions a reviewer can check, not a restatement of the title. Each one is
observable: something runs, returns, appears, or is recorded.

```markdown
## Acceptance criteria
- [ ] `POST /key/generate` accepts `max_budget` and rejects a negative value with 400
- [ ] A request that would exceed the key's remaining budget returns 429 with `budget_exceeded`
- [ ] Spend is recorded per key and survives a gateway restart
- [ ] `go test -race ./internal/service/budget/...` passes
- [ ] Documented in `docs/operations.md` under "Spend caps"
```

Rules:
- **Testable, not aspirational.** "Fast" → "p95 under 200 ms at 50 rps".
- **Name the verification.** The command, the endpoint, the screen. If nobody can name how
  to check it, the criterion is not done being written.
- **Include the docs.** Documentation lands with the behavior, in the same commit — so if
  the change needs a doc, that is a criterion, not a follow-up.
- **Out of scope is a criterion too.** One line listing what this ticket deliberately does
  not do prevents the reviewer from asking for it.

For a Bug, acceptance criteria include the reproduction no longer reproducing. For a
Discovery, the criterion is the written finding existing at a named path, plus a decision
recorded with its rejected alternative.

## Priority

Four levels, deliberately coarse. The point is to make the top of the queue obvious, not
to build a ranking system.

| Priority | Means | Reach for it when |
|---|---|---|
| **Urgent** | Drop everything; take it to done before returning to anything else | Something is broken or someone is blocked, and waiting until tomorrow makes it worse |
| **High** | Must be in the final deliverable; the work is not complete without it | It belongs at the top of the queue as soon as current work clears |
| **Medium** | Should be in the deliverable; cut only as a deliberate, stated decision | Clearly worth doing, no deadline pressure |
| **Low** | Nice to have; only once everything higher is clear | Genuinely optional, safe to sit in the backlog |

**Urgent is about timing. High, Medium, and Low are about scope** — they order the queue
but do not interrupt it. Urgent is the only level that says stop what you are doing.

**If everything is Urgent, nothing is.** Unsure between two levels? Pick the lower one and
raise it at standup if that turns out wrong. That costs a sentence; an inflated backlog
costs the whole team its sense of what matters.

## Which column does it start in?

```
Intake/Backlog → Todo → In Progress → In Review → Done
 not refined    ready   branch exists  PR open    merged
```

File a new ticket in **Intake/Backlog** by default. Move it to **Todo** only when it meets
the definition of ready:

- [ ] Requirements are clear enough that someone else could start
- [ ] Acceptance criteria are written and testable
- [ ] Priority is set
- [ ] An estimate exists
- [ ] It is agreed for the current or an upcoming cycle

Do not park a fresh ticket in Todo because it feels obvious. Todo is a claim that the team
agreed to it.

Two exits that are not Done: **Cancelled** — leave a note explaining why before closing,
because a cancelled ticket with no explanation is the one thing guaranteed to be
re-litigated in three months. And **Duplicate** — link the original, then close this one.

## Splitting a spec into tickets

- One ticket = one reviewable PR. If the acceptance criteria imply three separate PRs,
  that is three tickets.
- Sequence with dependencies stated in the body: `Blocked by AIGATEWAY-12` on each
  dependent, and a "gates" list on the gating ticket. Plane's relation API returns HTTP
  405 in this workspace, so the chain only exists if it is written in the text — never
  report tickets as "linked" on the strength of that call.
- Use an **Epic** as the parent only where a project already uses epics. Children move
  independently; the epic closes once they are all resolved.
- A ticket nobody can estimate is a Discovery plus a follow-up, not one big Feature.

**Create the gating ticket first.** Its ID is what the dependent tickets reference, and
creating in dependency order means you never need an ID that does not exist yet. Then add
the "gates" list to the gating ticket once the dependents have IDs.

**Do not write a deliverable path that embeds an ID you do not have.** Name it by slug
(`docs/perf/request-queueing-options.md`); if the repo convention prefixes the ticket ID,
create the ticket, then update its body with its own ID. Never guess the next number — the
board assigns it.

## Creating it in Plane

Ticket names, states, and labels differ per project — discover, do not assume:

1. `list_projects` → the project id (e.g. AI Gateway = `AIGATEWAY`).
2. `list_states <project_id>` → state ids. Column names vary (`Cancelled` vs `Canceled`;
   some projects add `In QA`).
3. `list_labels <project_id>` → the type label. Plane's work-item types are disabled on
   most projects here (`list_work_item_types` 404s), so **the template is carried by a
   label** named `Feature` / `Bug` / `Discovery`. TMASA and RebarIQ carry all three;
   AIGATEWAY has `Feature` and `Discovery`. If the label you need is absent, ask before
   creating it — labels are project-wide config, not per-ticket data.
4. `create_work_item` with the title, a markdown `description_html` body, `priority`,
   `state`, and label ids.

Leave `estimate_point` unset unless the team has actually estimated it. Do not invent an
estimate on someone else's behalf — that gate is supposed to stay visible.

To read a ticket back, pass `expand` rather than `fields` —
`retrieve_work_item_by_identifier` fails Pydantic validation unless `assignees` and
`labels` are in `fields`, and `description_stripped` comes back null.

## The ID is the handoff

The ticket ID is what connects git to the board. Take the branch name from the **copy
branch name** button on the ticket rather than typing it: `AIGATEWAY-123-short-slug`. With
that, plus `fixes AIGATEWAY-123` in the PR description, the board maintains itself and the
automated standup sees the work. A ticket in In Progress with no matching branch is
invisible to both.

## Common mistakes

| Mistake | Fix |
|---|---|
| Acceptance criteria restate the title | Each criterion names something observable a reviewer can check |
| "Improve X" / "Investigate Y" with no end condition | Define done, or make it a Discovery with a time box and a named deliverable |
| Everything filed as High or Urgent | Urgent = interrupts current work. Unsure → pick lower |
| New ticket dropped straight into Todo | Intake until refined, estimated, and agreed |
| Bug with no reproduction | Steps, expected, actual — otherwise the fix is unverifiable |
| Spec pasted in as one ticket | One ticket per reviewable PR; state the blocked-by chain |
| Docs left as a follow-up ticket | Docs land with the behavior; make it a criterion |
| Dependencies "linked" via the relation API | It returns 405 here; write the chain into the bodies |
| Cancelled with no note | Say why, in the description or a comment |
| Body is a wall of prose | Headed sections and a checklist; the reader is scanning, not studying |
| Next ticket number guessed into a title or path | The board assigns IDs; create first, reference after |

## Quick reference

**Starting a ticket:** clear title → description → acceptance criteria → type
(Feature / Bug / Discovery) → priority → estimate → file in Intake, or Todo if agreed.

**Board columns:** Intake/Backlog · (Epics, some projects) · Todo · In Progress · In
Review · Done, plus Cancelled (note why) and Duplicate (link the original).

**Where to raise it:** `#engineering` general and process, `#coord-{project-name}`
per-project, `#request-pr-review` for reviews. Process itself is up for change — retro is
the venue, and "this felt annoying twice this week" is a sufficient reason.
