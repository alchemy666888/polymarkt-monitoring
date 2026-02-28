from __future__ import annotations

import logging

import requests

from polymarkt_monitoring.retry import with_retries


class ExplorerClient:
    def __init__(
        self,
        *,
        api_base: str,
        api_key: str = "",
        request_timeout: int = 10,
        logger: logging.Logger | None = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key.strip()
        self.request_timeout = request_timeout
        self.logger = logger or logging.getLogger(__name__)
        self._session = requests.Session()

    def get_transaction_count(self, wallet_address: str) -> int:
        address = wallet_address.strip().lower()
        if not address.startswith("0x"):
            raise ValueError(f"Invalid wallet_address: {wallet_address}")

        def _request() -> int:
            params = {
                "module": "proxy",
                "action": "eth_getTransactionCount",
                "address": address,
                "tag": "latest",
            }
            if self.api_key:
                params["apikey"] = self.api_key

            response = self._session.get(self.api_base, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            payload = response.json()

            result = payload.get("result")
            if not isinstance(result, str):
                raise ValueError(f"Unexpected explorer payload: {payload}")
            return int(result, 16)

        return with_retries(_request, attempts=3, logger=self.logger)
