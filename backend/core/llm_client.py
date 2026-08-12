"""
Thin, provider-agnostic wrapper around whichever LLM backend is
configured via LLM_PROVIDER in .env. Every agent calls only the two
functions below (complete_text / analyze_image), so switching providers
never touches agent code.

Supported providers:
  - "gemini"    Google AI Studio free tier. Text + vision. No credit card.
  - "groq"      Free tier, very fast, TEXT ONLY (no vision support).
                If you pick "groq", also set GEMINI_API_KEY so the
                Image Agent still has a vision model to fall back on.
  - "anthropic" Paid, highest quality (original default).
"""
import base64
import mimetypes
import time
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.config import get_settings

settings = get_settings()


def _require(value: str, var_name: str):
    if not value:
        raise RuntimeError(
            f"{var_name} is not set. Add it to backend/.env before running MediAssist AI."
        )
    return value


class RateLimitError(Exception):
    """Raised on a 429 from the LLM provider — a distinct exception type
    so retry logic can wait much longer for this than for a transient
    network error."""
    pass


def _gemini_retry_delay_seconds(resp: requests.Response, attempt: int) -> float:
    """Gemini's 429 body often includes a suggested retry delay under
    error.details[].retryDelay (e.g. "20s"). Use it when present;
    otherwise back off generously, since free-tier limits are per
    MINUTE — a 2-10s retry (fine for a network blip) is nowhere near
    long enough to let a per-minute quota reset."""
    try:
        details = resp.json().get("error", {}).get("details", [])
        for d in details:
            delay = d.get("retryDelay")  # e.g. "19s"
            if delay:
                return float(delay.rstrip("s")) + 1
    except Exception:
        pass
    return min(15 * attempt, 65)  # 15s, 30s, 45s, 60s... capped just over a minute


# --------------------------------------------------------------------------
# Gemini (free tier, text + vision)
# --------------------------------------------------------------------------
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _gemini_generate(model: str, system: str, parts: list[dict], max_tokens: int, temperature: float) -> str:
    api_key = _require(settings.GEMINI_API_KEY, "GEMINI_API_KEY")
    url = f"{GEMINI_BASE}/{model}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
    }

    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        resp = requests.post(url, json=payload, timeout=60)

        if resp.status_code == 429:
            if attempt == max_attempts:
                raise RateLimitError(
                    "Gemini free-tier rate limit hit repeatedly (429). "
                    "Free tier allows roughly 10 requests/minute — wait a "
                    "minute and try again, or switch LLM_PROVIDER to reduce "
                    "call volume. See backend/.env for provider options."
                )
            wait_s = _gemini_retry_delay_seconds(resp, attempt)
            print(f"[llm_client] Gemini 429 rate limit — waiting {wait_s:.0f}s before retry {attempt}/{max_attempts - 1}...")
            time.sleep(wait_s)
            continue

        if resp.status_code >= 500 and attempt < max_attempts:
            # Transient server error — short backoff is fine here.
            time.sleep(2 * attempt)
            continue

        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {data}")
        return "".join(p.get("text", "") for p in candidates[0]["content"]["parts"])

    raise RuntimeError("Gemini request failed after all retry attempts.")


def _gemini_text(system: str, prompt: str, max_tokens: int, temperature: float) -> str:
    return _gemini_generate(settings.GEMINI_TEXT_MODEL, system, [{"text": prompt}], max_tokens, temperature)


def _gemini_image(image_path: str, system: str, prompt: str, max_tokens: int) -> str:
    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "image/png"
    with open(image_path, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
    parts = [
        {"inline_data": {"mime_type": mime_type, "data": image_b64}},
        {"text": prompt},
    ]
    return _gemini_generate(settings.GEMINI_VISION_MODEL, system, parts, max_tokens, 0.2)


# --------------------------------------------------------------------------
# Groq (free tier, OpenAI-compatible, TEXT ONLY)
# --------------------------------------------------------------------------
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _groq_text(system: str, prompt: str, max_tokens: int, temperature: float) -> str:
    api_key = _require(settings.GROQ_API_KEY, "GROQ_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.GROQ_TEXT_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# --------------------------------------------------------------------------
# Anthropic (paid)
# --------------------------------------------------------------------------
_anthropic_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        _anthropic_client = Anthropic(api_key=_require(settings.ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY"))
    return _anthropic_client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _anthropic_text(system: str, prompt: str, max_tokens: int, temperature: float) -> str:
    client = _get_anthropic_client()
    resp = client.messages.create(
        model=settings.TEXT_MODEL, max_tokens=max_tokens, temperature=temperature,
        system=system, messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _anthropic_image(image_path: str, system: str, prompt: str, max_tokens: int) -> str:
    client = _get_anthropic_client()
    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "image/png"
    with open(image_path, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
    resp = client.messages.create(
        model=settings.VISION_MODEL, max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": image_b64}},
            {"type": "text", "text": prompt},
        ]}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


# --------------------------------------------------------------------------
# Public interface used by every agent
# --------------------------------------------------------------------------
def complete_text(system: str, prompt: str, max_tokens: int = 1500, temperature: float = 0.2) -> str:
    provider = settings.LLM_PROVIDER.lower()
    if provider == "gemini":
        return _gemini_text(system, prompt, max_tokens, temperature)
    if provider == "groq":
        return _groq_text(system, prompt, max_tokens, temperature)
    if provider == "anthropic":
        return _anthropic_text(system, prompt, max_tokens, temperature)
    raise RuntimeError(f"Unknown LLM_PROVIDER: {provider}")


def analyze_image(image_path: str, system: str, prompt: str, max_tokens: int = 1200) -> str:
    provider = settings.LLM_PROVIDER.lower()
    # Groq's free tier has no vision models, so the Image Agent always
    # uses Gemini for images even if text generation is routed to Groq.
    if provider in ("gemini", "groq"):
        return _gemini_image(image_path, system, prompt, max_tokens)
    if provider == "anthropic":
        return _anthropic_image(image_path, system, prompt, max_tokens)
    raise RuntimeError(f"Unknown LLM_PROVIDER: {provider}")


OCR_SYSTEM = """You transcribe text from photographed or screenshotted
documents (lab reports, prescriptions) as accurately as possible.
Preserve numbers, units, and reference ranges exactly as shown. Output
only the transcribed text — no commentary, no markdown formatting."""

OCR_PROMPT = """Transcribe all readable text from this document image,
preserving the layout of test names, values, units, and reference
ranges as closely as possible (e.g. one line per row of a table)."""


def ocr_document_image(image_path: str) -> str:
    """Vision-based OCR for a photographed/screenshotted document (a
    blood report or prescription captured as a PNG/JPG instead of a
    PDF). Used by the Blood Agent and Drug Agent so image-format
    documents go through the same text-structuring pipeline as PDFs,
    instead of being misrouted to the Imaging Agent's scan-reading
    prompt."""
    return analyze_image(image_path, system=OCR_SYSTEM, prompt=OCR_PROMPT, max_tokens=2000)


CLASSIFY_IMAGE_SYSTEM = """You classify what kind of document a medical
image shows. Respond with STRICT JSON only: {"kind": "blood_report" |
"prescription" | "scan" | "unknown"}. Use "blood_report" for a
photographed/screenshotted lab or pathology report (a table of test
names and values). Use "prescription" for a photographed doctor's
prescription or medication list. Use "scan" for an actual medical
imaging scan (X-ray, MRI, CT — grayscale radiographic images, not a
document with text). Use "unknown" if you can't tell."""

CLASSIFY_IMAGE_PROMPT = "What kind of medical image is this? Respond with the JSON only."


def classify_image_content(image_path: str) -> str:
    """Best-effort content-based classification for an uploaded image,
    used when the filename gives no useful hint (e.g. a screenshot).
    Returns one of: blood_report, prescription, scan, unknown."""
    import json
    try:
        raw = analyze_image(image_path, system=CLASSIFY_IMAGE_SYSTEM, prompt=CLASSIFY_IMAGE_PROMPT, max_tokens=50)
        raw = raw.strip().strip("`")
        start, end = raw.find("{"), raw.rfind("}")
        parsed = json.loads(raw[start:end + 1]) if start != -1 and end != -1 else {}
        kind = parsed.get("kind", "unknown")
        return kind if kind in ("blood_report", "prescription", "scan") else "unknown"
    except Exception:
        return "unknown"
