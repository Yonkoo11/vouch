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
        "health_score", "created_at", "supported_protocols"]


def get_json(url, timeout=25, tries=4):
    """Retry with backoff. The registry rate-limits, and a silently empty
    category would be worse than a slow build."""
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "vouch-build/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            time.sleep(1.5 * (n + 1))
    raise last if last else RuntimeError(f"failed to fetch {url}")


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


# Protocol contracts on BSC. These let us check whether an agent's owner has
# ever taken the kind of position its listing claims to manage.
PCS_V3_POSITIONS = "0x46A15B0b27311cedF172AB29E4f4766fbE7F4364"  # NonfungiblePositionManager
VENUS_COMPTROLLER = "0xfD36E2c2a6789Db23113685031d7F16329158384"
CAKE = "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"

# Altana's Keystore records which keys may act on a wallet. It is a public read,
# so a marketplace can verify an agent's authority without integrating anything.
ALTANA_KEYSTORE = "0x6572427ED530BadcF7375Cf9A4709D8d2b0E7E0a"  # BNB mainnet

SEL_BALANCE_OF = "0x70a08231"   # balanceOf(address)
SEL_ASSETS_IN = "0xabfceffc"    # getAssetsIn(address)
SEL_GET_KEYS = "0x34e80c34"     # getKeys(address)


def _pad(addr):
    return addr.lower().replace("0x", "").rjust(64, "0")


def evidence(addresses):
    """
    Ask the protocols directly: does this address hold an LP position, has it
    entered a lending market, does it hold CAKE? A listing that claims to manage
    PancakeSwap liquidity while holding no position is making a claim the chain
    does not support.
    """
    out = {}
    for i in range(0, len(addresses), 12):
        chunk = addresses[i:i + 12]
        batch, idmap = [], {}
        rid = 0
        for a in chunk:
            calls = [
                ("lp_positions", PCS_V3_POSITIONS, SEL_BALANCE_OF + _pad(a)),
                ("venus_markets", VENUS_COMPTROLLER, SEL_ASSETS_IN + _pad(a)),
                ("cake", CAKE, SEL_BALANCE_OF + _pad(a)),
                ("altana_keys", ALTANA_KEYSTORE, SEL_GET_KEYS + _pad(a)),
            ]
            for key, to, data in calls:
                idmap[rid] = (a, key)
                batch.append({"jsonrpc": "2.0", "id": rid, "method": "eth_call",
                              "params": [{"to": to, "data": data}, "latest"]})
                rid += 1
        res = rpc(batch)
        if not isinstance(res, list):
            print("    protocol batch failed", file=sys.stderr)
            continue
        for item in res:
            addr, key = idmap.get(item.get("id"), (None, None))
            v = item.get("result")
            if not addr or v in (None, "0x"):
                continue
            d = out.setdefault(addr, {})
            try:
                if key in ("venus_markets", "altana_keys"):
                    # dynamic array: word 0 is the offset, word 1 the length
                    body = v[2:]
                    d[key] = int(body[64:128], 16) if len(body) >= 128 else 0
                elif key == "cake":
                    d[key] = int(v, 16) / 1e18
                else:
                    d[key] = int(v, 16)
            except Exception:
                pass
        time.sleep(0.3)
    return out


def detail(chain_id, token_id):
    """
    The list endpoint omits the fields that matter most: the wallet the registry
    itself declares for the agent, and whether 8004scan could verify the agent's
    published endpoint. Measuring owner_address when a separate agent_wallet is
    declared would be measuring the wrong address, so fetch it.
    """
    try:
        d = get_json(f"https://api.8004scan.io/api/v1/agents/{chain_id}/{token_id}")
        return {
            "agent_wallet": d.get("agent_wallet") or d.get("owner_address"),
            "creator_address": d.get("creator_address"),
            "is_endpoint_verified": d.get("is_endpoint_verified"),
            "endpoint_error": (d.get("endpoint_verification_error") or "")[:240] or None,
            "wallet_score": d.get("wallet_score"),
            "supported_protocols": d.get("supported_protocols"),
        }
    except Exception:
        return {}


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
            time.sleep(0.5)

        if not rows:
            raise SystemExit(f"FATAL: category {cid!r} returned no agents. "
                             "Refusing to write an empty category and pretend it is a result.")
        rows.sort(key=lambda r: (r.get("total_score") or 0), reverse=True)
        rows = rows[:PER_CATEGORY]

        print(f"    fetching declared wallet + endpoint verification for {len(rows)} agents")
        for r in rows:
            r.update(detail(CHAIN, r["token_id"]))
            r["measured_address"] = r.get("agent_wallet") or r.get("owner_address")
            time.sleep(0.35)

        addrs = sorted({r["measured_address"] for r in rows if r.get("measured_address")})
        print(f"    {len(rows)} agents, measuring {len(addrs)} owner addresses on BSC")
        chain = measure(addrs)
        print(f"    checking protocol positions for {len(addrs)} addresses")
        proto = evidence(addrs)
        measured = 0
        for r in rows:
            m = chain.get(r.get("measured_address"))
            if m and "txs" in m:
                r["onchain"] = m
                measured += 1
            else:
                r["onchain"] = None
            r["evidence"] = proto.get(r.get("measured_address")) or None

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
        owners[r.get("measured_address")] = owners.get(r.get("measured_address"), 0) + 1

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
        "altana_authorised": sum(1 for r in rows
                                  if (r.get("evidence") or {}).get("altana_keys")),
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
            ev = a.get("evidence") or {}
            # Does the chain support the category this listing is filed under?
            if cid in ("rebalancing",):
                supported = (ev.get("lp_positions") or 0) > 0
            elif cid in ("health",):
                supported = (ev.get("venus_markets") or 0) > 0
            elif cid in ("yield",):
                supported = ((ev.get("venus_markets") or 0) > 0
                             or (ev.get("cake") or 0) > 0
                             or (ev.get("lp_positions") or 0) > 0)
            else:
                supported = None  # grid trading has no single protocol to check
            a["flags"] = {
                "quiet": oc.get("txs") is not None and oc["txs"] < 5,
                "no_gas": oc.get("bnb") is not None and oc["bnb"] < 0.001,
                "no_feedback": not a.get("total_feedbacks"),
                "owner_agents": owners.get(a.get("measured_address"), 1),
                "category_supported": supported,
            }
        chk = [a for a in payload["items"] if a["flags"]["category_supported"] is not None]
        ok = sum(1 for a in chk if a["flags"]["category_supported"])
        payload["category_check"] = {"checked": len(chk), "supported": ok}
        if chk:
            print(f"  {cid:13} category claim supported on-chain for {ok}/{len(chk)} agents")
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
