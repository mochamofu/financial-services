---
description: View or edit the holdings and watchlist used by the morning brief
argument-hint: "[add|remove <ticker>]"
---

Manage the universe in `.claude/morning-brief.local.md` (create it from `.claude/morning-brief.local.md.example` if missing).

- With no arguments: show the current holdings and watchlist as a table.
- `add <ticker>`: ask whether it is a holding or a watchlist name, then append it.
- `remove <ticker>`: remove it from whichever list contains it.

Confirm the file contents after any edit.
