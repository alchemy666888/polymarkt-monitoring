from __future__ import annotations

import logging
from typing import Any

from polymarkt_monitoring.retry import with_retries

try:
    from web3 import Web3
except ImportError:  # pragma: no cover - import depends on runtime environment
    Web3 = None


TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


class RpcClient:
    def __init__(
        self,
        *,
        rpc_urls: list[str],
        request_timeout: int = 10,
        logger: logging.Logger | None = None,
    ) -> None:
        if Web3 is None:
            raise RuntimeError("web3 is required. Install dependencies with `pip install -e .`.")
        if not rpc_urls:
            raise ValueError("rpc_urls must include at least one endpoint")

        self.rpc_urls = [url.strip() for url in rpc_urls if url.strip()]
        self.request_timeout = request_timeout
        self.logger = logger or logging.getLogger(__name__)
        self._active_index = 0
        self._web3: Web3 | None = None
        self._connect_any()

    def latest_block_number(self) -> int:
        return int(self._request(lambda w3: w3.eth.block_number))

    def get_block_timestamp(self, block_number: int) -> int:
        block = self._request(lambda w3: w3.eth.get_block(block_number, full_transactions=False))
        return int(block["timestamp"])

    def get_native_transfers(self, block_number: int, target_addresses: set[str]) -> list[dict[str, Any]]:
        if not target_addresses:
            return []

        target_set = {address.lower() for address in target_addresses}
        block = self._request(lambda w3: w3.eth.get_block(block_number, full_transactions=True))

        transfers: list[dict[str, Any]] = []
        for tx in block["transactions"]:
            to_address = tx.get("to")
            if not to_address:
                continue

            to_normalized = str(to_address).lower()
            if to_normalized not in target_set:
                continue

            value_wei = int(tx.get("value", 0))
            if value_wei <= 0:
                continue

            transfers.append(
                {
                    "wallet_address": str(tx.get("from", "")).lower(),
                    "contract_address": to_normalized,
                    "tx_hash": _hexify(tx.get("hash")),
                    "block_number": block_number,
                    "raw_amount": value_wei,
                }
            )

        return transfers

    def get_erc20_transfers(
        self,
        *,
        token_address: str,
        from_block: int,
        to_block: int,
        target_addresses: set[str],
    ) -> list[dict[str, Any]]:
        if not target_addresses:
            return []

        token_checksum = self._request(lambda w3: w3.to_checksum_address(token_address))

        logs: list[Any] = []
        for target in target_addresses:
            params = {
                "fromBlock": from_block,
                "toBlock": to_block,
                "address": token_checksum,
                "topics": [TRANSFER_EVENT_TOPIC, None, _address_to_topic(target)],
            }
            log_batch = self._request(lambda w3, p=params: w3.eth.get_logs(p))
            logs.extend(log_batch)

        transfers: list[dict[str, Any]] = []
        for entry in logs:
            topics = entry.get("topics", [])
            if len(topics) < 3:
                continue

            raw_amount = _data_to_int(entry.get("data"))
            if raw_amount <= 0:
                continue

            transfers.append(
                {
                    "wallet_address": _topic_to_address(topics[1]),
                    "contract_address": _topic_to_address(topics[2]),
                    "tx_hash": _hexify(entry.get("transactionHash")),
                    "block_number": int(entry.get("blockNumber")),
                    "raw_amount": raw_amount,
                }
            )

        return transfers

    def _connect_any(self) -> None:
        errors: list[str] = []
        for offset in range(len(self.rpc_urls)):
            index = (self._active_index + offset) % len(self.rpc_urls)
            url = self.rpc_urls[index]
            provider = Web3.HTTPProvider(url, request_kwargs={"timeout": self.request_timeout})
            web3 = Web3(provider)
            if web3.is_connected():
                self._web3 = web3
                self._active_index = index
                self.logger.info("Connected to RPC", extra={"rpc_url": url})
                return
            errors.append(url)

        raise RuntimeError(f"Failed to connect to all RPC endpoints: {errors}")

    def _request(self, call: Any) -> Any:
        def _run() -> Any:
            if self._web3 is None or not self._web3.is_connected():
                self._connect_any()
            assert self._web3 is not None
            try:
                return call(self._web3)
            except Exception:
                self.logger.warning("RPC call failed; rotating provider", exc_info=True)
                self._active_index = (self._active_index + 1) % len(self.rpc_urls)
                self._connect_any()
                raise

        return with_retries(_run, attempts=2, logger=self.logger)


def _address_to_topic(address: str) -> str:
    clean = address.lower().strip()
    if not clean.startswith("0x"):
        raise ValueError(f"Invalid address: {address}")
    return "0x" + clean[2:].rjust(64, "0")


def _topic_to_address(topic: Any) -> str:
    topic_hex = _hexify(topic)
    if topic_hex.startswith("0x"):
        topic_hex = topic_hex[2:]
    return "0x" + topic_hex[-40:].lower()


def _data_to_int(data: Any) -> int:
    if data is None:
        return 0
    if isinstance(data, int):
        return data
    if isinstance(data, bytes):
        return int.from_bytes(data, byteorder="big")

    data_hex = _hexify(data)
    if data_hex.startswith("0x"):
        data_hex = data_hex[2:]
    return int(data_hex or "0", 16)


def _hexify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, int):
        return hex(value)
    if hasattr(value, "hex"):
        maybe = value.hex()
        return maybe if isinstance(maybe, str) else str(maybe)
    return str(value)
