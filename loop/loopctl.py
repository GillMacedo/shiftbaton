#!/usr/bin/env python3
"""Run Claude Code in repeated headless shifts, with hard limits on spend and failure."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK, EXIT_STOPPED, EXIT_USAGE = 0, 1, 2
DEFAULT_RUNS = 10
DEFAULT_TURNS = 50  # enough for one item of work, low enough to stop a runaway shift
DEFAULT_FAILURES = 2  # one failure can be a blip; two in a row usually isn't
DEFAULT_IDLE = 2  # shifts in a row with no new commit before stopping
DEFAULT_TIMEOUT = 3600  # seconds per shift
UNSAFE_MODES = {"bypassPermissions"}
MIN_USEFUL_BUDGET = 0.01  # below a cent, a shift can't do anything


def state_paths(root):
    loop = root / ".loop"
    return {"runs": loop / "runs.jsonl", "pause": root / "PAUSE", "done": root / "DONE", "blocked": root / "BLOCKED", "prompt": root / "loop" / "prompt.md"}


def read_runs(root):
    path = state_paths(root)["runs"]
    if not path.exists():
        return []
    runs = []
    for line in path.read_text().splitlines():
        try:
            runs.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a line cut off by a crash shouldn't stop the safety checks
    return runs


def record(root, entry):
    path = state_paths(root)["runs"]
    path.parent.mkdir(exist_ok=True)
    with path.open("a") as file:
        file.write(json.dumps(entry) + "\n")


def spent(runs):
    return sum(run.get("cost_usd", 0) for run in runs)


def git(root, *args):
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return done.stdout.strip() if done.returncode == 0 else None


def trailing(runs, status_is):
    count = 0
    for run in reversed(runs):
        if not status_is(run):
            break
        count += 1
    return count


def stop_reason(root, args, runs_this_call, all_runs):
    """Return why no new shift may start, or None. Checked before every shift."""
    paths = state_paths(root)
    if paths["pause"].exists():
        return "PAUSE file present"
    if os.environ.get("LOOP_ENABLED") == "false":
        return "LOOP_ENABLED=false"
    if paths["done"].exists():
        return "DONE file present: the agent says the goal is finished"
    if paths["blocked"].exists():
        return "BLOCKED file present: the agent needs a person. See BLOCKED"
    total = spent(all_runs)
    if args.max_usd - total < MIN_USEFUL_BUDGET:
        return f"budget reached: ${total:.2f} of ${args.max_usd:.2f}"
    if runs_this_call >= args.max_runs:
        return f"reached --max-runs {args.max_runs}"
    if trailing(all_runs, lambda run: run.get("status") == "failed") >= args.max_failures:
        return f"{args.max_failures} failed shifts in a row"
    if trailing(all_runs, lambda run: run.get("status") == "ok" and run.get("new_commits") == 0) >= args.max_idle:
        return f"{args.max_idle} shifts in a row with no new commit"
    return None


def run_shift(root, args, budget):
    prompt = state_paths(root)["prompt"].read_text()
    command = ["claude", "-p", prompt, "--output-format", "json", "--max-turns", str(args.max_turns),
               "--max-budget-usd", f"{budget:.2f}", "--permission-mode", args.permission_mode]
    if shutil.which("claude") is None:
        return {"status": "failed", "reason": "claude isn't installed", "cost_usd": 0}
    try:
        done = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=args.run_timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        # The cost of a killed shift is unknown, so the budget can be off by that much.
        return {"status": "failed", "reason": f"timed out after {args.run_timeout}s", "cost_usd": 0, "cost_unknown": True}
    try:
        result = json.loads(done.stdout)
    except json.JSONDecodeError:
        return {"status": "failed", "reason": f"no JSON from claude, exit {done.returncode}: {done.stderr.strip()[:200]}", "cost_usd": 0, "cost_unknown": True}
    entry = {"cost_usd": result.get("total_cost_usd") or 0, "session_id": result.get("session_id"), "turns": result.get("num_turns")}
    # Claude Code can report subtype "success" with is_error true, so subtype isn't enough.
    if result.get("is_error") or done.returncode != 0:
        entry.update(status="failed", reason=str(result.get("result") or result.get("subtype") or f"exit {done.returncode}")[:200])
    else:
        entry.update(status="ok", reason="")
    return entry


def describe(number, entry):
    if entry["status"] != "ok":
        return f"shift {number}: FAILED, ${entry['cost_usd']:.2f}: {entry['reason']}"
    commits = entry.get("new_commits", 0)
    return f"shift {number}: ok, ${entry['cost_usd']:.2f}, {commits} new commit{'' if commits == 1 else 's'}"


def command_run(root, args):
    if args.max_usd <= 0:
        print("--max-usd must be above 0", file=sys.stderr)
        return EXIT_USAGE
    if args.permission_mode in UNSAFE_MODES and not args.sandboxed:
        print(f"--permission-mode {args.permission_mode} removes prompts and rules. Run it only in a container or VM, and pass --sandboxed to confirm.", file=sys.stderr)
        return EXIT_USAGE
    if git(root, "rev-parse", "--is-inside-work-tree") != "true":
        print(f"{root} isn't a git repo. Progress is measured in commits, so it needs one.", file=sys.stderr)
        return EXIT_USAGE
    if not state_paths(root)["prompt"].exists():
        print(f"{state_paths(root)['prompt']} doesn't exist", file=sys.stderr)
        return EXIT_USAGE
    done_this_call = 0
    while True:
        all_runs = read_runs(root)
        reason = stop_reason(root, args, done_this_call, all_runs)
        if reason:
            finished = reason.startswith("DONE")
            print(f"stopped: {reason}. Spent ${spent(all_runs):.2f} of ${args.max_usd:.2f}.")
            return EXIT_OK if finished else EXIT_STOPPED
        before = git(root, "rev-parse", "HEAD")
        entry = run_shift(root, args, args.max_usd - spent(all_runs))
        after = git(root, "rev-parse", "HEAD")
        count = git(root, "rev-list", "--count", f"{before}..{after}") if before and after else None
        entry.update(time=datetime.now(timezone.utc).isoformat(), head=after, new_commits=int(count) if count else 0, uncommitted=bool(git(root, "status", "--porcelain")))
        record(root, entry)
        done_this_call += 1
        print(describe(done_this_call, entry))
        if entry["status"] == "ok" and entry["uncommitted"]:
            print("  warning: the shift left uncommitted changes")
        if entry.get("cost_unknown"):
            print("  warning: this shift's cost is unknown, so the budget may be off")


def command_status(root):
    runs = read_runs(root)
    paths = state_paths(root)
    flags = [name.upper() for name in ("pause", "done", "blocked") if paths[name].exists()]
    print(f"shifts: {len(runs)}, spent ${spent(runs):.2f}, flags: {', '.join(flags) or 'none'}")
    if runs:
        last = runs[-1]
        print(f"last: {last.get('status')} at {last.get('time')}, {last.get('new_commits', 0)} new commits. {last.get('reason', '')}".rstrip())
    return EXIT_OK


def build_parser():
    parser = argparse.ArgumentParser(description="Run Claude Code in repeated headless shifts, with hard limits.")
    parser.add_argument("--root", default=".", help="repo to work in (default: current folder)")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run shifts until a limit or stop condition")
    run.add_argument("--max-usd", type=float, required=True, help="total estimated spend across every run in this repo; Claude Code can pass it slightly")
    run.add_argument("--max-runs", type=int, default=DEFAULT_RUNS, help=f"most shifts in this call (default {DEFAULT_RUNS})")
    run.add_argument("--max-turns", type=int, default=DEFAULT_TURNS, help=f"most turns per shift (default {DEFAULT_TURNS})")
    run.add_argument("--max-failures", type=int, default=DEFAULT_FAILURES, help=f"stop after this many failures in a row (default {DEFAULT_FAILURES})")
    run.add_argument("--max-idle", type=int, default=DEFAULT_IDLE, help=f"stop after this many shifts with no commit (default {DEFAULT_IDLE})")
    run.add_argument("--run-timeout", type=int, default=DEFAULT_TIMEOUT, help=f"seconds per shift (default {DEFAULT_TIMEOUT})")
    run.add_argument("--permission-mode", default="dontAsk", help="Claude Code permission mode (default dontAsk, which denies anything not allowed in settings)")
    run.add_argument("--sandboxed", action="store_true", help="confirm you're in a container or VM, needed for bypassPermissions")
    commands.add_parser("status", help="show spend, flags and the last shift")
    commands.add_parser("pause", help="create PAUSE, so no new shift starts and the guard hook denies tool calls")
    commands.add_parser("resume", help="remove PAUSE")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "run":
        return command_run(root, args)
    if args.command == "status":
        return command_status(root)
    pause = state_paths(root)["pause"]
    if args.command == "pause":
        pause.touch()
        print("paused")
    else:
        pause.unlink(missing_ok=True)
        print("resumed")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
