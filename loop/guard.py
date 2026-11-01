#!/usr/bin/env python3
"""PreToolUse hook: deny risky commands, and stop the agent changing its own limits.

This catches mistakes. It matches text, so it isn't a security boundary. Use a container for that.
"""

import json
import os
import re
import sys
from pathlib import Path

# Each rule: (pattern, why). Patterns run on the whole command, case-insensitively.
RISKY_COMMANDS = [
    (r"\bgit\s+push\b.*(\s--force\b|\s--force-with-lease\b|\s-f\b|\s\+\S)", "force push rewrites shared history"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard discards work"),
    (r"\bgit\s+clean\b.*\s-\w*f", "git clean deletes untracked files"),
    (r"\bgit\s+checkout\s+(--\s+)?\.(\s|$)", "this discards uncommitted work"),
    (r"\bgit\b.*--no-verify\b", "--no-verify skips the project's checks"),
    (r"\brm\s+(-\w+\s+)*-\w*[rR]\w*\s+(-\w+\s+)*(/|~|\$HOME|\.\.|\*|\.(\s|$))", "recursive delete outside a named project folder"),
    (r"\bsudo\b", "sudo changes the machine, not the project"),
    (r"\b(curl|wget)\b[^|;&]*\|\s*(sudo\s+)?(ba|z|da)?sh\b", "piping a download into a shell runs unreviewed code"),
    (r"\bchmod\s+(-\w+\s+)*777\b", "chmod 777 opens files to everyone"),
    (r"\b(kubectl\s+(delete|apply|drain|scale|rollout\s+undo)|helm\s+(install|upgrade|uninstall|rollback)|terraform\s+(apply|destroy))\b", "this changes live infrastructure"),
    (r"\bdrop\s+(database|table)\b", "this deletes data"),
]
# The agent must not edit what limits it. A person changes these.
PROTECTED = ("PAUSE", ".loop/", "loop/loopctl.py", "loop/guard.py", ".claude/settings.json")
PROTECTED_IN_COMMAND = re.compile(r"(^|[\s;&|'\"/>])(PAUSE|\.loop/|loop/loopctl\.py|loop/guard\.py|\.claude/settings\.json)")
READ_ONLY_COMMAND = re.compile(r"^\s*(cat|ls|head|tail|grep|wc|git\s+(status|diff|log|show))\b[^;&|>]*$")
SECRET_FILE = re.compile(r"(^|/)\.env(?!\.example$)(\.[\w.-]+)?$")


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}))
    return 0


def relative(path, root):
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except ValueError:
        return Path(path).as_posix()


def check(tool, tool_input, root):
    """Return why this call is denied, or None."""
    if (root / "PAUSE").exists():
        return "The PAUSE file is present, so the loop is paused. Stop work and end the shift."
    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        for pattern, why in RISKY_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return f"Blocked: {why}. Find a safer way, or write the question in BLOCKED for a person."
        if PROTECTED_IN_COMMAND.search(command) and not READ_ONLY_COMMAND.match(command):
            return "Blocked: this could change the loop's limits or state. A person changes those."
    elif tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = relative(str(tool_input.get("file_path") or tool_input.get("notebook_path") or ""), root)
        if path == "PAUSE" or path.startswith(".loop/") or path in PROTECTED:
            return f"Blocked: {path} is part of the loop's limits or state. A person changes it."
        if SECRET_FILE.search(path):
            return "Blocked: don't write secrets files."
    elif tool == "Read":
        if SECRET_FILE.search(str(tool_input.get("file_path", ""))):
            return "Blocked: don't read secrets files."
    return None


def main(stdin=None):
    try:
        data = json.loads((stdin or sys.stdin).read())
    except json.JSONDecodeError:
        return deny("The guard couldn't read this tool call, so it was denied.")
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".").resolve()
    reason = check(data.get("tool_name"), data.get("tool_input") or {}, root)
    return deny(reason) if reason else 0


if __name__ == "__main__":
    sys.exit(main())
