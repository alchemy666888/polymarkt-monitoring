from __future__ import annotations

import logging
import time

import requests

from polymarkt_monitoring.retry import with_retries


class CoinGeckoPricingClient:
    def __init__(
        self,
        *,
        api_base: str = "https://api.coingecko.com/api/v3",
        cache_ttl_seconds: int = 30,
        request_timeout: int = 10,
        logger: logging.Logger | None = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.cache_ttl_seconds = cache_ttl_seconds
        self.request_timeout = request_timeout
        self.logger = logger or logging.getLogger(__name__)
        self._session = requests.Session()
        self._cache: dict[str, tuple[float, float]] = {}

    def get_usd_price(self, asset_id: str) -> float:
        asset = asset_id.strip().lower()
        if not asset:
            raise ValueError("asset_id is required")

        cached = self._cache.get(asset)
        now = time.time()
        if cached and now - cached[1] <= self.cache_ttl_seconds:
            return cached[0]

        def _request() -> float:
            response = self._session.get(
                f"{self.api_base}/simple/price",
                params={"ids": asset, "vs_currencies": "usd"},
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            payload = response.json()
            usd = payload.get(asset, {}).get("usd")
            if usd is None:
                raise ValueError(f"CoinGecko response missing usd price for {asset}")
            return float(usd)

        price = with_retries(_request, attempts=3, logger=self.logger)
        self._cache[asset] = (price, now)
        return price
