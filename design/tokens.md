# Tokens — Vouch

**Ratio.** 1.125, the dense-UI ratio. This is a data view, not a marketing page: sizes step gently so
that eight distinct roles fit between 11px and 44px without any two reading as the same thing.

**Floor.** 14px. The personal config enforces it and the shipped page broke it everywhere — 10.5, 11,
11.5, 12 and 12.5px all appeared. 11px survives as `--t-caption` for uppercase labels only, never for
a sentence, which is the one exemption Schoger's ramp allows.

**Accent.** `#F0B90B`, one per project, and it is BNB's own gold rather than a colour chosen from a
palette — the product lives on BNB Chain and borrows its chain's mark. Variety comes from opacity at
55/32/12/6%, never from a second hue. Linear's lesson: the accent is a marker, not a fill. The old page
painted every stat number gold, which spent the accent until it meant nothing.

**Grays.** One cool-neutral hue, ten steps, tuned to sit under gold without turning green.

**The pair that carries the product.** `--claim` and `--measured` are the only two semantic colours
that exist to encode an argument. The registry's claim is always `--gray-8`; the chain's measurement is
always `--gray-10`. Emphasis by de-emphasis, per Schoger: the chain wins on every row not because it is
louder but because the claim is quieter.

**Motion.** 120/180/260ms, ease-out. Hover responds within 120ms. `prefers-reduced-motion` collapses
all three to 0.01ms. Ambient budget for the page: one element, the live block-height dot.

**Radius.** Three roles — control 6, card 10, overlay 14. The old page used 4, 6, 7, 10 and 12px as
literals scattered through components, which the gauntlet flagged six times.
