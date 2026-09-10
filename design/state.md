# State map — Vouch

One screen. Data arrives from two places: static JSON built by `scripts/build-data.py` (the agent
evidence) and live RPC calls made in the browser (block height, Keystore authority, wallet balance).

| Region | Source | Updates | Empty | Loading | Populated | Error |
|---|---|---|---|---|---|---|
| Block height | BSC RPC, browser | every page load | n/a | "connecting to BSC…" | "BSC block 121,124,147" | "BSC RPC unreachable", amber dot |
| Registry line | `data/index.json` | per build | n/a | "registry: …" | "160 listings, 105 unique agents, 105 measured" | falls to the status line below |
| Findings band | `data/index.json` | per build | hidden until loaded | hidden | six stats + prose | hidden; page still renders rows |
| Category rows | `data/<cat>.json` | per build | "No agent in the live registry matches this category yet" — says *why* | "Loading agents…" | 40 rows | "Could not load the category data (…). Nothing is shown, because inventing rows is the exact failure this project exists to fix." |
| Evidence per agent | build-time RPC | per build | **"insufficient history"** where the registry holds no feedback | n/a, ships with the page | numbers with explorer links | `null` evidence renders as "unmeasured — node unreachable" |
| Authority check | Keystore, browser, on demand | per click | "No key is registered on this wallet…" | "reading the Altana Keystore…" | "1 of 1 registered key currently authorised" | "Keystore read failed: …" |
| Hire dialog | Altana SDK + RPC | per attempt | n/a | step log, line per step | session + explorer link | needs-funding gets the address, the faucet, and the mainnet-requirement explanation |

**Empty states say why, always.** Tufte: an empty region must distinguish "no data yet" from "nothing
matched" from "the source failed". All three appear above and are worded differently on purpose.

**The one that matters most:** "insufficient history". It is not an error and not a zero. It is the
honest answer for an agent the chain has nothing to say about, and it must never be styled as a
failure state — it is the product working.
