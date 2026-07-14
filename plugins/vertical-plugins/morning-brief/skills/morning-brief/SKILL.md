---
name: morning-brief
description: Generate a personal one-page morning market brief scoped to the user's own holdings and watchlist — overnight developments, today's earnings and events, and upcoming catalysts. Triggers on "morning brief", "朝刊", "マーケット朝刊", "my morning note", "what happened to my stocks overnight", or "daily portfolio brief".
---

# Morning Brief

A personal daily "market newspaper" for an individual investor. This skill composes three equity-research workflows — morning note, catalyst calendar, and earnings preview — but scopes everything to the user's own holdings and watchlist instead of an analyst's coverage universe.

## Workflow

### Step 1: Load the Universe

Read `.claude/morning-brief.local.md` from the plugin directory:

- `holdings` — positions the user owns; these lead the brief
- `watchlist` — tracked names; covered more briefly
- `macro` — standing macro events to always include
- Output preferences: `language`, `max_length`, `include_trade_ideas`

If the file does not exist, ask the user for their holdings and watchlist, offer to save them by copying `.claude/morning-brief.local.md.example`, then continue with what they gave you.

### Step 2: Overnight Scan

For each holding (and more briefly, each watchlist name), search for developments since the prior close:

- Earnings reported overnight or pre-market — actual vs. consensus
- Company news: M&A, guidance changes, management changes, product or regulatory news, notable analyst rating changes
- Price context: overnight/pre-market move if available, and why

Also check macro context relevant to the universe: index futures, rates, FX (especially USD/JPY if Japanese names are held), commodities, and any macro data released overnight.

Skip anything immaterial. "No news" for a name is fine — do not pad.

### Step 3: Today's Events

Build today's slice of a catalyst calendar (see the equity-research `catalyst-calendar` skill for the full framework):

- Any universe name reporting earnings today? Note the time (pre/post market) and consensus expectations
- Macro releases and central bank events today, with scheduled times in the user's timezone
- Conferences, investor days, ex-dividend dates, lockup expirations

For a holding reporting today or tomorrow, add a compact earnings setup (2-3 lines: consensus, the one metric that will move the stock, bull/bear swing) following the `earnings-preview` skill's framework.

### Step 4: Look Ahead

One short section: key events in the next 5 trading days for the universe — earnings dates per name, major macro events. Show days-until-earnings for every holding.

### Step 5: Compose the Brief

Keep it readable in 2 minutes, one page maximum. Default format:

---

**[Date] Morning Brief**

**Top Story: [The one thing that matters most to this portfolio today]**
- 2-3 sentences: what happened and why it matters to the user's positions

**Overnight — Holdings**
- [Ticker]: one-line development + impact. Flag moves over 5%.
- (Names with no material news: collapse into one line — "No material news: X, Y, Z")

**Overnight — Watchlist** (only names with actual news)

**Today**
- [Time]: [Company] Q[X] earnings — consensus, key metric to watch
- [Time]: [Macro release] — expectation

**Next 5 Days**
- [Date]: [Event] ([N] days away)

---

Write in the configured `language`. If `include_trade_ideas` is true, add a final "Ideas" section following the morning-note discipline: a view plus the risk that would make it wrong.

## Automation

To deliver the brief automatically every morning, set up a scheduled Routine (or cron trigger) that sends the prompt "Generate my morning brief" at the configured `delivery_time`. The skill re-reads the local config on every run, so watchlist edits take effect the next morning without touching the schedule.

## Important Notes

- This is a personal brief, not investment advice — summarize and contextualize, but attribute market views to sources
- Lead with the user's holdings; watchlist names never displace holdings news
- Be selective: five sharp lines beat twenty exhaustive ones
- Time-stamp the brief and note that pre-market conditions can change by the open
- If web search is unavailable, say so explicitly rather than generating stale or invented "news"
