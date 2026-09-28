---
name: plane
description: Create, read, update, and search Plane work items (tickets/issues), projects, and members via the Plane REST API at plane.actualreality.ai. Use whenever the user mentions Plane, tickets, issues, work items, or a Plane project identifier (e.g. FIVOS-45, FIVOSPRHRD).
---

# Plane REST API

Self-hosted Plane. There is no Plane MCP server — use `curl` against the REST API.

- Base: `https://plane.actualreality.ai/api/v1/workspaces/actual`
- Auth header: `X-API-Key: $PLANE_API_KEY` (already exported in the user's shell; never print it or read it from config files)
- Send `Content-Type: application/json` on writes. Parse responses with `python3 -c 'import json,sys; ...'`.

```bash
B=https://plane.actualreality.ai/api/v1/workspaces/actual
curl -s -H "X-API-Key: $PLANE_API_KEY" "$B/projects/"
```

## Endpoints

| Action | Method + path (relative to `$B`) |
|---|---|
| List projects | `GET /projects/` → `results[]` with `id`, `identifier`, `name` |
| Workspace members | `GET /members/` → list with `id`, `display_name`, `email` |
| Project members | `GET /projects/{project_id}/members/` |
| List issues | `GET /projects/{project_id}/issues/` (paginated: `results`, `next_cursor`) |
| Get issue by key | `GET /issues/{PROJECT_IDENTIFIER}-{sequence_id}/` (e.g. `/issues/FIVOSPRHRD-2/`) |
| Create issue | `POST /projects/{project_id}/issues/` |
| Update issue | `PATCH /projects/{project_id}/issues/{issue_id}/` |
| States | `GET /projects/{project_id}/states/` |
| Labels | `GET /projects/{project_id}/labels/` |
| Comments | `GET`/`POST /projects/{project_id}/issues/{issue_id}/comments/` (`{"comment_html": "<p>…</p>"}`) |

Create/update body fields: `name`, `description_html` (HTML string, escape `&` as `&amp;`), `assignees` (list of member UUIDs), `state` (state UUID), `labels` (label UUIDs), `priority` (`urgent|high|medium|low|none`), `start_date`/`target_date` (`YYYY-MM-DD`), `parent` (issue UUID).

Build JSON bodies with `python3 -c 'import json; print(json.dumps({...}))'` rather than hand-quoting, so titles with quotes or ampersands don't break.

## Resolving names

- **Projects:** always resolve the identifier → UUID via `GET /projects/`. Don't hardcode IDs.
- **People:** users refer to people loosely (a nickname, a full name run together). Match against `display_name`, `email`, `first_name`, `last_name` in `GET /members/`. If there's no exact match, pick the obvious one only if unambiguous and tell the user which member you chose; otherwise ask.

## Known projects

- `FIVOSPRHRD` — FIVOS Production Hardening (current SOW for the PathwaysAI repo; new tickets go here)
- `FIVOS` — FIVOS Pathways AI prototype (previous SOW; older `FIVOS-NN` refs point here)
