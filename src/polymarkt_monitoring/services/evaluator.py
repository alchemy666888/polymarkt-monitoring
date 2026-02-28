from __future__ import annotations


class BetEvaluator:
    def __init__(self, *, usd_threshold: float, wallet_max_tx_count: int) -> None:
        self.usd_threshold = usd_threshold
        self.wallet_max_tx_count = wallet_max_tx_count

    def is_above_threshold(self, usd_value: float) -> bool:
        return usd_value >= self.usd_threshold

    def is_new_wallet(self, wallet_tx_count: int) -> bool:
        return wallet_tx_count < self.wallet_max_tx_count
