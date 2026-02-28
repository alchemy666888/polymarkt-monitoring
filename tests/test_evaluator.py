import unittest

from polymarkt_monitoring.services.evaluator import BetEvaluator


class BetEvaluatorTests(unittest.TestCase):
    def test_threshold_is_inclusive(self) -> None:
        evaluator = BetEvaluator(usd_threshold=5000, wallet_max_tx_count=5)

        self.assertFalse(evaluator.is_above_threshold(4999.99))
        self.assertTrue(evaluator.is_above_threshold(5000.00))
        self.assertTrue(evaluator.is_above_threshold(5000.01))

    def test_wallet_novelty_uses_strict_less_than(self) -> None:
        evaluator = BetEvaluator(usd_threshold=5000, wallet_max_tx_count=5)

        self.assertTrue(evaluator.is_new_wallet(0))
        self.assertTrue(evaluator.is_new_wallet(4))
        self.assertFalse(evaluator.is_new_wallet(5))
        self.assertFalse(evaluator.is_new_wallet(6))


if __name__ == "__main__":
    unittest.main()
