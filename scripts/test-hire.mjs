// Drive the hire flow end to end with a Chrome virtual WebAuthn authenticator.
//
// Passkeys are not untestable. Chrome exposes WebAuthn.addVirtualAuthenticator
// over the DevTools protocol precisely so a passkey flow can run without a
// human finger. Claiming this path "cannot be automated" was wrong, and the
// first run of this script immediately found a real bug: createPasskeyWallet is
// a client method, not a module export.
//
//   cd scripts && npm i puppeteer-core && node test-hire.mjs
//
// Chrome exposes so WebAuthn can be tested without a human finger.
import puppeteer from 'puppeteer-core';
const EXEC='/Users/yonko/.cache/puppeteer/chrome/mac_arm-146.0.7680.153/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const browser = await puppeteer.launch({ headless:true, executablePath:EXEC, protocolTimeout:180000 });
const page = await browser.newPage();
const cdp = await page.target().createCDPSession();
await cdp.send('WebAuthn.enable');
const { authenticatorId } = await cdp.send('WebAuthn.addVirtualAuthenticator', {
  options: { protocol:'ctap2', transport:'internal', hasResidentKey:true,
             hasUserVerification:true, isUserVerified:true, automaticPresenceSimulation:true },
});
console.log('virtual authenticator:', authenticatorId);
const logs=[];
page.on('console', m => logs.push(m.text().slice(0,200)));
page.on('pageerror', e => logs.push('PAGEERROR ' + String(e).slice(0,200)));
await page.goto('https://yonkoo11.github.io/vouch/?pk=1', { waitUntil:'networkidle2', timeout:60000 });
const res = await page.evaluate(async () => {
  const out = { steps: [] };
  const m = await import('/vouch/hire.js');
  out.moduleLoaded = true;

  // Stage 1: can a passkey wallet actually be created headlessly?
  try {
    const sdk = await import('https://esm.sh/@altananetwork/sdk@0.9.0');
    const client = sdk.createClient({ chains: [sdk.BNB_TESTNET] });
    const w = await client.createPasskeyWallet({ name: 'Vouch test' });
    out.walletCreated = true;
    out.walletAddress = w.address;
    out.balance = await (async () => {
      const r = await fetch('https://bsc-testnet-rpc.publicnode.com', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({jsonrpc:'2.0',id:1,method:'eth_getBalance',params:[w.address,'latest']})});
      const j = await r.json();
      return j.result ? (parseInt(j.result,16)/1e18) : null;
    })();
  } catch (e) {
    out.walletCreated = false;
    out.walletError = String(e && e.message ? e.message : e).slice(0,300);
    return out;
  }

  // Stage 2: the full hire, which needs the wallet funded first.
  try {
    const r = await m.hire({
      agent:{name:'test'}, category:'rebalancing',
      spendCapWei:'10000000000000000', hours:1, chainId:97,
      onStep:s=>out.steps.push(s),
    });
    out.hired = true;
    out.result = { wallet:r.wallet, expiry:r.expiry, txHash:r.txHash, authority:r.authority };
  } catch (e) {
    out.hired = false;
    out.hireError = String(e && e.message ? e.message : e).slice(0,300);
  }
  return out;
});
console.log(JSON.stringify(res,null,1));
console.log('CONSOLE:', logs.slice(0,12).join('\n'));
await browser.close();
