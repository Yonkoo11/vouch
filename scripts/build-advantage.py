#!/usr/bin/env python3
"""
Agent Advantage Report.

The TermiX question is not "does this agent exist" but "is hiring it worth
anything". This computes an answer from the same measured data the marketplace
runs on, so the report cannot drift from the page: run it after build-data.py
and it regenerates from docs/data/*.json.

The original plan was three tasks run with an agent and without, timed. That
needs a hired agent, which needs a funded session key, which needs a faucet that
asks for human verification. So this reports the thing that is actually knowable
today and says plainly which question it is answering instead.
"""
import json, pathlib, datetime

DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"

# Four bars, each one a reason a hire would fail in practice rather than a
# quality score. An agent that cannot pay gas cannot act no matter how good it is.
BARS = [
    ("holds the position its category implies", "position"),
    ("can pay for its own gas",                 "gas"),
    ("acted in the last 30 days",               "active"),
    ("has sent at least 25 transactions",       "history"),
]

def bars(it):
    oc, ev, h = it["onchain"], it["evidence"], it["history"]
    idle = h.get("idle_days")
    return {
        "position": (ev.get("lp_positions") or 0) > 0 or (ev.get("venus_markets") or 0) > 0,
        "gas":      (oc.get("bnb") or 0) >= 0.001,
        "active":   idle is not None and idle < 30,
        "history":  (oc.get("txs") or 0) >= 25,
        "authority": (ev.get("altana_keys") or 0) > 0,
    }

def esc(s):
    return (str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            .replace('"',"&quot;"))

def main():
    idx = json.loads((DOCS/"data/index.json").read_text())
    cats = [(c, json.loads((DOCS/f"data/{c['id']}.json").read_text())) for c in idx["categories"]]

    uniq, rows = {}, []
    for meta, d in cats:
        tally = {k: 0 for _, k in BARS}
        tally["all"] = 0
        for it in d["items"]:
            b = bars(it)
            for _, k in BARS:
                tally[k] += b[k]
            passed = all(b[k] for _, k in BARS)
            tally["all"] += passed
            if it["agent_id"] not in uniq:
                uniq[it["agent_id"]] = (it, b, passed)
        rows.append((meta, len(d["items"]), tally))

    clears = [(it, b) for it, b, ok in uniq.values() if ok]
    clears.sort(key=lambda t: -(t[0]["onchain"].get("txs") or 0))
    n_uniq = len(uniq)

    def bar_cells(t, n):
        return "".join(
            f'<td class="num">{t[k]}<span class="of"> / {n}</span></td>' for _, k in BARS
        ) + f'<td class="num strong">{t["all"]}<span class="of"> / {n}</span></td>'

    table = "\n".join(
        f'<tr><th scope="row">{esc(m["label"])}</th>{bar_cells(t, n)}</tr>'
        for m, n, t in rows
    )

    def agent_block(it, b):
        oc, ev, h = it["onchain"], it["evidence"], it["history"]
        held = []
        if ev.get("lp_positions"): held.append(f'{ev["lp_positions"]} PancakeSwap position'
                                               f'{"" if ev["lp_positions"]==1 else "s"}')
        if ev.get("venus_markets"): held.append(f'{ev["venus_markets"]} Venus market'
                                                f'{"" if ev["venus_markets"]==1 else "s"}')
        auth = ("holds an Altana session key" if b["authority"]
                else "holds no session key, so it cannot act on anyone's behalf yet")
        return f"""<article class="agent">
  <h3>{esc(it["name"])}</h3>
  <dl class="kv">
    <div><dt>on-chain history</dt><dd class="num">{oc.get("txs",0):,} transactions over {h.get("active_span_days",0):.0f} days</dd></div>
    <div><dt>last acted</dt><dd class="num">{h.get("idle_days",0):.1f} days ago</dd></div>
    <div><dt>holds</dt><dd>{esc(", ".join(held) or "nothing")}</dd></div>
    <div><dt>gas runway</dt><dd class="num">{oc.get("bnb",0):.4f} BNB</dd></div>
    <div><dt>authority</dt><dd>{auth}</dd></div>
  </dl>
  <p class="src"><a href="https://bscscan.com/address/{esc(it.get("measured_address") or it.get("agent_wallet") or "")}" target="_blank" rel="noopener">verify this wallet on BscScan</a></p>
</article>"""

    agents = "\n".join(agent_block(it, b) for it, b in clears)
    built = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    head_th = "".join(f"<th scope=\"col\">{esc(label)}</th>" for label, _ in BARS)

    html = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Advantage Report — Vouch</title>
<link rel="icon" href="./icon.svg" type="image/svg+xml">
<link rel="stylesheet" href="./tokens.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
body{{background:var(--bg);color:var(--text);font-family:var(--font-sans);
  -webkit-font-smoothing:antialiased;line-height:1.55}}
.wrap{{max-width:900px;margin:0 auto;padding:var(--s-7) var(--s-5) var(--s-9)}}
a{{color:var(--text-accent)}}
header{{border-bottom:1px solid var(--hairline);padding-bottom:var(--s-5);margin-bottom:var(--s-7)}}
.up{{font-family:var(--font-mono);font-size:var(--t-caption);text-transform:uppercase;
  letter-spacing:.09em;color:var(--text-faint)}}
h1{{font-size:var(--t-lede-xl);line-height:1.2;letter-spacing:-.02em;font-weight:500;
  margin:var(--s-3) 0 0;max-width:26ch}}
h2{{font-size:var(--t-h3);font-weight:500;margin:var(--s-8) 0 var(--s-3);letter-spacing:-.01em}}
h3{{font-size:var(--t-sm);font-weight:600;margin:0 0 var(--s-3)}}
p{{color:var(--text-muted);font-size:var(--t-sm);max-width:74ch;margin:0 0 var(--s-4)}}
.figure{{font-family:var(--font-mono);font-weight:700;font-size:var(--t-figure);
  line-height:.86;letter-spacing:-.045em;color:var(--text-accent);margin:var(--s-5) 0 0}}
table{{width:100%;border-collapse:collapse;font-family:var(--font-mono);font-size:var(--t-meta);
  margin:var(--s-4) 0 var(--s-5)}}
th,td{{text-align:right;padding:var(--s-3) var(--s-2);border-bottom:1px solid var(--border-subtle)}}
thead th{{font-weight:400;color:var(--text-faint);font-size:var(--t-caption);
  text-transform:uppercase;letter-spacing:.06em;vertical-align:bottom;line-height:1.35}}
tbody th{{text-align:left;font-weight:500;color:var(--text);font-family:var(--font-sans);
  font-size:var(--t-sm)}}
.num{{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}}
.of{{color:var(--text-faint)}}
.strong{{color:var(--text-accent)}}
.agent{{border-top:1px solid var(--border-subtle);padding:var(--s-5) 0}}
.kv{{margin:0;font-family:var(--font-mono);font-size:var(--t-meta);
  display:grid;gap:var(--s-2)}}
.kv > div{{display:grid;grid-template-columns:minmax(0,13ch) 1fr;gap:var(--s-4)}}
.kv dt{{color:var(--text-faint)}}
.kv dd{{margin:0;color:var(--text)}}
.src{{margin:var(--s-3) 0 0;font-family:var(--font-mono);font-size:var(--t-meta)}}
.note{{border-left:2px solid var(--hairline);padding-left:var(--s-4);margin:var(--s-5) 0}}
footer{{margin-top:var(--s-9);padding-top:var(--s-5);border-top:1px solid var(--hairline);
  color:var(--text-faint);font-size:var(--t-meta);font-family:var(--font-mono)}}
a:focus-visible,:focus-visible{{outline:none;
  box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--ring);border-radius:var(--r-chip)}}
@media (max-width:620px){{
  .kv > div{{grid-template-columns:1fr}}
  table{{display:block;overflow-x:auto}}
}}
</style>
<div class="wrap">
<header>
  <p class="up">Vouch · Agent Advantage Report</p>
  <p class="figure">{len(clears)}</p>
  <h1>of {n_uniq} listed agents are worth hiring today on measured evidence.</h1>
</header>

<p>Hiring an agent through Vouch costs a session key, a spend cap and some gas. This report asks
what you get back. It does not score capability, because a registry listing is a claim and this
project exists on the argument that a claim is not evidence. It measures four things that decide
whether a hire can work at all.</p>

<ol>
{"".join(f"<li>{esc(l)}</li>" for l,_ in BARS)}
</ol>

<p>An agent that cannot pay its own gas cannot act however good it is. One that has never held the
position its category implies has not done the job it is listed for. One idle for a month may be
switched off. One with fewer than 25 transactions has not done enough for the record to mean
anything.</p>

<h2>How many clear each bar</h2>
<table>
  <thead><tr><th scope="col"></th>{head_th}<th scope="col">all four</th></tr></thead>
  <tbody>
{table}
  </tbody>
</table>
<p>Counts are per category listing. {n_uniq} unique agents hold the {sum(n for _,n,_ in rows)}
listings, so an agent listed in two categories is counted in both rows above and once in the
figure at the top.</p>

<h2>The agents that clear all four</h2>
{agents}

<h2>What this does not measure</h2>
<div class="note">
<p>Realized profit and loss, maximum drawdown and revert rate are the numbers that would actually
rank these three against each other. They need full per-transaction history, which needs an
indexer this project does not run. Every public BNB Chain node refuses a full-range
<code>eth_getLogs</code>, so the record here is transaction count with recovered first and last
active dates: a floor, not a complete track record.</p>
<p>The original report design was three tasks run with an agent and without, timed and costed. That
needs a granted session key, which needs a funded wallet, which needs a faucet that asks for human
verification. Rather than describe a comparison that was never run, this reports the question that
the measured data can answer today.</p>
</div>

<footer>
  Generated by <code>scripts/build-advantage.py</code> from the same data the marketplace reads.
  Built {built}. <a href="./">Back to the marketplace</a>.
</footer>
</div>
"""
    (DOCS/"advantage.html").write_text(html)
    print(f"advantage.html: {len(clears)} of {n_uniq} clear all four bars")

if __name__ == "__main__":
    main()
