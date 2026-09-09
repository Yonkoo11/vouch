# Fix Plan — Vouch

Phase 1 Gate lives in ai/memory.md. Nothing below ships until the gate passes.

## Tasks

- [ ] Task 1: Apply for 8004scan Pro API access
  - Acceptance: API key issued, a live call returns BSC agents (chain 56)
  - Files: ai/memory.md (record key presence only, never the value)

- [ ] Task 2: Pull live BSC agents from 8004scan into a typed list
  - Acceptance: >= 1 real agent returned for each of the four categories, no fixtures
  - Files: src/lib/agents.ts

- [ ] Task 3: Compute the record layer from BSC on-chain history
  - Acceptance: for one agent, realized PnL / win rate / max drawdown / revert rate computed from
    real transactions, each number backed by a tx hash that resolves on the explorer
  - Files: src/lib/record.ts

- [ ] Task 4: Marketplace front end, four categories at equal depth
  - Acceptance: land -> filter by category -> open an agent -> understand it, with no dead end,
    for all four categories
  - Files: src/app/page.tsx, src/components/AgentCard.tsx

- [ ] Task 5: Altana session-key hire flow
  - Acceptance: hire mints a session key with allowlist + spend cap + expiry, registered in Keystore
    and readable on-chain independently of our UI
  - Files: src/lib/altana.ts

- [ ] Task 6: Real on-chain transaction through the session key
  - Acceptance: tx visible in the Altana explorer, linked from the agent page
  - Files: src/lib/altana.ts

- [ ] Task 7: Spend-cap refusal + one-transaction revoke, both user-visible
  - Acceptance: over-cap call refused with a visible reason; revoke kills the session and the UI updates
  - Files: src/components/SessionPanel.tsx

- [ ] Task 8: Agent Advantage Report (TermiX)
  - Acceptance: 3 tasks run both ways with time/cost/quality and raw outputs attached,
    >= 1 from trading/stock/security reporting win rate, window and risk taken
  - Files: docs/agent-advantage-report.md

- [ ] Task 9: Public repo hygiene
  - Acceptance: OSI licence, README opening with the pitch, CONTRIBUTING, no secrets in history
  - Files: LICENSE, README.md, CONTRIBUTING.md

- [ ] Task 10: Cold self-test on the live URL in incognito
  - Acceptance: every Phase 1 success-test step passes on the deployed URL with no local state

## Completed
(builder fills this in)
