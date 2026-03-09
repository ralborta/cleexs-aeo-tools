"""
Tool 5: AI Search Presence Tester
Based on mangools.com/ai-search-grader

Queries ChatGPT, Gemini, and Perplexity with brand-related prompts
and checks if the brand/domain is actually mentioned in responses.
Falls back to on-page signal analysis when API keys are not configured.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from tools.http_client import create_session

from ai_engines import (
    query_openai, query_gemini, query_perplexity,
    check_brand_mentioned, has_api_keys,
)


class AIPresenceTester:

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    async def test(self, url: str) -> dict:
        if not url.startswith("http"):
            url = "https://" + url

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        brand = domain.split(".")[0].capitalize()

        connector, timeout_config, headers = create_session(timeout=self.timeout, max_connections=5)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout_config,
            headers=headers,
        ) as session:
            try:
                async with session.get(url, allow_redirects=True) as resp:
                    if resp.status != 200:
                        return self._error_result(url, f"HTTP {resp.status}")
                    html = await resp.text()
            except Exception as e:
                return self._error_result(url, str(e)[:200])

        soup = BeautifulSoup(html, "lxml")

        # Extract context for better prompts
        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc = meta_desc.get("content", "")[:100] if meta_desc else ""

        # On-page signals (always available)
        signals = self._analyze_signals(url, soup, domain, brand)

        # Real AI engine queries
        keys = has_api_keys()
        engine_results = await self._query_engines(brand, domain, desc, keys)

        # Calculate score combining signals + real presence
        score = self._calculate_score(signals, engine_results, keys)

        # Suggestions based on real results
        suggestions = self._generate_suggestions(signals, engine_results, keys)

        return {
            "url": url,
            "brand_name": brand,
            "domain": domain,
            "signals": signals,
            "engine_results": engine_results,
            "api_keys_configured": keys,
            "score": score,
            "suggestions": suggestions,
        }

    async def _query_engines(self, brand: str, domain: str, description: str, keys: dict) -> list:
        """Query each AI engine and check if brand is mentioned."""
        engines = []
        prompt = f"Que es {brand} ({domain})? Que ofrece y es recomendable?"
        alt_prompt = f"Recomienda las mejores empresas o herramientas de {description}" if description else f"Que sabes sobre {domain}?"

        tasks = {}

        if keys["openai"]:
            tasks["ChatGPT"] = query_openai(prompt)
        if keys["gemini"]:
            tasks["Gemini"] = query_gemini(prompt)
        if keys["perplexity"]:
            tasks["Perplexity"] = query_perplexity(prompt)

        if tasks:
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for engine_name, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    engines.append({
                        "engine": engine_name,
                        "status": "error",
                        "mentioned": False,
                        "response_preview": "",
                        "snippet": "",
                        "error": str(result)[:200],
                    })
                elif result.get("error"):
                    engines.append({
                        "engine": engine_name,
                        "status": "error",
                        "mentioned": False,
                        "response_preview": "",
                        "snippet": "",
                        "error": result["error"],
                    })
                else:
                    text = result.get("text", "")
                    mention = check_brand_mentioned(text, brand, domain)
                    citations = result.get("citations", [])
                    domain_cited = any(domain.lower() in c.lower() for c in citations) if citations else False

                    engines.append({
                        "engine": engine_name,
                        "status": "found" if mention["mentioned"] else "not_found",
                        "mentioned": mention["mentioned"],
                        "brand_found": mention["brand_found"],
                        "domain_found": mention["domain_found"],
                        "domain_cited": domain_cited,
                        "response_preview": text[:300] + ("..." if len(text) > 300 else ""),
                        "snippet": mention["snippet"],
                        "citations": citations[:5] if citations else [],
                    })

        # Also query with alternative prompt for Perplexity (category search)
        if keys["perplexity"] and alt_prompt:
            alt_result = await query_perplexity(alt_prompt)
            if alt_result and not alt_result.get("error"):
                text = alt_result.get("text", "")
                mention = check_brand_mentioned(text, brand, domain)
                citations = alt_result.get("citations", [])
                domain_cited = any(domain.lower() in c.lower() for c in citations)

                engines.append({
                    "engine": "Perplexity (busqueda de categoria)",
                    "status": "found" if mention["mentioned"] or domain_cited else "not_found",
                    "mentioned": mention["mentioned"],
                    "brand_found": mention["brand_found"],
                    "domain_found": mention["domain_found"],
                    "domain_cited": domain_cited,
                    "response_preview": text[:300] + ("..." if len(text) > 300 else ""),
                    "snippet": mention["snippet"],
                    "citations": citations[:5] if citations else [],
                    "query_used": alt_prompt,
                })

        return engines

    def _analyze_signals(self, url: str, soup: BeautifulSoup, domain: str, brand: str) -> list:
        signals = []

        title = soup.find("title")
        title_text = title.get_text(strip=True) if title else ""
        has_brand_in_title = brand.lower() in title_text.lower() if title_text else False
        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc_text = meta_desc.get("content", "") if meta_desc else ""

        signals.append({
            "name": "Identidad de marca",
            "status": "pass" if has_brand_in_title and desc_text else "warning" if title_text else "fail",
            "details": f"Titulo: '{title_text[:60]}'" if title_text else "Sin titulo",
        })

        json_ld = soup.find_all("script", type="application/ld+json")
        signals.append({
            "name": "Datos estructurados (Schema)",
            "status": "pass" if len(json_ld) > 0 else "fail",
            "details": f"{len(json_ld)} bloques JSON-LD" if json_ld else "Sin schema",
        })

        h1 = soup.find_all("h1")
        h2 = soup.find_all("h2")
        h3 = soup.find_all("h3")
        heading_score = min(len(h1), 1) + min(len(h2), 3) + min(len(h3), 3)
        signals.append({
            "name": "Estructura de contenido",
            "status": "pass" if heading_score >= 4 else "warning" if heading_score >= 2 else "fail",
            "details": f"{len(h1)} H1, {len(h2)} H2, {len(h3)} H3",
        })

        og_tags = soup.find_all("meta", attrs={"property": lambda x: x and x.startswith("og:")})
        signals.append({
            "name": "Meta tags sociales",
            "status": "pass" if len(og_tags) >= 3 else "warning" if len(og_tags) >= 1 else "fail",
            "details": f"{len(og_tags)} Open Graph tags",
        })

        body = soup.find("body")
        text_content = body.get_text(strip=True) if body else ""
        word_count = len(text_content.split())
        signals.append({
            "name": "Profundidad de contenido",
            "status": "pass" if word_count >= 500 else "warning" if word_count >= 200 else "fail",
            "details": f"~{word_count} palabras",
        })

        return signals

    def _calculate_score(self, signals: list, engine_results: list, keys: dict) -> int:
        # If we have real engine results, weight them heavily
        any_key = any(keys.values())

        if any_key and engine_results:
            # Real presence: 70% weight, signals: 30%
            mentioned_count = sum(1 for e in engine_results if e.get("mentioned") or e.get("domain_cited"))
            total_queries = len(engine_results)
            presence_score = round((mentioned_count / total_queries) * 100) if total_queries > 0 else 0

            signal_passes = sum(1 for s in signals if s["status"] == "pass")
            signal_total = len(signals)
            signal_score = round((signal_passes / signal_total) * 100) if signal_total > 0 else 0

            return max(0, min(100, round(presence_score * 0.7 + signal_score * 0.3)))
        else:
            # No API keys: pure signal score
            signal_passes = sum(1 for s in signals if s["status"] == "pass")
            signal_warns = sum(1 for s in signals if s["status"] == "warning")
            signal_total = len(signals)
            return round(((signal_passes + signal_warns * 0.5) / signal_total) * 100) if signal_total > 0 else 0

    def _generate_suggestions(self, signals: list, engine_results: list, keys: dict) -> list:
        suggestions = []

        if not any(keys.values()):
            suggestions.append({
                "priority": "info",
                "message": "Configura API keys para obtener resultados reales",
                "detail": "Sin API keys de OpenAI, Gemini o Perplexity, solo se analizan senales on-page. Con API keys se consultan los motores de IA directamente.",
            })

        # Check real presence
        if engine_results:
            not_found = [e for e in engine_results if not e.get("mentioned") and not e.get("domain_cited") and e.get("status") != "error"]
            found = [e for e in engine_results if e.get("mentioned") or e.get("domain_cited")]

            if not_found:
                names = ", ".join(e["engine"] for e in not_found)
                suggestions.append({
                    "priority": "alta",
                    "message": f"Tu marca no aparece en: {names}",
                    "detail": "Las IAs no mencionan tu marca cuando se les pregunta directamente. Necesitas mas autoridad de contenido, backlinks y presencia en fuentes que las IAs consultan.",
                })

            if found:
                names = ", ".join(e["engine"] for e in found)
                suggestions.append({
                    "priority": "info",
                    "message": f"Tu marca aparece en: {names}",
                    "detail": "Buen indicador de presencia. Sigue creando contenido autoritativo.",
                })

        # Signal-based suggestions
        for s in signals:
            if s["status"] == "fail":
                suggestions.append({
                    "priority": "alta",
                    "message": f"{s['name']}: necesita mejora",
                    "detail": s["details"],
                })

        return suggestions

    def _error_result(self, url: str, error: str) -> dict:
        return {
            "url": url, "brand_name": "", "domain": "",
            "signals": [], "engine_results": [],
            "api_keys_configured": has_api_keys(),
            "score": 0, "suggestions": [],
        }
