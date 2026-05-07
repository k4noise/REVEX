from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Any

from core.ttl_cache import RedisCache


class HintRateLimitExceeded(Exception):
    def __init__(self, retry_after: int, attempts: int, hard_blocked: bool = False):
        self.retry_after = retry_after
        self.attempts = attempts
        self.hard_blocked = hard_blocked
        super().__init__("Hint rate limit exceeded")


@dataclass
class HintRateLimitDecision:
    allowed: bool
    retry_after: int = 0
    attempts: int = 0
    hard_blocked: bool = False


class HintRateLimiter:
    def __init__(
            self,
            cache: RedisCache,
            *,
            free_attempts: int = 2,
            max_attempts: int = 5,
            base_delay_seconds: int = 30,
            multiplier: float = 4.0,
            max_delay_seconds: int = 3600,
            state_ttl_seconds: int = 86400,
    ) -> None:
        self.cache = cache
        self.redis = cache._redis

        self.free_attempts = free_attempts
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.multiplier = multiplier
        self.max_delay_seconds = max_delay_seconds
        self.state_ttl_seconds = state_ttl_seconds

    def check_and_consume(
            self,
            *,
            user_id: str,
            report_id: uuid.UUID,
            element_id: uuid.UUID,
            answer_payload: Any,
    ) -> HintRateLimitDecision:
        key = self._key(user_id, report_id, element_id)
        answer_hash = self._hash_answer(answer_payload)

        now = int(time.time())
        state = self._load_state(key)

        if state is None or state.get("answer_hash") != answer_hash:
            state = {
                "answer_hash": answer_hash,
                "attempts": 0,
                "blocked_until": 0,
                "hard_blocked": False,
            }

        attempts = int(state.get("attempts", 0))
        blocked_until = int(state.get("blocked_until", 0))
        hard_blocked = bool(state.get("hard_blocked", False))

        if hard_blocked:
            return HintRateLimitDecision(
                allowed=False,
                retry_after=self.state_ttl_seconds,
                attempts=attempts,
                hard_blocked=True,
            )

        if blocked_until > now:
            return HintRateLimitDecision(
                allowed=False,
                retry_after=blocked_until - now,
                attempts=attempts,
                hard_blocked=False,
            )

        attempts += 1

        if attempts > self.max_attempts:
            state.update(
                {
                    "answer_hash": answer_hash,
                    "attempts": attempts,
                    "blocked_until": 0,
                    "hard_blocked": True,
                }
            )
            self._save_state(key, state)
            return HintRateLimitDecision(
                allowed=False,
                retry_after=self.state_ttl_seconds,
                attempts=attempts,
                hard_blocked=True,
            )

        cooldown = self._compute_cooldown(attempts)
        blocked_until = now + cooldown if cooldown > 0 else 0

        state.update(
            {
                "answer_hash": answer_hash,
                "attempts": attempts,
                "blocked_until": blocked_until,
                "hard_blocked": False,
            }
        )
        self._save_state(key, state)

        return HintRateLimitDecision(
            allowed=True,
            retry_after=0,
            attempts=attempts,
            hard_blocked=False,
        )

    def reset(
            self,
            *,
            user_id: str,
            report_id: uuid.UUID,
            element_id: uuid.UUID,
    ) -> None:
        self.cache.delete(self._key(user_id, report_id, element_id))

    def _compute_cooldown(self, attempts: int) -> int:
        if attempts <= self.free_attempts:
            return 0

        step = attempts - self.free_attempts - 1
        delay = int(self.base_delay_seconds * (self.multiplier ** step))
        return min(delay, self.max_delay_seconds)

    def _key(self, user_id: str, report_id: uuid.UUID, element_id: uuid.UUID) -> str:
        return f"hint:attempt:{user_id}:{report_id}:{element_id}"

    def _hash_answer(self, answer_payload: Any) -> str:
        raw = json.dumps(answer_payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _load_state(self, key: str) -> Optional[dict[str, Any]]:
        try:
            raw = self.cache.get(key)
            if isinstance(raw, dict):
                return raw
            return None
        except Exception:
            return None

    def _save_state(self, key: str, state: dict[str, Any]) -> None:
        self.cache.set(key, state, ttl=self.state_ttl_seconds)