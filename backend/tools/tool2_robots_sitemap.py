import asyncio
import time
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from typing import Optional
from xml.etree import ElementTree

import aiohttp
from bs4 import BeautifulSoup
from tools.http_client import create_session


AI_BOTS = [
    {"name": "GPTBot", "engine": "ChatGPT / OpenAI", "agent": "GPTBot"},
    {"name": "ChatGPT-User", "engine": "ChatGPT Browse", "agent": "ChatGPT-User"},
    {"name": "ClaudeBot", "engine": "Claude / Anthropic", "agent": "ClaudeBot"},
    {"name": "Claude-Web", "engine": "Claude Web", "agent": "Claude-Web"},
    {"name": "Google-Extended", "engine": "Google AI / Gemini", "agent": "Google-Extended"},
    {"name": "Bytespider", "engine": "TikTok / ByteDance", "agent": "Bytespider"},
    {"name": "CCBot", "engine": "Common Crawl", "agent": "CCBot"},
    {"name": "PerplexityBot", "engine": "Perplexity AI", "agent": "PerplexityBot"},
    {"name": "Amazonbot", "engine": "Amazon Alexa AI", "agent": "Amazonbot"},
    {"name": "FacebookBot", "engine": "Meta AI", "agent": "FacebookBot"},
    {"name": "Applebot-Extended", "engine": "Apple Intelligence", "agent": "Applebot-Extended"},
    {"name": "cohere-ai", "engine": "Cohere", "agent": "cohere-ai"},
]

SEARCH_BOTS = [
    {"name": "Googlebot", "engine": "Google Search"},
    {"name": "Bingbot", "engine": "Bing Search"},
    {"name": "YandexBot", "engine": "Yandex Search"},
    {"name": "Baiduspider", "engine": "Baidu Search"},
    {"name": "DuckDuckBot", "engine": "DuckDuckGo"},
]


@dataclass
class RobotsRule:
    user_agent: str
    rules: list = field(default_factory=list)


@dataclass
class BotStatus:
    name: str
    engine: str
    allowed: bool
    rule_found: bool
    details: str = ""


@dataclass
class SitemapUrl:
    loc: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[str] = None


@dataclass
class SitemapInfo:
    found: bool = False
    url: str = ""
    urls_count: int = 0
    urls: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    is_index: bool = False
    child_sitemaps: list = field(default_factory=list)


@dataclass
class RobotsAnalysis:
    found: bool = False
    url: str = ""
    raw_content: str = ""
    rules: list = field(default_factory=list)
    ai_bots: list = field(default_factory=list)
    search_bots: list = field(default_factory=list)
    sitemaps_declared: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    issues: list = field(default_factory=list)


@dataclass
class AnalysisResult:
    target_url: str
    robots: dict = field(default_factory=dict)
    sitemap: dict = field(default_factory=dict)
    generated_sitemap: str = ""
    score: int = 100
    analysis_time: float = 0.0


class SiteAnalyzer:
    def __init__(self, timeout: int = 10, max_crawl_pages: int = 50):
        self.timeout = timeout
        self.max_crawl_pages = max_crawl_pages

    async def analyze(self, url: str) -> AnalysisResult:
        start_time = time.time()
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        connector, timeout_config, headers = create_session(timeout=self.timeout)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout_config,
            headers=headers,
        ) as session:
            robots_analysis = await self._analyze_robots(session, base_url)
            sitemap_info = await self._analyze_sitemap(session, base_url, robots_analysis)

            # Generate sitemap if none found
            generated_sitemap = ""
            if not sitemap_info.found or sitemap_info.urls_count == 0:
                generated_sitemap = await self._generate_sitemap(session, base_url, url)

        analysis_time = time.time() - start_time
        score = self._calculate_score(robots_analysis, sitemap_info)

        return AnalysisResult(
            target_url=url,
            robots=self._robots_to_dict(robots_analysis),
            sitemap=self._sitemap_to_dict(sitemap_info),
            generated_sitemap=generated_sitemap,
            score=score,
            analysis_time=round(analysis_time, 2),
        )

    async def _analyze_robots(self, session: aiohttp.ClientSession, base_url: str) -> RobotsAnalysis:
        analysis = RobotsAnalysis()
        robots_url = f"{base_url}/robots.txt"
        analysis.url = robots_url

        try:
            async with session.get(robots_url, allow_redirects=True) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get("content-type", "")
                    text = await resp.text()

                    # Check if it's actually a robots.txt (not an HTML error page)
                    if "text/html" in content_type and "<html" in text.lower()[:200]:
                        analysis.found = False
                        analysis.issues.append({
                            "severity": "warning",
                            "message": "La URL robots.txt devuelve una pagina HTML en vez de texto plano",
                        })
                    else:
                        analysis.found = True
                        analysis.raw_content = text
                        analysis.rules = self._parse_robots(text)
                        analysis.sitemaps_declared = self._extract_sitemaps(text)
                        analysis.ai_bots = self._check_bots(text, AI_BOTS, is_ai=True)
                        analysis.search_bots = self._check_bots(text, SEARCH_BOTS, is_ai=False)
                        analysis.suggestions = self._generate_suggestions(analysis)
                        analysis.issues = self._find_issues(analysis)
                else:
                    analysis.found = False
                    analysis.issues.append({
                        "severity": "info",
                        "message": f"No se encontro robots.txt (HTTP {resp.status})",
                    })
                    analysis.suggestions.append({
                        "type": "create",
                        "priority": "alta",
                        "message": "Crear un archivo robots.txt para controlar el acceso de bots",
                        "detail": "Sin robots.txt, todos los bots pueden acceder a todo tu sitio. Crea uno para gestionar que rastreadores pueden ver tu contenido.",
                    })
        except Exception as e:
            analysis.issues.append({
                "severity": "critical",
                "message": f"Error al acceder a robots.txt: {str(e)[:150]}",
            })

        return analysis

    def _parse_robots(self, text: str) -> list:
        rules = []
        current_agent = None
        current_rules = []

        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.lower().startswith("user-agent:"):
                if current_agent is not None:
                    rules.append({"user_agent": current_agent, "rules": current_rules})
                current_agent = line.split(":", 1)[1].strip()
                current_rules = []
            elif ":" in line and current_agent is not None:
                directive, value = line.split(":", 1)
                current_rules.append({
                    "directive": directive.strip(),
                    "value": value.strip(),
                })

        if current_agent is not None:
            rules.append({"user_agent": current_agent, "rules": current_rules})

        return rules

    def _extract_sitemaps(self, text: str) -> list:
        sitemaps = []
        for line in text.split("\n"):
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                url = line.split(":", 1)[1].strip()
                if url:
                    sitemaps.append(url)
        return sitemaps

    def _check_bots(self, text: str, bots: list, is_ai: bool) -> list:
        results = []
        text_lower = text.lower()
        lines = text.split("\n")

        for bot_info in bots:
            bot_name = bot_info["name"]
            status = BotStatus(
                name=bot_name,
                engine=bot_info["engine"],
                allowed=True,
                rule_found=False,
            )

            # Check for specific bot rules
            in_bot_section = False
            in_wildcard_section = False
            bot_disallowed = False
            wildcard_disallowed = False

            for line in lines:
                stripped = line.strip()
                lower = stripped.lower()

                if lower.startswith("user-agent:"):
                    agent = lower.split(":", 1)[1].strip()
                    if agent == bot_name.lower():
                        in_bot_section = True
                        in_wildcard_section = False
                    elif agent == "*":
                        in_bot_section = False
                        in_wildcard_section = True
                    else:
                        in_bot_section = False
                        in_wildcard_section = False
                elif in_bot_section:
                    if lower.startswith("disallow:"):
                        path = stripped.split(":", 1)[1].strip()
                        if path == "/":
                            bot_disallowed = True
                            status.rule_found = True
                    elif lower.startswith("allow:"):
                        path = stripped.split(":", 1)[1].strip()
                        if path == "/":
                            bot_disallowed = False
                            status.rule_found = True
                elif in_wildcard_section:
                    if lower.startswith("disallow:"):
                        path = stripped.split(":", 1)[1].strip()
                        if path == "/":
                            wildcard_disallowed = True

            if status.rule_found:
                status.allowed = not bot_disallowed
                if bot_disallowed:
                    status.details = f"Bloqueado explicitamente en robots.txt"
                else:
                    status.details = f"Permitido explicitamente en robots.txt"
            elif wildcard_disallowed:
                status.allowed = False
                status.rule_found = False
                status.details = "Bloqueado por regla general (User-agent: *)"
            else:
                status.allowed = True
                status.rule_found = False
                status.details = "Permitido (sin regla especifica)"

            results.append({
                "name": status.name,
                "engine": status.engine,
                "allowed": status.allowed,
                "rule_found": status.rule_found,
                "details": status.details,
            })

        return results

    def _generate_suggestions(self, analysis: RobotsAnalysis) -> list:
        suggestions = []

        # Check if all AI bots are blocked
        ai_blocked = [b for b in analysis.ai_bots if not b["allowed"]]
        ai_allowed = [b for b in analysis.ai_bots if b["allowed"]]

        if len(ai_blocked) == len(analysis.ai_bots):
            suggestions.append({
                "type": "ai_access",
                "priority": "alta",
                "message": "Todos los bots de IA estan bloqueados",
                "detail": "Tu sitio es invisible para ChatGPT, Claude, Perplexity y otros motores de IA. Si quieres visibilidad en IA, debes permitir al menos los bots principales.",
            })
        elif len(ai_blocked) > 0:
            blocked_names = ", ".join(b["name"] for b in ai_blocked)
            suggestions.append({
                "type": "ai_access",
                "priority": "media",
                "message": f"Algunos bots de IA estan bloqueados: {blocked_names}",
                "detail": "Considera permitir estos bots si quieres maximizar tu visibilidad en motores de IA.",
            })

        if not analysis.sitemaps_declared:
            suggestions.append({
                "type": "sitemap",
                "priority": "alta",
                "message": "No hay sitemap declarado en robots.txt",
                "detail": "Agrega una linea 'Sitemap: https://tusitio.com/sitemap.xml' al final de tu robots.txt para que los bots encuentren tu mapa del sitio.",
            })

        # Check for wildcard disallow
        for rule_group in analysis.rules:
            if rule_group["user_agent"] == "*":
                for rule in rule_group["rules"]:
                    if rule["directive"].lower() == "disallow" and rule["value"] == "/":
                        suggestions.append({
                            "type": "access",
                            "priority": "critica",
                            "message": "El sitio completo esta bloqueado para todos los bots",
                            "detail": "La regla 'Disallow: /' para User-agent: * impide que cualquier bot acceda a tu sitio. Esto incluye Google, Bing y todos los motores de IA.",
                        })

        if len(ai_allowed) > 0 and len(ai_blocked) == 0:
            suggestions.append({
                "type": "positive",
                "priority": "info",
                "message": "Todos los bots de IA principales tienen acceso",
                "detail": "Tu configuracion permite que los motores de IA rastreen tu contenido. Esto es ideal para maximizar la visibilidad.",
            })

        return suggestions

    def _find_issues(self, analysis: RobotsAnalysis) -> list:
        issues = []

        # Check for crawl-delay
        for rule_group in analysis.rules:
            for rule in rule_group["rules"]:
                if rule["directive"].lower() == "crawl-delay":
                    try:
                        delay = float(rule["value"])
                        if delay > 10:
                            issues.append({
                                "severity": "warning",
                                "message": f"Crawl-delay muy alto ({delay}s) para {rule_group['user_agent']}",
                            })
                    except ValueError:
                        pass

        return issues

    async def _analyze_sitemap(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        robots: RobotsAnalysis,
    ) -> SitemapInfo:
        info = SitemapInfo()

        # Try sitemaps from robots.txt first
        sitemap_urls = list(robots.sitemaps_declared) if robots.sitemaps_declared else []

        # Try common locations
        common_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap/sitemap.xml"]
        for path in common_paths:
            candidate = base_url + path
            if candidate not in sitemap_urls:
                sitemap_urls.append(candidate)

        for sitemap_url in sitemap_urls:
            try:
                async with session.get(sitemap_url, allow_redirects=True) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if "<urlset" in text or "<sitemapindex" in text:
                            info.found = True
                            info.url = sitemap_url
                            info = self._parse_sitemap(text, info)
                            break
            except Exception:
                continue

        if not info.found:
            info.errors.append("No se encontro un sitemap XML valido en las ubicaciones comunes.")

        return info

    def _parse_sitemap(self, xml_text: str, info: SitemapInfo) -> SitemapInfo:
        try:
            root = ElementTree.fromstring(xml_text)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Check if it's a sitemap index
            if "sitemapindex" in root.tag:
                info.is_index = True
                for sitemap in root.findall(".//sm:sitemap", ns):
                    loc = sitemap.find("sm:loc", ns)
                    if loc is not None and loc.text:
                        info.child_sitemaps.append(loc.text)
                info.urls_count = len(info.child_sitemaps)
            else:
                urls = root.findall(".//sm:url", ns)
                for url_elem in urls[:200]:  # Limit to 200 for display
                    loc = url_elem.find("sm:loc", ns)
                    lastmod = url_elem.find("sm:lastmod", ns)
                    changefreq = url_elem.find("sm:changefreq", ns)
                    priority = url_elem.find("sm:priority", ns)

                    if loc is not None and loc.text:
                        info.urls.append({
                            "loc": loc.text,
                            "lastmod": lastmod.text if lastmod is not None else None,
                            "changefreq": changefreq.text if changefreq is not None else None,
                            "priority": priority.text if priority is not None else None,
                        })
                info.urls_count = len(urls)

            # Check for issues
            if info.urls_count == 0:
                info.errors.append("El sitemap existe pero no contiene URLs.")

        except ElementTree.ParseError as e:
            info.errors.append(f"Error al parsear el XML del sitemap: {str(e)[:100]}")

        return info

    async def _generate_sitemap(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        start_url: str,
    ) -> str:
        """Crawl the site and generate a basic sitemap XML."""
        visited = set()
        to_visit = [start_url]
        found_urls = []

        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc

        while to_visit and len(visited) < self.max_crawl_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue

            parsed = urlparse(url)
            if parsed.netloc != base_domain:
                continue

            visited.add(url)

            try:
                async with session.get(url, allow_redirects=True) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get("content-type", "")
                        if "text/html" not in content_type:
                            continue

                        found_urls.append(url)
                        html = await resp.text()
                        soup = BeautifulSoup(html, "lxml")

                        for a in soup.find_all("a", href=True):
                            href = a["href"]
                            full_url = urljoin(url, href)
                            parsed_link = urlparse(full_url)

                            if parsed_link.netloc != base_domain:
                                continue
                            if parsed_link.scheme not in ("http", "https"):
                                continue

                            clean = f"{parsed_link.scheme}://{parsed_link.netloc}{parsed_link.path}"
                            if clean not in visited and clean not in to_visit:
                                to_visit.append(clean)
            except Exception:
                continue

        # Generate XML
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for u in sorted(found_urls):
            lines.append("  <url>")
            lines.append(f"    <loc>{u}</loc>")
            lines.append("  </url>")
        lines.append("</urlset>")

        return "\n".join(lines)

    def _calculate_score(self, robots: RobotsAnalysis, sitemap: SitemapInfo) -> int:
        score = 100

        if not robots.found:
            score -= 15

        if not sitemap.found:
            score -= 20

        # AI bots blocked
        ai_blocked = sum(1 for b in robots.ai_bots if not b["allowed"])
        score -= ai_blocked * 5

        # No sitemap in robots.txt
        if robots.found and not robots.sitemaps_declared:
            score -= 10

        # Critical suggestions
        for s in robots.suggestions:
            if s["priority"] == "critica":
                score -= 20
            elif s["priority"] == "alta":
                score -= 10

        if sitemap.errors:
            score -= 5 * len(sitemap.errors)

        return max(0, min(100, score))

    def _robots_to_dict(self, analysis: RobotsAnalysis) -> dict:
        return {
            "found": analysis.found,
            "url": analysis.url,
            "raw_content": analysis.raw_content,
            "rules": analysis.rules,
            "ai_bots": analysis.ai_bots,
            "search_bots": analysis.search_bots,
            "sitemaps_declared": analysis.sitemaps_declared,
            "suggestions": analysis.suggestions,
            "issues": analysis.issues,
        }

    def _sitemap_to_dict(self, info: SitemapInfo) -> dict:
        return {
            "found": info.found,
            "url": info.url,
            "urls_count": info.urls_count,
            "urls": info.urls[:200],
            "errors": info.errors,
            "is_index": info.is_index,
            "child_sitemaps": info.child_sitemaps,
        }


def generate_recommended_robots(base_url: str, allow_ai: bool = True) -> str:
    """Generate a recommended robots.txt content."""
    lines = ["# Robots.txt generado por Cleexs", ""]

    lines.append("User-agent: *")
    lines.append("Allow: /")
    lines.append("Disallow: /admin/")
    lines.append("Disallow: /private/")
    lines.append("Disallow: /api/")
    lines.append("")

    if allow_ai:
        lines.append("# Bots de IA - Permitidos para maximizar visibilidad")
        for bot in AI_BOTS:
            lines.append(f"User-agent: {bot['name']}")
            lines.append("Allow: /")
            lines.append("")
    else:
        lines.append("# Bots de IA - Bloqueados")
        for bot in AI_BOTS:
            lines.append(f"User-agent: {bot['name']}")
            lines.append("Disallow: /")
            lines.append("")

    lines.append(f"Sitemap: {base_url}/sitemap.xml")

    return "\n".join(lines)
