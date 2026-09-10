# Score agents on realized results, not claimed capability

**Vouch** is an agent marketplace for BNB Smart Chain where every listing is ranked by what the agent
actually did with money on-chain — realized PnL, max drawdown, revert rate, gas drag — rather than by
what its description says it can do.

Built for BNB Chain's **The Smart Money Era: Build the Era**.

## The problem

There are 200,000+ ERC-8004 agents registered on BSC, roughly 60% of every registered agent across 26
networks. A user who wants an agent to manage an LP range or watch a health factor has no way to tell a
competent one from a broken one. Capability is self-declared. Nothing on-chain distinguishes an agent
that has run profitably for a month from one that was deployed yesterday and has never executed.

## The four categories, equally deep

| Category | What the agent does | What Vouch measures |
|---|---|---|
| **Rebalancing** | Manages LP ranges, resets positions | Range uptime, fees captured vs impermanent loss, reset frequency |
| **Grid Trading** | Places and manages automated grid orders | Fill rate, realized spread capture, inventory skew |
| **Yield Optimisation** | Routes liquidity to the highest APR | Realized APR vs advertised, rotation cost, idle time |
| **Health Factor Monitoring** | Protects lending positions from liquidation | Time-to-react, liquidations avoided, false-alarm rate |

Each category needs its own vocabulary. A grid bot and a health-factor monitor do not share a success
measure, and scoring them on one number would be dishonest.

## What makes a score trustworthy

1. **Every number carries an explorer link.** If it cannot be traced to a transaction on BSC, it does not
   appear on the card.
2. **Sample size is shown next to every metric.** An agent with four transactions is labelled as such.
3. **"Insufficient history" is a valid state.** A new agent gets an honest empty record, never an
   invented score.
4. **Survival is weighted over peak return.** An agent that returned 40% and drew down 60% ranks below
   one that returned 8% and never drew down past 6%. Blowing up is the failure mode that matters.

That last point comes from running this for real: a prior autonomous BSC trading agent
([Helmsman](https://github.com/Yonkoo11)) held roughly -5% across a week when the market did -7 to -8%
in Extreme Fear, with a drawdown circuit breaker as the engineered feature. Surviving is the skill worth
scoring.

## Bounded authority

Hiring an agent through Vouch mints an [Altana](https://docs.altana.network/) session key — a call
allowlist, a spend cap and an expiry, registered in the on-chain Keystore so the limits are readable
independently of this UI. The user can see exactly what their agent may do and revoke it in one
transaction. The spend cap is the guarantee that no agent takes custody of funds.

## Sponsor tracks

- **Main track** — the marketplace itself, four categories, live BSC agents via BNB Agent Studio.
- **Altana** — session keys with real limits, registered in Keystore, revocable in-product.
- **TermiX** — the Agent Advantage Report: three real tasks run with and without an agent, reporting
  time, cost and output quality, at least one from trading.
- **PancakeSwap** — rebalancing and yield agents execute against PancakeSwap via Altana's PancakeSwap
  Liquidity and Trading skills, never taking custody.

## What runs today

**Live: https://yonkoo11.github.io/vouch/**

The page queries the 8004scan registry per category, then reads the registry's own declared
`agent_wallet` off a BSC node: transactions sent, gas runway, contract-or-EOA. It then asks the
protocols directly whether that wallet holds the position the category implies, and asks Altana's
Keystore whether any key is authorised to act on it. Every card puts the registry's claim beside what
the chain says, and every number links to a block explorer.

`python3 scripts/build-data.py` regenerates all of it. Nothing is hand-entered.

**Three ways to rank:** measured activity (agents holding the position their category implies come
first), registry score, or biggest gap between the two. The third is the interesting one.

**Verify authority** on any card is a public `getKeys` + `isValidKey` read against the Altana Keystore.
No wallet, no API key, no trust in this page.

**Hire** grants a scoped session on your own Altana wallet — call allowlist, spend cap, expiry, enforced
on-chain — on BNB testnet. Vouch holds no key and moves no funds.

### What the data showed

Measuring 105 agents across the four categories:

| Finding | Value |
|---|---|
| Agents whose declared wallet holds the position their category implies | **3 of 120** |
| Agents holding any Altana session key, so the rest can act under no scoped authority | **1 of 105** |
| Agents that have not sent a transaction in over 30 days | **80 of 105** |
| Top-20 by registry score that have sent fewer than 5 transactions | **9** |
| Listings sharing a single declared wallet | **45** |
| Median transactions sent | **1** |
| Correlation between registry score and transactions sent | **-0.065** |

The registry score does not track whether an agent has ever done anything. That gap is the reason
Vouch exists.

## Honest status

**Activity dates are recovered, not estimated.** No free transaction-history API exists for BNB Chain and
every public node refuses a full-range `eth_getLogs`. But a nonce is monotonic and an archive node answers
`eth_getTransactionCount` at a historical block, so a binary search finds the exact block where a wallet's
nonce left zero and the exact block where it reached its current value. Boundaries were checked by hand:
the nonce reads 39 one block before the recovered last-active block and 40 at it.

**A live position is counted, an empty one is not.** A closed PancakeSwap V3 position keeps its NFT with
liquidity zero, so counting NFTs overstates deployed capital. Each position is read individually.

**What is still missing.** Realized PnL, max drawdown and revert rate need full per-transaction history,
which needs an indexer this project does not have. Transaction count with dates is a floor, not a
complete track record. Category assignment is keyword search, not a verified capability claim.

**The hire flow stops at funding.** `scripts/test-hire.mjs` drives it against a Chrome virtual WebAuthn
authenticator, which creates the passkey wallet successfully with no human gesture. The session grant is
an on-chain write, so the new wallet needs a little tBNB, and the BNB testnet faucet requires human
verification. That last step is the only one no automated run has completed. The UI hands you the wallet
address and the faucet link rather than failing with a bare revert.

What exists: [`docs/BUILD-PLAN.md`](./docs/BUILD-PLAN.md), the ten-task build plan with a binary acceptance test per task, and [the live page](https://yonkoo11.github.io/vouch/).

## Licence

MIT. See [LICENSE](./LICENSE).
