---
name: working-in-shifts
description: Explains how to work in a repo run by repeated headless Claude Code shifts, including what to read first, how to hand off through plan.md and progress.md, and when to write DONE or BLOCKED. Use when working from loop/prompt.md, when the user asks to set up or start the loop, or when a hook denies a command during a shift.
---

# Working in shifts

Each shift starts with no memory. The next shift knows only what you commit.

## During a shift
Follow `loop/prompt.md`. Do one item from `plan.md`, then commit, tick it and append to `progress.md`.

## Writing a useful handoff
In `progress.md`, say what changed, what you checked and how, anything surprising, and the next step. Name files and commands. Say so plainly if something is unfinished or a check didn't run.

## When a hook denies something
The guard blocks risky commands and changes to the loop's limits. Don't work around it. If the item can't be done without it, write the question in `BLOCKED` and end the shift.

## Setting up for a person
1. Help them write `goal.md` with a result that can be checked, and split it into small items in `plan.md`.
2. Add their real test command to the `Makefile`, and add commands the agent needs to the allow list in `.claude/settings.json`. Keep that list narrow.
3. Tell them to start it themselves, with a budget they choose:

       python3 loop/loopctl.py run --max-usd 5

Don't start the loop or raise its limits unless they ask.
