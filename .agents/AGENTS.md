# Agent instructions

Apply [unslop](skills/unslop/SKILL.md) to all communication and written artifacts.

## Workflow

use `grill-with-docs` to clarify decisions, `to-spec` to record agreement, `to-tickets` to divide large changes, `implement` to build test-first, and `code-review` to check the diff against the spec and standards.


- For changes touching 2+ files, new endpoints, or external integrations, get approval on a plan before building. Skip formal planning for fully specified edits whose diff fits in one sentence.
- Follow nearby code patterns. Use `tdd` for services, domain logic, and handlers, agreeing on public test boundaries first.
- Use `diagnosing-bugs` for failures. Reproduce before fixing; reconsider the approach after three failed attempts.
- For 3+ independent sub-problems, delegate focused tasks with isolated context. Review each result against the spec and code standards.
- Before opening a PR, run `code-review` and fix findings. Use `pr` for its description and `pr-feedback-resolver` for reviewer feedback. Assess suggestions against the code and pinned versions.
- Merge and deploy when authorized, then verify production behavior. Use atomic conventional commits and squash feature branches on merge.

## Engineering and verification

Read [engineering-standards](skills/engineering-standards/SKILL.md) when designing, implementing, refactoring, or reviewing code. Follow established project conventions; use the skill's defaults where the project leaves a choice open.

Run the project's checks and exercise changed behavior before claiming completion. Report results and any checks you could not run. Investigate failures; change tests only when expectations are wrong or behavior intentionally changes.

## Other guidance

- Use `ui-research-design` for UI design research, `prototype` for experiments, and `research` for sourced answers.
- Use `codebase-design` for module interfaces and `domain-modeling` for terminology and ADRs.
- Use `technical-writing` for documentation and `writing-for-agents` for instructions and skills.
- When requested, use `teach` for sustained learning in a separate workspace and `wait-what` to explain something again with missing context. Use `handoff` to carry a learning question out of a build session.
