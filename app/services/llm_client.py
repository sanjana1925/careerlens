"""Thin wrapper around the Gemini API.

Every caller must treat this as best-effort: no key configured, a network
hiccup, or a malformed response should all fall back to the heuristic path
in the calling service rather than break the request.
"""

import json
import logging

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

# The SDK logs a harmless one-time "use Chat instead of generate_content" tip
# at WARNING level on the first call — we call generate_content directly on
# purpose (no multi-turn chat state needed here), so silence just that notice.
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

MODEL = "gemini-3.6-flash"

_client: genai.Client | None = None
_client_initialized = False


def is_available() -> bool:
    return bool(settings.gemini_api_key)


def _get_client() -> genai.Client | None:
    global _client, _client_initialized
    if not _client_initialized:
        _client_initialized = True
        if settings.gemini_api_key:
            _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def generate_json(prompt: str) -> dict | list | None:
    """Calls Gemini asking for a JSON response. Returns None on any failure
    (missing key, network error, invalid JSON) so callers can fall back."""
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(response.text)
    except Exception:
        logger.warning("Gemini call failed, falling back to heuristic scoring", exc_info=True)
        return None
