"""
Tool 6: AI Citation Tracker
Based on querycat.app

Sends real queries to Perplexity (which returns source citations),
ChatGPT, and Gemini, then checks if the target domain appears
in the AI responses and cited sources.
Falls back to heuristic analysis when API keys are not configured.
"""

import asyncio
import re
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from tools.http_client import create_session

from ai_engines import (
    query_perplexity, query_openai, query_gemini,
    check_brand_mentioned, has_api_keys,
)


class QueryCitationTracker:

    def __init__(self, timeout: int = 15, max_pages: int = 15):
        self.timeout = timeout
        self.max_pages = max_pages

    async def analyze(self, url: str) -> dict:
        if not url.startswith("http"):
            url = "https://" + url

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        brand = domain.split(".")[0].capitalize()
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Crawl site to understand topics
        topics, pages_analyzed = await self._crawl_topics(url, domain, base_url)

        # Generate queries to test
        queries = self._generate_queries(brand, domain, topics)

        # Query real AI engines
        keys = has_api_keys()
        citation_results = await self._check_citations(queries, brand, domain, keys)

        # Aggregate per-engine stats
        engine_scores = self._aggregate_engine_scores(citation_results, keys)

        # Source diversity from Perplexity citations
        cited_sources = self._extract_cited_sources(citation_results, domain)

        # Suggestions
        suggestions = self._generate_suggestions(engine_scores, citation_results, keys)

        # Score
        score = self._calculate_score(engine_scores, keys)

        return {
            "url": url,
            "brand": brand,
            "domain": domain,
            "pages_analyzed": pages_analyzed,
            "engine_scores": engine_scores,
            "citation_results": citation_results[:20],
            "cited_sources": cited_sources,
            "suggestions": suggestions,
            "score": score,
            "topics": topics[:10],
            "api_keys_configured": keys,
        }

    async def _crawl_topics(self, url: str, domain: str, base_url: str) -> tuple:
        """Crawl site to extract topics/keywords for query generation."""
        connector, timeout_config, headers = create_session(timeout=self.timeout, max_connections=5)
        topics = []
        visited = set()
        to_visit = [url]

        async with aiohttp.ClientSession(
            connector=connector, timeout=timeout_config,
            headers=headers,
        ) as session:
            while to_visit and len(visited) < self.max_pages:
                current = to_visit.pop(0)
                if current in visited:
                    continue
                cp = urlparse(current)
                if cp.netloc.replace("www.", "") != domain:
                    continue
                visited.add(current)
                try:
                    async with session.get(current, allow_redirects=True) as resp:
                        if resp.status != 200:
                            continue
                        ct = resp.headers.get("content-type", "")
                        if "text/html" not in ct:
                            continue
                        html = await resp.text()
                except Exception:
                    continue

                soup = BeautifulSoup(html, "lxml")
                for tag in soup.find_all(["h1", "h2"])[:5]:
                    t = tag.get_text(strip=True)
                    if t and 3 < len(t) < 80:
                        topics.append(t)
                meta = soup.find("meta", attrs={"name": "description"})
                if meta and meta.get("content"):
                    topics.append(meta["content"][:80])

                new_links = set()
                for a in soup.find_all("a", href=True):
                    full = urljoin(current, a["href"])
                    fp = urlparse(full)
                    if fp.netloc.replace("www.", "") == domain:
                        clean = f"{fp.scheme}://{fp.netloc}{fp.path}"
                        if clean not in visited:
                            new_links.add(clean)
                to_visit.extend(sorted(new_links))

        # Deduplicate topics
        seen = set()
        unique = []
        for t in topics:
            tl = t.lower().strip()
            if tl not in seen:
                seen.add(tl)
                unique.append(t)
        return unique, len(visited)

    def _generate_queries(self, brand: str, domain: str, topics: list) -> list:
        queries = [
            {"query": f"Que es {brand}?", "type": "brand"},
            {"query": f"Opiniones sobre {brand}", "type": "brand"},
            {"query": f"Alternativas a {brand}", "type": "competitive"},
        ]
        for topic in topics[:4]:
            clean = topic[:60]
            queries.append({"query": f"Mejores {clean.lower()}", "type": "category"})
        return queries

    async def _check_citations(self, queries: list, brand: str, domain: str, keys: dict) -> list:
        """Send queries to AI engines and check for citations."""
        results = []

        for q in queries[:7]:
            query_text = q["query"]
            query_results = {"query": query_text, "type": q["type"], "engines": []}

            tasks = {}
            if keys["perplexity"]:
                tasks["Perplexity"] = query_perplexity(query_text)
            if keys["openai"]:
                tasks["ChatGPT"] = query_openai(query_text)
            if keys["gemini"]:
                tasks["Gemini"] = query_gemini(query_text)

            if tasks:
                responses = await asyncio.gather(*tasks.values(), return_exceptions=True)
                for engine_name, resp in zip(tasks.keys(), responses):
                    if isinstance(resp, Exception) or (isinstance(resp, dict) and resp.get("error")):
                        error = str(resp) if isinstance(resp, Exception) else resp.get("error", "")
                        query_results["engines"].append({
                            "engine": engine_name,
                            "mentioned": False,
                            "cited": False,
                            "error": error[:150],
                        })
                    else:
                        text = resp.get("text", "")
                        mention = check_brand_mentioned(text, brand, domain)
                        citations = resp.get("citations", [])
                        domain_cited = any(domain.lower() in c.lower() for c in citations)

                        query_results["engines"].append({
                            "engine": engine_name,
                            "mentioned": mention["mentioned"],
                            "cited": domain_cited,
                            "snippet": mention["snippet"],
                            "response_preview": text[:200] + ("..." if len(text) > 200 else ""),
                            "citations": citations[:5] if citations else [],
                        })

            results.append(query_results)

        return results

    def _aggregate_engine_scores(self, citation_results: list, keys: dict) -> list:
        """Calculate per-engine citation scores."""
        engine_data = {}

        for cr in citation_results:
            for eng in cr.get("engines", []):
                name = eng["engine"]
                if name not in engine_data:
                    engine_data[name] = {"total": 0, "mentioned": 0, "cited": 0}
                engine_data[name]["total"] += 1
                if eng.get("mentioned"):
                    engine_data[name]["mentioned"] += 1
                if eng.get("cited"):
                    engine_data[name]["cited"] += 1

        scores = []
        for name, data in engine_data.items():
            total = data["total"]
            if total == 0:
                continue
            mention_rate = round((data["mentioned"] / total) * 100)
            cite_rate = round((data["cited"] / total) * 100)
            # Score: mentions worth 60%, direct citations worth 40%
            score = round(mention_rate * 0.6 + cite_rate * 0.4)
            scores.append({
                "engine": name,
                "score": score,
                "queries_tested": total,
                "mentioned_count": data["mentioned"],
                "cited_count": data["cited"],
                "mention_rate": mention_rate,
                "cite_rate": cite_rate,
            })

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores

    def _extract_cited_sources(self, citation_results: list, domain: str) -> dict:
        """Extract all unique sources that Perplexity cited alongside us."""
        our_citations = 0
        competitor_sources = {}

        for cr in citation_results:
            for eng in cr.get("engines", []):
                citations = eng.get("citations", [])
                for cite_url in citations:
                    cite_domain = urlparse(cite_url).netloc.replace("www.", "")
                    if domain.lower() in cite_domain.lower():
                        our_citations += 1
                    else:
                        if cite_domain not in competitor_sources:
                            competitor_sources[cite_domain] = 0
                        competitor_sources[cite_domain] += 1

        top_competitors = sorted(competitor_sources.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "our_citation_count": our_citations,
            "total_queries": len(citation_results),
            "competitor_sources": [{"domain": d, "count": c} for d, c in top_competitors],
        }

    def _generate_suggestions(self, engine_scores: list, citation_results: list, keys: dict) -> list:
        suggestions = []

        if not any(keys.values()):
            suggestions.append({
                "priority": "info",
                "message": "Configura API keys para obtener citaciones reales",
                "detail": "Sin API keys, no se pueden verificar citaciones reales. Agrega PERPLEXITY_API_KEY, OPENAI_API_KEY o GEMINI_API_KEY en .env.",
            })
            return suggestions

        for es in engine_scores:
            if es["score"] < 30:
                suggestions.append({
                    "priority": "alta",
                    "message": f"Baja presencia en {es['engine']} ({es['mention_rate']}% mencion, {es['cite_rate']}% citacion)",
                    "detail": f"De {es['queries_tested']} consultas, solo {es['mentioned_count']} mencionaron tu marca.",
                })
            elif es["score"] < 60:
                suggestions.append({
                    "priority": "media",
                    "message": f"Presencia moderada en {es['engine']}",
                    "detail": f"Mencionado en {es['mention_rate']}% de consultas. Crea contenido mas autoritativo.",
                })

        if not suggestions:
            suggestions.append({
                "priority": "info",
                "message": "Buena presencia de citaciones",
                "detail": "Tu marca aparece frecuentemente en las respuestas de IA.",
            })

        return suggestions

    def _calculate_score(self, engine_scores: list, keys: dict) -> int:
        if not any(keys.values()) or not engine_scores:
            return 0
        avg = sum(es["score"] for es in engine_scores) / len(engine_scores)
        return max(0, min(100, round(avg)))
