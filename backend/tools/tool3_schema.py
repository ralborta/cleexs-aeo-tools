import json
import re
from dataclasses import dataclass, field
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup
from tools.http_client import create_session


IMPORTANT_SCHEMA_TYPES = [
    "Organization", "LocalBusiness", "Person", "Product", "Service",
    "WebSite", "WebPage", "BreadcrumbList", "FAQPage", "HowTo",
    "Article", "BlogPosting", "NewsArticle", "Review", "AggregateRating",
    "Event", "Course", "Recipe", "VideoObject", "ImageObject",
    "SoftwareApplication", "MobileApplication",
]

RECOMMENDED_PROPERTIES = {
    "Organization": ["name", "url", "logo", "description", "sameAs", "contactPoint", "address"],
    "LocalBusiness": ["name", "address", "telephone", "openingHours", "geo", "priceRange", "image"],
    "Product": ["name", "description", "image", "offers", "brand", "review", "aggregateRating", "sku"],
    "Service": ["name", "description", "provider", "areaServed", "offers"],
    "WebSite": ["name", "url", "potentialAction"],
    "WebPage": ["name", "description", "url", "breadcrumb"],
    "FAQPage": ["mainEntity"],
    "Article": ["headline", "author", "datePublished", "dateModified", "image", "publisher"],
    "BlogPosting": ["headline", "author", "datePublished", "dateModified", "image", "publisher"],
    "BreadcrumbList": ["itemListElement"],
    "Review": ["reviewRating", "author", "itemReviewed"],
    "AggregateRating": ["ratingValue", "reviewCount", "bestRating"],
    "Event": ["name", "startDate", "location", "description", "offers"],
    "Person": ["name", "url", "jobTitle", "worksFor"],
}


@dataclass
class SchemaItem:
    schema_type: str
    source: str  # "json-ld", "microdata", "rdfa"
    properties: dict = field(default_factory=dict)
    missing_recommended: list = field(default_factory=list)
    is_valid: bool = True
    errors: list = field(default_factory=list)


@dataclass
class SchemaResult:
    url: str
    has_schema: bool = False
    schemas_found: list = field(default_factory=list)
    missing_types: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    score: int = 0
    raw_json_ld: list = field(default_factory=list)
    page_info: dict = field(default_factory=dict)


class SchemaChecker:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def check(self, url: str) -> dict:
        if not url.startswith("http"):
            url = "https://" + url

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
        result = SchemaResult(url=url)

        # Extract page info
        title_tag = soup.find("title")
        result.page_info = {
            "title": title_tag.get_text(strip=True) if title_tag else None,
            "has_h1": soup.find("h1") is not None,
        }

        # Extract JSON-LD
        json_ld_schemas = self._extract_json_ld(soup)
        for schema in json_ld_schemas:
            result.raw_json_ld.append(schema)
            items = self._parse_schema(schema, "json-ld")
            result.schemas_found.extend(items)

        # Extract Microdata
        microdata_items = self._extract_microdata(soup)
        result.schemas_found.extend(microdata_items)

        result.has_schema = len(result.schemas_found) > 0

        # Check missing recommended types
        found_types = set()
        for item in result.schemas_found:
            found_types.add(item["schema_type"])

        # Check which important types are missing
        for schema_type in ["Organization", "WebSite", "BreadcrumbList"]:
            if schema_type not in found_types:
                result.missing_types.append(schema_type)

        # Generate suggestions
        result.suggestions = self._generate_suggestions(result, found_types)

        # Calculate score
        result.score = self._calculate_score(result)

        return {
            "url": result.url,
            "has_schema": result.has_schema,
            "schemas_found": result.schemas_found,
            "missing_types": result.missing_types,
            "suggestions": result.suggestions,
            "score": result.score,
            "raw_json_ld": result.raw_json_ld,
            "page_info": result.page_info,
            "total_schemas": len(result.schemas_found),
        }

    def _extract_json_ld(self, soup: BeautifulSoup) -> list:
        schemas = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                text = script.string
                if text:
                    data = json.loads(text)
                    if isinstance(data, list):
                        schemas.extend(data)
                    else:
                        schemas.append(data)
            except (json.JSONDecodeError, TypeError):
                continue
        return schemas

    def _parse_schema(self, data: dict, source: str) -> list:
        items = []

        if isinstance(data, list):
            for item in data:
                items.extend(self._parse_schema(item, source))
            return items

        if not isinstance(data, dict):
            return items

        # Handle @graph
        if "@graph" in data:
            for node in data["@graph"]:
                items.extend(self._parse_schema(node, source))
            return items

        schema_type = data.get("@type", "")
        if isinstance(schema_type, list):
            schema_type = schema_type[0] if schema_type else ""

        if not schema_type:
            return items

        # Get properties (top-level keys excluding @context, @type, @id)
        properties = {}
        for key, value in data.items():
            if not key.startswith("@"):
                if value is not None and value != "" and value != []:
                    properties[key] = type(value).__name__

        # Check missing recommended
        missing = []
        if schema_type in RECOMMENDED_PROPERTIES:
            for prop in RECOMMENDED_PROPERTIES[schema_type]:
                if prop not in data or data[prop] is None or data[prop] == "":
                    missing.append(prop)

        items.append({
            "schema_type": schema_type,
            "source": source,
            "properties": properties,
            "missing_recommended": missing,
            "property_count": len(properties),
        })

        return items

    def _extract_microdata(self, soup: BeautifulSoup) -> list:
        items = []
        for element in soup.find_all(attrs={"itemtype": True}):
            itemtype = element.get("itemtype", "")
            # Extract type name from URL
            schema_type = itemtype.split("/")[-1] if "/" in itemtype else itemtype

            props = {}
            for prop_elem in element.find_all(attrs={"itemprop": True}):
                prop_name = prop_elem.get("itemprop", "")
                if prop_name:
                    props[prop_name] = "string"

            if schema_type:
                missing = []
                if schema_type in RECOMMENDED_PROPERTIES:
                    for prop in RECOMMENDED_PROPERTIES[schema_type]:
                        if prop not in props:
                            missing.append(prop)

                items.append({
                    "schema_type": schema_type,
                    "source": "microdata",
                    "properties": props,
                    "missing_recommended": missing,
                    "property_count": len(props),
                })

        return items

    def _generate_suggestions(self, result: SchemaResult, found_types: set) -> list:
        suggestions = []

        if not result.has_schema:
            suggestions.append({
                "priority": "critica",
                "message": "No se encontro ningun schema en la pagina",
                "detail": "Solo el 12.4% de los sitios tienen schema. Agregar datos estructurados mejora drasticamente la visibilidad en motores de IA y busqueda.",
                "action": "Agrega al menos Organization, WebSite y BreadcrumbList como JSON-LD.",
            })
            return suggestions

        if "Organization" not in found_types and "LocalBusiness" not in found_types:
            suggestions.append({
                "priority": "alta",
                "message": "Falta schema de Organization o LocalBusiness",
                "detail": "Los motores de IA necesitan saber quien eres. Agrega Organization con nombre, URL, logo, descripcion y redes sociales.",
                "action": "Agrega un bloque JSON-LD de tipo Organization.",
            })

        if "WebSite" not in found_types:
            suggestions.append({
                "priority": "alta",
                "message": "Falta schema de WebSite",
                "detail": "WebSite con SearchAction permite que tu sitio aparezca con barra de busqueda en resultados.",
                "action": "Agrega un bloque JSON-LD de tipo WebSite con potentialAction.",
            })

        if "BreadcrumbList" not in found_types:
            suggestions.append({
                "priority": "media",
                "message": "Falta schema de BreadcrumbList",
                "detail": "Las migas de pan estructuradas ayudan a entender la jerarquia de tu sitio.",
                "action": "Agrega BreadcrumbList en paginas internas.",
            })

        if "FAQPage" not in found_types:
            suggestions.append({
                "priority": "media",
                "message": "Considera agregar FAQPage",
                "detail": "Las preguntas frecuentes estructuradas son altamente citadas por motores de IA como ChatGPT y Perplexity.",
                "action": "Crea una seccion de FAQ con schema FAQPage.",
            })

        # Check for incomplete schemas
        for schema in result.schemas_found:
            if schema["missing_recommended"] and len(schema["missing_recommended"]) > 2:
                missing_str = ", ".join(schema["missing_recommended"][:5])
                suggestions.append({
                    "priority": "media",
                    "message": f"{schema['schema_type']} tiene propiedades faltantes: {missing_str}",
                    "detail": f"Completar estas propiedades mejora la comprension del contenido por parte de las IAs.",
                    "action": f"Agrega las propiedades faltantes al schema {schema['schema_type']}.",
                })

        if not suggestions:
            suggestions.append({
                "priority": "info",
                "message": "Tu schema se ve bien configurado",
                "detail": "Tienes los tipos principales implementados. Revisa las propiedades faltantes para optimizar aun mas.",
                "action": "Considera agregar Review y AggregateRating si aplica a tu negocio.",
            })

        return suggestions

    def _calculate_score(self, result: SchemaResult) -> int:
        if not result.has_schema:
            return 0

        score = 30  # Base for having any schema

        found_types = set(s["schema_type"] for s in result.schemas_found)

        # Points for important types
        if "Organization" in found_types or "LocalBusiness" in found_types:
            score += 15
        if "WebSite" in found_types:
            score += 10
        if "BreadcrumbList" in found_types:
            score += 10
        if "FAQPage" in found_types:
            score += 10
        if "Product" in found_types or "Service" in found_types:
            score += 10
        if "Article" in found_types or "BlogPosting" in found_types:
            score += 5
        if "Review" in found_types or "AggregateRating" in found_types:
            score += 10

        # Penalty for missing recommended properties
        total_missing = sum(len(s["missing_recommended"]) for s in result.schemas_found)
        score -= min(20, total_missing * 2)

        return max(0, min(100, score))

    def _error_result(self, url: str, error: str) -> dict:
        return {
            "url": url,
            "has_schema": False,
            "schemas_found": [],
            "missing_types": [],
            "suggestions": [{"priority": "critica", "message": f"Error al acceder: {error}", "detail": "", "action": ""}],
            "score": 0,
            "raw_json_ld": [],
            "page_info": {},
            "total_schemas": 0,
        }
