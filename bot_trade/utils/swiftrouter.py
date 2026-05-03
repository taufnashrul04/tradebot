"""
Swift Router API Client with automatic key rotation.

Handles rate limiting by rotating through multiple API keys automatically.
"""
import os
import random
from typing import Optional
from dataclasses import dataclass, field
from collections import deque
import time


@dataclass
class SwiftRouterKey:
    """API key with usage tracking."""
    key: str
    last_used: float = 0.0
    error_count: int = 0
    rate_limited_until: float = 0.0


@dataclass
class SwiftRouterConfig:
    """Swift Router configuration."""
    base_url: str = "https://api.swiftrouter.com/v1"
    keys: list[SwiftRouterKey] = field(default_factory=list)
    current_index: int = 0
    cooldown_seconds: int = 60  # Wait 60s before retrying a rate-limited key
    max_errors: int = 3  # Switch key after N errors


class SwiftRouterClient:
    """
    Swift Router API client with automatic key rotation.

    Usage:
        client = SwiftRouterClient()
        response = client.request("POST", "/chat/completions", json={...})
    """

    def __init__(self, config: Optional[SwiftRouterConfig] = None):
        self.config = config or self._load_config()
        self._session = None

    def _load_config(self) -> SwiftRouterConfig:
        """Load configuration from environment or file."""
        # Try environment variable first
        keys_str = os.getenv("SWIFT_ROUTER_KEYS", "")
        if not keys_str:
            # Try loading from .env.swiftrouter file
            env_file = "/home/ubuntu/tradebot/.env.swiftrouter"
            if os.path.exists(env_file):
                with open(env_file) as f:
                    for line in f:
                        if line.startswith("SWIFT_ROUTER_KEYS="):
                            keys_str = line.split("=", 1)[1].strip()
                            break

        # Parse keys
        keys = []
        if keys_str:
            for key in keys_str.split(","):
                key = key.strip()
                if key:
                    keys.append(SwiftRouterKey(key=key))

        if not keys:
            raise ValueError("No Swift Router API keys configured. "
                           "Set SWIFT_ROUTER_KEYS environment variable.")

        return SwiftRouterConfig(keys=keys)

    def _get_next_key(self) -> SwiftRouterKey:
        """Get next available API key, skipping rate-limited ones."""
        now = time.time()
        keys = self.config.keys

        # Try to find a non-rate-limited key
        for _ in range(len(keys)):
            key = keys[self.config.current_index]

            # Check if key is rate-limited
            if key.rate_limited_until > now:
                # Move to next key
                self.config.current_index = (self.config.current_index + 1) % len(keys)
                continue

            # Check if key has too many errors
            if key.error_count >= self.config.max_errors:
                # Reset error count after cooldown
                if now - key.last_used > self.config.cooldown_seconds:
                    key.error_count = 0
                else:
                    # Move to next key
                    self.config.current_index = (self.config.current_index + 1) % len(keys)
                    continue

            return key

        # All keys rate-limited, return the one that will be available soonest
        return min(keys, key=lambda k: k.rate_limited_until)

    def _mark_key_error(self, key: SwiftRouterKey, is_rate_limit: bool = False):
        """Mark a key as having an error."""
        key.error_count += 1
        key.last_used = time.time()

        if is_rate_limit:
            key.rate_limited_until = time.time() + self.config.cooldown_seconds
            # Switch to next key immediately
            self.config.current_index = (self.config.current_index + 1) % len(self.config.keys)

    def _mark_key_success(self, key: SwiftRouterKey):
        """Mark a key as successful."""
        key.error_count = 0
        key.last_used = time.time()

    def request(self, method: str, path: str, **kwargs) -> dict:
        """
        Make an HTTP request with automatic key rotation.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/chat/completions")
            **kwargs: Additional arguments for requests.request

        Returns:
            Response JSON as dict

        Raises:
            Exception: If all keys are rate-limited or request fails
        """
        import requests

        url = f"{self.config.base_url}{path}"
        max_retries = len(self.config.keys) * 2  # Allow cycling through keys twice

        for attempt in range(max_retries):
            key = self._get_next_key()

            # Check if key is rate-limited
            if key.rate_limited_until > time.time():
                wait_time = key.rate_limited_until - time.time()
                if attempt == max_retries - 1:
                    raise Exception(f"All keys rate-limited. Wait {wait_time:.0f}s")
                time.sleep(min(wait_time, 1.0))
                continue

            # Add API key to headers
            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Bearer {key.key}"
            headers["Content-Type"] = "application/json"

            try:
                response = requests.request(method, url, headers=headers, **kwargs, timeout=30)

                # Check for rate limit
                if response.status_code == 429:
                    self._mark_key_error(key, is_rate_limit=True)
                    continue

                # Check for other errors
                if response.status_code >= 400:
                    self._mark_key_error(key)
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    raise Exception(f"API error {response.status_code}: {error_data}")

                # Success
                self._mark_key_success(key)
                return response.json()

            except requests.exceptions.Timeout:
                self._mark_key_error(key)
                if attempt == max_retries - 1:
                    raise Exception("Request timeout after all retries")
                continue

            except requests.exceptions.RequestException as e:
                self._mark_key_error(key)
                if attempt == max_retries - 1:
                    raise Exception(f"Request failed: {e}")
                continue

        raise Exception("All API keys exhausted")

    def get_current_key(self) -> str:
        """Get the current API key (for debugging)."""
        key = self._get_next_key()
        return key.key

    def get_status(self) -> dict:
        """Get status of all API keys."""
        now = time.time()
        return {
            "total_keys": len(self.config.keys),
            "current_index": self.config.current_index,
            "keys": [
                {
                    "key": k.key[:20] + "...",
                    "last_used": now - k.last_used,
                    "error_count": k.error_count,
                    "rate_limited": k.rate_limited_until > now,
                    "rate_limited_for": max(0, k.rate_limited_until - now) if k.rate_limited_until > now else 0,
                }
                for k in self.config.keys
            ]
        }


# Singleton instance
_swift_router_client: Optional[SwiftRouterClient] = None


def get_swift_router_client() -> SwiftRouterClient:
    """Get or create the singleton Swift Router client."""
    global _swift_router_client
    if _swift_router_client is None:
        _swift_router_client = SwiftRouterClient()
    return _swift_router_client


def reset_swift_router_client():
    """Reset the singleton client (useful for testing)."""
    global _swift_router_client
    _swift_router_client = None
