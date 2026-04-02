"""
Shared module for querying AI engines and SERP APIs.
All functions return structured dicts and handle errors gracefully.
"""

import json

import aiohttp
from config import (
    OPENAI_API_KEY,
    PERPLEXITY_API_KEY,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    SERP_API_KEY,
    ENABLE_PERPLEXITY,
    ENABLE_SERP,
)

# Secundarios si el modelo principal devuelve 404 / no encontrado (Google renombra modelos con frecuencia)
_GEMINI_MODEL_FALLBACKS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
)


async def query_perplexity(prompt: str, timeout: int = 30) -> dict:
    """Query Perplexity API. Returns response text and source citations."""
    if not ENABLE_PERPLEXITY:
        return {"error": "disabled", "text": "", "citations": []}
    if not PERPLEXITY_API_KEY:
        return {"error": "no_api_key", "text": "", "citations": []}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sonar",
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data["choices"][0]["message"]["content"]
                    citations = data.get("citations", [])
                    return {"text": text, "citations": citations, "error": None}
                else:
                    body = await resp.text()
                    return {"error": f"HTTP {resp.status}: {body[:200]}", "text": "", "citations": []}
        except Exception as e:
            return {"error": str(e)[:200], "text": "", "citations": []}


async def query_openai(prompt: str, timeout: int = 30) -> dict:
    """Query OpenAI ChatGPT API. Returns response text."""
    if not OPENAI_API_KEY:
        return {"error": "no_api_key", "text": ""}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 600,
                },
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data["choices"][0]["message"]["content"]
                    return {"text": text, "error": None}
                else:
                    body = await resp.text()
                    return {"error": f"HTTP {resp.status}: {body[:200]}", "text": ""}
        except Exception as e:
            return {"error": str(e)[:200], "text": ""}


def _gemini_models_to_try() -> list:
    """Orden: GEMINI_MODEL si está definido, luego fallbacks sin duplicados."""
    out = []
    if GEMINI_MODEL:
        out.append(GEMINI_MODEL)
    for m in _GEMINI_MODEL_FALLBACKS:
        if m not in out:
            out.append(m)
    return out


def _gemini_should_retry_next_model(status: int, body: str) -> bool:
    """404/403 de modelo o permiso → probar siguiente id."""
    if status in (404, 403):
        return True
    low = body.lower()
    if "not found" in low or "not_available" in low or "invalid model" in low:
        return True
    if status == 400 and ("model" in low and ("not found" in low or "does not exist" in low)):
        return True
    return False


def _gemini_extract_text(data: dict) -> tuple:
    """Devuelve (texto o None, error_corto o None)."""
    feedback = data.get("promptFeedback") or {}
    block = feedback.get("blockReason")
    if block:
        return None, f"blocked_prompt:{block}"

    cands = data.get("candidates") or []
    if not cands:
        return None, "no_candidates"

    cand = cands[0]
    reason = cand.get("finishReason") or ""
    if reason and reason not in ("STOP", "MAX_TOKENS", "FINISH_REASON_UNSPECIFIED", ""):
        if reason in ("SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "RECITATION", "OTHER"):
            return None, f"blocked_response:{reason}"

    parts = (cand.get("content") or {}).get("parts") or []
    texts = []
    for p in parts:
        if isinstance(p, dict) and p.get("text"):
            texts.append(p["text"])
    if texts:
        return "\n".join(texts), None
    return None, f"no_text finishReason={reason or '?'}"


async def query_gemini(prompt: str, timeout: int = 30) -> dict:
    """Query Google Gemini API. Returns response text."""
    if not GEMINI_API_KEY:
        return {"error": "no_api_key", "text": ""}

    last_error = ""
    models = _gemini_models_to_try()

    async with aiohttp.ClientSession() as session:
        for model in models:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={GEMINI_API_KEY}"
            )
            try:
                async with session.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    body = await resp.text()
                    if resp.status != 200:
                        last_error = f"{model} HTTP {resp.status}: {body[:280]}"
                        if _gemini_should_retry_next_model(resp.status, body):
                            continue
                        return {"error": last_error[:300], "text": ""}

                    try:
                        data = json.loads(body)
                    except json.JSONDecodeError:
                        last_error = f"{model}: invalid JSON"
                        continue

                    text, err = _gemini_extract_text(data)
                    if text is not None:
                        return {"text": text, "error": None}
                    last_error = f"{model}: {err}"
                    # Bloqueo de contenido: no suele arreglarse cambiando modelo
                    if err and err.startswith("blocked_"):
                        return {"error": last_error[:300], "text": ""}
                    continue
            except Exception as e:
                last_error = f"{model}: {str(e)[:200]}"
                continue

    return {"error": last_error[:300] or "gemini_all_models_failed", "text": ""}


async def search_serp(query: str, timeout: int = 30) -> dict:
    """Search Google via SerpAPI. Returns organic results + AI Overview if present."""
    if not ENABLE_SERP:
        return {"error": "disabled", "results": [], "ai_overview": None}
    if not SERP_API_KEY:
        return {"error": "no_api_key", "results": [], "ai_overview": None}

    async with aiohttp.ClientSession() as session:
        try:
            params = {
                "q": query,
                "api_key": SERP_API_KEY,
                "engine": "google",
                "hl": "es",
                "gl": "es",
            }
            async with session.get(
                "https://serpapi.com/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ai_overview = data.get("ai_overview", None)
                    organic = data.get("organic_results", [])[:10]
                    return {"ai_overview": ai_overview, "organic_results": organic, "error": None}
                else:
                    body = await resp.text()
                    return {"error": f"HTTP {resp.status}: {body[:200]}", "results": [], "ai_overview": None}
        except Exception as e:
            return {"error": str(e)[:200], "results": [], "ai_overview": None}


def check_brand_mentioned(text: str, brand: str, domain: str) -> dict:
    """Check if a brand or domain is mentioned in AI response text."""
    text_lower = text.lower()
    brand_lower = brand.lower()
    domain_lower = domain.lower()
    domain_no_tld = domain_lower.split(".")[0]

    brand_found = brand_lower in text_lower
    domain_found = domain_lower in text_lower
    partial_found = domain_no_tld in text_lower and len(domain_no_tld) > 3

    mentioned = brand_found or domain_found or partial_found

    # Extract the relevant snippet
    snippet = ""
    if mentioned:
        for term in [brand_lower, domain_lower, domain_no_tld]:
            idx = text_lower.find(term)
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(text), idx + len(term) + 80)
                snippet = text[start:end].strip()
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
                break

    return {
        "mentioned": mentioned,
        "brand_found": brand_found,
        "domain_found": domain_found,
        "snippet": snippet,
    }


def has_api_keys() -> dict:
    """Check which API keys are configured and not disabled via ENABLE_* flags."""
    return {
        "openai": bool(OPENAI_API_KEY),
        "perplexity": bool(PERPLEXITY_API_KEY) and ENABLE_PERPLEXITY,
        "gemini": bool(GEMINI_API_KEY),
        "serp": bool(SERP_API_KEY) and ENABLE_SERP,
    }
