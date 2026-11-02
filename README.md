# shiftbaton: template for long-running Claude Code agents

[![CI](https://github.com/GillMacedo/shiftbaton/actions/workflows/ci.yml/badge.svg)](https://github.com/GillMacedo/shiftbaton/actions/workflows/ci.yml) [![MIT license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**A GitHub template that runs Claude Code in repeated headless shifts, with a spend limit, a kill switch, stop conditions and a guard hook.**

A long agent run loses context, so each new session needs a way to pick up the work. And a loop running unattended needs limits that the agent can't remove. `shiftbaton` gives you both: progress files and a shift prompt for the handoff, and a small runner and hook for the limits.

The handoff follows Anthropic's [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents): one item per session, commit before ending, and write progress down. The limits come from running a real agent loop. This is an independent project, not affiliated with or endorsed by Anthropic.

## Use it

Click **Use this template** on GitHub, or:

    gh repo create my-project --template GillMacedo/shiftbaton --private --clone
    cd my-project

Then write what you want in `goal.md`, split it into small items in `plan.md`, put your real test command in the `Makefile`, and start with a budget:

    python3 loop/loopctl.py run --max-usd 5

Needs Claude Code and Python 3.10 or newer, with nothing from pip. Read the allow list in `.claude/settings.json` first. The default mode, `dontAsk`, denies anything not on it.

## What you can ask Claude

- "Set this repo up so it can keep working overnight."
- "Help me split this goal into items for `plan.md`."
- "Why did the loop stop?"

## Example

On made-up shifts, through the stand-in `claude` in `tests/fakes`:

    $ make demo
    shift 1: ok, $0.25, 1 new commit
    shift 2: ok, $0.25, 1 new commit
    shift 3: ok, $0.25, 1 new commit
    stopped: DONE file present: the agent says the goal is finished. Spent $0.75 of $5.00.

## When it stops

| Condition | Default |
|---|---|
| Spend across every run in this repo reaches `--max-usd` | Required, no default |
| `PAUSE` file exists, or `LOOP_ENABLED=false` | Checked before each shift |
| Agent writes `DONE` (finished) or `BLOCKED` (needs a person) | Checked before each shift |
| Failed shifts in a row, `--max-failures` | 2 |
| Shifts in a row with no new commit, `--max-idle` | 2 |
| Shifts in this call, `--max-runs` | 10 |

Each shift also has `--max-turns` (50) and `--run-timeout` (1 hour). `python3 loop/loopctl.py pause` creates `PAUSE`. Run `status` to see spend and the last shift.

It treats a result with `is_error: true` as a failure even when `subtype` says `success`, because Claude Code reports a login failure that way.

## The guard hook

`loop/guard.py` runs before Bash, read and write tools. It denies:

- **Risky commands:** force pushes, `git reset --hard`, `--no-verify`, broad recursive deletes, `sudo`, piping a download into a shell, and changes to live infrastructure through `kubectl`, `helm` or `terraform`.
- **Changes to its own limits:** `PAUSE`, `.loop/`, `loop/loopctl.py`, `loop/guard.py` and `.claude/settings.json`.
- **Secrets files:** `.env` and `.env.*`, except `.env.example`.
- **Everything** while `PAUSE` exists, so a running shift stops at its next tool call.

## Limits

- **The guard isn't a security boundary.** It matches text and catches mistakes, so a determined agent could get around it. For real isolation, run in a container or VM with no production credentials.
- **The budget is an estimate.** It uses Claude Code's cost estimate, which can differ from your bill, and a shift can pass its cap. A shift that's killed or returns no JSON has an unknown cost, and the runner warns you.
- **Spend is stored in `.loop/`**, which git ignores, so it's per clone.
- **A commit isn't proof of progress.** The tests and your review have to judge the work.
- **`bypassPermissions` is refused** unless you also pass `--sandboxed` to confirm you're in a container or VM.

## FAQ

**How do I run Claude Code in a loop?** Use `claude -p` with limits around it. `loopctl.py` starts one headless session per shift and checks the stop conditions between them.

**How do I stop a long-running agent?** Run `python3 loop/loopctl.py pause`. No new shift starts, and the hook denies the current shift's next tool call.

**How do I limit what an autonomous agent spends?** `--max-usd` is required, and it counts every run in the repo.

**Why new sessions instead of one long session?** Each shift starts from what's committed and written down, so the handoff is something you can read and check.

## Tested on

Unit tests use a stand-in `claude` and the documented hook input. The runner also ran against the real `claude` CLI in a blank config, which isn't logged in, and stopped on its failure check. **A full agent shift, and the hook inside a live session, haven't been tested yet.** Try it with a small budget first.

## Contributing

Contributions are welcome, from people and from people working with AI agents. See [CONTRIBUTING.md](CONTRIBUTING.md). Good first issues are [listed here](https://github.com/GillMacedo/shiftbaton/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

### How pull requests work

1. **Open a PR.** Fork the repo, work on a branch, and keep it to one change. Write a title that says what changes for users, because it becomes the changelog line: `feat:` goes under Added and `fix:` under Fixed.
2. **Automatic check.** Code changes need tests, and `make test` must pass. Changes over 30 lines need a linked open issue (`Closes #<number>`), and a PR can have at most 800 changed lines. If something is missing, a comment tells you what to fix.
3. **Review.** Claude reviews each PR automatically. Code PRs also get a security review and are tested in a sandbox. The review then merges the PR or asks for changes. PRs that change CI, agent settings, dependencies or build files go to the maintainer, as does anything the security review doesn't clear.
4. **Release.** A merge that changes what users install becomes a new version within about two hours, with a GitHub Release and, if the project has one, its npm package. Docs and CI changes wait for the next release.

## AI disclosure

This project was largely generated with Claude Code and reviewed by its maintainer.

## About me

I'm Giulliano Macedo, and I build developer tools at GoTech Solutions. Follow along or get in touch:

- GitHub: [GillMacedo](https://github.com/GillMacedo)
- LinkedIn: [giulliano](https://www.linkedin.com/in/giulliano/)
- X: [@giumacedo](https://x.com/giumacedo)

If `shiftbaton` helped your agent finish something, a star helps others find it.

---

Built by [Giulliano Macedo](https://github.com/GillMacedo), GoTech Solutions · [LinkedIn](https://www.linkedin.com/in/giulliano/) · [X](https://x.com/giumacedo)
