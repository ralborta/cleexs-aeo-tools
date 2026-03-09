"""
Tool 10: Duplicate Content Finder
Based on siteliner.com

Crawls a site and finds pages with duplicate or very similar content.
"""

from urllib.parse import urljoin, urlparse
import hashlib

import aiohttp
from bs4 import BeautifulSoup
from tools.http_client import create_session


class DuplicateContentFinder:

    def __init__(self, timeout: int = 15, max_pages: int = 30):
        self.timeout = timeout
        self.max_pages = max_pages

    async def find(self, url: str) -> dict:
        if not url.startswith("http"):
            url = "https://" + url

        parsed = urlparse(url)
        domain = parsed.netloc
        base_url = f"{parsed.scheme}://{parsed.netloc}"

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
                current = to_visit.pop(0)
                if current in visited:
                    continue

                current_parsed = urlparse(current)
                if current_parsed.netloc != domain:
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

                # Extract text content
                body = soup.find("body")
                if not body:
                    continue

                # Remove boilerplate elements for comparison
                for tag in body.find_all(["nav", "footer", "header", "aside", "script", "style", "noscript", "iframe", "form"]):
                    tag.decompose()
                # Remove common boilerplate by class/id patterns
                for tag in body.find_all(attrs={"class": True}):
                    classes = " ".join(tag.get("class", []))
                    if any(kw in classes.lower() for kw in ["sidebar", "widget", "menu", "breadcrumb", "cookie", "popup", "modal", "banner", "social", "share", "comment"]):
                        tag.decompose()
                for tag in body.find_all(attrs={"id": True}):
                    tag_id = tag.get("id", "")
                    if any(kw in tag_id.lower() for kw in ["sidebar", "widget", "menu", "cookie", "popup", "modal", "banner"]):
                        tag.decompose()

                text = body.get_text(separator=" ", strip=True)
                text_clean = " ".join(text.split())

                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else ""

                # Generate content fingerprint using shingles
                shingles = self._generate_shingles(text_clean, 5)
                content_hash = hashlib.md5(text_clean.encode()).hexdigest()

                pages.append({
                    "url": current,
                    "title": title,
                    "text_length": len(text_clean),
                    "word_count": len(text_clean.split()),
                    "content_hash": content_hash,
                    "shingles": shingles,
                    "text_preview": text_clean[:200],
                })

                # Follow links (sorted for deterministic order)
                new_links = set()
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full = urljoin(current, href)
                    fp = urlparse(full)
                    if fp.netloc == domain:
                        clean = f"{fp.scheme}://{fp.netloc}{fp.path}"
                        if clean not in visited:
                            new_links.add(clean)
                to_visit.extend(sorted(new_links))

        # Find duplicates
        duplicates = self._find_duplicates(pages)

        # Find similar pages
        similar = self._find_similar(pages)

        # Summary
        summary = self._generate_summary(pages, duplicates, similar)
        suggestions = self._generate_suggestions(duplicates, similar, pages)
        score = self._calculate_score(pages, duplicates, similar)

        return {
            "url": url,
            "domain": domain,
            "pages_analyzed": len(pages),
            "duplicates": duplicates,
            "similar_pages": similar[:20],
            "summary": summary,
            "suggestions": suggestions,
            "score": score,
            "pages": [{
                "url": p["url"],
                "title": p["title"],
                "word_count": p["word_count"],
            } for p in pages],
        }

    def _generate_shingles(self, text: str, n: int) -> set:
        words = text.lower().split()
        if len(words) < n:
            return {hashlib.md5(" ".join(words).encode()).hexdigest()}
        shingles = set()
        for i in range(len(words) - n + 1):
            shingle = " ".join(words[i:i + n])
            shingles.add(hashlib.md5(shingle.encode()).hexdigest())
        return shingles

    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _find_duplicates(self, pages: list) -> list:
        """Find exact duplicate pages (same content hash)."""
        hash_groups = {}
        for page in pages:
            h = page["content_hash"]
            if h not in hash_groups:
                hash_groups[h] = []
            hash_groups[h].append(page["url"])

        duplicates = []
        for h, urls in hash_groups.items():
            if len(urls) > 1:
                duplicates.append({
                    "type": "exact",
                    "urls": urls,
                    "count": len(urls),
                })

        return duplicates

    def _find_similar(self, pages: list) -> list:
        """Find pages with high content similarity."""
        similar = []
        checked = set()

        for i, page_a in enumerate(pages):
            for j, page_b in enumerate(pages):
                if i >= j:
                    continue
                pair_key = f"{i}-{j}"
                if pair_key in checked:
                    continue
                checked.add(pair_key)

                sim = self._jaccard_similarity(page_a["shingles"], page_b["shingles"])
                if sim > 0.3 and page_a["content_hash"] != page_b["content_hash"]:
                    similar.append({
                        "url_a": page_a["url"],
                        "url_b": page_b["url"],
                        "similarity_pct": round(sim * 100, 1),
                        "title_a": page_a["title"],
                        "title_b": page_b["title"],
                    })

        similar.sort(key=lambda x: x["similarity_pct"], reverse=True)
        return similar

    def _generate_summary(self, pages: list, duplicates: list, similar: list) -> dict:
        total = len(pages)
        total_words = sum(p["word_count"] for p in pages)
        avg_words = round(total_words / total) if total > 0 else 0

        duplicate_urls = set()
        for d in duplicates:
            for u in d["urls"]:
                duplicate_urls.add(u)

        similar_urls = set()
        for s in similar:
            similar_urls.add(s["url_a"])
            similar_urls.add(s["url_b"])

        unique_pages = total - len(duplicate_urls)

        return {
            "total_pages": total,
            "total_words": total_words,
            "avg_words_per_page": avg_words,
            "exact_duplicates": len(duplicate_urls),
            "similar_pages": len(similar_urls),
            "unique_pages": max(0, unique_pages),
            "duplicate_groups": len(duplicates),
            "similar_pairs": len(similar),
            "uniqueness_pct": round((unique_pages / total) * 100) if total > 0 else 100,
        }

    def _generate_suggestions(self, duplicates: list, similar: list, pages: list) -> list:
        suggestions = []

        if duplicates:
            total_dup = sum(d["count"] for d in duplicates)
            suggestions.append({
                "priority": "alta",
                "message": f"{total_dup} paginas con contenido exactamente duplicado",
                "detail": "El contenido duplicado confunde a las IAs y diluye tu autoridad. Usa canonicals o consolida estas paginas.",
                "urls": [d["urls"] for d in duplicates[:3]],
            })

        high_similar = [s for s in similar if s["similarity_pct"] > 70]
        if high_similar:
            suggestions.append({
                "priority": "alta",
                "message": f"{len(high_similar)} pares de paginas con contenido muy similar (>70%)",
                "detail": "Paginas muy parecidas compiten entre si. Considera combinarlas o diferenciar claramente el contenido.",
                "urls": [[s["url_a"], s["url_b"]] for s in high_similar[:3]],
            })

        medium_similar = [s for s in similar if 30 < s["similarity_pct"] <= 70]
        if medium_similar:
            suggestions.append({
                "priority": "media",
                "message": f"{len(medium_similar)} pares con similitud moderada (30-70%)",
                "detail": "Revisa estas paginas para asegurar que cada una aporta valor unico.",
                "urls": [[s["url_a"], s["url_b"]] for s in medium_similar[:3]],
            })

        thin = [p for p in pages if p["word_count"] < 100]
        if thin:
            suggestions.append({
                "priority": "media",
                "message": f"{len(thin)} paginas con contenido muy corto (<100 palabras)",
                "detail": "Paginas thin content son dificiles de diferenciar y aportan poco valor para las IAs.",
                "urls": [p["url"] for p in thin[:5]],
            })

        if not suggestions:
            suggestions.append({
                "priority": "info",
                "message": "No se encontraron problemas significativos de contenido duplicado",
                "detail": "Tu sitio tiene buen nivel de contenido unico.",
                "urls": [],
            })

        return suggestions

    def _calculate_score(self, pages: list, duplicates: list, similar: list) -> int:
        total = len(pages)
        if total == 0:
            return 0

        score = 100

        # Penalty for exact duplicates
        dup_count = sum(d["count"] for d in duplicates)
        score -= min(30, dup_count * 10)

        # Penalty for high similarity
        high_sim = sum(1 for s in similar if s["similarity_pct"] > 70)
        score -= min(20, high_sim * 5)

        # Penalty for medium similarity
        med_sim = sum(1 for s in similar if 30 < s["similarity_pct"] <= 70)
        score -= min(15, med_sim * 3)

        return max(0, min(100, score))
