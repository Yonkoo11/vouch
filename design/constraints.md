# Constraints — Vouch

Merged from `~/.claude/style.config.md` (personal) and this project. Most specific wins.
This file is what the gauntlet reads.

## Colour mode

**dark-only.** Decided once, recorded here. The audience is developers and on-chain operators reading
dense numeric data, the personal config's observed pattern is dark-first, and shipping both modes would
double the surface for no gain a judge will ever see. Dark has to earn its place; here it does.

## Forbidden (hard no, from personal config)

```
#8B5CF6 #7C3AED #6366F1   purple-blue AI-slop gradients
#14B8A6 + #FB7185          generic teal/coral pairing
gradient text              of any kind
rounded-everything         bubbly radii on every surface
decorative elements        anything that carries no information
stock imagery              photos, generic illustrations
"card grids that all look the same"
"anything that looks like AI made this"
```

## Binding values

```
body_min           14px          ENFORCED. Current page violates this throughout (10.5-12.5px).
mono               JetBrains Mono, tabular-nums, for every number
accent             one per project. #F0B90B (BNB gold) — chain-native, not chosen from a palette.
motion             functional only: 150ms hover, 200ms transition, ease-out
motion_budget      one ambient element per screen, maximum
elevation          card-based with subtle elevation and tinted borders
contrast           4.5:1 body, 3:1 UI, verified in the shipped mode
hit_area           44px minimum on every interactive element
focus              designed ring, visible on keyboard walk, never removed
reduced_motion     honoured
```

## Reference bar

`Linear`, `wrapped.abs.xyz`, `Spotify Wrapped` — from the personal config. Calibration, not a target
to copy.

## Known violations at baseline

1. **Type floor.** 10.5px, 11px, 11.5px, 12px and 12.5px all ship today. The floor is 14px.
2. **Uniform card grid.** The page is exactly the "card grids that all look the same" the config kills
   on sight. Every card carries identical weight regardless of what its evidence says.
3. **No motion.** Not even the functional 150ms hover the config specifies. Nothing transitions.
4. **No focus rings.** Interactive elements rely on the browser default.
