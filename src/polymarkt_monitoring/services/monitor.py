from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

from polymarkt_monitoring.config import MonitorConfig
from polymarkt_monitoring.models import BetCandidate
from polymarkt_monitoring.services.evaluator import BetEvaluator


class MonitoringService:
    def __init__(
        self,
        *,
        config: MonitorConfig,
        rpc_client,
        pricing_client,
        explorer_client,
        notifier,
        evaluator: BetEvaluator,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config
        self.rpc_client = rpc_client
        self.pricing_client = pricing_client
        self.explorer_client = explorer_client
        self.notifier = notifier
        self.evaluator = evaluator
        self.logger = logger or logging.getLogger(__name__)
        self._seen_event_keys: set[tuple[str, str, str, str]] = set()
        self._pending_candidates: dict[tuple[str, str, str, str], BetCandidate] = {}
        self._timestamp_cache: dict[int, int] = {}

    async def run(self, *, once: bool = False) -> None:
        current_block = self._initial_block()
        self.logger.info("Monitor started", extra={"start_block": current_block, "once": once})

        while True:
            self._retry_pending_candidates()

            latest_confirmed = max(0, self.rpc_client.latest_block_number() - self.config.block_confirmations)
            if latest_confirmed <= current_block:
                if once:
                    if self._pending_candidates:
                        self.logger.warning(
                            "Exiting with pending candidates after failed downstream operations",
                            extra={"pending_count": len(self._pending_candidates)},
                        )
                    self.logger.info("No new confirmed blocks to process")
                    return
                await asyncio.sleep(self.config.poll_interval_seconds)
                continue

            from_block = current_block + 1
            to_block = min(current_block + self.config.max_blocks_per_cycle, latest_confirmed)
            candidates = self._collect_candidates(from_block, to_block)
            self._evaluate_and_alert(candidates)

            current_block = to_block
            self.logger.info(
                "Processed block range",
                extra={
                    "from_block": from_block,
                    "to_block": to_block,
                    "latest_confirmed": latest_confirmed,
                },
            )

            if once and current_block >= latest_confirmed:
                return

    def _initial_block(self) -> int:
        if self.config.start_block is not None:
            return max(-1, self.config.start_block - 1)

        latest = self.rpc_client.latest_block_number()
        return max(0, latest - self.config.block_confirmations - 1)

    def _collect_candidates(self, from_block: int, to_block: int) -> list[BetCandidate]:
        addresses = set(self.config.bet_contract_addresses)
        candidates: list[BetCandidate] = []

        candidates.extend(self._collect_native_candidates(from_block, to_block, addresses))
        candidates.extend(self._collect_erc20_candidates(from_block, to_block, addresses))

        return candidates

    def _collect_native_candidates(
        self,
        from_block: int,
        to_block: int,
        target_addresses: set[str],
    ) -> list[BetCandidate]:
        if not target_addresses:
            return []

        native_price = self.pricing_client.get_usd_price(self.config.native_coingecko_id)
        candidates: list[BetCandidate] = []

        for block_number in range(from_block, to_block + 1):
            transfers = self.rpc_client.get_native_transfers(block_number, target_addresses)
            timestamp = self._block_timestamp(block_number)
            for transfer in transfers:
                amount = transfer["raw_amount"] / (10**18)
                usd_value = amount * native_price
                if not self.evaluator.is_above_threshold(usd_value):
                    continue

                candidates.append(
                    BetCandidate(
                        wallet_address=transfer["wallet_address"],
                        tx_hash=transfer["tx_hash"],
                        block_number=transfer["block_number"],
                        timestamp=timestamp,
                        contract_address=transfer["contract_address"],
                        token_symbol=self.config.native_symbol,
                        token_amount=amount,
                        usd_value=usd_value,
                        source="native_transfer",
                    )
                )

        return candidates

    def _collect_erc20_candidates(
        self,
        from_block: int,
        to_block: int,
        target_addresses: set[str],
    ) -> list[BetCandidate]:
        if not self.config.token_contracts:
            return []

        candidates: list[BetCandidate] = []

        for token_symbol, token_address in self.config.token_contracts.items():
            decimals = self.config.token_decimals.get(token_symbol, 18)
            price_id = self.config.token_coingecko_ids.get(token_symbol, "")
            price = self.pricing_client.get_usd_price(price_id) if price_id else 1.0

            transfers = self.rpc_client.get_erc20_transfers(
                token_address=token_address,
                from_block=from_block,
                to_block=to_block,
                target_addresses=target_addresses,
            )

            for transfer in transfers:
                amount = transfer["raw_amount"] / (10**decimals)
                usd_value = amount * price
                if not self.evaluator.is_above_threshold(usd_value):
                    continue

                block_number = transfer["block_number"]
                candidates.append(
                    BetCandidate(
                        wallet_address=transfer["wallet_address"],
                        tx_hash=transfer["tx_hash"],
                        block_number=block_number,
                        timestamp=self._block_timestamp(block_number),
                        contract_address=transfer["contract_address"],
                        token_symbol=token_symbol,
                        token_amount=amount,
                        usd_value=usd_value,
                        source="erc20_transfer",
                    )
                )

        return candidates

    def _evaluate_and_alert(self, candidates: Iterable[BetCandidate]) -> None:
        for candidate in candidates:
            if candidate.dedup_key in self._seen_event_keys or candidate.dedup_key in self._pending_candidates:
                continue
            self._process_candidate(candidate)

    def _retry_pending_candidates(self) -> None:
        if not self._pending_candidates:
            return

        self.logger.info("Retrying pending candidates", extra={"pending_count": len(self._pending_candidates)})
        for candidate in list(self._pending_candidates.values()):
            self._process_candidate(candidate)

    def _process_candidate(self, candidate: BetCandidate) -> None:
        try:
            wallet_tx_count = self.explorer_client.get_transaction_count(candidate.wallet_address)
        except Exception:
            self._pending_candidates[candidate.dedup_key] = candidate
            self.logger.error(
                "Failed wallet novelty check",
                extra={"wallet_address": candidate.wallet_address, "tx_hash": candidate.tx_hash},
                exc_info=True,
            )
            return

        if not self.evaluator.is_new_wallet(wallet_tx_count):
            self._pending_candidates.pop(candidate.dedup_key, None)
            self._seen_event_keys.add(candidate.dedup_key)
            return

        message = self._format_alert_message(candidate, wallet_tx_count)
        try:
            self.notifier.send_message(message)
            self._pending_candidates.pop(candidate.dedup_key, None)
            self._seen_event_keys.add(candidate.dedup_key)
            self.logger.info(
                "Alert sent",
                extra={
                    "tx_hash": candidate.tx_hash,
                    "wallet_address": candidate.wallet_address,
                    "usd_value": round(candidate.usd_value, 2),
                },
            )
        except Exception:
            self._pending_candidates[candidate.dedup_key] = candidate
            self.logger.error("Failed to send alert", exc_info=True)

    def _block_timestamp(self, block_number: int) -> int:
        cached = self._timestamp_cache.get(block_number)
        if cached is not None:
            return cached

        timestamp = self.rpc_client.get_block_timestamp(block_number)
        self._timestamp_cache[block_number] = timestamp
        return timestamp

    @staticmethod
    def _format_alert_message(candidate: BetCandidate, wallet_tx_count: int) -> str:
        return "\n".join(
            [
                "High-value bet from new wallet detected",
                f"Wallet: {candidate.wallet_address}",
                f"Tx: {candidate.tx_hash}",
                f"Block: {candidate.block_number}",
                f"Contract: {candidate.contract_address}",
                f"Token: {candidate.token_symbol}",
                f"Amount: {candidate.token_amount:.6f}",
                f"USD: ${candidate.usd_value:,.2f}",
                f"Wallet tx count: {wallet_tx_count}",
                f"Source: {candidate.source}",
                f"Timestamp (unix): {candidate.timestamp}",
            ]
        )
