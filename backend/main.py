import asyncio
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
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
from config import SKIP_DB

app = FastAPI(title="Cleexs Tools - All-in-One AEO Analyzer")


@app.on_event("startup")
async def startup():
    try:
        await init_db()
    except Exception:
        pass  # App arranca igual; endpoints que usen DB fallarán hasta que MySQL esté bien

# CORS: permitir cualquier origen (Vercel, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


class URLRequest(BaseModel):
    url: str


ANALYZE_JOBS: dict[str, dict] = {}


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Preset "API-safe": evita jobs extremadamente largos que terminan en timeout del cliente.
FAST_MAX_PAGES = {
    "crawlability": 8,
    "robots_sitemap": 18,
    "freshness": 10,
    "citations": 6,
    "ai_overview": 6,
    "duplicates": 8,
}

TOOL_TIMEOUT_SEC = {
    "schema": 22,
    "axp": 22,
    "ai_presence": 36,
    "alerts": 40,
    "crawlability": 38,
    "robots_sitemap": 45,
    "freshness": 38,
    "citations": 52,
    "ai_overview": 30,
    "duplicates": 34,
}


class RobotsGenRequest(BaseModel):
    url: str
    allow_ai: bool = True


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/status")
async def api_status():
    """Para comprobar que el backend está vivo y SKIP_DB está activo."""
    return {"status": "ok", "skip_db": SKIP_DB}


# ─── Full Analysis (all tools at once) ───


def _normalize_analyze_url(raw: str) -> str:
    url = raw.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL es requerida")
    if not url.startswith("http"):
        url = "https://" + url
    return url


async def run_analyze_all_impl(url: str) -> dict:
    output: dict = {}

    fast_results = await asyncio.gather(
        _run_tool_budgeted("schema", SchemaChecker().check(url)),
        _run_tool_budgeted("axp", AXPGenerator().generate(url)),
        _run_tool_budgeted("ai_presence", AIPresenceTester().test(url)),
        _run_tool_budgeted("alerts", MentionAlertAnalyzer().analyze(url)),
        return_exceptions=True,
    )
    fast_names = ["schema", "axp", "ai_presence", "alerts"]
    for name, result in zip(fast_names, fast_results):
        output[name] = _process_result(name, result)

    # Crawl + robots en paralelo (mismo host; ahorra ~30–40s de cola en el análisis total).
    cr, rb = await asyncio.gather(
        _run_tool_budgeted(
            "crawlability",
            SiteCrawler(max_pages=FAST_MAX_PAGES["crawlability"], max_depth=2).crawl(url),
        ),
        _run_tool_budgeted(
            "robots_sitemap",
            SiteAnalyzer(max_crawl_pages=FAST_MAX_PAGES["robots_sitemap"]).analyze(url),
        ),
    )
    output["crawlability"] = _process_result("crawlability", cr)
    output["robots_sitemap"] = _process_result("robots_sitemap", rb)

    crawl_tools = [
        ("freshness", ContentFreshnessChecker(max_pages=FAST_MAX_PAGES["freshness"]).check(url)),
        ("citations", QueryCitationTracker(max_pages=FAST_MAX_PAGES["citations"]).analyze(url)),
        ("ai_overview", AIOverviewChecker(max_pages=FAST_MAX_PAGES["ai_overview"]).check(url)),
        ("duplicates", DuplicateContentFinder(max_pages=FAST_MAX_PAGES["duplicates"]).find(url)),
    ]
    for name, coro in crawl_tools:
        result = await _run_tool_budgeted(name, coro)
        output[name] = _process_result(name, result)

    scores = []
    for name in output:
        if isinstance(output[name], dict):
            s = output[name].get("score", 0)
            if isinstance(s, (int, float)):
                scores.append(s)

    output["overall_score"] = round(sum(scores) / len(scores)) if scores else 0
    output["target_url"] = url

    try:
        domain = urlparse(url).netloc.replace("www.", "")
        await save_analysis(url, domain, output["overall_score"], output)
    except Exception:
        pass

    return output


async def _analyze_all_job_task(job_id: str, url: str) -> None:
    try:
        result = await run_analyze_all_impl(url)
        result["job_status"] = "completed"
        ANALYZE_JOBS[job_id] = result
    except Exception as e:
        ANALYZE_JOBS[job_id] = {
            "job_status": "failed",
            "error": str(e)[:500],
            "failed_at": _utc_iso(),
        }


@app.post("/api/analyze-all/start")
async def analyze_all_start(request: URLRequest):
    url = _normalize_analyze_url(request.url)
    job_id = str(uuid.uuid4())
    ANALYZE_JOBS[job_id] = {"job_status": "running", "started_at": _utc_iso()}
    asyncio.create_task(_analyze_all_job_task(job_id, url))
    return JSONResponse(
        status_code=202,
        content={"job_id": job_id, "poll_url": f"/api/analyze-all/jobs/{job_id}"},
    )


@app.get("/api/analyze-all/jobs/{job_id}")
async def analyze_all_job_status(job_id: str):
    if job_id not in ANALYZE_JOBS:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return ANALYZE_JOBS[job_id]


@app.post("/api/analyze-all")
async def analyze_all(request: URLRequest):
    url = _normalize_analyze_url(request.url)
    try:
        return await run_analyze_all_impl(url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _run_tool(name: str, coro):
    try:
        result = await coro
        return result
    except Exception as e:
        return {"error": str(e)[:200], "score": 0}


async def _run_tool_budgeted(name: str, coro):
    """Timeout por herramienta con resultado degradado en vez de colgar el job completo."""
    budget = TOOL_TIMEOUT_SEC.get(name, 30)
    try:
        result = await asyncio.wait_for(coro, timeout=budget)
        return result
    except asyncio.TimeoutError:
        return {"error": f"timeout_tool_{name}_{budget}s", "score": 0}
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
