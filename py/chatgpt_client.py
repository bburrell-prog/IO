"""
Lightweight ChatGPT client wrapper used by the Desktop Analyzer.

This module provides a ChatGPTClient class that:
- loads environment variables (using python-dotenv if available)
- validates the presence of OPENAI_API_KEY
- sends requests to OpenAI Chat Completions endpoint with proper
  Authorization: Bearer <key> header
- implements retry with exponential backoff for 429/5xx errors

It intentionally replaces the previous shim so the rest of the app can import
from `chatgpt_client import ChatGPTClient` directly.
"""
from __future__ import annotations
import os
import time
import random
import json
import logging
from typing import Any, Dict

try:
    import requests
except Exception:  # pragma: no cover - runtime dependency
    requests = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; env may already be set
    pass

LOG = logging.getLogger(__name__)

OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")

class ChatGPTClient:
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None, max_retries: int = 5):
        if requests is None:
            raise RuntimeError("requests library is required for ChatGPTClient")

        # Detect common mistake: user passed the API key as the first positional
        # argument (so `model` contains the key). If `model` looks like an API key
        # (starts with 'sk-'), treat it as api_key and use the default model.
        inferred_api_key = None
        if isinstance(model, str) and model.startswith("sk-") and (api_key is None):
            inferred_api_key = model
            LOG.warning("Detected API key passed as first positional argument; treating first arg as api_key and using default model.")

        self.model = model if inferred_api_key is None else (api_key or os.getenv("DEFAULT_MODEL", "gpt-4o"))
        self.api_key = api_key or inferred_api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            LOG.critical("OPENAI_API_KEY not found in environment or constructor. Set OPENAI_API_KEY in .env or pass api_key param.")
            raise RuntimeError("OPENAI_API_KEY not configured")

        # Keep a session to reuse connections
        self.session = requests.Session()
        self.max_retries = int(max_retries)
        LOG.info("ChatGPTClient initialized for model: %s", self.model)

    def _make_api_request(self, messages: list[Dict[str, Any]], temperature: float = 0.0) -> Dict[str, Any]:
        """Send request to OpenAI Chat Completions with retries on 429/5xx.

        Returns JSON response on success, raises on permanent failure.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": float(temperature),
        }

        attempt = 0
        while True:
            attempt += 1
            try:
                resp = self.session.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                # Retry on rate limit or server errors
                if status in (429, 500, 502, 503, 504) and attempt <= self.max_retries:
                    jitter = random.uniform(0, 0.5)
                    delay = (2 ** (attempt - 1)) + jitter
                    LOG.warning("API returned %s. Retry %d/%d after %.2fs", status, attempt, self.max_retries, delay)
                    time.sleep(delay)
                    continue
                LOG.exception("API request failed with HTTP error: %s", e)
                raise
            except requests.exceptions.RequestException as e:
                if attempt <= self.max_retries:
                    jitter = random.uniform(0, 0.5)
                    delay = (2 ** (attempt - 1)) + jitter
                    LOG.warning("Network error on API request. Retry %d/%d after %.2fs: %s", attempt, self.max_retries, delay, e)
                    time.sleep(delay)
                    continue
                LOG.exception("API request failed permanently: %s", e)
                raise

    def get_actions_from_report(self, report: Dict[str, Any], screenshot_path: str | None = None) -> str:
        """Get action recommendations from ChatGPT, optionally with vision analysis."""
        system = {
            "role": "system",
            "content": "You are a desktop automation assistant. Analyze the screen content and suggest specific actions the user might want to take. Focus on practical, actionable suggestions like clicking buttons, typing text, or navigating menus. Be specific about coordinates when suggesting clicks."
        }

        # Prepare content array for multimodal input
        content = []

        # Add text analysis first
        content.append({
            "type": "text",
            "text": f"Screen analysis data:\n{json.dumps(report, indent=2)}\n\nPlease analyze this screen and suggest specific actions the user could take."
        })

        # Add screenshot if provided (for vision analysis)
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                import base64
                with open(screenshot_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')

                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_data}",
                        "detail": "high"
                    }
                })

                LOG.info("Including screenshot in vision analysis request")
            except Exception as e:
                LOG.warning("Failed to include screenshot in request: %s", e)

        user = {"role": "user", "content": content}

        LOG.info("Sending request to OpenAI API...")
        resp = self._make_api_request([system, user])
        # Extract assistant text
        try:
            return resp["choices"][0]["message"]["content"].strip()
        except Exception as e:
            LOG.exception("Failed to parse API response: %s", e)
            raise

    # Backwards-compat convenience method name used by older code
    def send_analysis(self, report: Dict[str, Any]) -> str:
        return self.get_actions_from_report(report)

__all__ = ["ChatGPTClient"]
