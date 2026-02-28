from __future__ import annotations

import logging

import requests

from polymarkt_monitoring.retry import with_retries


class TelegramNotifier:
    def __init__(
        self,
        *,
        bot_token: str,
        chat_id: str,
        request_timeout: int = 10,
        logger: logging.Logger | None = None,
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.request_timeout = request_timeout
        self.logger = logger or logging.getLogger(__name__)
        self._session = requests.Session()

    def send_message(self, text: str) -> None:
        if not text.strip():
            raise ValueError("message text must not be empty")

        endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        def _request() -> None:
            response = self._session.post(
                endpoint,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "disable_web_page_preview": True,
                },
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("ok"):
                raise ValueError(f"Telegram send failed: {payload}")

        with_retries(_request, attempts=3, logger=self.logger)
