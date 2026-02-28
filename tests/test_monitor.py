import unittest

from polymarkt_monitoring.config import MonitorConfig
from polymarkt_monitoring.models import BetCandidate
from polymarkt_monitoring.services import BetEvaluator, MonitoringService


class FakeRpcClient:
    def __init__(self, latest_block_number: int = 100) -> None:
        self._latest_block_number = latest_block_number

    def latest_block_number(self) -> int:
        return self._latest_block_number

    def get_block_timestamp(self, block_number: int) -> int:
        return 1700000000 + block_number


class FakePricingClient:
    def get_usd_price(self, asset_id: str) -> float:
        return 1.0


class FakeExplorerClient:
    def __init__(self, responses: list[int | Exception]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def get_transaction_count(self, wallet_address: str) -> int:
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeNotifier:
    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.messages: list[str] = []
        self.calls = 0

    def send_message(self, text: str) -> None:
        self.calls += 1
        if self.failures > 0:
            self.failures -= 1
            raise RuntimeError("temporary telegram failure")
        self.messages.append(text)


def build_config(*, start_block: int | None = None) -> MonitorConfig:
    return MonitorConfig(
        chain_name="polygon",
        rpc_urls=["https://polygon-rpc.com"],
        bet_contract_addresses=["0x1111111111111111111111111111111111111111"],
        token_contracts={},
        token_decimals={},
        token_coingecko_ids={},
        native_symbol="MATIC",
        native_coingecko_id="matic-network",
        usd_threshold=5000.0,
        wallet_max_tx_count=5,
        poll_interval_seconds=15,
        block_confirmations=2,
        max_blocks_per_cycle=50,
        start_block=start_block,
        explorer_api_base="https://api.polygonscan.com/api",
        explorer_api_key="demo",
        coingecko_api_base="https://api.coingecko.com/api/v3",
        telegram_bot_token="token",
        telegram_chat_id="chat",
        log_level="INFO",
    )


class MonitoringServiceTests(unittest.TestCase):
    def test_start_block_is_processed_inclusively(self) -> None:
        service = MonitoringService(
            config=build_config(start_block=42),
            rpc_client=FakeRpcClient(),
            pricing_client=FakePricingClient(),
            explorer_client=FakeExplorerClient([0]),
            notifier=FakeNotifier(),
            evaluator=BetEvaluator(usd_threshold=5000.0, wallet_max_tx_count=5),
        )

        self.assertEqual(service._initial_block(), 41)

    def test_failed_notification_is_retried_from_pending_queue(self) -> None:
        explorer = FakeExplorerClient([1, 1])
        notifier = FakeNotifier(failures=1)
        service = MonitoringService(
            config=build_config(),
            rpc_client=FakeRpcClient(),
            pricing_client=FakePricingClient(),
            explorer_client=explorer,
            notifier=notifier,
            evaluator=BetEvaluator(usd_threshold=5000.0, wallet_max_tx_count=5),
        )
        candidate = BetCandidate(
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            tx_hash="0xdeadbeef",
            block_number=77,
            timestamp=1700000077,
            contract_address="0x1111111111111111111111111111111111111111",
            token_symbol="USDC",
            token_amount=6000.0,
            usd_value=6000.0,
            source="erc20_transfer",
        )

        service._evaluate_and_alert([candidate])
        self.assertIn(candidate.dedup_key, service._pending_candidates)
        self.assertEqual(len(notifier.messages), 0)

        service._retry_pending_candidates()
        self.assertNotIn(candidate.dedup_key, service._pending_candidates)
        self.assertIn(candidate.dedup_key, service._seen_event_keys)
        self.assertEqual(len(notifier.messages), 1)
        self.assertEqual(explorer.calls, 2)


if __name__ == "__main__":
    unittest.main()
