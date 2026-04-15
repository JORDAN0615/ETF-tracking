"""Notification services for ETF tracking system."""
from __future__ import annotations

import os
from typing import Optional

import requests


class TelegramNotifier:
    """Telegram notification service for ETF tracking alerts."""
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        weight_threshold: float = 5.0
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.weight_threshold = weight_threshold
        self.enabled = bool(self.bot_token and self.chat_id)
    
    def send_message(self, message: str) -> bool:
        """Send a message to Telegram chat."""
        if not self.enabled:
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json().get("ok", False)
        except requests.RequestException as e:
            print(f"Telegram notification failed: {e}")
            return False
    
    def notify_major_change(
        self,
        ticker: str,
        etf_name: str,
        trade_date: str,
        instrument_key: str,
        instrument_name: str,
        change_type: str,
        prev_weight: Optional[float],
        curr_weight: Optional[float]
    ) -> bool:
        """Send notification for major holding changes."""
        if not self.enabled:
            return False
        
        # Calculate weight change
        weight_delta = None
        if prev_weight is not None and curr_weight is not None:
            weight_delta = curr_weight - prev_weight
        
        # Check if change exceeds threshold
        if weight_delta is not None and abs(weight_delta) < self.weight_threshold:
            return False
        
        # Build message
        change_emoji = {
            "enter_top10": "🆕",
            "exit_top10": "👋",
            "increase": "📈",
            "decrease": "📉"
        }
        emoji = change_emoji.get(change_type, "📊")
        
        weight_info = ""
        if prev_weight is not None and curr_weight is not None:
            weight_info = f"\n權重變化：{prev_weight:.2f}% → {curr_weight:.2f}% ({weight_delta:+.2f}%)".format(
                prev_weight, curr_weight, weight_delta
            )
        elif curr_weight is not None:
            weight_info = f"\n當前權重：{curr_weight:.2f}%".format(curr_weight)
        
        message = (
            f"{emoji} <b>ETF 持股重大變動通知</b>\n\n"
            f"📌 ETF: {ticker} ({etf_name})\n"
            f"📅 交易日：{trade_date}\n\n"
            f"📊 標的：{instrument_key} ({instrument_name})\n"
            f"🔄 變動類型：{self._format_change_type(change_type)}\n"
            f"{weight_info}"
        )
        
        return self.send_message(message)
    
    def _format_change_type(self, change_type: str) -> str:
        """Format change type for display."""
        change_types = {
            "enter_top10": "新進前十大",
            "exit_top10": "退出前十大",
            "increase": "增持",
            "decrease": "減持"
        }
        return change_types.get(change_type, change_type)


def create_telegram_notifier() -> TelegramNotifier:
    """Create a Telegram notifier instance with default configuration."""
    threshold = float(os.getenv("ETF_NOTIFICATION_WEIGHT_THRESHOLD", "5.0"))
    return TelegramNotifier(weight_threshold=threshold)
