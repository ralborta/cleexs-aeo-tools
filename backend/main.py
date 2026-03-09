import asyncio
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from tools.tool1_crawlability import SiteCrawler
from tools.tool2_robots_sitemap import SiteAnalyzer, generate_recommended_robots
from tools.tool3_schema import SchemaChecker
from tools.tool4_axp import AXPGenerator
from tools.tool5_ai_presence import AIPresenceTester
from tools.tool6_query_citations import QueryCitationTracker
from tools.tool7_mention_alerts import MentionAlertAnalyzer
from tools.tool8_content_freshness import ContentFreshnessChecker
from tools.tool9_ai_overview import AIOverviewChecker
from tools.tool10_duplicate_content import DuplicateContentFinder
from database import init_db, save_analysis, get_history, get_analysis, get_domain_history

app = FastAPI(title="Cleexs Tools - All-in-One AEO Analyzer")


@app.on_event("startup")
async def startup():
    await init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class URLRequest(BaseModel):
    url: str


class RobotsGenRequest(BaseModel):
    url: str
    allow_ai: bool = True


@app.get("/health")
async def health():
    return {"status": "ok"}


# ─── Full Analysis (all tools at once) ───

@app.post("/api/analyze-all")
async def analyze_all(request: URLRequest):
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL es requerida")
    if not url.startswith("http"):
        url = "https://" + url

    output = {}

    try:
        # Phase 1 — single-page tools in parallel (each fetches only 1 page)
        fast_results = await asyncio.gather(
            _run_tool("schema", SchemaChecker().check(url)),
            _run_tool("axp", AXPGenerator().generate(url)),
            _run_tool("ai_presence", AIPresenceTester().test(url)),
            _run_tool("alerts", MentionAlertAnalyzer().analyze(url)),
            return_exceptions=True,
        )
        fast_names = ["schema", "axp", "ai_presence", "alerts"]
        for name, result in zip(fast_names, fast_results):
            output[name] = _process_result(name, result)

        # Phase 2 — crawling tools ONE AT A TIME to avoid server overload
        crawl_tools = [
            ("crawlability", SiteCrawler(max_pages=15, max_depth=2).crawl(url)),
            ("robots_sitemap", SiteAnalyzer(max_crawl_pages=50).analyze(url)),
            ("freshness", ContentFreshnessChecker(max_pages=30).check(url)),
            ("citations", QueryCitationTracker(max_pages=15).analyze(url)),
            ("ai_overview", AIOverviewChecker(max_pages=10).check(url)),
            ("duplicates", DuplicateContentFinder(max_pages=15).find(url)),
        ]
        for name, coro in crawl_tools:
            result = await _run_tool(name, coro)
            output[name] = _process_result(name, result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Overall score
    scores = []
    for name in output:
        if isinstance(output[name], dict):
            s = output[name].get("score", 0)
            if isinstance(s, (int, float)):
                scores.append(s)

    output["overall_score"] = round(sum(scores) / len(scores)) if scores else 0
    output["target_url"] = url

    # Save to database
    try:
        domain = urlparse(url).netloc.replace("www.", "")
        await save_analysis(url, domain, output["overall_score"], output)
    except Exception:
        pass  # Don't fail the response if DB save fails

    return output


async def _run_tool(name: str, coro):
    try:
        result = await coro
        return result
    except Exception as e:
        return {"error": str(e)[:200], "score": 0}


def _process_result(name: str, result) -> dict:
    if isinstance(result, dict) and "error" in result:
        return {"error": result["error"], "score": 0}
    elif isinstance(result, dict):
        return result
    elif hasattr(result, "__dict__"):
        return _crawl_result_to_dict(result) if name == "crawlability" else _analyzer_result_to_dict(result)
    else:
        return {"error": str(result), "score": 0}


def _crawl_result_to_dict(result) -> dict:
    return {
        "target_url": result.target_url,
        "pages_crawled": result.pages_crawled,
        "total_links_found": result.total_links_found,
        "score": result.score,
        "issues": result.issues,
        "summary": result.summary,
        "crawl_time": result.crawl_time,
    }


def _analyzer_result_to_dict(result) -> dict:
    return {
        "target_url": result.target_url,
        "robots": result.robots,
        "sitemap": result.sitemap,
        "generated_sitemap": result.generated_sitemap,
        "score": result.score,
        "analysis_time": result.analysis_time,
    }


# ─── History Endpoints ───

@app.get("/api/history")
async def history(limit: int = 50):
    return await get_history(limit)


@app.get("/api/history/{analysis_id}")
async def history_detail(analysis_id: int):
    result = await get_analysis(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analisis no encontrado")
    return result


@app.get("/api/history/domain/{domain}")
async def history_by_domain(domain: str, limit: int = 20):
    return await get_domain_history(domain, limit)


# ─── Individual Tool Endpoints ───

@app.post("/api/tool/crawlability")
async def tool_crawlability(request: URLRequest):
    url = _clean_url(request.url)
    crawler = SiteCrawler(max_pages=30, max_depth=3)
    result = await crawler.crawl(url)
    return _crawl_result_to_dict(result)


@app.post("/api/tool/robots-sitemap")
async def tool_robots_sitemap(request: URLRequest):
    url = _clean_url(request.url)
    analyzer = SiteAnalyzer()
    result = await analyzer.analyze(url)
    return _analyzer_result_to_dict(result)


@app.post("/api/tool/schema")
async def tool_schema(request: URLRequest):
    url = _clean_url(request.url)
    return await SchemaChecker().check(url)


@app.post("/api/tool/axp")
async def tool_axp(request: URLRequest):
    url = _clean_url(request.url)
    return await AXPGenerator().generate(url)


@app.post("/api/tool/ai-presence")
async def tool_ai_presence(request: URLRequest):
    url = _clean_url(request.url)
    return await AIPresenceTester().test(url)


@app.post("/api/tool/citations")
async def tool_citations(request: URLRequest):
    url = _clean_url(request.url)
    return await QueryCitationTracker().analyze(url)


@app.post("/api/tool/alerts")
async def tool_alerts(request: URLRequest):
    url = _clean_url(request.url)
    return await MentionAlertAnalyzer().analyze(url)


@app.post("/api/tool/freshness")
async def tool_freshness(request: URLRequest):
    url = _clean_url(request.url)
    return await ContentFreshnessChecker().check(url)


@app.post("/api/tool/ai-overview")
async def tool_ai_overview(request: URLRequest):
    url = _clean_url(request.url)
    return await AIOverviewChecker().check(url)


@app.post("/api/tool/duplicates")
async def tool_duplicates(request: URLRequest):
    url = _clean_url(request.url)
    return await DuplicateContentFinder().find(url)


@app.post("/api/generate-robots")
async def gen_robots(request: RobotsGenRequest):
    url = _clean_url(request.url)
    from urllib.parse import urlparse
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    return {"content": generate_recommended_robots(base, request.allow_ai)}


def _clean_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL es requerida")
    if not url.startswith("http"):
        url = "https://" + url
    return url


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
