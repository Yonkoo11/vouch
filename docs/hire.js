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
export async function verifyAuthority(wallet, chainId = 56) {
  const net = NETWORKS[chainId];
  if (!net) throw new Error('unsupported chain ' + chainId);
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

// ---------------------------------------------------------------------------
// Hiring
// ---------------------------------------------------------------------------

let sdk = null;
async function loadSdk() {
  if (sdk) return sdk;
  // Loaded on demand so a visitor who never hires pays nothing for the bundle.
  sdk = await import('https://esm.sh/@altananetwork/sdk@0.9.0');
  return sdk;
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
  const { createClient, createPrivateKeySigner, BNB, BNB_TESTNET } = sdkm;
  const chain = chainId === 97 ? BNB_TESTNET : BNB;
  const client = createClient({ chains: [chain] });

  // createPasskeyWallet is a client method, not a module export. Writing it the
  // other way is what the virtual-authenticator test caught first.
  step('creating your passkey wallet — approve the biometric prompt');
  const wallet = await client.createPasskeyWallet({ name: 'Vouch' });

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

  return {
    wallet: wallet.address,
    session,
    expiry,
    allow,
    authority,
    txHash: session?.transactionHash || null,
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
