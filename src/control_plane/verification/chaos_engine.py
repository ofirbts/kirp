from __future__ import annotations

import asyncio
from typing import Any


class ChaosEngine:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    async def maybe_delay_ms(self, ms: int) -> None:
        if self.enabled and ms > 0:
            await asyncio.sleep(ms / 1000.0)
