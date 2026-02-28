from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class BetCandidate:
    wallet_address: str
    tx_hash: str
    block_number: int
    timestamp: int
    contract_address: str
    token_symbol: str
    token_amount: float
    usd_value: float
    source: str

    @property
    def dedup_key(self) -> tuple[str, str, str, str]:
        return (
            self.tx_hash.lower(),
            self.wallet_address.lower(),
            self.contract_address.lower(),
            self.token_symbol.upper(),
        )


@dataclass(slots=True, frozen=True)
class AlertEvent:
    candidate: BetCandidate
    wallet_tx_count: int
