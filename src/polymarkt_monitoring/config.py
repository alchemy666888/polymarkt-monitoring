from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency should be installed in runtime env
    load_dotenv = None


DEFAULT_NATIVE_COINGECKO_ID = {
    "ethereum": "ethereum",
    "polygon": "matic-network",
}

DEFAULT_EXPLORER_API_BASE = {
    "ethereum": "https://api.etherscan.io/api",
    "polygon": "https://api.polygonscan.com/api",
}


@dataclass(slots=True, frozen=True)
class MonitorConfig:
    chain_name: str
    rpc_urls: list[str]
    bet_contract_addresses: list[str]
    token_contracts: dict[str, str]
    token_decimals: dict[str, int]
    token_coingecko_ids: dict[str, str]
    native_symbol: str
    native_coingecko_id: str
    usd_threshold: float
    wallet_max_tx_count: int
    poll_interval_seconds: int
    block_confirmations: int
    max_blocks_per_cycle: int
    start_block: int | None
    explorer_api_base: str
    explorer_api_key: str
    coingecko_api_base: str
    telegram_bot_token: str
    telegram_chat_id: str
    log_level: str


def load_config(env_file: str = ".env") -> MonitorConfig:
    env_path = Path(env_file)
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)

    chain_name = os.getenv("CHAIN_NAME", "polygon").strip().lower()
    rpc_urls = _parse_csv_required("RPC_URLS")
    bet_contract_addresses = _parse_addresses_required("BET_CONTRACT_ADDRESSES")

    token_contracts = _parse_symbol_address_map(os.getenv("TOKEN_CONTRACTS", ""))
    token_decimals = _parse_symbol_int_map(os.getenv("TOKEN_DECIMALS", ""))
    token_coingecko_ids = _parse_symbol_str_map(os.getenv("TOKEN_COINGECKO_IDS", ""), lowercase_values=True)

    for symbol in token_contracts:
        token_decimals.setdefault(symbol, 18)
        if symbol == "USDC":
            token_decimals[symbol] = 6
            token_coingecko_ids.setdefault(symbol, "usd-coin")

    native_symbol = os.getenv("NATIVE_SYMBOL", "ETH").strip().upper()
    native_coingecko_id = os.getenv(
        "NATIVE_COINGECKO_ID", DEFAULT_NATIVE_COINGECKO_ID.get(chain_name, "ethereum")
    ).strip()

    usd_threshold = _parse_float(os.getenv("USD_THRESHOLD", "5000"), "USD_THRESHOLD")
    wallet_max_tx_count = _parse_int(os.getenv("WALLET_MAX_TX_COUNT", "5"), "WALLET_MAX_TX_COUNT")
    poll_interval_seconds = _parse_int(os.getenv("POLL_INTERVAL_SECONDS", "15"), "POLL_INTERVAL_SECONDS")
    block_confirmations = _parse_int(os.getenv("BLOCK_CONFIRMATIONS", "2"), "BLOCK_CONFIRMATIONS")
    max_blocks_per_cycle = _parse_int(os.getenv("MAX_BLOCKS_PER_CYCLE", "50"), "MAX_BLOCKS_PER_CYCLE")

    raw_start_block = os.getenv("START_BLOCK", "").strip()
    start_block = _parse_int(raw_start_block, "START_BLOCK") if raw_start_block else None

    explorer_api_base = os.getenv(
        "EXPLORER_API_BASE", DEFAULT_EXPLORER_API_BASE.get(chain_name, "https://api.etherscan.io/api")
    ).strip()
    explorer_api_key = os.getenv("EXPLORER_API_KEY", "").strip()
    coingecko_api_base = os.getenv("COINGECKO_API_BASE", "https://api.coingecko.com/api/v3").strip()

    telegram_bot_token = _required("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = _required("TELEGRAM_CHAT_ID")
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    if usd_threshold <= 0:
        raise ValueError("USD_THRESHOLD must be > 0")
    if wallet_max_tx_count < 0:
        raise ValueError("WALLET_MAX_TX_COUNT must be >= 0")
    if poll_interval_seconds < 1:
        raise ValueError("POLL_INTERVAL_SECONDS must be >= 1")
    if block_confirmations < 0:
        raise ValueError("BLOCK_CONFIRMATIONS must be >= 0")
    if max_blocks_per_cycle < 1:
        raise ValueError("MAX_BLOCKS_PER_CYCLE must be >= 1")

    return MonitorConfig(
        chain_name=chain_name,
        rpc_urls=rpc_urls,
        bet_contract_addresses=bet_contract_addresses,
        token_contracts=token_contracts,
        token_decimals=token_decimals,
        token_coingecko_ids=token_coingecko_ids,
        native_symbol=native_symbol,
        native_coingecko_id=native_coingecko_id,
        usd_threshold=usd_threshold,
        wallet_max_tx_count=wallet_max_tx_count,
        poll_interval_seconds=poll_interval_seconds,
        block_confirmations=block_confirmations,
        max_blocks_per_cycle=max_blocks_per_cycle,
        start_block=start_block,
        explorer_api_base=explorer_api_base,
        explorer_api_key=explorer_api_key,
        coingecko_api_base=coingecko_api_base,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        log_level=log_level,
    )


def _required(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def _parse_csv_required(key: str) -> list[str]:
    raw = _required(key)
    items = _parse_csv(raw)
    if not items:
        raise ValueError(f"{key} must include at least one value")
    return items


def _parse_addresses_required(key: str) -> list[str]:
    values = _parse_csv_required(key)
    return [_normalize_address(value, key) for value in values]


def _parse_symbol_address_map(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for symbol, address in _parse_symbol_value_pairs(raw):
        result[symbol] = _normalize_address(address, "TOKEN_CONTRACTS")
    return result


def _parse_symbol_int_map(raw: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for symbol, value in _parse_symbol_value_pairs(raw):
        parsed = _parse_int(value, f"TOKEN_DECIMALS[{symbol}]")
        if parsed < 0:
            raise ValueError(f"TOKEN_DECIMALS[{symbol}] must be >= 0")
        result[symbol] = parsed
    return result


def _parse_symbol_str_map(raw: str, *, lowercase_values: bool = False) -> dict[str, str]:
    result: dict[str, str] = {}
    for symbol, value in _parse_symbol_value_pairs(raw):
        result[symbol] = value.lower() if lowercase_values else value
    return result


def _parse_symbol_value_pairs(raw: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in _parse_csv(raw):
        if ":" not in item:
            raise ValueError(f"Invalid key:value pair: '{item}'")
        symbol, value = item.split(":", 1)
        symbol_clean = symbol.strip().upper()
        value_clean = value.strip()
        if not symbol_clean or not value_clean:
            raise ValueError(f"Invalid key:value pair: '{item}'")
        pairs.append((symbol_clean, value_clean))
    return pairs


def _parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_int(raw: str, key: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:  # pragma: no cover - trivial conversion
        raise ValueError(f"Invalid integer for {key}: {raw}") from exc


def _parse_float(raw: str, key: str) -> float:
    try:
        return float(raw)
    except ValueError as exc:  # pragma: no cover - trivial conversion
        raise ValueError(f"Invalid float for {key}: {raw}") from exc


def _normalize_address(value: str, key: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned.startswith("0x") or len(cleaned) != 42:
        raise ValueError(f"Invalid EVM address for {key}: {value}")
    return cleaned
