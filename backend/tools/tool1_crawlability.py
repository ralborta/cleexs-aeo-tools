import asyncio
import time
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup
from tools.http_client import create_session


@dataclass
class CrawlIssue:
    severity: str  # "critical", "warning", "info"
    category: str
    url: str
    message: str
    details: Optional[str] = None


@dataclass
class PageResult:
    url: str
    status_code: int
    response_time: float
    title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_robots: Optional[str] = None
    canonical: Optional[str] = None
    has_h1: bool = False
    internal_links: list = field(default_factory=list)
    external_links: list = field(default_factory=list)
    images_without_alt: int = 0
    total_images: int = 0


@dataclass
class CrawlResult:
    target_url: str
    pages_crawled: int = 0
    total_links_found: int = 0
    score: int = 100
    issues: list = field(default_factory=list)
    pages: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    crawl_time: float = 0.0


def _normalize_url(url: str) -> str:
    """Normalize URL to avoid duplicates like example.com vs example.com/"""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


class SiteCrawler:
    def __init__(self, max_pages: int = 30, max_depth: int = 3, timeout: int = 15):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout
        self.visited = set()
        self.issues: list[CrawlIssue] = []
        self.pages: list[PageResult] = []
        self.broken_links: list[dict] = []
        self.redirects: list[dict] = []
        self.slow_pages: list[dict] = []

    async def crawl(self, url: str) -> CrawlResult:
        start_time = time.time()
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)
        self.base_domain = parsed.netloc
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        connector, timeout_config, headers = create_session(timeout=self.timeout, max_connections=5)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout_config,
            headers=headers,
        ) as session:
            # Check robots.txt first
            await self._check_robots_txt(session)

            # BFS crawl — deterministic order
            queue = [(_normalize_url(url), 0)]  # (url, depth)
            while queue and len(self.visited) < self.max_pages:
                current_url, depth = queue.pop(0)
                if _normalize_url(current_url) in self.visited or depth > self.max_depth:
                    continue
                p = urlparse(current_url)
                if p.netloc != self.base_domain:
                    continue
                new_links = await self._crawl_page(session, current_url, depth)
                for link in sorted(new_links):
                    if link not in self.visited:
                        queue.append((link, depth + 1))

        crawl_time = time.time() - start_time
        score = self._calculate_score()
        summary = self._generate_summary()

        return CrawlResult(
            target_url=url,
            pages_crawled=len(self.pages),
            total_links_found=len(self.visited),
            score=score,
            issues=[vars(i) for i in self.issues],
            pages=[vars(p) for p in self.pages],
            summary=summary,
            crawl_time=round(crawl_time, 2),
        )

    async def _check_robots_txt(self, session: aiohttp.ClientSession):
        robots_url = f"{self.base_url}/robots.txt"
        try:
            async with session.get(robots_url, allow_redirects=True) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if "Disallow: /" in text and "Disallow: //" not in text:
                        lines = text.split("\n")
                        for line in lines:
                            stripped = line.strip()
                            if stripped.lower().startswith("user-agent") and "*" in stripped:
                                # Check if next disallow blocks everything
                                pass
                            if stripped == "Disallow: /":
                                self.issues.append(CrawlIssue(
                                    severity="critical",
                                    category="robots_txt",
                                    url=robots_url,
                                    message="robots.txt bloquea todo el sitio con 'Disallow: /'",
                                    details="Los motores de busqueda e IAs no pueden acceder a ninguna pagina."
                                ))

                    # Check for AI bot blocks
                    ai_bots = ["GPTBot", "ClaudeBot", "Google-Extended", "Bytespider", "CCBot", "PerplexityBot"]
                    for bot in ai_bots:
                        if bot.lower() in text.lower():
                            blocked = False
                            lines = text.split("\n")
                            in_bot_section = False
                            for line in lines:
                                stripped = line.strip()
                                if stripped.lower().startswith("user-agent") and bot.lower() in stripped.lower():
                                    in_bot_section = True
                                elif stripped.lower().startswith("user-agent"):
                                    in_bot_section = False
                                elif in_bot_section and stripped.startswith("Disallow"):
                                    if stripped.replace("Disallow:", "").strip() in ["/", ""]:
                                        if stripped.replace("Disallow:", "").strip() == "/":
                                            blocked = True
                            if blocked:
                                self.issues.append(CrawlIssue(
                                    severity="warning",
                                    category="ai_bots",
                                    url=robots_url,
                                    message=f"El bot de IA '{bot}' esta bloqueado en robots.txt",
                                    details=f"{bot} no puede rastrear tu sitio. Esto afecta tu visibilidad en IA."
                                ))
                else:
                    self.issues.append(CrawlIssue(
                        severity="info",
                        category="robots_txt",
                        url=robots_url,
                        message="No se encontro archivo robots.txt",
                        details="Sin robots.txt, todos los bots pueden acceder. Considera crear uno para controlar el acceso."
                    ))
        except Exception:
            self.issues.append(CrawlIssue(
                severity="info",
                category="robots_txt",
                url=robots_url,
                message="No se pudo acceder al robots.txt",
            ))

    async def _crawl_page(self, session: aiohttp.ClientSession, url: str, depth: int) -> list[str]:
        """Crawl a single page and return discovered internal links (sorted)."""
        url = _normalize_url(url)
        self.visited.add(url)
        discovered = []

        try:
            start = time.time()
            async with session.get(url, allow_redirects=True) as resp:
                response_time = time.time() - start
                status = resp.status
                final_url = str(resp.url)

                # Track redirects
                if final_url != url:
                    self.redirects.append({"from": url, "to": final_url, "status": status})
                    if resp.history:
                        for r in resp.history:
                            if r.status in (301, 302, 303, 307, 308):
                                self.issues.append(CrawlIssue(
                                    severity="info",
                                    category="redirects",
                                    url=url,
                                    message=f"Redireccion {r.status} detectada",
                                    details=f"De {url} a {final_url}"
                                ))

                # Broken links
                if status >= 400:
                    self.broken_links.append({"url": url, "status": status})
                    severity = "critical" if status == 404 else "warning"
                    self.issues.append(CrawlIssue(
                        severity=severity,
                        category="broken_links",
                        url=url,
                        message=f"Enlace roto: HTTP {status}",
                        details=f"Esta pagina devuelve error {status}."
                    ))
                    return discovered

                # Slow pages
                if response_time > 3.0:
                    self.slow_pages.append({"url": url, "time": round(response_time, 2)})
                    self.issues.append(CrawlIssue(
                        severity="warning",
                        category="performance",
                        url=url,
                        message=f"Pagina lenta: {round(response_time, 2)}s",
                        details="Tiempo de respuesta superior a 3 segundos afecta el rastreo."
                    ))

                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type:
                    return discovered

                html = await resp.text()
                soup = BeautifulSoup(html, "lxml")

                page_result = self._analyze_page(url, status, response_time, soup)
                self.pages.append(page_result)

                # Check meta robots
                if page_result.meta_robots:
                    robots_content = page_result.meta_robots.lower()
                    if "noindex" in robots_content:
                        self.issues.append(CrawlIssue(
                            severity="warning",
                            category="indexability",
                            url=url,
                            message="Meta tag 'noindex' detectado",
                            details="Esta pagina no sera indexada por motores de busqueda."
                        ))
                    if "nofollow" in robots_content:
                        self.issues.append(CrawlIssue(
                            severity="info",
                            category="indexability",
                            url=url,
                            message="Meta tag 'nofollow' detectado",
                            details="Los enlaces de esta pagina no seran seguidos."
                        ))

                # Check title
                if not page_result.title:
                    self.issues.append(CrawlIssue(
                        severity="warning",
                        category="seo",
                        url=url,
                        message="Falta el titulo de la pagina",
                        details="Sin titulo, los motores de busqueda e IAs no pueden entender el contenido."
                    ))
                elif len(page_result.title) > 70:
                    self.issues.append(CrawlIssue(
                        severity="info",
                        category="seo",
                        url=url,
                        message=f"Titulo demasiado largo ({len(page_result.title)} caracteres)",
                        details="Se recomienda un titulo de menos de 70 caracteres."
                    ))

                # Check meta description
                if not page_result.meta_description:
                    self.issues.append(CrawlIssue(
                        severity="info",
                        category="seo",
                        url=url,
                        message="Falta la meta descripcion",
                        details="La meta descripcion ayuda a IAs y buscadores a entender tu pagina."
                    ))

                # Check H1
                if not page_result.has_h1:
                    self.issues.append(CrawlIssue(
                        severity="warning",
                        category="seo",
                        url=url,
                        message="No se encontro etiqueta H1",
                        details="Cada pagina deberia tener un H1 claro para los rastreadores."
                    ))

                # Check canonical
                if page_result.canonical and page_result.canonical != url:
                    self.issues.append(CrawlIssue(
                        severity="info",
                        category="indexability",
                        url=url,
                        message="Canonical apunta a otra URL",
                        details=f"Canonical: {page_result.canonical}"
                    ))

                # Check images without alt
                if page_result.images_without_alt > 0:
                    self.issues.append(CrawlIssue(
                        severity="info",
                        category="accessibility",
                        url=url,
                        message=f"{page_result.images_without_alt} imagenes sin atributo alt",
                        details="Las imagenes sin alt son invisibles para los rastreadores de IA."
                    ))

                # Return internal links (sorted for deterministic order)
                discovered = sorted(page_result.internal_links[:20])

        except asyncio.TimeoutError:
            self.issues.append(CrawlIssue(
                severity="critical",
                category="performance",
                url=url,
                message="Timeout: la pagina no respondio",
                details=f"La pagina no respondio en {self.timeout} segundos."
            ))
        except Exception as e:
            self.issues.append(CrawlIssue(
                severity="warning",
                category="connectivity",
                url=url,
                message=f"Error al acceder a la pagina",
                details=str(e)[:200]
            ))

        return discovered

    def _analyze_page(self, url: str, status: int, response_time: float, soup: BeautifulSoup) -> PageResult:
        # Title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Meta description
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta_desc_tag.get("content", "") if meta_desc_tag else None

        # Meta robots
        meta_robots_tag = soup.find("meta", attrs={"name": "robots"})
        meta_robots = meta_robots_tag.get("content", "") if meta_robots_tag else None

        # Canonical
        canonical_tag = soup.find("link", attrs={"rel": "canonical"})
        canonical = canonical_tag.get("href", "") if canonical_tag else None

        # H1
        h1_tag = soup.find("h1")
        has_h1 = h1_tag is not None

        # Links
        internal_links = []
        external_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(url, href)
            parsed = urlparse(full_url)
            if parsed.scheme not in ("http", "https"):
                continue
            if parsed.netloc == self.base_domain:
                clean_url = _normalize_url(full_url)
                if clean_url not in internal_links:
                    internal_links.append(clean_url)
            else:
                external_links.append(full_url)

        # Images
        images = soup.find_all("img")
        total_images = len(images)
        images_without_alt = sum(1 for img in images if not img.get("alt"))

        return PageResult(
            url=url,
            status_code=status,
            response_time=round(response_time, 3),
            title=title,
            meta_description=meta_desc,
            meta_robots=meta_robots,
            canonical=canonical,
            has_h1=has_h1,
            internal_links=internal_links,
            external_links=external_links,
            images_without_alt=images_without_alt,
            total_images=total_images,
        )

    def _calculate_score(self) -> int:
        score = 100
        for issue in self.issues:
            if issue.severity == "critical":
                score -= 15
            elif issue.severity == "warning":
                score -= 5
            elif issue.severity == "info":
                score -= 1
        return max(0, min(100, score))

    def _generate_summary(self) -> dict:
        critical = sum(1 for i in self.issues if i.severity == "critical")
        warnings = sum(1 for i in self.issues if i.severity == "warning")
        info = sum(1 for i in self.issues if i.severity == "info")

        categories = {}
        for issue in self.issues:
            cat = issue.category
            if cat not in categories:
                categories[cat] = {"critical": 0, "warning": 0, "info": 0}
            categories[cat][issue.severity] += 1

        return {
            "total_issues": len(self.issues),
            "critical": critical,
            "warnings": warnings,
            "info": info,
            "broken_links": len(self.broken_links),
            "redirects": len(self.redirects),
            "slow_pages": len(self.slow_pages),
            "pages_with_title": sum(1 for p in self.pages if p.title),
            "pages_with_meta_desc": sum(1 for p in self.pages if p.meta_description),
            "pages_with_h1": sum(1 for p in self.pages if p.has_h1),
            "categories": categories,
        }
