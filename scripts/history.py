#!/usr/bin/env python3
"""
Turn a nonce into a track record.

There is no free transaction-history API for BSC, and full-range eth_getLogs is
refused by every public node. But an archive node will answer
eth_getTransactionCount at a historical block, and a nonce is monotonic. So a
binary search over block height recovers two real dates from public data alone:

  first_active  — the block where the wallet's nonce first left zero
  last_active   — the block where it first reached the value it still has

That gives "sent 40 transactions" a shape: when it started, when it stopped, and
how long it has been idle. An agent that sent every one of its transactions
eight months ago is a different proposition from one that sent them yesterday,
and the registry shows neither.

All searches run in lockstep across every address so each round is one batched
RPC call rather than one per wallet.
"""
import json, time, urllib.request

ARCHIVE_RPCS = [
    "https://bsc-mainnet.public.blastapi.io",
    "https://bsc.drpc.org",
]

# Both archive nodes reject urllib's default agent: blastapi with a 403, drpc by
# dropping the TLS record. A normal browser agent is all either one wants.
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}


def rpc(batch, tries=3):
    body = json.dumps(batch).encode()
    for attempt in range(tries):
        for url in ARCHIVE_RPCS:
            try:
                req = urllib.request.Request(url, data=body, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=45) as r:
                    out = json.loads(r.read().decode())
                if isinstance(out, list) and out:
                    return out
                if isinstance(out, dict) and "result" in out:
                    return out
            except Exception:
                continue
        time.sleep(1.5 * (attempt + 1))
    return None


def latest_block():
    r = rpc({"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []})
    if isinstance(r, dict) and r.get("result"):
        return int(r["result"], 16)
    return None


def _nonces(addresses, blocks):
    """One batched round: nonce for each (address, block) pair."""
    batch, idmap = [], {}
    for i, (a, b) in enumerate(zip(addresses, blocks)):
        idmap[i] = a
        batch.append({"jsonrpc": "2.0", "id": i, "method": "eth_getTransactionCount",
                      "params": [a, hex(b)]})
    res = rpc(batch)
    out = {}
    if not isinstance(res, list):
        return out
    for item in res:
        a = idmap.get(item.get("id"))
        v = item.get("result")
        if a and v:
            try:
                out[a] = int(v, 16)
            except ValueError:
                pass
    return out


def _search(addresses, head, predicate_target):
    """
    Smallest block where nonce(addr) >= target(addr), by binary search run in
    lockstep across every address. Returns {addr: block or None}.
    """
    lo = {a: 0 for a in addresses}
    hi = {a: head for a in addresses}
    live = [a for a in addresses if predicate_target.get(a)]
    rounds = 0
    while live and rounds < 34:
        mids = [(lo[a] + hi[a]) // 2 for a in live]
        got = _nonces(live, mids)
        if not got:
            break
        nxt = []
        for a, mid in zip(live, mids):
            n = got.get(a)
            if n is None:
                continue
            if n >= predicate_target[a]:
                hi[a] = mid
            else:
                lo[a] = mid + 1
            if lo[a] < hi[a]:
                nxt.append(a)
        live = nxt
        rounds += 1
        time.sleep(0.12)
    return {a: (hi[a] if hi[a] < head else None) for a in addresses}


def block_times(blocks):
    """Unix timestamp for each block number."""
    uniq = sorted({b for b in blocks if b})
    out = {}
    for i in range(0, len(uniq), 25):
        chunk = uniq[i:i + 25]
        batch = [{"jsonrpc": "2.0", "id": n, "method": "eth_getBlockByNumber",
                  "params": [hex(b), False]} for n, b in enumerate(chunk)]
        res = rpc(batch)
        if not isinstance(res, list):
            continue
        for item in res:
            r = item.get("result") or {}
            if r.get("number") and r.get("timestamp"):
                out[int(r["number"], 16)] = int(r["timestamp"], 16)
        time.sleep(0.2)
    return out


def records(addresses, current_nonces, head=None):
    """
    {addr: {first_active_block, last_active_block, first_active_ts,
            last_active_ts, idle_days, active_span_days}}
    Addresses that have never sent a transaction get None throughout.
    """
    head = head or latest_block()
    if not head:
        return {}
    live = [a for a in addresses if (current_nonces.get(a) or 0) > 0]
    if not live:
        return {a: None for a in addresses}  # type: ignore[return-value]

    first = _search(live, head, {a: 1 for a in live})
    last = _search(live, head, {a: current_nonces[a] for a in live})

    ts = block_times(list(first.values()) + list(last.values()))
    now = time.time()
    out: dict = {a: None for a in addresses}
    for a in live:
        fb, lb = first.get(a), last.get(a)
        ft, lt = ts.get(fb), ts.get(lb)
        out[a] = {
            "first_active_block": fb,
            "last_active_block": lb,
            "first_active_ts": ft,
            "last_active_ts": lt,
            "idle_days": round((now - lt) / 86400, 1) if lt else None,
            "active_span_days": round((lt - ft) / 86400, 1) if (ft and lt) else None,
        }
    return out


if __name__ == "__main__":
    import sys
    addrs = sys.argv[1:] or ["0x20f1ca5d1e5a3ee94c29dbf95e6bf6cea6a8d64b"]
    head = latest_block()
    cur = _nonces(addrs, [head] * len(addrs))
    print("head", head, "nonces", cur)
    for a, r in records(addrs, cur, head).items():
        print(a, json.dumps(r))
