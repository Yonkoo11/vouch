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

## Honest status

**Fresh idea, entered at the registration stage.** This repository contains the specification, the
category metric definitions, the sponsor integration plan with acceptance tests, and the build plan.
No application code has been written and nothing has been deployed. Any claim in this README about what
the product does is a statement of intent, not of working software.

What exists: [`docs/BUILD-PLAN.md`](./docs/BUILD-PLAN.md), the ten-task build plan with a binary acceptance test per task, and [the live page](https://yonkoo11.github.io/vouch/).

## Licence

MIT. See [LICENSE](./LICENSE).
