"""
Shared module for querying AI engines and SERP APIs.
All functions return structured dicts and handle errors gracefully.
"""

import aiohttp
from config import OPENAI_API_KEY, PERPLEXITY_API_KEY, GEMINI_API_KEY, SERP_API_KEY


async def query_perplexity(prompt: str, timeout: int = 30) -> dict:
    """Query Perplexity API. Returns response text and source citations."""
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


async def query_gemini(prompt: str, timeout: int = 30) -> dict:
    """Query Google Gemini API. Returns response text."""
    if not GEMINI_API_KEY:
        return {"error": "no_api_key", "text": ""}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return {"text": text, "error": None}
                else:
                    body = await resp.text()
                    return {"error": f"HTTP {resp.status}: {body[:200]}", "text": ""}
        except Exception as e:
            return {"error": str(e)[:200], "text": ""}


async def search_serp(query: str, timeout: int = 30) -> dict:
    """Search Google via SerpAPI. Returns organic results + AI Overview if present."""
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
    """Check which API keys are configured."""
    return {
        "openai": bool(OPENAI_API_KEY),
        "perplexity": bool(PERPLEXITY_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
        "serp": bool(SERP_API_KEY),
    }
