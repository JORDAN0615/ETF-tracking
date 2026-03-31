from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models import Holding


class SourceAdapter(ABC):
    @abstractmethod
    def fetch(self, source_url: str, source_config: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw_data: str, source_config: dict[str, Any]) -> tuple[str, list[Holding]]:
        raise NotImplementedError
