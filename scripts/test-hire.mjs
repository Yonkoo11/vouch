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
  const out = {};
  try {
    const m = await import('/vouch/hire.js');
    out.moduleLoaded = true;
    const steps = [];
    const r = await m.hire({
      agent:{name:'test'}, category:'rebalancing',
      spendCapWei:'10000000000000000', hours:1, chainId:97,
      onStep:s=>steps.push(s),
    });
    out.steps = steps; out.result = { wallet:r.wallet, expiry:r.expiry };
  } catch (e) {
    out.error = String(e && e.message ? e.message : e).slice(0,400);
    out.stack = String(e && e.stack || '').split('\n').slice(0,4).join(' | ').slice(0,400);
  }
  return out;
});
console.log(JSON.stringify(res,null,1));
console.log('CONSOLE:', logs.slice(0,12).join('\n'));
await browser.close();
