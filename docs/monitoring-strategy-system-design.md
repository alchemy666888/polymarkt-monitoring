# Monitoring Strategy and System Design

## 1) Objectives
- Detect high-value bets (default: over $5,000 USD) placed on tracked betting contracts.
- Flag only bets from "new" wallets (default: fewer than 5 historical transactions).
- Deliver alerts in near real time (target under 60 seconds end-to-end latency).
- Keep operation cost at $0 by using free-tier/open-source tooling.

## 2) Scope and Assumptions
- Target chains: EVM-compatible chains (initially Polygon or Ethereum).
- Target dApps: Contract-address based monitoring (for Polymarket-related addresses configured by user).
- Data source: Public blockchain + free APIs (RPC, CoinGecko, Etherscan-compatible explorers, Telegram API).
- No private or personal data is collected; only public on-chain transaction metadata is processed.

## 3) Detection Strategy
- Monitor confirmed blocks continuously with configurable confirmation depth.
- Detect two bet-like patterns:
  - Native transfers: transactions where `to` is a monitored contract and `value > 0`.
  - ERC-20 transfers: `Transfer` logs where recipient is a monitored contract.
- Convert transferred amount to USD:
  - Native token and non-stable ERC-20: CoinGecko spot price.
  - Stablecoins (for example USDC): fixed/near-1.0 USD with configurable mapping.
- Apply threshold filter (`usd_value >= threshold_usd`).
- Check sender wallet novelty through explorer API transaction count (`tx_count < max_prior_txs`).
- Send alert only if both high-value and new-wallet conditions pass.

## 4) System Architecture

### Components
1. Config Loader
- Reads `.env` and validates required values.
- Stores thresholds, monitored contracts, chain metadata, and API credentials.

2. RPC Client Layer
- Connects to one of multiple RPC URLs with failover.
- Fetches blocks, full transactions, and ERC-20 transfer logs.

3. Pricing Client
- Pulls USD prices from CoinGecko.
- Uses short TTL cache to reduce API usage and improve resilience.

4. Wallet Novelty Client
- Queries Etherscan-compatible explorer API for historical tx count.

5. Evaluator
- Encodes rule decisions: high-value + new-wallet.

6. Alerting Client
- Sends formatted Telegram messages to configured chat.

7. Monitor Orchestrator
- Poll loop with block checkpoints.
- Deduplication per event key.
- Error handling and retry/backoff.

8. Logging/Telemetry
- Structured logs for processed blocks, candidate events, alerts, and failures.

### Data Flow
1. Poll latest confirmed block.
2. Process unseen block range.
3. Extract native and ERC-20 candidate transfers to monitored contracts.
4. Convert amounts to USD.
5. Filter by threshold.
6. Enrich candidate with wallet tx count.
7. Apply novelty rule.
8. Dispatch Telegram alert.
9. Persist/update checkpoint in memory (extendable to durable storage).

## 5) Reliability and Performance Design
- Poll interval: default 15 seconds.
- Confirmation depth: default 2 blocks to reduce reorg noise.
- Retry strategy: bounded retries + exponential backoff for external APIs.
- Fallback strategy:
  - Multiple RPC URLs with reconnect attempts.
  - Cached prices when CoinGecko is temporarily unavailable.
- Throughput approach:
  - Process blocks in bounded batches.
  - Reuse block timestamp cache for many events within same block.

## 6) Security and Compliance
- Secrets only through environment variables; no secret logging.
- Alert payload contains public addresses and transaction metadata only.
- Principle of least data retention; no PII processing.

## 7) Configuration Model
Key parameters:
- `BET_CONTRACT_ADDRESSES`
- `USD_THRESHOLD`
- `WALLET_MAX_TX_COUNT`
- `POLL_INTERVAL_SECONDS`
- `BLOCK_CONFIRMATIONS`
- `RPC_URLS`
- `EXPLORER_API_BASE` and `EXPLORER_API_KEY`
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- Token metadata (`TOKEN_*`) and CoinGecko ids

## 8) Testing Strategy
- Unit tests:
  - Threshold rule edge cases.
  - Wallet novelty rule boundary (`< max_prior_txs`).
- Integration tests (mocked clients):
  - End-to-end candidate -> alert path.
  - API failure handling/recovery.
- Operational validation:
  - Dry run on testnet contracts.
  - Latency and false-positive review.

## 9) Roadmap Extensions
- Durable checkpoint storage (SQLite/Redis).
- Multi-channel alerts (Discord/Slack/Webhook).
- Multi-chain concurrent workers.
- Heuristic scoring and anomaly detection.
