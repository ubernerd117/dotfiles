#!/usr/bin/env python3
"""Deterministic read/write helper for the review-incoming-prs config.

The review-incoming-prs skill calls this instead of hand-editing JSON, so the
stored config in ~/.claude/review-incoming-prs.config.json is always well-formed.

Config shape (designed for a bare + worktrees layout, but works for normal clones too):
{
  "slack":   {"my_user_id": "U...", "channel_id": "C...", "channel_name": "#..."},
  "state_file": "~/.claude/pr-review-state.json",
  "projects": {
    "example-project": {
      "slack":      {"channel_id": "C...", "channel_name": "#..."},   # optional override
      "repo":       {"git_common_dir": "...",   # `git rev-parse --git-common-dir`; the repo's IDENTITY
                     "worktrees_dir": "...",     # where review worktrees are created (your normal worktree dir)
                     "default_branch": "main", "owner": "...", "name": "..."},
      "plane":      {"ticket_prefix": "PROJ"},
      "ui_gate":    {"component_globs": ["client/src/components/**"]},
      "docs_sync":  [{"code_glob": "...", "docs_dir": "...", "fallback_docs_dir": null}]
    }
  }
}

Subcommands:
  path                       print the config file path
  show                       print the whole config (pretty); creates {} if missing
  set KEY VALUE              set a dotted global key (e.g. slack.my_user_id, state_file)
  upsert-project NAME        read a project JSON object from stdin, store at projects.NAME
  claim KEY [--ttl MIN]      atomically claim a PR (KEY = "owner/repo#num") for review.
                             exit 0: you own it. exit 5: another instance holds a live
                             claim -> skip this PR. Stale claims older than MIN (default
                             60) are reclaimed (crash recovery). This is the real
                             cross-instance gate; the Slack 👀 reaction is not (same user).
  release KEY                release a claim (idempotent; never errors on an unheld key).
  effective [NAME]           resolve the effective settings for a project and print them as
                             flat JSON (channel falls back project->global, ~ expanded).
  effective --git-dir PATH   resolve by the repo you're in: pick the project whose
                             repo.git_common_dir matches PATH (= `git rev-parse --git-common-dir`).
                             This resolves identically from the bare repo, any linked worktree,
                             or a normal clone.
                             exit 3: nothing to resolve (empty config / not in a repo) -> prints keys
                             exit 4: no project matched NAME / PATH -> prints keys

Resolution is by the active repo, not a static default. All paths in `effective` output
are ~-expanded so the skill can use them directly.
"""
import json
import os
import re
import shutil
import sys
import time

# Override with REVIEW_PRS_CONFIG (used by tests; normally unset).
CONFIG_PATH = os.path.expanduser(
    os.environ.get("REVIEW_PRS_CONFIG", "~/.claude/review-incoming-prs.config.json")
)
DEFAULT_STATE_FILE = "~/.claude/pr-review-state.json"

# Cross-instance per-PR claim locks (override with REVIEW_PRS_LOCK_DIR; tests do).
# A claim is an atomic mkdir, so exactly one concurrent claimer wins. This — NOT the
# Slack 👀 reaction — is the real gate, because two instances react as the SAME Slack
# user, so 👀 cannot distinguish them. The TTL must exceed the longest realistic
# single-PR review, or a slow review's lock gets stolen mid-flight and double-reviewed.
LOCK_DIR = os.path.expanduser(
    os.environ.get("REVIEW_PRS_LOCK_DIR", "~/.claude/pr-review-locks")
)
DEFAULT_LOCK_TTL_MIN = 60.0


def load():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def expand(p):
    return os.path.expanduser(p) if isinstance(p, str) else p


def project_keys(cfg):
    return sorted(k for k in cfg.get("projects", {}) if not k.startswith("_"))


def cmd_path():
    print(CONFIG_PATH)


def cmd_show():
    print(json.dumps(load(), indent=2))


def cmd_set(key, value):
    cfg = load()
    parts = key.split(".")
    node = cfg
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = value
    save(cfg)
    print(f"set {key} = {value}")


def cmd_upsert_project(name):
    payload = json.load(sys.stdin)
    cfg = load()
    cfg.setdefault("projects", {})[name] = payload
    save(cfg)
    print(f"saved project '{name}' to {CONFIG_PATH}")


def match_by_git_dir(cfg, path):
    """Return the project name whose repo.git_common_dir matches `path`, else None.
    `git rev-parse --git-common-dir` is canonical — it returns the same absolute path
    from the bare repo, any linked worktree, or a normal clone — so an exact realpath
    match is correct and unambiguous."""
    target = os.path.realpath(expand(path))
    for name in project_keys(cfg):
        gcd = cfg["projects"][name].get("repo", {}).get("git_common_dir")
        if gcd and os.path.realpath(expand(gcd)) == target:
            return name
    return None


def cmd_effective(name=None, git_dir=None):
    cfg = load()
    projects = cfg.get("projects", {})

    if name is None and git_dir is not None:
        name = match_by_git_dir(cfg, git_dir)
        if name is None:
            sys.stderr.write(
                f"no configured project for git dir: {os.path.realpath(expand(git_dir))}\n"
                f"available projects: {', '.join(project_keys(cfg)) or '(none)'}\n"
            )
            sys.exit(4)
    if not name:
        sys.stderr.write(
            "no project given and no git dir to resolve from.\n"
            f"available projects: {', '.join(project_keys(cfg)) or '(none)'}\n"
        )
        sys.exit(3)
    if name not in projects:
        sys.stderr.write(
            f"project '{name}' not found.\n"
            f"available projects: {', '.join(project_keys(cfg)) or '(none)'}\n"
        )
        sys.exit(4)

    p = projects[name]
    g_slack = cfg.get("slack", {})
    p_slack = p.get("slack", {})
    repo = p.get("repo", {})

    out = {
        "project": name,
        "channel_id": p_slack.get("channel_id") or g_slack.get("channel_id"),
        "channel_name": p_slack.get("channel_name") or g_slack.get("channel_name"),
        "my_user_id": g_slack.get("my_user_id"),
        "git_dir": expand(repo.get("git_common_dir")),
        "worktrees_dir": expand(repo.get("worktrees_dir")),
        "default_branch": repo.get("default_branch", "main"),
        "owner": repo.get("owner"),
        "name": repo.get("name"),
        "ticket_prefix": p.get("plane", {}).get("ticket_prefix"),
        "ui_globs": p.get("ui_gate", {}).get("component_globs", []),
        "docs_sync": p.get("docs_sync", []),
        "state_file": expand(cfg.get("state_file", DEFAULT_STATE_FILE)),
    }
    print(json.dumps(out, indent=2))


def _lock_path(key):
    return os.path.join(LOCK_DIR, re.sub(r"[^A-Za-z0-9._-]", "_", key))


def _write_marker(path, stolen):
    try:
        with open(os.path.join(path, "owner.json"), "w") as f:
            json.dump({"pid": os.getpid(), "ts": int(time.time()), "stolen": stolen}, f)
            f.write("\n")
    except OSError:
        pass


def cmd_claim(key, ttl_min=DEFAULT_LOCK_TTL_MIN):
    """Atomically claim a PR for review. exit 0 = you own it; exit 5 = another
    instance holds a live claim (skip this PR this cycle)."""
    os.makedirs(LOCK_DIR, exist_ok=True)
    path = _lock_path(key)
    try:
        os.mkdir(path)  # atomic: exactly one concurrent claimer succeeds
    except FileExistsError:
        age_min = (time.time() - os.path.getmtime(path)) / 60.0
        if age_min <= ttl_min:
            sys.stderr.write(
                f"already claimed by another instance: {key} "
                f"(age {age_min:.1f}m <= ttl {ttl_min:g}m)\n"
            )
            sys.exit(5)
        # Lock is older than the TTL — the holder almost certainly crashed. Reclaim it.
        shutil.rmtree(path, ignore_errors=True)
        try:
            os.mkdir(path)
        except FileExistsError:
            sys.stderr.write(f"lost the race to reclaim a stale lock: {key}\n")
            sys.exit(5)
        _write_marker(path, stolen=True)
        print(f"claimed {key} (stole stale lock, age {age_min:.0f}m)")
        return
    _write_marker(path, stolen=False)
    print(f"claimed {key}")


def cmd_release(key):
    """Release a claim. Idempotent — never errors on an unheld key."""
    shutil.rmtree(_lock_path(key), ignore_errors=True)
    print(f"released {key}")


def main():
    args = sys.argv[1:]
    if not args:
        sys.stderr.write(__doc__)
        sys.exit(1)
    cmd, rest = args[0], args[1:]
    if cmd == "path":
        cmd_path()
    elif cmd == "show":
        cmd_show()
    elif cmd == "set" and len(rest) == 2:
        cmd_set(rest[0], rest[1])
    elif cmd == "upsert-project" and len(rest) == 1:
        cmd_upsert_project(rest[0])
    elif cmd == "claim" and rest:
        key = rest[0]
        ttl = DEFAULT_LOCK_TTL_MIN
        if len(rest) == 3 and rest[1] == "--ttl":
            ttl = float(rest[2])
        elif len(rest) != 1:
            sys.stderr.write(f"malformed: claim {' '.join(rest)}\n")
            sys.exit(1)
        cmd_claim(key, ttl)
    elif cmd == "release" and len(rest) == 1:
        cmd_release(rest[0])
    elif cmd == "effective":
        if rest and rest[0] == "--git-dir" and len(rest) == 2:
            cmd_effective(name=None, git_dir=rest[1])
        elif rest and rest[0].startswith("--"):
            sys.stderr.write(f"malformed: effective {' '.join(rest)}\n")
            sys.exit(1)
        else:
            cmd_effective(name=rest[0] if rest else None)
    else:
        sys.stderr.write(f"unknown or malformed command: {' '.join(args)}\n\n")
        sys.stderr.write(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
