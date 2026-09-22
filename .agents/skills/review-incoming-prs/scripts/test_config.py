#!/usr/bin/env python3
"""CLI tests for config.py. Runs the script as a subprocess against a throwaway
config (REVIEW_PRS_CONFIG), so the real ~/.claude config is never touched.

Run:  python3 scripts/test_config.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "config.py")

passed = failed = 0


def run(args, stdin=None, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        input=stdin, capture_output=True, text=True, env=e,
    )


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok   {name}")
    else:
        failed += 1
        print(f"  FAIL {name}")


def main():
    tmp = tempfile.mkdtemp()
    cfg_path = os.path.join(tmp, "config.json")
    # bare + worktrees layout: <repo>/.bare is the common dir, worktrees are siblings
    repo = os.path.join(tmp, "repos", "example-project")
    gitdir = os.path.join(repo, ".bare")
    worktrees = repo  # normal worktrees live directly under <repo>/
    os.makedirs(gitdir)
    os.makedirs(os.path.join(repo, "main", "client", "src"))  # an existing worktree
    env = {"REVIEW_PRS_CONFIG": cfg_path}

    # --- set global keys ---
    r = run(["set", "slack.my_user_id", "UXXXXXXXXXX"], env=env)
    check("set creates file + key", r.returncode == 0 and os.path.exists(cfg_path))
    run(["set", "slack.channel_id", "CXXXXXXXXXX"], env=env)
    run(["set", "slack.channel_name", "#pr-reviews"], env=env)

    # --- effective with empty projects -> exit 3 ---
    r = run(["effective"], env=env)
    check("no name/root, no projects -> exit 3", r.returncode == 3)
    check("exit 3 lists '(none)'", "(none)" in r.stderr)

    # --- upsert a project (no slack override -> inherits global channel) ---
    proj = {
        "repo": {"git_common_dir": gitdir, "worktrees_dir": worktrees,
                 "default_branch": "main", "owner": "example-org", "name": "example-repo"},
        "plane": {"ticket_prefix": "PROJ"},
        "ui_gate": {"component_globs": ["client/src/components/**"]},
        "docs_sync": [{"code_glob": "client/**", "docs_dir": "client/docs/",
                       "fallback_docs_dir": "docs/"}],
    }
    r = run(["upsert-project", "example-project"], stdin=json.dumps(proj), env=env)
    check("upsert-project succeeds", r.returncode == 0)
    check("no default_project written", "default_project" not in open(cfg_path).read())

    # --- effective by name ---
    r = run(["effective", "example-project"], env=env)
    check("effective by name exit 0", r.returncode == 0)
    eff = json.loads(r.stdout)
    check("channel falls back to global", eff["channel_id"] == "CXXXXXXXXXX")
    check("global my_user_id resolved", eff["my_user_id"] == "UXXXXXXXXXX")
    check("ticket_prefix resolved", eff["ticket_prefix"] == "PROJ")
    check("git_dir resolved", eff["git_dir"] == gitdir)
    check("worktrees_dir resolved", eff["worktrees_dir"] == worktrees)
    check("state_file defaults + ~-expanded",
          eff["state_file"].endswith("/.claude/pr-review-state.json")
          and "~" not in eff["state_file"])
    check("docs_sync passed through", eff["docs_sync"][0]["code_glob"] == "client/**")

    # --- resolve by --git-dir: exact common dir (from the bare repo) ---
    r = run(["effective", "--git-dir", gitdir], env=env)
    check("--git-dir exact match exit 0", r.returncode == 0)
    check("--git-dir resolves right project", json.loads(r.stdout)["project"] == "example-project")

    # --- resolve by --git-dir: from a linked worktree the common dir is still gitdir ---
    # (git rev-parse --git-common-dir from any worktree returns the same path, so we
    #  pass gitdir again — this asserts a normal-clone .git path also resolves)
    normal_gitdir = os.path.join(tmp, "plain", ".git")
    os.makedirs(normal_gitdir)
    sys.stdin = None
    proj2 = {"repo": {"git_common_dir": normal_gitdir, "worktrees_dir": os.path.join(tmp, "plain-wts"),
                      "default_branch": "main", "owner": "x", "name": "plain"}}
    run(["upsert-project", "plain"], stdin=json.dumps(proj2), env=env)
    r = run(["effective", "--git-dir", normal_gitdir], env=env)
    check("normal-clone .git also resolves", r.returncode == 0
          and json.loads(r.stdout)["project"] == "plain")

    # --- resolve by --git-dir: unrelated dir -> exit 4 ---
    r = run(["effective", "--git-dir", tmp], env=env)
    check("--git-dir unrelated -> exit 4", r.returncode == 4)

    # --- unknown explicit name -> exit 4 with valid keys listed ---
    r = run(["effective", "ghost"], env=env)
    check("unknown name -> exit 4", r.returncode == 4 and "example-project" in r.stderr)

    # --- per-project channel override beats global ---
    proj2 = dict(proj)
    proj2["slack"] = {"channel_id": "C0OTHER", "channel_name": "#other"}
    run(["upsert-project", "example-project"], stdin=json.dumps(proj2), env=env)
    r = run(["effective", "example-project"], env=env)
    check("project channel override wins",
          json.loads(r.stdout)["channel_id"] == "C0OTHER")

    # --- _-prefixed keys are ignored as project names ---
    cfg = json.load(open(cfg_path))
    cfg["projects"]["_example"] = {"repo": {"git_common_dir": "/nope"}}
    json.dump(cfg, open(cfg_path, "w"))
    r = run(["effective", "--git-dir", tmp], env=env)
    check("_-prefixed project keys ignored", "_example" not in r.stderr)

    # --- malformed effective flag -> exit 1 ---
    r = run(["effective", "--bogus"], env=env)
    check("malformed flag -> exit 1", r.returncode == 1)

    # --- show is valid JSON ---
    r = run(["show"], env=env)
    check("show emits valid JSON", json.loads(r.stdout) is not None)

    # --- claim / release: the cross-instance per-PR lock ---
    lockdir = os.path.join(tmp, "locks")
    lenv = dict(env)
    lenv["REVIEW_PRS_LOCK_DIR"] = lockdir

    r = run(["claim", "acme/app#7"], env=lenv)
    check("claim new key -> exit 0", r.returncode == 0)

    r = run(["claim", "acme/app#7"], env=lenv)
    check("claim already-held key -> exit 5", r.returncode == 5)

    # a different PR is independently claimable while the first is held
    r = run(["claim", "acme/app#8"], env=lenv)
    check("claim a different key -> exit 0", r.returncode == 0)

    r = run(["release", "acme/app#7"], env=lenv)
    check("release held key -> exit 0", r.returncode == 0)

    r = run(["claim", "acme/app#7"], env=lenv)
    check("re-claim after release -> exit 0", r.returncode == 0)

    # stale-lock steal: backdate the lock dir past the TTL, a normal claim reclaims it
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", "acme/app#7")
    lockpath = os.path.join(lockdir, safe)
    old = time.time() - 2 * 3600  # 2h old, well past default 60m TTL
    os.utime(lockpath, (old, old))
    r = run(["claim", "acme/app#7"], env=lenv)
    check("stale lock (age>TTL) is stolen -> exit 0", r.returncode == 0 and "stole" in r.stdout)

    # the just-stolen lock is now fresh, so it is NOT stolen again
    r = run(["claim", "acme/app#7"], env=lenv)
    check("fresh lock is not stolen -> exit 5", r.returncode == 5)

    # an explicit short --ttl makes a fresh lock reclaimable (knob works)
    r = run(["claim", "acme/app#7", "--ttl", "0"], env=lenv)
    check("--ttl 0 steals even a fresh lock -> exit 0", r.returncode == 0)

    # release is idempotent on a never-claimed key
    r = run(["release", "never-claimed#1"], env=lenv)
    check("release of unheld key -> exit 0", r.returncode == 0)

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
