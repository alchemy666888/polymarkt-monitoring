from __future__ import annotations

import argparse
import asyncio
import logging

from polymarkt_monitoring.clients import CoinGeckoPricingClient, ExplorerClient, RpcClient, TelegramNotifier
from polymarkt_monitoring.config import load_config
from polymarkt_monitoring.services import BetEvaluator, MonitoringService


def cli_entrypoint() -> None:
    parser = argparse.ArgumentParser(description="Monitor high-value bets from new wallets")
    parser.add_argument("--env-file", default=".env", help="Path to environment file")
    parser.add_argument("--once", action="store_true", help="Process available confirmed blocks once then exit")
    args = parser.parse_args()

    config = load_config(args.env_file)
    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("polymarkt_monitoring")

    rpc_client = RpcClient(rpc_urls=config.rpc_urls, logger=logger)
    pricing_client = CoinGeckoPricingClient(api_base=config.coingecko_api_base, logger=logger)
    explorer_client = ExplorerClient(
        api_base=config.explorer_api_base,
        api_key=config.explorer_api_key,
        logger=logger,
    )
    notifier = TelegramNotifier(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
        logger=logger,
    )
    evaluator = BetEvaluator(
        usd_threshold=config.usd_threshold,
        wallet_max_tx_count=config.wallet_max_tx_count,
    )

    service = MonitoringService(
        config=config,
        rpc_client=rpc_client,
        pricing_client=pricing_client,
        explorer_client=explorer_client,
        notifier=notifier,
        evaluator=evaluator,
        logger=logger,
    )

    asyncio.run(service.run(once=args.once))


if __name__ == "__main__":
    cli_entrypoint()
