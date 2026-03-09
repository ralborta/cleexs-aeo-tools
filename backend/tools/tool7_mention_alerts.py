"""
Tool 7: Brand Mention Monitor
Based on alertmouse.com

Queries AI engines and Google SERP to find real current mentions
of the brand. Checks ChatGPT, Gemini, Perplexity and Google
for brand presence, then provides monitoring configuration.
Falls back to on-page visibility analysis when API keys are not configured.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus
from tools.http_client import create_session

from ai_engines import (
    query_openai, query_gemini, query_perplexity,
    search_serp, check_brand_mentioned, has_api_keys,
)


class MentionAlertAnalyzer:

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    async def analyze(self, url: str) -> dict:
        if not url.startswith("http"):
            url = "https://" + url

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        brand = domain.split(".")[0].capitalize()

        connector, timeout_config, headers = create_session(timeout=self.timeout, max_connections=5)

        # Fetch site for context
        async with aiohttp.ClientSession(
            connector=connector, timeout=timeout_config,
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
        brand_keywords = self._extract_brand_keywords(soup, brand, domain)

        # Real AI engine checks
        keys = has_api_keys()
        ai_mentions = await self._check_ai_mentions(brand, domain, keys)

        # Real SERP mentions
        serp_mentions = await self._check_serp_mentions(brand, domain, keys)

        # Visibility signals (always available)
        visibility = self._check_visibility_signals(soup, brand)

        # Monitoring config
        monitoring_queries = self._generate_monitoring_queries(brand, domain, brand_keywords)
        channels = self._get_monitoring_channels(brand, domain)
        alert_rules = self._generate_alert_rules(brand, brand_keywords)

        # Score based on real mentions + signals
        score = self._calculate_score(ai_mentions, serp_mentions, visibility, keys)

        # Suggestions
        suggestions = self._generate_suggestions(ai_mentions, serp_mentions, visibility, keys)

        return {
            "url": url,
            "brand": brand,
            "domain": domain,
            "brand_keywords": brand_keywords,
            "ai_mentions": ai_mentions,
            "serp_mentions": serp_mentions,
            "monitoring_queries": monitoring_queries,
            "channels": channels,
            "alert_rules": alert_rules,
            "visibility_signals": visibility,
            "api_keys_configured": keys,
            "score": score,
            "suggestions": suggestions,
        }

    async def _check_ai_mentions(self, brand: str, domain: str, keys: dict) -> list:
        """Query AI engines for real brand mentions."""
        mentions = []
        prompts = [
            {"text": f"Que es {brand}? Es recomendable?", "type": "direct"},
            {"text": f"Recomienda empresas similares a {brand}", "type": "competitive"},
        ]

        for prompt_info in prompts:
            prompt = prompt_info["text"]
            tasks = {}
            if keys["openai"]:
                tasks["ChatGPT"] = query_openai(prompt)
            if keys["gemini"]:
                tasks["Gemini"] = query_gemini(prompt)
            if keys["perplexity"]:
                tasks["Perplexity"] = query_perplexity(prompt)

            if not tasks:
                continue

            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for engine_name, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    mentions.append({
                        "engine": engine_name,
                        "query": prompt,
                        "query_type": prompt_info["type"],
                        "mentioned": False,
                        "error": str(result)[:150],
                    })
                elif result.get("error"):
                    mentions.append({
                        "engine": engine_name,
                        "query": prompt,
                        "query_type": prompt_info["type"],
                        "mentioned": False,
                        "error": result["error"][:150],
                    })
                else:
                    text = result.get("text", "")
                    mention = check_brand_mentioned(text, brand, domain)
                    citations = result.get("citations", [])
                    domain_cited = any(domain.lower() in c.lower() for c in citations)

                    mentions.append({
                        "engine": engine_name,
                        "query": prompt,
                        "query_type": prompt_info["type"],
                        "mentioned": mention["mentioned"],
                        "brand_found": mention["brand_found"],
                        "domain_found": mention["domain_found"],
                        "domain_cited": domain_cited,
                        "snippet": mention["snippet"],
                        "response_preview": text[:250] + ("..." if len(text) > 250 else ""),
                    })

        return mentions

    async def _check_serp_mentions(self, brand: str, domain: str, keys: dict) -> list:
        """Check Google SERP for brand mentions."""
        if not keys.get("serp"):
            return []

        serp_queries = [
            f'"{brand}"',
            f'"{domain}"',
            f'"{brand}" review OR opinion',
        ]

        mentions = []
        for q in serp_queries[:3]:
            result = await search_serp(q)
            if result.get("error"):
                mentions.append({"query": q, "error": result["error"][:150], "results": []})
                continue

            organic = result.get("organic_results", [])
            found_results = []
            for r in organic[:5]:
                found_results.append({
                    "title": r.get("title", ""),
                    "link": r.get("link", ""),
                    "snippet": r.get("snippet", "")[:150],
                })

            mentions.append({
                "query": q,
                "total_results": len(organic),
                "results": found_results,
            })

        return mentions

    def _extract_brand_keywords(self, soup: BeautifulSoup, brand: str, domain: str) -> list:
        keywords = [brand, domain]

        meta_kw = soup.find("meta", attrs={"name": "keywords"})
        if meta_kw and meta_kw.get("content"):
            for kw in meta_kw["content"].split(",")[:5]:
                kw = kw.strip()
                if kw and kw not in keywords:
                    keywords.append(kw)

        title = soup.find("title")
        if title:
            title_text = title.get_text(strip=True)
            words = [w for w in title_text.split() if len(w) > 3]
            for w in words[:3]:
                if w.lower() not in [k.lower() for k in keywords]:
                    keywords.append(w)

        return keywords[:8]

    def _generate_monitoring_queries(self, brand: str, domain: str, keywords: list) -> list:
        queries = [
            {
                "query": f'"{brand}"',
                "type": "exact_match",
                "description": "Menciones exactas de tu marca",
            },
            {
                "query": f'"{domain}"',
                "type": "domain",
                "description": "Enlaces y menciones de tu dominio",
            },
            {
                "query": f'"{brand}" review OR opinion OR experience',
                "type": "sentiment",
                "description": "Opiniones y resenas sobre tu marca",
            },
            {
                "query": f'"{brand}" vs OR alternative OR competitor',
                "type": "competitive",
                "description": "Comparaciones con competidores",
            },
        ]

        for kw in keywords[2:4]:
            queries.append({
                "query": f'"{kw}" {brand}',
                "type": "topical",
                "description": f"Menciones en contexto de '{kw}'",
            })

        return queries

    def _get_monitoring_channels(self, brand: str, domain: str) -> list:
        encoded_brand = quote_plus(brand)
        return [
            {
                "name": "Google Alerts",
                "type": "web",
                "setup_url": f"https://www.google.com/alerts#1:1:d:f:t:0:{encoded_brand}",
                "description": "Alertas gratuitas de Google para menciones web",
            },
            {
                "name": "Google Search (reciente)",
                "type": "search",
                "setup_url": f"https://www.google.com/search?q=%22{encoded_brand}%22&tbs=qdr:w",
                "description": "Busca menciones recientes en Google (ultima semana)",
            },
            {
                "name": "Reddit",
                "type": "social",
                "setup_url": f"https://www.reddit.com/search/?q={encoded_brand}&sort=new",
                "description": "Menciones recientes en Reddit",
            },
            {
                "name": "Twitter/X",
                "type": "social",
                "setup_url": f"https://twitter.com/search?q={encoded_brand}&f=live",
                "description": "Menciones en tiempo real en Twitter/X",
            },
        ]

    def _generate_alert_rules(self, brand: str, keywords: list) -> list:
        return [
            {
                "name": "Mencion de marca",
                "trigger": f'Cualquier mencion de "{brand}"',
                "priority": "alta",
                "frequency": "inmediata",
            },
            {
                "name": "Mencion negativa",
                "trigger": f'"{brand}" + palabras negativas (problema, error, queja)',
                "priority": "critica",
                "frequency": "inmediata",
            },
            {
                "name": "Comparacion competitiva",
                "trigger": f'"{brand}" + vs, alternativa, mejor que',
                "priority": "media",
                "frequency": "diaria",
            },
            {
                "name": "Mencion en IA",
                "trigger": f"Aparicion de {brand} en respuestas de ChatGPT/Perplexity",
                "priority": "alta",
                "frequency": "semanal",
            },
        ]

    def _check_visibility_signals(self, soup: BeautifulSoup, brand: str) -> list:
        signals = []

        social_domains = ["twitter.com", "x.com", "linkedin.com", "facebook.com", "instagram.com", "youtube.com"]
        social_found = []
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            for sd in social_domains:
                if sd in href:
                    social_found.append(sd.replace(".com", ""))
                    break

        signals.append({
            "name": "Presencia en redes sociales",
            "status": "pass" if len(set(social_found)) >= 3 else "warning" if len(set(social_found)) >= 1 else "fail",
            "detail": f"Encontrados: {', '.join(set(social_found))}" if social_found else "Sin links a redes sociales",
        })

        email_pattern = soup.find(string=lambda t: t and "@" in t and "." in t) if soup.find("body") else None
        signals.append({
            "name": "Informacion de contacto",
            "status": "pass" if email_pattern else "warning",
            "detail": "Email encontrado en la pagina" if email_pattern else "Sin email visible",
        })

        press_links = [a for a in soup.find_all("a", href=True)
                       if any(w in a.get_text(strip=True).lower() for w in ["press", "prensa", "media", "noticias"])]
        signals.append({
            "name": "Seccion de prensa/media",
            "status": "pass" if press_links else "fail",
            "detail": "Pagina de prensa encontrada" if press_links else "Sin seccion de prensa",
        })

        return signals

    def _calculate_score(self, ai_mentions: list, serp_mentions: list, visibility: list, keys: dict) -> int:
        any_key = any(keys.values())

        if any_key and ai_mentions:
            valid = [m for m in ai_mentions if not m.get("error")]
            mentioned = sum(1 for m in valid if m.get("mentioned") or m.get("domain_cited"))
            total = len(valid)
            ai_score = round((mentioned / total) * 100) if total > 0 else 0

            signal_passes = sum(1 for s in visibility if s["status"] == "pass")
            signal_total = len(visibility)
            signal_score = round((signal_passes / signal_total) * 100) if signal_total > 0 else 0

            return max(0, min(100, round(ai_score * 0.6 + signal_score * 0.4)))
        else:
            if not visibility:
                return 50
            total = len(visibility)
            passed = sum(1 for s in visibility if s["status"] == "pass")
            warned = sum(1 for s in visibility if s["status"] == "warning")
            return round(((passed + warned * 0.5) / total) * 100)

    def _generate_suggestions(self, ai_mentions: list, serp_mentions: list, visibility: list, keys: dict) -> list:
        suggestions = []

        if not any(keys.values()):
            suggestions.append({
                "priority": "info",
                "message": "Configura API keys para verificar menciones reales",
                "detail": "Sin API keys de OpenAI, Gemini o Perplexity, solo se analizan senales on-page.",
            })

        if ai_mentions:
            valid = [m for m in ai_mentions if not m.get("error")]
            not_found = [m for m in valid if not m.get("mentioned") and not m.get("domain_cited")]
            found = [m for m in valid if m.get("mentioned") or m.get("domain_cited")]

            if not_found:
                engines = list(set(m["engine"] for m in not_found))
                suggestions.append({
                    "priority": "alta",
                    "message": f"Tu marca no aparece en: {', '.join(engines)}",
                    "detail": "Las IAs no mencionan tu marca. Necesitas mas autoridad, backlinks y presencia en fuentes consultadas por IAs.",
                })

            if found:
                engines = list(set(m["engine"] for m in found))
                suggestions.append({
                    "priority": "info",
                    "message": f"Tu marca aparece en: {', '.join(engines)}",
                    "detail": "Buen indicador de presencia. Sigue creando contenido autoritativo.",
                })

        for s in visibility:
            if s["status"] == "fail":
                suggestions.append({
                    "priority": "alta",
                    "message": f"{s['name']}: necesita mejora",
                    "detail": s["detail"],
                })

        return suggestions

    def _error_result(self, url: str, error: str) -> dict:
        return {
            "url": url, "brand": "", "domain": "",
            "brand_keywords": [], "ai_mentions": [],
            "serp_mentions": [], "monitoring_queries": [],
            "channels": [], "alert_rules": [],
            "visibility_signals": [], "api_keys_configured": has_api_keys(),
            "score": 0, "suggestions": [],
        }
