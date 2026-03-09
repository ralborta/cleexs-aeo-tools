import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field

import aiohttp
from bs4 import BeautifulSoup
from tools.http_client import create_session


@dataclass
class PageFreshness:
    url: str
    title: str = ""
    date_published: str = ""
    date_modified: str = ""
    days_since_update: int = -1
    freshness_status: str = "unknown"  # "fresh", "aging", "outdated", "unknown"
    content_length: int = 0
    has_dates: bool = False
    issues: list = field(default_factory=list)


class ContentFreshnessChecker:
    """
    Scans a site to find outdated content.
    Checks dates, content age, and suggests what needs updating.
    Based on wrodium.com concept.
    """

    def __init__(self, timeout: int = 15, max_pages: int = 30):
        self.timeout = timeout
        self.max_pages = max_pages

    async def check(self, url: str) -> dict:
        if not url.startswith("http"):
            url = "https://" + url

        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        # Normalize domain for comparison (strip www.)
        base_domain = parsed.netloc.replace("www.", "")

        connector, timeout_config, headers = create_session(timeout=self.timeout, max_connections=5)

        pages = []
        visited = set()
        to_visit = [url]

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout_config,
            headers=headers,
        ) as session:
            while to_visit and len(visited) < self.max_pages:
                current_url = to_visit.pop(0)
                if current_url in visited:
                    continue

                current_parsed = urlparse(current_url)
                if current_parsed.netloc.replace("www.", "") != base_domain:
                    continue

                visited.add(current_url)

                try:
                    async with session.get(current_url, allow_redirects=True) as resp:
                        if resp.status != 200:
                            continue
                        content_type = resp.headers.get("content-type", "")
                        if "text/html" not in content_type:
                            continue
                        html = await resp.text()
                except Exception:
                    continue

                soup = BeautifulSoup(html, "lxml")
                page_result = self._analyze_page(current_url, soup)
                pages.append(page_result)

                # Find more links (sorted for deterministic order)
                new_links = set()
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full_url = urljoin(current_url, href)
                    link_parsed = urlparse(full_url)
                    if link_parsed.netloc.replace("www.", "") == base_domain:
                        clean = f"{link_parsed.scheme}://{link_parsed.netloc}{link_parsed.path}"
                        if clean not in visited:
                            new_links.add(clean)
                to_visit.extend(sorted(new_links))

        # Generate summary
        summary = self._generate_summary(pages)
        suggestions = self._generate_suggestions(pages)
        score = self._calculate_score(pages)

        return {
            "url": url,
            "pages_analyzed": len(pages),
            "pages": [self._page_to_dict(p) for p in pages],
            "summary": summary,
            "suggestions": suggestions,
            "score": score,
        }

    def _analyze_page(self, url: str, soup: BeautifulSoup) -> PageFreshness:
        page = PageFreshness(url=url)

        # Title
        title_tag = soup.find("title")
        page.title = title_tag.get_text(strip=True) if title_tag else ""

        # Content length
        body = soup.find("body")
        if body:
            text = body.get_text(strip=True)
            page.content_length = len(text)

        # Extract dates from meta tags
        date_fields = [
            ("article:published_time", "date_published"),
            ("article:modified_time", "date_modified"),
            ("datePublished", "date_published"),
            ("dateModified", "date_modified"),
            ("og:updated_time", "date_modified"),
            ("last-modified", "date_modified"),
            ("date", "date_published"),
        ]

        for meta_name, field_name in date_fields:
            tag = soup.find("meta", attrs={"property": meta_name}) or \
                  soup.find("meta", attrs={"name": meta_name})
            if tag and tag.get("content"):
                value = tag["content"].strip()
                if value and not getattr(page, field_name):
                    setattr(page, field_name, value)

        # Check JSON-LD for dates
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    if "datePublished" in data and not page.date_published:
                        page.date_published = str(data["datePublished"])
                    if "dateModified" in data and not page.date_modified:
                        page.date_modified = str(data["dateModified"])
            except Exception:
                continue

        # Check <time> elements
        if not page.date_published and not page.date_modified:
            time_tags = soup.find_all("time", datetime=True)
            for t in time_tags:
                dt = t.get("datetime", "")
                if dt:
                    if not page.date_published:
                        page.date_published = dt
                    break

        # Calculate age
        page.has_dates = bool(page.date_published or page.date_modified)
        latest_date = page.date_modified or page.date_published

        if latest_date:
            try:
                # Parse various date formats
                parsed_date = None
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%dT%H:%M:%S.%f%z",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d",
                    "%Y/%m/%d",
                    "%B %d, %Y",
                    "%d %B %Y",
                ]:
                    try:
                        parsed_date = datetime.strptime(latest_date[:25], fmt)
                        break
                    except ValueError:
                        continue

                if parsed_date:
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    delta = now - parsed_date
                    page.days_since_update = delta.days

                    if page.days_since_update <= 90:
                        page.freshness_status = "fresh"
                    elif page.days_since_update <= 365:
                        page.freshness_status = "aging"
                    else:
                        page.freshness_status = "outdated"
            except Exception:
                page.freshness_status = "unknown"

        # Issues
        if page.freshness_status == "outdated":
            page.issues.append(f"Contenido desactualizado: {page.days_since_update} dias sin modificar")
        if not page.has_dates:
            page.issues.append("Sin fecha de publicacion o modificacion visible")
        if page.content_length < 300:
            page.issues.append("Contenido muy corto (thin content)")

        return page

    def _generate_summary(self, pages: list) -> dict:
        total = len(pages)
        if total == 0:
            return {"total": 0}

        fresh = sum(1 for p in pages if p.freshness_status == "fresh")
        aging = sum(1 for p in pages if p.freshness_status == "aging")
        outdated = sum(1 for p in pages if p.freshness_status == "outdated")
        unknown = sum(1 for p in pages if p.freshness_status == "unknown")
        with_dates = sum(1 for p in pages if p.has_dates)
        thin_content = sum(1 for p in pages if p.content_length < 300)

        avg_age = 0
        dated_pages = [p for p in pages if p.days_since_update >= 0]
        if dated_pages:
            avg_age = round(sum(p.days_since_update for p in dated_pages) / len(dated_pages))

        return {
            "total": total,
            "fresh": fresh,
            "aging": aging,
            "outdated": outdated,
            "unknown": unknown,
            "with_dates": with_dates,
            "without_dates": total - with_dates,
            "thin_content": thin_content,
            "avg_days_since_update": avg_age,
        }

    def _generate_suggestions(self, pages: list) -> list:
        suggestions = []

        outdated = [p for p in pages if p.freshness_status == "outdated"]
        if outdated:
            urls = [p.url for p in outdated[:5]]
            suggestions.append({
                "priority": "alta",
                "message": f"{len(outdated)} paginas desactualizadas (mas de 1 ano sin modificar)",
                "detail": "El contenido viejo pierde relevancia para las IAs. Actualiza fechas, datos y estadisticas.",
                "urls": urls,
            })

        no_dates = [p for p in pages if not p.has_dates]
        if no_dates:
            suggestions.append({
                "priority": "media",
                "message": f"{len(no_dates)} paginas sin fecha visible",
                "detail": "Las IAs y buscadores priorizan contenido con fechas claras. Agrega datePublished y dateModified en meta tags o JSON-LD.",
                "urls": [p.url for p in no_dates[:5]],
            })

        thin = [p for p in pages if p.content_length < 300]
        if thin:
            suggestions.append({
                "priority": "media",
                "message": f"{len(thin)} paginas con contenido muy corto",
                "detail": "Paginas con poco texto son dificiles de citar para las IAs. Expande el contenido con informacion relevante.",
                "urls": [p.url for p in thin[:5]],
            })

        aging = [p for p in pages if p.freshness_status == "aging"]
        if aging:
            suggestions.append({
                "priority": "baja",
                "message": f"{len(aging)} paginas envejeciendo (3-12 meses sin actualizar)",
                "detail": "Revisa estas paginas y actualiza los datos si es necesario para mantener la relevancia.",
                "urls": [p.url for p in aging[:5]],
            })

        if not suggestions:
            suggestions.append({
                "priority": "info",
                "message": "Tu contenido se ve actualizado",
                "detail": "La mayoria de tus paginas tienen fechas recientes. Sigue actualizando regularmente.",
                "urls": [],
            })

        return suggestions

    def _calculate_score(self, pages: list) -> int:
        if not pages:
            return 0

        score = 50
        total = len(pages)

        # Dated pages bonus
        with_dates = sum(1 for p in pages if p.has_dates)
        date_ratio = with_dates / total
        score += int(date_ratio * 20)

        # Freshness
        fresh = sum(1 for p in pages if p.freshness_status == "fresh")
        fresh_ratio = fresh / total if total > 0 else 0
        score += int(fresh_ratio * 20)

        # Penalties
        outdated = sum(1 for p in pages if p.freshness_status == "outdated")
        score -= int((outdated / total) * 30) if total > 0 else 0

        thin = sum(1 for p in pages if p.content_length < 300)
        score -= int((thin / total) * 10) if total > 0 else 0

        return max(0, min(100, score))

    def _page_to_dict(self, page: PageFreshness) -> dict:
        return {
            "url": page.url,
            "title": page.title,
            "date_published": page.date_published,
            "date_modified": page.date_modified,
            "days_since_update": page.days_since_update,
            "freshness_status": page.freshness_status,
            "content_length": page.content_length,
            "has_dates": page.has_dates,
            "issues": page.issues,
        }
