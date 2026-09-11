// Vouch — agent authority and hiring.
//
// Two things live here.
//
// 1. verifyAuthority(wallet) reads Altana's Keystore directly over a public RPC.
//    No SDK, no key, no wallet connection: it is the same eth_call anyone can
//    make, which is the point. A marketplace should be able to prove what an
//    agent may do without asking anyone to trust the marketplace.
//
// 2. hire() grants a scoped session to an agent: a call allowlist, a spend cap
//    and an expiry, registered on-chain in the Keystore. The user signs it in
//    their own wallet. Vouch never holds a key and never moves funds.
//
// Hiring targets BNB Smart Chain Testnet (chain 97). The Altana track counts
// testnet, and it means nobody risks real money to try the product.

export const NETWORKS = {
  56: {
    name: 'BNB Smart Chain',
    rpc: ['https://bsc-dataseed.binance.org', 'https://bsc-rpc.publicnode.com'],
    keystore: '0x6572427ED530BadcF7375Cf9A4709D8d2b0E7E0a',
    explorer: 'https://bscscan.com',
    keystoreExplorer: 'https://explorer.altana.network',
  },
  97: {
    name: 'BNB Smart Chain Testnet',
    rpc: ['https://bsc-testnet-rpc.publicnode.com', 'https://data-seed-prebsc-1-s1.bnbchain.org:8545'],
    keystore: '0x6b8361C29d05D498b1a12B54A37310f94171E94A',
    explorer: 'https://testnet.bscscan.com',
    keystoreExplorer: 'https://testnet.altana.network',
    faucet: 'https://testnet.bnbchain.org/faucet-smart',
  },
};

const SEL_GET_KEYS = '0x34e80c34';     // getKeys(address)
const SEL_IS_VALID_KEY = '0x8fd4f06b'; // isValidKey(address,bytes32)

const pad = a => a.toLowerCase().replace(/^0x/, '').padStart(64, '0');
const padHex = h => h.replace(/^0x/, '').padStart(64, '0');

async function call(chainId, to, data) {
  const net = NETWORKS[chainId];
  for (const url of net.rpc) {
    try {
      const r = await fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_call',
                               params: [{ to, data }, 'latest'] }),
      });
      if (!r.ok) continue;
      const j = await r.json();
      if (j.error) throw new Error(j.error.message);
      if (j.result) return j.result;
    } catch (e) { /* try the next node */ }
  }
  return null;
}

function decodeBytes32Array(hex) {
  if (!hex || hex === '0x') return [];
  const body = hex.slice(2);
  if (body.length < 128) return [];
  const len = parseInt(body.slice(64, 128), 16);
  const out = [];
  for (let i = 0; i < len; i++) out.push('0x' + body.slice(128 + i * 64, 192 + i * 64));
  return out;
}

/**
 * What may act on this wallet, according to the chain.
 * Returns { keys: [{ id, active }], total, active } or null if unreadable.
 */
const isAddress = a => /^0x[a-fA-F0-9]{40}$/.test(String(a || ''));

export async function verifyAuthority(wallet, chainId = 56) {
  const net = NETWORKS[chainId];
  if (!net) throw new Error('unsupported chain ' + chainId);
  // The address comes from the registry, so it is attacker controlled. Refusing
  // a malformed one here stops it reaching an href or an eth_call downstream.
  if (!isAddress(wallet)) throw new Error('not a valid address: ' + String(wallet).slice(0, 60));
  const raw = await call(chainId, net.keystore, SEL_GET_KEYS + pad(wallet));
  if (raw == null) return null;
  const ids = decodeBytes32Array(raw);
  // isValidKey is true only when a key exists, is unrevoked and unexpired.
  const keys = await Promise.all(ids.map(async id => {
    const r = await call(chainId, net.keystore,
                         SEL_IS_VALID_KEY + pad(wallet) + padHex(id));
    return { id, active: r != null && /1$/.test(r) };
  }));
  return {
    keys,
    total: keys.length,
    active: keys.filter(k => k.active).length,
    explorer: `${net.keystoreExplorer}/account/${wallet}`,
  };
}

/** Native balance in whole units, or null if no node answered. */
export async function nativeBalance(address, chainId = 97) {
  const net = NETWORKS[chainId];
  for (const url of net.rpc) {
    try {
      const r = await fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_getBalance',
                               params: [address, 'latest'] }),
      });
      const j = await r.json();
      if (j.result) return parseInt(j.result, 16) / 1e18;
    } catch (e) { /* next node */ }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Hiring
// ---------------------------------------------------------------------------

let sdk = null;

/* A passkey wallet that has been created but has never executed a transaction.
   Reading the SDK settles why this has to exist: createPasskeyWallet mints a
   fresh passkey, writes the new wallet address into its userHandle, and
   PRE-SIGNS the admin-key registration — that registration only reaches the
   Keystore when the wallet first executes. So recoverFromPasskey cannot work
   before the first grant, by construction, and every retry before then was
   calling createPasskeyWallet again and getting a different address.

   That is how funds get stranded: the page asks for gas at address A, the user
   funds A, presses Grant again, and the retry mints address B and asks again.
   Verified against a virtual authenticator — two calls, two credentials, two
   addresses. Holding the wallet for the life of the page closes that loop. */
let pendingWallet = null;   // { address, signer, chainId }

/* The in-memory hold above dies on reload, and a reload is exactly what a user
   does while waiting on a faucet. What gets written here is the passkey's
   public half only — credential id, public key, rpId, 243 bytes of JSON. The
   private key never leaves the passkey and nothing here can sign on its own;
   signerFromPasskey rebuilds the signer around it and every signature still
   goes through the WebAuthn ceremony. Cleared the moment the grant lands. */
const PENDING_KEY = 'vouch.pending-wallet.v1';

function rememberPending(address, signer, chainId) {
  pendingWallet = { address, signer, chainId };
  try {
    const cred = signer && signer.credential;
    if (!cred) return;
    localStorage.setItem(PENDING_KEY, JSON.stringify({ address, credential: cred, chainId }));
  } catch (e) { /* private mode, or storage disabled. The in-memory hold stands. */ }
}

function forgetPending() {
  pendingWallet = null;
  try { localStorage.removeItem(PENDING_KEY); } catch (e) { /* nothing to clear */ }
}

/** A wallet created in an earlier page load whose first grant never landed. */
function readPending(chainId, signerFromPasskey) {
  try {
    const raw = localStorage.getItem(PENDING_KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw);
    if (!saved || saved.chainId !== chainId || !saved.address || !saved.credential) return null;
    return { address: saved.address, signer: signerFromPasskey(saved.credential, {}), chainId };
  } catch (e) { return null; }
}

// Two CDNs, because one blocked CDN should not take the whole feature down.
// Ad blockers and corporate DNS reach esm.sh far more often than jsdelivr.
export const SDK_SOURCES = [
  'https://esm.sh/@altananetwork/sdk@0.9.0',
  'https://cdn.jsdelivr.net/npm/@altananetwork/sdk@0.9.0/+esm',
];

async function loadSdk() {
  if (sdk) return sdk;
  const failures = [];
  for (const url of SDK_SOURCES) {
    try {
      sdk = await import(/* @vite-ignore */ url);
      if (sdk && sdk.createClient) return sdk;
      failures.push(url + ': loaded but exported no createClient');
    } catch (e) {
      failures.push(url + ': ' + String((e && e.message) || e).slice(0, 90));
    }
  }
  const err = new Error(
    'Could not load the Altana SDK from any CDN. An ad blocker or network filter is the usual ' +
    'cause. Details — ' + failures.join(' | '));
  err.code = 'SDK_UNREACHABLE';
  throw err;
}

/**
 * Report which moving parts work in THIS browser, so a dead button becomes a
 * readable list instead of something the user has to characterise for us.
 */
export async function diagnose(chainId = 97) {
  const out = [];
  const add = (name, ok, note) => out.push({ name, ok, note: note || '' });

  add('WebAuthn (passkeys) available', typeof window.PublicKeyCredential === 'function',
      typeof window.PublicKeyCredential === 'function' ? '' : 'this browser cannot create a passkey');
  try {
    const av = window.PublicKeyCredential &&
      await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    add('Touch ID / platform authenticator', !!av, av ? '' : 'no platform authenticator on this device');
  } catch (e) { add('Touch ID / platform authenticator', false, String(e).slice(0, 80)); }

  add('secure context (https)', window.isSecureContext, window.isSecureContext ? '' : 'passkeys need https');

  for (const url of SDK_SOURCES) {
    try {
      const m = await import(/* @vite-ignore */ url);
      add('SDK from ' + new URL(url).hostname, !!(m && m.createClient));
      break;
    } catch (e) {
      add('SDK from ' + new URL(url).hostname, false, String((e && e.message) || e).slice(0, 80));
    }
  }

  const net = NETWORKS[chainId];
  for (const url of net.rpc) {
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_blockNumber', params: [] }) });
      const j = await r.json();
      add('testnet RPC ' + new URL(url).hostname, !!j.result,
          j.result ? 'block ' + parseInt(j.result, 16) : '');
      break;
    } catch (e) { add('testnet RPC ' + new URL(url).hostname, false, String(e).slice(0, 70)); }
  }
  return out;
}

/** Contracts a hired agent is allowed to touch, per category. */
export const CALL_ALLOWLIST = {
  rebalancing: [
    { to: '0x46A15B0b27311cedF172AB29E4f4766fbE7F4364', label: 'PancakeSwap V3 positions' },
  ],
  yield: [
    { to: '0xfD36E2c2a6789Db23113685031d7F16329158384', label: 'Venus comptroller' },
  ],
  health: [
    { to: '0xfD36E2c2a6789Db23113685031d7F16329158384', label: 'Venus comptroller' },
  ],
  grid: [
    { to: '0x13f4EA83D0bd40E75C8222255bc855a974568Dd4', label: 'PancakeSwap V3 router' },
  ],
};

/**
 * Grant an agent a scoped session on the user's Altana wallet.
 *
 * Nothing here custodies anything. The user's passkey is the admin authority,
 * the session key is what the agent gets, and the limits are enforced on-chain
 * at validation time rather than by our UI.
 *
 * Exercised against a Chrome virtual WebAuthn authenticator (scripts/test-hire.mjs),
 * which is how the createPasskeyWallet call-shape bug was found. See that script
 * for exactly how far the automated run gets.
 */
export async function hire({ agent, category, spendCapWei, hours = 24, chainId = 97, onStep }) {
  const step = onStep || (() => {});
  const net = NETWORKS[chainId];
  if (!net) throw new Error('unsupported chain ' + chainId);

  step('loading the Altana SDK');
  const sdkm = await loadSdk();
  const { createClient, createPrivateKeySigner, signerFromPasskey, BNB, BNB_TESTNET } = sdkm;
  const chain = chainId === 97 ? BNB_TESTNET : BNB;
  const client = createClient({ chains: [chain] });

  // Recover before creating. recoverFromPasskey is a pure read — two eth_calls,
  // no transaction, no cost — so a returning user lands back on the wallet they
  // already funded. Minting a fresh wallet every hire, which is what this did
  // first, would force the user through the faucet on every single hire.
  let wallet = null, recoverError = null;

  // A retry after funding has to land on the wallet the user just funded, not a
  // fresh one. Nothing below runs on a retry within the same page.
  if (pendingWallet && pendingWallet.chainId === chainId) {
    wallet = pendingWallet;
    step('reusing the wallet from this page session ' + wallet.address.slice(0, 10) + '…');
  } else {
    const saved = readPending(chainId, signerFromPasskey);
    if (saved) {
      wallet = pendingWallet = saved;
      step('picking up the wallet you were funding ' + wallet.address.slice(0, 10) + '…');
    }
  }

  if (!wallet) {
  step('looking for a wallet you already have');
  try {
    // rpId must match the page's origin; passing it explicitly avoids relying
    // on a default that differs between browser and embedded runtimes.
    wallet = await client.recoverFromPasskey({ rpId: location.hostname });
    step('recovered your existing wallet ' + wallet.address.slice(0, 10) + '…');
  } catch (e) {
    // Falling back silently would hide a broken recovery path behind a working
    // create path, and the user would pay a faucet trip for every hire.
    recoverError = String((e && e.message) || e);

    // The SDK refuses to hand back a wallet whose keys are not in the Keystore
    // yet, which is exactly the state of a wallet that was funded but whose
    // first grant never landed. Creating a fresh wallet here would strand that
    // funding in an address the user can never reach again, so surface it.
    const m = recoverError.match(/0x[a-fA-F0-9]{40}/);
    if (m) {
      const pending = m[0];
      const bal = await nativeBalance(pending, chainId);
      // This address cannot be used, and saying "fund it" was wrong. The passkey
      // carries the address in its userHandle, but the SDK rebuilds a signer
      // from the admin key in the Keystore, and this wallet never executed a
      // transaction so that key never landed. A WebAuthn assertion does not
      // carry the public key, so the signer cannot be reconstructed from the
      // passkey alone. Funding it sends money somewhere nothing can sign for.
      const err = new Error(
        `A passkey on this device points at wallet ${pending}` +
        `${bal ? ` holding ${bal} tBNB` : ''}, but that wallet never completed its first ` +
        `transaction, so its admin key was never registered on-chain and no signer can be ` +
        `rebuilt for it. Do not send anything to that address — it cannot be spent from. ` +
        `Press Grant session again to create a fresh wallet; this page will then keep that ` +
        `one until the grant lands, so you fund a single address once.`);
      err.code = 'UNRECOVERABLE_WALLET';
      err.wallet = pending;
      err.faucet = net.faucet;
      throw err;
    }

    step('no existing wallet found (' + recoverError.slice(0, 120) + ')');
    step('creating a new passkey wallet — approve the biometric prompt');
    wallet = await client.createPasskeyWallet({ name: 'Vouch', rpId: location.hostname });
    // Held from here so a retry after funding reuses it rather than minting
    // another one and stranding whatever was just sent.
    rememberPending(wallet.address, wallet.signer, chainId);
  }
  }

  // The session grant is an on-chain write from the new wallet, so it needs gas.
  // Checking first turns an opaque "Reason: 0x" revert into an instruction.
  step('checking the new wallet has gas');
  const bal = await nativeBalance(wallet.address, chainId);
  if (bal !== null && bal === 0) {
    const err = new Error(
      `Your wallet ${wallet.address} holds 0 tBNB, so the session grant would revert. ` +
      `Fund it from ${net.faucet} and press Grant session again. This page holds this ` +
      `wallet until the grant lands, so the retry uses this same address — you fund it once.`);
    err.code = 'NEEDS_FUNDING';
    err.wallet = wallet.address;
    err.faucet = net.faucet;
    throw err;
  }

  const allow = CALL_ALLOWLIST[category] || [];
  const expiry = Math.floor(Date.now() / 1000) + hours * 3600;

  step('granting a session scoped to ' + (allow.length || 0) + ' contract(s)');
  const session = await client.grantSession({
    wallet,
    signer: wallet.signer,
    // The SDK generates the agent's key; the agent never sees the passkey.
    sessionSigner: createPrivateKeySigner(),
    permissions: {
      calls: allow.map(a => ({ to: a.to })),
      spend: [{ limit: BigInt(spendCapWei), period: 'day' }],
    },
    expiry,
  });

  step('confirming the session is recorded in the Keystore');
  const authority = await verifyAuthority(wallet.address, chainId);

  // The grant carried the pre-signed admin-key registration on-chain, so this
  // wallet is recoverable from its passkey from now on. Holding it any longer
  // would keep a stale signer alive across hires.
  forgetPending();

  return {
    wallet: wallet.address,
    session,
    expiry,
    allow,
    authority,
    txHash: session?.transactionHash || null,
    recoverError: recoverError ? recoverError.slice(0, 200) : null,
    explorer: `${net.keystoreExplorer}/account/${wallet.address}`,
    agent: agent?.name,
  };
}

/** Revoke in one transaction. The agent stops being able to act immediately. */
export async function revoke({ wallet, session, chainId = 97 }) {
  const { createClient, BNB, BNB_TESTNET } = await loadSdk();
  const chain = chainId === 97 ? BNB_TESTNET : BNB;
  const client = createClient({ chains: [chain] });
  // Revocation is monotonic: once cut, the agent's next call reverts at validation.
  return client.revokeSession({ wallet, signer: wallet.signer, session });
}
