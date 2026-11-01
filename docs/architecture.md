# Architecture

    goal.md, plan.md, progress.md, git log --> one shift (claude -p with loop/prompt.md) --> commit + handoff
    loopctl.py: stop_reason? --> run_shift --> record in .loop/runs.jsonl --> repeat
    guard.py: PreToolUse hook --> deny or say nothing

- **`stop_reason`** runs before every shift, and reads spend from the log, so limits last across calls.
- **`run_shift`** treats `is_error`, a bad exit or missing JSON as failure.
- **`guard.py`** fails closed on input it can't read, and protects the files that hold the limits.

Key choice: new sessions with file handoff, rather than one long session. See `decisions/`.
