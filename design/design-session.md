# Design session — Vouch

Product: a marketplace that ranks BNB Chain agents by measured on-chain evidence instead of the
registry's self-declared score. Single static page, no build step, vanilla JS modules, dark-only,
served from `docs/` on GitHub Pages.

Started 2026-09-10. Mode: full pass. Track: greenfield tokens over an existing hand-built page.

## Phases

| # | Phase | Status | Artifact |
|---|---|---|---|
| 0 | Brief, taste, constraints | done | `brief.md`, `constraints.md`, `gauntlet-before.txt` |
| 1 | Research | done | `lookbook.md`, `lookbook/` (OWID, Linear, DefiLlama, 8004scan) |
| 2 | State | done | `state.md` |
| 3 | Design system | done | `../docs/tokens.css`, `tokens.md` |
| 4 | Direction | done | `directions.md` — three proposals, one chosen |
| 5 | Build | done | `../docs/index.html` rebuilt as "The Seam" |
| 6 | Polish | done | `gauntlet-after.txt`, ui-revamp audit clean |
| 7 | Formalize | **skipped** | see below |
| 8 | QA gate | done | `qa.md` |

## Decisions

**Dark-only, and it had to earn it.** The page is read next to 8004scan and a BSC explorer, both
dark. A light mode would have doubled the token surface for a page nobody will open in daylight
next to those two.

**Not a table.** The look book's sharpest finding was that the incumbent is already a competent
dark table with 311,875 agents. Matching it loses. The comparison primitive became a sorted row
with the deciding number right-aligned.

**The signature element is the seam.** Grid is `1fr 1px 1.25fr`: registry claim right-aligned and
de-emphasised at `--claim`, a 1px rule, then what the chain says at `--measured`. Disagreement
between the two sides is the product, so it is the layout.

**Gold is a marker, not a fill.** `#F0B90B` appears on the opening figure, on live values, and in
the focus ring. Nothing is filled with it.

**Three-tier tokens.** Base scale → semantic meaning → component usage. Components read semantic
tokens only. After phase 8 there are zero raw pixel values left in the component CSS.

**Type ladder, after the QA fixes.** 12px uppercase tracked labels only; 13px lowercase mono meta
labels and inline code; 14px body floor; 17px, 26px; fluid `--t-lede-xl` and `--t-figure` for the
one editorial moment. The most-used size on the page is 14px.

## Warnings from the phase 6 gauntlet, and what happened to each

Baseline was 0 blockers, 10 warnings, 5 nits. After the rebuild and polish: 0, 0, 0. Every warning
was fixed rather than accepted; the two that mattered were caption contrast at 3.40:1 (moved
`--text-faint` from gray-7 to gray-8, now 6.71:1) and the fonts being linked but unused while the
tokens still said `-apple-system`.

## Phase 7 skipped, and why

`design-forge` produces `DESIGN_SYSTEM.md`, `brand.json` and a logo. The token file already carries
its own rationale inline and is 60 lines; a second document restating it would drift from it. A
mark was needed for one reason only — the tab icon — so that was built directly in phase 8 rather
than through the full brand pass. If Vouch outlives the hackathon and grows a second surface, run
phase 7 then, when there is something for a shared baseline to be shared *with*.

## Next action

None outstanding for design. The QA gate is green and `qa.md` records what was not covered:
light mode (does not exist by decision), physical iOS Safari, and a screen-reader walk.
