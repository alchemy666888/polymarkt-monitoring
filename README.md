# Polymarkt Monitoring

Python monitoring service for detecting high-value bets from new wallets on EVM betting contracts (for example Polymarket-related contracts).

## What It Does
- Polls confirmed EVM blocks from RPC endpoints.
- Detects:
  - Native transfers into monitored betting contracts.
  - ERC-20 `Transfer` events into monitored betting contracts.
- Converts transfer amounts to USD with CoinGecko prices.
- Filters by configurable USD threshold (`USD_THRESHOLD`, default `$5,000`).
- Checks wallet novelty with Etherscan-compatible explorer API transaction count.
- Sends Telegram alerts when all criteria match.

## Project Docs
- Requirements source: [`docs/requirements.md`](docs/requirements.md)
- Strategy and design: [`docs/monitoring-strategy-system-design.md`](docs/monitoring-strategy-system-design.md)
- Development plan: [`docs/vibe-coding-development-plan.md`](docs/vibe-coding-development-plan.md)

## Quick Start
1. Create and activate a virtualenv.
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Create environment file:
   ```bash
   cp .env.example .env
   ```
4. Update `.env` with your real RPC, contracts, explorer API key, and Telegram credentials.
5. Run once (smoke check):
   ```bash
   python -m polymarkt_monitoring.main --once
   ```
6. Run continuously:
   ```bash
   python -m polymarkt_monitoring.main
   ```

## Environment File Setup
Start from the provided template:
```bash
cp .env.example .env
```

The monitor reads configuration from `.env`. Most values are plain strings, numbers, or comma-separated lists. Address values must be full EVM addresses such as `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`.

Example `.env` for Polygon + USDC monitoring:
```dotenv
CHAIN_NAME=polygon
RPC_URLS=https://polygon-rpc.com
NATIVE_SYMBOL=MATIC
NATIVE_COINGECKO_ID=matic-network

BET_CONTRACT_ADDRESSES=0x1111111111111111111111111111111111111111
TOKEN_CONTRACTS=USDC:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
TOKEN_DECIMALS=USDC:6
TOKEN_COINGECKO_IDS=USDC:usd-coin

USD_THRESHOLD=5000
WALLET_MAX_TX_COUNT=5
POLL_INTERVAL_SECONDS=15
BLOCK_CONFIRMATIONS=2
MAX_BLOCKS_PER_CYCLE=50

EXPLORER_API_BASE=https://api.polygonscan.com/api
EXPLORER_API_KEY=your_polygonscan_key
COINGECKO_API_BASE=https://api.coingecko.com/api/v3

TELEGRAM_BOT_TOKEN=123456:ABCDEF...
TELEGRAM_CHAT_ID=123456789

LOG_LEVEL=INFO
```

## Environment Variables Reference

| Variable | Required | What it controls | Format / Example | How to get the value |
| --- | --- | --- | --- | --- |
| `CHAIN_NAME` | No | Selects the chain label and defaults for explorer and native pricing metadata. | `polygon`, `ethereum` | Choose the chain where the betting contracts live. Use `polygon` if you are monitoring Polygon contracts; use `ethereum` for Ethereum mainnet contracts. |
| `RPC_URLS` | Yes | RPC endpoints used to read blocks, transactions, and logs. Multiple URLs act as failover. | `https://polygon-rpc.com,https://another-rpc.example` | Get these from your RPC provider dashboard or public RPC endpoints. Free options are available from providers such as Infura, Alchemy, Chainstack, or chain community RPCs. |
| `NATIVE_SYMBOL` | No | Symbol shown in alerts for native transfers. | `MATIC`, `ETH` | Set this to the native gas token symbol of the chain you are monitoring. |
| `NATIVE_COINGECKO_ID` | No | CoinGecko asset id for native token USD pricing. | `matic-network`, `ethereum` | Open the asset page on CoinGecko and copy the id from the URL slug. For example, Polygon uses `matic-network`. |
| `BET_CONTRACT_ADDRESSES` | Yes | Contract addresses treated as monitored betting destinations. Native transfers and ERC-20 transfers into these addresses are evaluated. | `0xabc...,0xdef...` | Collect the target contract addresses from the protocol documentation, deployment docs, your own contract registry, or the block explorer pages for the specific Polymarket-related contracts you want to watch. |
| `TOKEN_CONTRACTS` | No | ERC-20 contracts to inspect for `Transfer` events into the monitored betting contracts. | `USDC:0x2791...` | Use the token contract address published by the token issuer or shown on the chain explorer. For stablecoin-funded Polymarket flows on Polygon, this is typically the Polygon USDC contract. |
| `TOKEN_DECIMALS` | No | Decimal precision used to convert ERC-20 raw integer amounts into human-readable token amounts. | `USDC:6,WETH:18` | Find decimals on the token contract page in the explorer, in the token documentation, or by reading the token contract metadata. USDC is usually `6`; most ERC-20 tokens are `18`. |
| `TOKEN_COINGECKO_IDS` | No | CoinGecko asset id per tracked ERC-20 token for USD conversion. | `USDC:usd-coin,WETH:weth` | Open each token page on CoinGecko and copy the asset id from the URL slug. For stablecoins such as USDC, `usd-coin` is appropriate. |
| `USD_THRESHOLD` | No | Minimum USD value required for a candidate event to qualify. | `5000` | Choose the alert threshold you care about. The default is based on the requirement document: bets over `$5,000` USD. |
| `WALLET_MAX_TX_COUNT` | No | Defines a “new wallet” as having strictly fewer than this many historical transactions. | `5` | Set this to your novelty rule. If you want “new wallet” to mean 0 prior transactions, set it to `1`. |
| `POLL_INTERVAL_SECONDS` | No | Delay between polling cycles when running continuously. | `15` | Choose a balance between freshness and API usage. `10-30` seconds is a reasonable free-tier range. |
| `BLOCK_CONFIRMATIONS` | No | Number of blocks to wait before processing to reduce reorg noise. | `2` | Use `1-3` for faster monitoring on EVM chains; increase if you want more conservative confirmation handling. |
| `MAX_BLOCKS_PER_CYCLE` | No | Maximum block range processed in one loop iteration. Prevents large catch-up spikes. | `50` | Keep this moderate when using free RPC tiers. Increase only if you need faster backlog catch-up. |
| `START_BLOCK` | No | First block number to process. If omitted, the monitor starts near the current confirmed head. | `65000000` | Use a block number from the chain explorer when you want to backfill from a known point in time. Leave it unset for forward-only monitoring. |
| `EXPLORER_API_BASE` | Yes | Base URL for the Etherscan-compatible explorer API used to query wallet transaction count. | `https://api.polygonscan.com/api` | Copy the API base for the explorer matching your chain. Common examples are Etherscan for Ethereum and Polygonscan for Polygon. |
| `EXPLORER_API_KEY` | Recommended | API key for the explorer service. Improves reliability and rate limits. | `ABC123...` | Create an account in the relevant explorer and generate an API key from its API/dashboard section. |
| `COINGECKO_API_BASE` | No | CoinGecko base URL used for price lookups. | `https://api.coingecko.com/api/v3` | Normally keep the default. Only change it if you are routing through a proxy or alternative compatible endpoint. |
| `TELEGRAM_BOT_TOKEN` | Yes | Auth token for the Telegram bot that sends alerts. | `123456:ABCDEF...` | Open Telegram, start a chat with BotFather, create a bot with `/newbot`, and copy the token it returns. |
| `TELEGRAM_CHAT_ID` | Yes | Target chat, group, or channel id where alerts will be posted. | `123456789` or `-1001234567890` | Send a message to your bot, then inspect Telegram Bot API updates for the `chat.id`. For groups/channels, add the bot first and use the group/channel chat id. |
| `LOG_LEVEL` | No | Runtime logging verbosity. | `INFO`, `DEBUG`, `WARNING`, `ERROR` | Use `INFO` for normal operation and `DEBUG` when troubleshooting configuration or event parsing issues. |

## How Each Variable Is Used at Runtime
- `RPC_URLS` drives the chain reader in `RpcClient`. If the first endpoint fails, the code rotates to the next one.
- `BET_CONTRACT_ADDRESSES` is the core filter. Transfers that do not end at one of these addresses are ignored.
- `TOKEN_CONTRACTS`, `TOKEN_DECIMALS`, and `TOKEN_COINGECKO_IDS` work together. The code reads ERC-20 logs from the token contracts, converts raw amounts with decimals, then converts token amounts to USD with CoinGecko ids.
- `USD_THRESHOLD` and `WALLET_MAX_TX_COUNT` feed the decision engine in `BetEvaluator`.
- `EXPLORER_API_BASE` and `EXPLORER_API_KEY` are used by `ExplorerClient` to fetch `eth_getTransactionCount` for the sending wallet.
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are used by `TelegramNotifier` to send the final alert message.
- `START_BLOCK`, `BLOCK_CONFIRMATIONS`, `POLL_INTERVAL_SECONDS`, and `MAX_BLOCKS_PER_CYCLE` control how the monitor moves through chain history and how aggressively it polls.

## Practical Notes for Filling `.env`
- If you only care about ERC-20-funded bets, you can leave native token pricing defaults alone and focus on `TOKEN_*` plus `BET_CONTRACT_ADDRESSES`.
- If you monitor multiple ERC-20 tokens, list them as comma-separated pairs in each matching variable, for example:
  ```dotenv
  TOKEN_CONTRACTS=USDC:0x...,WETH:0x...
  TOKEN_DECIMALS=USDC:6,WETH:18
  TOKEN_COINGECKO_IDS=USDC:usd-coin,WETH:weth
  ```
- All addresses should be on the same chain selected by `CHAIN_NAME`.
- Do not commit `.env` into git. Keep secrets such as `EXPLORER_API_KEY` and `TELEGRAM_BOT_TOKEN` private.

## Testing
Run unit tests:
```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Notes
- The implementation is modular for extension to multi-chain workers and additional alert channels.
- `MonitoringService` keeps in-memory dedup state for current process lifetime.
