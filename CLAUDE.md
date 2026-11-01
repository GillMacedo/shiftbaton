# Project instructions

This repo runs in shifts. See `loop/prompt.md` for how a shift works, and use the `working-in-shifts` skill.

## Commands
- `make test`: unit tests. Replace or extend this for your project.

## Rules
- One item per shift. Commit before ending.
- `progress.md` is append-only.
- `PAUSE`, `.loop/`, `loop/loopctl.py`, `loop/guard.py` and `.claude/settings.json` are limits. A person changes them.
- If a hook denies something, don't look for another way to do it. Write the question in `BLOCKED`.

## Definition of done
Tests pass, the work was checked the way a user would, and it's committed, with `plan.md` and `progress.md` updated.

## Working on shiftbaton itself
Python 3.10+, standard library only. Update `CHANGELOG.md`, `ROADMAP.md` and docs when relevant. Behavior claims about Claude Code should link its docs. Delete this section in your own project.
