#!/usr/bin/env python3
"""
Build the category datasets Vouch serves.

For each of the four hackathon categories, this queries the 8004scan registry
server-side (which sidesteps the browser CORS restriction), dedupes, then reads
each agent owner's real state off a BSC node: transactions sent, gas runway,
and whether the address is a contract or an EOA.

Nothing here is invented. An agent with no history gets nulls, and the page
renders that as "insufficient history" rather than a zero dressed up as a score.

    python3 scripts/build-data.py
"""
import json, time, urllib.request, urllib.parse, datetime, sys
from pathlib import Path

API = "https://api.8004scan.io/api/v1/agents"
RPCS = [
    "https://bsc-dataseed.binance.org",
    "https://bsc-dataseed1.defibit.io",
    "https://bsc-dataseed2.bnbchain.org",
]
CHAIN = 56
OUT = Path(__file__).resolve().parent.parent / "docs" / "data"
PER_CATEGORY = 24

CATEGORIES = {
    "rebalancing": {
        "label": "Rebalancing",
        "blurb": "Manages LP ranges and resets positions. Measured on range uptime, "
                 "fees captured against impermanent loss, and reset frequency.",
        "terms": ["rebalance", "liquidity", "LP", "concentrated liquidity", "pool"],
    },
    "grid": {
        "label": "Grid Trading",
        "blurb": "Places and manages automated grid orders. Measured on fill rate, "
                 "realized spread capture, and inventory skew.",
        "terms": ["grid", "trading", "market maker", "DCA", "arbitrage"],
    },
    "yield": {
        "label": "Yield Optimisation",
        "blurb": "Routes liquidity to the highest available APR. Measured on realized "
                 "APR against advertised, rotation cost, and idle time.",
        "terms": ["yield", "APY", "staking", "vault", "farming", "lending"],
    },
    "health": {
        "label": "Health Factor",
        "blurb": "Protects lending positions from liquidation. Measured on time-to-react, "
                 "liquidations avoided, and false-alarm rate.",
        "terms": ["health factor", "liquidation", "collateral", "risk monitor", "position monitor"],
    },
}

KEEP = ["agent_id", "token_id", "contract_address", "owner_address", "name", "description",
        "is_verified", "x402_supported", "total_score", "average_score", "total_feedbacks",
        "health_score", "created_at"]


def get_json(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "vouch-build/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def rpc(batch):
    body = json.dumps(batch).encode()
    for url in RPCS:
        try:
            req = urllib.request.Request(
                url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except Exception:
            continue
    return None


def search(term, limit=20):
    q = urllib.parse.urlencode({
        "chain_id": CHAIN, "limit": limit, "search": term,
        "sort_by": "total_score", "sort_order": "desc", "is_testnet": "false",
    })
    try:
        return get_json(f"{API}?{q}").get("items", [])
    except Exception as e:
        print(f"    search({term!r}) failed: {e}", file=sys.stderr)
        return []


def measure(addresses):
    """Read tx count, balance and code for each address off a BSC node."""
    out = {}
    for i in range(0, len(addresses), 20):
        chunk = addresses[i:i + 20]
        batch, idmap = [], {}
        for n, a in enumerate(chunk):
            for k, method in enumerate(("eth_getTransactionCount", "eth_getBalance", "eth_getCode")):
                rid = n * 3 + k
                idmap[rid] = (a, method)
                batch.append({"jsonrpc": "2.0", "id": rid, "method": method,
                              "params": [a, "latest"]})
        res = rpc(batch)
        if not isinstance(res, list):
            print("    RPC batch failed, addresses left unmeasured", file=sys.stderr)
            continue
        for item in res:
            addr, method = idmap.get(item.get("id"), (None, None))
            if not addr:
                continue
            d = out.setdefault(addr, {})
            v = item.get("result")
            if v is None:
                continue
            if method == "eth_getTransactionCount":
                d["txs"] = int(v, 16)
            elif method == "eth_getBalance":
                d["bnb"] = int(v, 16) / 1e18
            else:
                d["kind"] = "contract" if v not in (None, "0x") else "EOA"
        time.sleep(0.3)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    index = {"built_at": stamp, "chain_id": CHAIN,
             "registry": "8004scan", "categories": []}

    for cid, cfg in CATEGORIES.items():
        print(f"[{cid}] querying {len(cfg['terms'])} terms")
        seen, rows = set(), []
        for term in cfg["terms"]:
            for a in search(term):
                if a["agent_id"] in seen:
                    continue
                seen.add(a["agent_id"])
                rows.append({k: a.get(k) for k in KEEP})
            time.sleep(0.25)

        rows.sort(key=lambda r: (r.get("total_score") or 0), reverse=True)
        rows = rows[:PER_CATEGORY]

        addrs = sorted({r["owner_address"] for r in rows if r.get("owner_address")})
        print(f"    {len(rows)} agents, measuring {len(addrs)} owner addresses on BSC")
        chain = measure(addrs)
        measured = 0
        for r in rows:
            m = chain.get(r.get("owner_address"))
            if m and "txs" in m:
                r["onchain"] = m
                measured += 1
            else:
                r["onchain"] = None

        never = sum(1 for r in rows if r.get("onchain") and r["onchain"]["txs"] == 0)
        norep = sum(1 for r in rows if not (r.get("total_feedbacks") or r.get("total_score")))
        print(f"    measured {measured}/{len(rows)} · never executed {never} · no reputation {norep}")

        payload = {"category": cid, "label": cfg["label"], "blurb": cfg["blurb"],
                   "terms": cfg["terms"], "built_at": stamp, "count": len(rows),
                   "measured": measured, "never_executed": never, "items": rows}
        (OUT / f"{cid}.json").write_text(json.dumps(payload, indent=1))
        index["categories"].append({"id": cid, "label": cfg["label"], "blurb": cfg["blurb"],
                                    "count": len(rows), "measured": measured,
                                    "never_executed": never})

    # Cross-category findings. These are the numbers that justify the product,
    # so they are computed from the same rows the page renders, not asserted.
    allrows = {}
    for cid in CATEGORIES:
        for a in json.loads((OUT / f"{cid}.json").read_text())["items"]:
            allrows[a["agent_id"]] = a
    rows = list(allrows.values())
    meas = [r for r in rows if r.get("onchain")]

    owners = {}
    for r in rows:
        owners[r.get("owner_address")] = owners.get(r.get("owner_address"), 0) + 1

    top20 = sorted(meas, key=lambda r: -(r.get("total_score") or 0))[:20]
    quiet = [r for r in top20 if r["onchain"]["txs"] < 5]
    broke = [r for r in quiet if (r["onchain"].get("bnb") or 0) < 0.001]

    def corr(pairs):
        n = len(pairs)
        if n < 2:
            return None
        ms = sum(p[0] for p in pairs) / n
        mt = sum(p[1] for p in pairs) / n
        cov = sum((a - ms) * (b - mt) for a, b in pairs)
        va = sum((a - ms) ** 2 for a, _ in pairs) ** 0.5
        vb = sum((b - mt) ** 2 for _, b in pairs) ** 0.5
        return round(cov / (va * vb), 3) if va and vb else None

    txs = sorted(r["onchain"]["txs"] for r in meas)
    findings = {
        "built_at": stamp,
        "agents": len(rows),
        "measured": len(meas),
        "top20_under_5_tx": len(quiet),
        "top20_cannot_pay_gas": len(broke),
        "distinct_owners": len(owners),
        "largest_owner_agents": max(owners.values()) if owners else 0,
        "zero_feedback": sum(1 for r in rows if not r.get("total_feedbacks")),
        "median_tx": txs[len(txs) // 2] if txs else None,
        "score_activity_correlation": corr(
            [((r.get("total_score") or 0), r["onchain"]["txs"]) for r in meas]),
    }
    index["findings"] = findings

    # Flag each agent where the registry score and the chain disagree.
    for cid in CATEGORIES:
        p = OUT / f"{cid}.json"
        payload = json.loads(p.read_text())
        for a in payload["items"]:
            oc = a.get("onchain") or {}
            a["flags"] = {
                "quiet": oc.get("txs") is not None and oc["txs"] < 5,
                "no_gas": oc.get("bnb") is not None and oc["bnb"] < 0.001,
                "no_feedback": not a.get("total_feedbacks"),
                "owner_agents": owners.get(a.get("owner_address"), 1),
            }
        p.write_text(json.dumps(payload, indent=1))

    (OUT / "index.json").write_text(json.dumps(index, indent=1))
    print("\nwrote", OUT)
    for c in index["categories"]:
        print(f"  {c['id']:13} {c['count']:>3} agents  {c['measured']:>3} measured  "
              f"{c['never_executed']:>3} never executed")
    print("\nfindings:")
    for k, v in findings.items():
        print(f"  {k:32} {v}")


if __name__ == "__main__":
    main()
