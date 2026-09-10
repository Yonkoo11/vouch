# Directions — Vouch

Three built, live data in each, screenshots in `docs/screenshots/`. Evaluated against
`design/constraints.md` and the look book synthesis, not against taste.

| # | DNA | Stance | Signature element |
|---|---|---|---|
| 1 | DNA-S-T-M-N-E | Forensic Ledger | The disagreement bar — claim and chain percentile pips on one drawn-to-scale rule |
| 2 | DNA-A-S-S-M-S | The Seam | A vertical rule down the page: claim left at low contrast, chain right at full contrast |
| 3 | DNA-B-H-F-D-S | Weight of Evidence | Cell area is a function of measured activity, so a dead category looks like hairlines |

DNA overlap: 1↔2 share 0 genes, 1↔3 share 0, 2↔3 share 1 (typography). Within the ≤2 limit.

## Evaluation

**1 — Forensic Ledger.** The serif headline is the most distinctive thing any of the three do, and the
bar is a real comparison primitive: 40 agents scan in one pass. It fails on decoding. "100 pts apart"
and "chain pctl" are percentiles, and a percentile is an abstraction over the evidence rather than the
evidence. Worse, the *best* agent in the category shows the *widest* bar, because the registry
underrates it — true, interesting, and exactly backwards from what a first-time reader assumes a wide
bar means. A judge with ninety seconds should not have to learn a key.

**2 — The Seam.** The argument becomes spatial before it becomes verbal: everything the registry
asserts sits left and dim, everything the chain records sits right and bright, and a single rule
divides them. It is the `--claim` / `--measured` token pair made into layout. Nothing needs decoding —
"2,515 transactions sent · today · no position held" is the raw measurement, not a derived score. The
side rail keeps all four categories permanently visible, which matters because Agent Diversity is
scored explicitly and a hidden nav makes a judge hunt for it. Weaknesses: a large void opens in the
claim column at wide viewports, and the dispute flag is too blunt (see below).

**3 — Weight of Evidence.** The full-viewport "1 of 105 agents holds any authority to act on-chain at
all" is the most arresting opening of the three and the finding that best carries the product. The
browse view underneath does not work. The bento tiles raggedly and leaves holes that read as broken
rather than composed; size encoding fights the numbers, so a 2,515-transaction agent sits in a smaller
cell than a 1-position agent; and eight identical "29 transactions sent" HeyAnon cells reproduce the
exact "card grids that all look the same" pattern the constraints kill on sight.

## Selected: 2, with 3's opening

**The Seam for the browse, Weight of Evidence's hero finding above it.** Not a hedge — they solve
different halves. Direction 3 is the best *comprehension* surface and the worst *comparison* surface;
direction 2 is the reverse. A judge reads one finding, understands the thesis, scrolls once, and every
row after that is the thesis restated with evidence. Direction 1's bar is retired: elegant, but it
teaches a key before it gives an answer, and Data Quality is judged on whether a user can make an
informed call, not on whether the chart is clever.

## Bug found while evaluating, to fix in the build

The dispute flag fires on `category_supported === false`, so "LP Agent 1 by 4LPHA" — 2,515
transactions, active today — is labelled **claim outruns evidence**. It does not. It holds no
PancakeSwap position, which is one signal among several, and the agent is plainly alive. A flag that
fires on the most active agent in the category is worse than no flag. The build must weigh activity
and recency before it disputes anything.
