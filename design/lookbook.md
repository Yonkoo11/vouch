# Look book — Vouch

Register: data / finance. Three captures in `design/lookbook/`, numbers extracted rather than vibes.

---

## 1. Our World in Data — `owid.png`  (register: data/analytics, the bar)

| Observed | Value |
|---|---|
| Comparison pattern | right rail: **sorted list, label left, value right-aligned**, ~34px rows |
| Entities visible at once | ~14 in a 700px column. No card chrome at all. |
| Sort control | explicit, names the column: "Sort by: Life expectancy, 2023" |
| Selected vs available | checkbox + tinted row; unselected rows sit at lower contrast, still readable |
| Provenance | "Data source: Riley (2005); Zijdeman et al. (2015); HMD (2025)" — **linked, under the chart** |
| Headline | serif, ~30px, sentence case. Sub-line explains the metric in one sentence. |

**Steal:** the sorted-list-with-right-aligned-value as the comparison primitive, and citing the source
directly under the data rather than in a footer nobody reaches.

---

## 2. Linear — `linear.png`  (register: developer tool, taste calibration from the personal config)

| Observed | Value |
|---|---|
| Background | near-black, roughly `#08080A`; panels lift by ~4% not by border weight |
| Type contrast | headline ~72px / 1.05 against 15px body. Ratio about 4.8:1. |
| Accent use | a single amber dot for priority. **The accent is never a fill, only a marker.** |
| App UI | rows with a leading status glyph, not cards |
| Borders | 1px hairlines at very low contrast, doing the work shadows would do |
| Negative space | the hero is ~45% empty vertical space |

**Steal:** extreme type contrast instead of colour for hierarchy, and the accent as a marker rather
than a surface. Vouch currently uses gold as a fill on every stat number, which spends the accent.

---

## 3. 8004scan — `8004scan.png`  (the incumbent, and the source of our data)

| Observed | Value |
|---|---|
| Form | dark table, 10 rows per page, 9 columns, 49px row height |
| Scale shown | "Showing 1-10 of **311,875** agents" |
| Score column | `0 0 0 0 0 0 0 0 12 0` — **the metric it sorts on is almost always zero** |
| Dead columns | Chain is always "BNB Smart Chain"; Stars always 0; X402 mostly "-" |
| Identity | generated avatar per agent, purple accent, pill badges |

**This is the most important reference and it is a warning.** 8004scan is already a competent dark
table. If Vouch ships another dark table it reads as a worse 8004scan built in a weekend. It also
shows why Vouch exists: nine columns, and not one of them answers "has this agent ever done anything".

---

## Synthesis, five lines

1. The comparison primitive is a **sorted row with the deciding number right-aligned**, not a card.
2. **Do not build a table.** The incumbent owns that form and does it well; matching it loses.
3. Hierarchy comes from **type contrast and de-emphasis**, not from more colour — the accent is a
   marker, spent once per row at most.
4. **Provenance sits with the number**, the way OWID puts its sources under the chart, because the
   entire product claim is that these numbers can be checked.
5. Vouch's one visual idea has to be **the confrontation** — claim against chain, on the same row, with
   the disagreement made legible. That is the thing no reference does, because no reference has to.
