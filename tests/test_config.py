import os
import unittest
from unittest.mock import patch

from polymarkt_monitoring.config import load_config


BASE_ENV = {
    "CHAIN_NAME": "polygon",
    "RPC_URLS": "https://polygon-rpc.com",
    "BET_CONTRACT_ADDRESSES": "0x1111111111111111111111111111111111111111",
    "TOKEN_CONTRACTS": "USDC:0x2222222222222222222222222222222222222222",
    "TOKEN_DECIMALS": "USDC:6",
    "TOKEN_COINGECKO_IDS": "USDC:usd-coin",
    "USD_THRESHOLD": "5000",
    "WALLET_MAX_TX_COUNT": "5",
    "POLL_INTERVAL_SECONDS": "15",
    "BLOCK_CONFIRMATIONS": "2",
    "MAX_BLOCKS_PER_CYCLE": "50",
    "EXPLORER_API_BASE": "https://api.polygonscan.com/api",
    "EXPLORER_API_KEY": "demo",
    "COINGECKO_API_BASE": "https://api.coingecko.com/api/v3",
    "TELEGRAM_BOT_TOKEN": "token",
    "TELEGRAM_CHAT_ID": "123456",
    "LOG_LEVEL": "INFO",
}


class ConfigTests(unittest.TestCase):
    def test_load_config_parses_valid_environment(self) -> None:
        with patch.dict(os.environ, BASE_ENV, clear=True):
            config = load_config(env_file=".env.does-not-exist")

        self.assertEqual(config.chain_name, "polygon")
        self.assertEqual(config.rpc_urls, ["https://polygon-rpc.com"])
        self.assertEqual(
            config.bet_contract_addresses,
            ["0x1111111111111111111111111111111111111111"],
        )
        self.assertEqual(
            config.token_contracts,
            {"USDC": "0x2222222222222222222222222222222222222222"},
        )
        self.assertEqual(config.token_decimals["USDC"], 6)
        self.assertEqual(config.telegram_chat_id, "123456")

    def test_missing_required_field_raises(self) -> None:
        env = dict(BASE_ENV)
        env.pop("TELEGRAM_BOT_TOKEN")

        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                load_config(env_file=".env.does-not-exist")


if __name__ == "__main__":
    unittest.main()
