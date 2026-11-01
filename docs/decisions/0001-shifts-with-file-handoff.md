# 0001: New sessions with file handoff, and limits outside the agent

**Decision:** each shift is a new `claude -p` session that reads progress from files and git. Limits live in a separate runner and hook, which the agent is told not to change and the guard stops it editing.

**Why:** Anthropic's article on long-running harnesses describes this handoff working. Limits inside the prompt depend on the agent following them.

**Alternatives:** resuming one session keeps more context but makes the handoff harder to inspect. A full framework would do more, at the cost of a dependency for something this small.
