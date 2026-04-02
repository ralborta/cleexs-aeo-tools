"""
Tool 9: AI Overview Traffic Impact Checker
Based on seoaireview.com

Uses SerpAPI to detect real AI Overviews in Google search results
for the site's target keywords. Checks organic ranking and whether
the domain appears cited in AI Overviews.
Falls back to heuristic risk estimation when SERP_API_KEY is not configured.
"""

import re
from urllib.parse import urlparse, urljoin

import aiohttp
from bs4 import BeautifulSoup
from tools.http_client import create_session

from ai_engines import search_serp, has_api_keys
from config import SERP_API_KEY, ENABLE_SERP


class AIOverviewChecker:

    def __init__(self, timeout: int = 15, max_pages: int = 20):
        self.timeout = timeout
        self.max_pages = max_pages

    async def check(self, url: str) -> dict:
        if not url.startswith("http"):
            url = "https://" + url

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        brand = domain.split(".")[0].capitalize()
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Crawl site to extract keyword targets
        keywords, pages_analyzed = await self._crawl_keywords(url, domain, base_url)

        # Build search queries from keywords
        queries = self._build_queries(keywords, brand, domain)

        # Query real SERP data
        keys = has_api_keys()
        serp_results = await self._check_serp(queries, domain, keys)

        # Analyze results
        impact = self._calculate_impact(serp_results, keys)
        suggestions = self._generate_suggestions(impact, serp_results, keys)
        score = self._calculate_score(impact, keys)

        return {
            "url": url,
            "domain": domain,
            "pages_analyzed": pages_analyzed,
            "total_keywords": len(keywords),
            "queries_tested": len(serp_results),
            "serp_results": serp_results[:20],
            "impact": impact,
            "suggestions": suggestions,
            "score": score,
            "api_keys_configured": keys,
        }

    async def _crawl_keywords(self, url: str, domain: str, base_url: str) -> tuple:
        """Crawl site to extract keyword targets from content."""
        connector, timeout_config, headers = create_session(timeout=self.timeout, max_connections=5)
        keywords = []
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

                title = soup.find("title")
                if title:
                    t = title.get_text(strip=True)
                    if t and len(t) < 100:
                        keywords.append(t)

                meta = soup.find("meta", attrs={"name": "description"})
                if meta and meta.get("content"):
                    keywords.append(meta["content"][:80])

                for tag in soup.find_all(["h1", "h2"])[:4]:
                    t = tag.get_text(strip=True)
                    if t and 3 < len(t) < 80:
                        keywords.append(t)

                # Follow links
                new_links = set()
                for a in soup.find_all("a", href=True):
                    full = urljoin(current, a["href"])
                    fp = urlparse(full)
                    if fp.netloc.replace("www.", "") == domain:
                        clean = f"{fp.scheme}://{fp.netloc}{fp.path}"
                        if clean not in visited:
                            new_links.add(clean)
                to_visit.extend(sorted(new_links))

        # Deduplicate
        seen = set()
        unique = []
        for k in keywords:
            kl = k.lower().strip()
            if kl not in seen:
                seen.add(kl)
                unique.append(k)
        return unique, len(visited)

    def _build_queries(self, keywords: list, brand: str, domain: str) -> list:
        """Build search queries from extracted keywords."""
        queries = [
            {"query": f"Que es {brand}", "type": "brand"},
            {"query": f"Mejores alternativas a {brand}", "type": "competitive"},
        ]
        for kw in keywords[:5]:
            clean = kw[:60]
            queries.append({"query": clean, "type": "topic"})
        return queries

    async def _check_serp(self, queries: list, domain: str, keys: dict) -> list:
        """Check real SERP results for AI Overview presence."""
        results = []

        if keys.get("serp"):
            for q in queries[:7]:
                serp_data = await search_serp(q["query"])
                if serp_data.get("error"):
                    results.append({
                        "query": q["query"],
                        "type": q["type"],
                        "has_ai_overview": False,
                        "ai_overview_preview": "",
                        "domain_in_ai_overview": False,
                        "organic_position": None,
                        "domain_in_organic": False,
                        "top_results": [],
                        "error": serp_data["error"][:150],
                    })
                    continue

                ai_overview = serp_data.get("ai_overview")
                has_aio = ai_overview is not None

                # Check if domain appears in AI Overview
                domain_in_aio = False
                aio_text = ""
                if has_aio:
                    if isinstance(ai_overview, dict):
                        aio_text = str(ai_overview.get("text", "") or ai_overview.get("snippet", ""))
                        sources = ai_overview.get("sources", [])
                        for src in sources:
                            if domain.lower() in str(src).lower():
                                domain_in_aio = True
                        if domain.lower() in aio_text.lower():
                            domain_in_aio = True
                    elif isinstance(ai_overview, str):
                        aio_text = ai_overview
                        if domain.lower() in aio_text.lower():
                            domain_in_aio = True

                # Check organic results
                organic = serp_data.get("organic_results", [])
                organic_pos = None
                domain_in_organic = False
                top_results = []

                for i, item in enumerate(organic[:10]):
                    link = item.get("link", "")
                    item_domain = urlparse(link).netloc.replace("www.", "") if link else ""
                    top_results.append({
                        "position": i + 1,
                        "title": item.get("title", ""),
                        "domain": item_domain,
                        "link": link,
                    })
                    if domain.lower() in item_domain.lower():
                        if organic_pos is None:
                            organic_pos = i + 1
                        domain_in_organic = True

                results.append({
                    "query": q["query"],
                    "type": q["type"],
                    "has_ai_overview": has_aio,
                    "ai_overview_preview": aio_text[:300] if aio_text else "",
                    "domain_in_ai_overview": domain_in_aio,
                    "organic_position": organic_pos,
                    "domain_in_organic": domain_in_organic,
                    "top_results": top_results[:5],
                })
        else:
            # No SERP key — mark as unavailable
            for q in queries[:7]:
                results.append({
                    "query": q["query"],
                    "type": q["type"],
                    "has_ai_overview": None,
                    "ai_overview_preview": "",
                    "domain_in_ai_overview": None,
                    "organic_position": None,
                    "domain_in_organic": None,
                    "top_results": [],
                    "no_api_key": True,
                })

        return results

    def _calculate_impact(self, serp_results: list, keys: dict) -> dict:
        if not keys.get("serp"):
            return {
                "total_queries": len(serp_results),
                "queries_with_ai_overview": 0,
                "ai_overview_rate": 0,
                "domain_in_ai_overview": 0,
                "domain_cited_in_aio_rate": 0,
                "domain_in_organic": 0,
                "organic_presence_rate": 0,
                "avg_organic_position": None,
                "no_api_key": True,
            }

        valid = [r for r in serp_results if not r.get("error")]
        total = len(valid)
        if total == 0:
            return {
                "total_queries": 0, "queries_with_ai_overview": 0,
                "ai_overview_rate": 0, "domain_in_ai_overview": 0,
                "domain_cited_in_aio_rate": 0, "domain_in_organic": 0,
                "organic_presence_rate": 0, "avg_organic_position": None,
            }

        with_aio = sum(1 for r in valid if r.get("has_ai_overview"))
        domain_aio = sum(1 for r in valid if r.get("domain_in_ai_overview"))
        domain_org = sum(1 for r in valid if r.get("domain_in_organic"))
        positions = [r["organic_position"] for r in valid if r.get("organic_position")]
        avg_pos = round(sum(positions) / len(positions), 1) if positions else None

        return {
            "total_queries": total,
            "queries_with_ai_overview": with_aio,
            "ai_overview_rate": round((with_aio / total) * 100) if total > 0 else 0,
            "domain_in_ai_overview": domain_aio,
            "domain_cited_in_aio_rate": round((domain_aio / with_aio) * 100) if with_aio > 0 else 0,
            "domain_in_organic": domain_org,
            "organic_presence_rate": round((domain_org / total) * 100) if total > 0 else 0,
            "avg_organic_position": avg_pos,
        }

    def _generate_suggestions(self, impact: dict, serp_results: list, keys: dict) -> list:
        suggestions = []

        if not keys.get("serp"):
            if SERP_API_KEY and not ENABLE_SERP:
                suggestions.append({
                    "priority": "info",
                    "message": "SerpAPI está desactivado (ENABLE_SERP=false)",
                    "detail": "Tienes SERP_API_KEY en Railway, pero el código no usa SerpAPI mientras ENABLE_SERP sea false. En Variables pon ENABLE_SERP=true o borra ENABLE_SERP y vuelve a desplegar.",
                })
            else:
                suggestions.append({
                    "priority": "info",
                    "message": "Configura SERP_API_KEY para datos reales de Google",
                    "detail": "Sin API key de SerpAPI, no se pueden verificar AI Overviews reales. Agrega SERP_API_KEY en el servicio backend de Railway (no solo en MySQL) y redeploy.",
                })
            return suggestions

        aio_rate = impact.get("ai_overview_rate", 0)
        if aio_rate > 50:
            suggestions.append({
                "priority": "alta",
                "message": f"{aio_rate}% de tus consultas muestran AI Overview",
                "detail": "Google muestra resumen de IA en mas de la mitad de tus consultas. Tu trafico organico puede verse reducido.",
            })
        elif aio_rate > 0:
            suggestions.append({
                "priority": "media",
                "message": f"{aio_rate}% de tus consultas tienen AI Overview",
                "detail": "Algunas de tus consultas objetivo muestran AI Overview en Google.",
            })

        if impact.get("domain_in_ai_overview", 0) > 0:
            suggestions.append({
                "priority": "info",
                "message": f"Tu dominio aparece citado en {impact['domain_in_ai_overview']} AI Overviews",
                "detail": "Buen indicador. Google cita tu sitio como fuente en sus respuestas de IA.",
            })
        elif impact.get("queries_with_ai_overview", 0) > 0:
            suggestions.append({
                "priority": "alta",
                "message": "Tu dominio no aparece en ningun AI Overview",
                "detail": "Google no cita tu sitio en sus AI Overviews. Optimiza tu contenido con datos estructurados y respuestas directas.",
            })

        avg_pos = impact.get("avg_organic_position")
        if avg_pos and avg_pos > 5:
            suggestions.append({
                "priority": "media",
                "message": f"Posicion organica promedio: {avg_pos}",
                "detail": "Mejorar tu ranking organico aumenta probabilidad de ser citado en AI Overview.",
            })

        if not suggestions:
            suggestions.append({
                "priority": "info",
                "message": "Buena posicion frente a AI Overview",
                "detail": "Tu sitio tiene presencia en resultados organicos de Google.",
            })

        return suggestions

    def _calculate_score(self, impact: dict, keys: dict) -> int:
        if not keys.get("serp"):
            return 0

        score = 50  # Base

        # Penalize high AI overview rate (potential traffic loss)
        aio_rate = impact.get("ai_overview_rate", 0)
        score -= aio_rate * 0.3

        # Bonus for being cited in AI overview
        aio_cited = impact.get("domain_cited_in_aio_rate", 0)
        score += aio_cited * 0.3

        # Bonus for organic presence
        org_rate = impact.get("organic_presence_rate", 0)
        score += org_rate * 0.2

        return max(0, min(100, round(score)))
