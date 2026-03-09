/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState } from "react";
import ScoreCircle from "./ScoreCircle";
import { SuggestionItem, StatusBadge, IssueItem } from "./tools/GenericToolView";

interface Props {
  data: any;
  onReset: () => void;
}

const TOOLS = [
  { key: "crawlability", label: "Crawlability", num: 1, icon: "spider" },
  { key: "robots_sitemap", label: "Robots & Sitemap", num: 2, icon: "file" },
  { key: "schema", label: "Schema", num: 3, icon: "code" },
  { key: "axp", label: "AXP", num: 4, icon: "cpu" },
  { key: "ai_presence", label: "AI Presence", num: 5, icon: "eye" },
  { key: "citations", label: "Citations", num: 6, icon: "quote" },
  { key: "alerts", label: "Alerts", num: 7, icon: "bell" },
  { key: "freshness", label: "Freshness", num: 8, icon: "clock" },
  { key: "ai_overview", label: "AI Overview", num: 9, icon: "chart" },
  { key: "duplicates", label: "Duplicados", num: 10, icon: "copy" },
  { key: "actions", label: "Acciones a Ejecutar", num: 0, icon: "list" },
];

export default function Dashboard({ data, onReset }: Props) {
  const [activeTab, setActiveTab] = useState("crawlability");

  const getScore = (key: string) => {
    const d = data[key];
    if (!d) return 0;
    return d.score ?? 0;
  };

  const overallScore = data.overall_score || 0;
  const scoreColor = overallScore >= 80 ? "var(--success)" : overallScore >= 50 ? "var(--warning)" : "var(--critical)";

  return (
    <section className="px-4 md:px-8 pt-6 pb-16 max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-2xl shadow-sm p-5 mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={onReset} className="w-9 h-9 rounded-xl bg-[var(--background)] hover:bg-gray-100 flex items-center justify-center transition-colors cursor-pointer">
            <svg className="w-4 h-4 text-[var(--text-muted)]" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
          </button>
          <div>
            <p className="text-xs text-[var(--text-muted)] mb-0.5">Resultados para</p>
            <h2 className="text-lg font-bold leading-tight">{data.target_url}</h2>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-xs text-[var(--text-muted)]">Score global</p>
            <p className="text-2xl font-extrabold leading-tight" style={{ color: scoreColor }}>{overallScore}</p>
          </div>
          <div className="w-12 h-12 rounded-full border-[3px] flex items-center justify-center" style={{ borderColor: scoreColor }}>
            <span className="text-xs font-bold" style={{ color: scoreColor }}>/100</span>
          </div>
        </div>
      </div>

      {/* Main grid */}
      <div className="flex gap-5">
        {/* Sidebar */}
        <div className="w-56 shrink-0">
          <div className="bg-white rounded-2xl shadow-sm p-2 space-y-0.5">
            {TOOLS.map((tool) => {
              const isActions = tool.key === "actions";
              const score = isActions ? 0 : getScore(tool.key);
              const isActive = activeTab === tool.key;
              const hasError = !isActions && data[tool.key]?.error;
              const hasData = isActions || !!data[tool.key];
              const sColor = score >= 80 ? "var(--success)" : score >= 50 ? "var(--warning)" : "var(--critical)";

              return (
                <div key={tool.key}>
                  {isActions && <div className="border-t border-gray-100 my-1" />}
                  <button
                    onClick={() => setActiveTab(tool.key)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all cursor-pointer group ${
                      isActive
                        ? isActions
                          ? "bg-amber-500 text-white shadow-md shadow-amber-500/20"
                          : "bg-[var(--primary)] text-white shadow-md shadow-[var(--primary)]/20"
                        : "hover:bg-[var(--background)] text-[var(--foreground)]"
                    }`}
                  >
                    {isActions ? (
                      <span className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 ${
                        isActive ? "bg-white/20 text-white" : "bg-amber-50 text-amber-600"
                      }`}>
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                          <path d="M9 5l7 7-7 7" />
                        </svg>
                      </span>
                    ) : (
                      <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-bold shrink-0 ${
                        isActive ? "bg-white/20 text-white" : "bg-[var(--background)] text-[var(--text-muted)]"
                      }`}>
                        {tool.num}
                      </span>
                    )}
                    <span className="flex-1 text-left font-medium truncate">{tool.label}</span>
                    {!isActions && hasError ? (
                      <span className={`text-xs ${isActive ? "text-white/70" : "text-red-400"}`}>!</span>
                    ) : !isActions && hasData && (
                      <span
                        className="text-xs font-bold tabular-nums"
                        style={{ color: isActive ? "white" : sColor }}
                      >
                        {score}
                      </span>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 bg-white rounded-2xl shadow-sm p-6 min-h-[540px] overflow-auto">
          {activeTab === "crawlability" && <CrawlabilityView data={data.crawlability} />}
          {activeTab === "robots_sitemap" && <RobotsSitemapView data={data.robots_sitemap} />}
          {activeTab === "schema" && <SchemaView data={data.schema} />}
          {activeTab === "axp" && <AXPView data={data.axp} />}
          {activeTab === "ai_presence" && <AIPresenceView data={data.ai_presence} />}
          {activeTab === "citations" && <CitationsView data={data.citations} />}
          {activeTab === "alerts" && <AlertsView data={data.alerts} />}
          {activeTab === "freshness" && <FreshnessView data={data.freshness} />}
          {activeTab === "ai_overview" && <AIOverviewView data={data.ai_overview} />}
          {activeTab === "duplicates" && <DuplicatesView data={data.duplicates} />}
          {activeTab === "actions" && <ActionsView data={data} />}
        </div>
      </div>
    </section>
  );
}

/* ──── Tool Views ──── */

function SchemaView({ data }: { data: any }) {
  if (!data) return <ErrorState />;
  return (
    <div className="space-y-5">
      <ToolHeader title="Datos Estructurados (Schema)" score={data.score} subtitle={`${data.total_schemas || 0} schemas encontrados`} />
      {data.schemas_found?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Schemas detectados</h4>
          <div className="flex flex-wrap gap-2">
            {data.schemas_found.map((s: any, i: number) => (
              <div key={i} className="bg-blue-50 text-blue-700 px-3 py-1.5 rounded-lg text-xs font-medium">
                {s.schema_type} <span className="opacity-60">({s.source}, {s.property_count} props)</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {data.missing_types?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Tipos faltantes</h4>
          <div className="flex flex-wrap gap-2">
            {data.missing_types.map((t: string) => (
              <span key={t} className="bg-red-50 text-red-600 px-3 py-1.5 rounded-lg text-xs font-medium">{t}</span>
            ))}
          </div>
        </div>
      )}
      <Suggestions items={data.suggestions} />
    </div>
  );
}

function AXPView({ data }: { data: any }) {
  if (!data) return <ErrorState />;
  const llm = data.llm_evaluation;
  return (
    <div className="space-y-5">
      <ToolHeader title="AXP — Optimizacion para IA" score={data.score} subtitle="Estructura y comprension por IA" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Original" value={formatBytes(data.original_size)} />
        <StatCard label="Optimizado" value={formatBytes(data.optimized_size)} />
        <StatCard label="Reduccion" value={`${data.reduction_pct}%`} />
        <StatCard label="Tokens est." value={`${data.optimized_tokens_est}`} />
      </div>

      {/* LLM Evaluation */}
      {llm && !llm.error && (
        <div>
          <h4 className="font-semibold text-sm mb-3">Evaluacion por IA</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            {[
              { label: "Claridad", key: "claridad" },
              { label: "Completitud", key: "completitud" },
              { label: "Estructura", key: "estructura" },
              { label: "Diferenciacion", key: "diferenciacion" },
            ].map(dim => {
              const val = llm[dim.key];
              if (typeof val !== "number") return null;
              const c = val >= 7 ? "green" : val >= 5 ? "yellow" : "red";
              return <StatCard key={dim.key} label={dim.label} value={`${val}/10`} color={c} />;
            })}
          </div>
          {llm.resumen && (
            <div className="bg-gray-50 rounded-lg p-3 text-sm">
              <span className="font-medium">Resumen IA:</span> {llm.resumen}
            </div>
          )}
          {llm.sugerencias?.length > 0 && (
            <div className="mt-2 space-y-1">
              {llm.sugerencias.map((s: string, i: number) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className="text-amber-500 mt-0.5">&#9679;</span>
                  <span>{s}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {data.ai_friendly_content && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Contenido limpio (preview)</h4>
          <pre className="bg-gray-50 p-4 rounded-xl text-xs leading-relaxed max-h-64 overflow-auto">{data.ai_friendly_content.substring(0, 2000)}</pre>
        </div>
      )}
      <Issues items={data.issues} />
      <Suggestions items={data.suggestions} />
    </div>
  );
}

function FreshnessView({ data }: { data: any }) {
  if (!data) return <ErrorState />;
  const s = data.summary || {};
  const total = s.total || data.pages_analyzed || 0;
  const freshPct = total > 0 ? Math.round(((s.fresh || 0) / total) * 100) : 0;
  const agingPct = total > 0 ? Math.round(((s.aging || 0) / total) * 100) : 0;
  const outdatedPct = total > 0 ? Math.round(((s.outdated || 0) / total) * 100) : 0;
  const unknownPct = total > 0 ? Math.round(((s.unknown || 0) / total) * 100) : 0;
  return (
    <div className="space-y-5">
      <ToolHeader title="Frescura del Contenido" score={data.score} subtitle={`${data.pages_analyzed || 0} paginas analizadas`} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Frescas (<90d)" value={s.fresh || 0} color="green" />
        <StatCard label="Envejeciendo" value={s.aging || 0} color="yellow" />
        <StatCard label="Desactualizadas" value={s.outdated || 0} color="red" />
        <StatCard label="Sin fecha" value={s.without_dates || 0} />
      </div>

      {/* Freshness distribution bar */}
      {total > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Distribucion de frescura</h4>
          <div className="flex w-full h-4 rounded-full overflow-hidden bg-gray-100">
            {freshPct > 0 && <div className="bg-green-500 h-full" style={{ width: `${freshPct}%` }} title={`Frescas: ${freshPct}%`} />}
            {agingPct > 0 && <div className="bg-amber-400 h-full" style={{ width: `${agingPct}%` }} title={`Envejeciendo: ${agingPct}%`} />}
            {outdatedPct > 0 && <div className="bg-red-400 h-full" style={{ width: `${outdatedPct}%` }} title={`Desactualizadas: ${outdatedPct}%`} />}
            {unknownPct > 0 && <div className="bg-gray-300 h-full" style={{ width: `${unknownPct}%` }} title={`Sin fecha: ${unknownPct}%`} />}
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 mt-1">
            <span>Frescas {freshPct}%</span>
            <span>Envejeciendo {agingPct}%</span>
            <span>Desactualizadas {outdatedPct}%</span>
            <span>Sin fecha {unknownPct}%</span>
          </div>
        </div>
      )}

      {s.avg_days_since_update > 0 && (
        <div className="bg-gray-50 rounded-lg p-3 text-sm">
          Promedio de antiguedad: <span className="font-semibold">{s.avg_days_since_update} dias</span> desde ultima actualizacion
        </div>
      )}

      {data.pages?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Detalle por pagina ({data.pages.length})</h4>
          <div className="space-y-0.5 max-h-80 overflow-auto">
            {data.pages.map((p: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 text-xs border-b border-gray-50 gap-2">
                <div className="min-w-0 flex-1">
                  <a href={p.url} target="_blank" rel="noopener noreferrer"
                    className="text-[var(--primary)] hover:underline truncate block">{p.title || p.url}</a>
                  {p.title && <p className="text-gray-400 truncate text-[10px]">{p.url}</p>}
                  {p.issues?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-0.5">
                      {p.issues.map((issue: string, j: number) => (
                        <span key={j} className="text-[10px] bg-red-50 text-red-600 px-1.5 py-0.5 rounded">{issue}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {p.date_modified ? (
                    <span className="text-gray-400 text-[10px]">{p.date_modified.slice(0, 10)}</span>
                  ) : p.date_published ? (
                    <span className="text-gray-400 text-[10px]">{p.date_published.slice(0, 10)}</span>
                  ) : null}
                  <span className={`px-2 py-0.5 rounded-full font-medium ${
                    p.freshness_status === "fresh" ? "bg-green-50 text-green-700" :
                    p.freshness_status === "aging" ? "bg-amber-50 text-amber-700" :
                    p.freshness_status === "outdated" ? "bg-red-50 text-red-700" :
                    "bg-gray-50 text-gray-500"
                  }`}>{p.freshness_status === "fresh" ? "Fresca" :
                       p.freshness_status === "aging" ? "Envejeciendo" :
                       p.freshness_status === "outdated" ? "Desactualizada" : "Sin fecha"}
                  {p.days_since_update >= 0 ? ` (${p.days_since_update}d)` : ""}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      <Suggestions items={data.suggestions} />
    </div>
  );
}

function CrawlabilityView({ data }: { data: any }) {
  if (!data) return <ErrorState />;
  const s = data.summary || {};
  const issues = data.issues || [];

  // Separate issues by category for better display
  const brokenLinks = issues.filter((i: any) => i.category === "broken_links");
  const imgIssues = issues.filter((i: any) => i.category === "accessibility");
  const seoIssues = issues.filter((i: any) => i.category === "seo");
  const indexIssues = issues.filter((i: any) => i.category === "indexability");
  const perfIssues = issues.filter((i: any) => i.category === "performance");
  const robotsIssues = issues.filter((i: any) => i.category === "robots_txt" || i.category === "ai_bots");
  const redirectIssues = issues.filter((i: any) => i.category === "redirects");

  // Aggregate image alt issues into one summary
  const totalImgsWithoutAlt = imgIssues.reduce((sum: number, i: any) => {
    const match = i.message?.match(/(\d+) imagen/);
    return sum + (match ? parseInt(match[1]) : 0);
  }, 0);

  return (
    <div className="space-y-5">
      <ToolHeader title="Crawlability" score={data.score} subtitle={`${data.pages_crawled || 0} paginas, ${data.crawl_time}s`} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Criticos" value={s.critical || 0} color="red" />
        <StatCard label="Advertencias" value={s.warnings || 0} color="yellow" />
        <StatCard label="Info" value={s.info || 0} color="blue" />
        <StatCard label="Enlaces rotos" value={s.broken_links || 0} color="red" />
      </div>

      {/* Broken Links — explicit URLs */}
      {brokenLinks.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Enlaces rotos ({brokenLinks.length})</h4>
          <div className="space-y-1">
            {brokenLinks.map((i: any, idx: number) => (
              <div key={idx} className="flex items-center gap-2 py-1.5 text-xs border-b border-gray-50">
                <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded font-mono font-bold shrink-0">
                  {i.message?.match(/HTTP (\d+)/)?.[1] || "ERR"}
                </span>
                <span className="truncate text-[var(--foreground)]">{i.url}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Images without alt — aggregated */}
      {totalImgsWithoutAlt > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Imagenes sin atributo alt</h4>
          <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 text-sm text-blue-700">
            <p className="font-medium">{totalImgsWithoutAlt} imagenes sin alt en {imgIssues.length} pagina{imgIssues.length !== 1 ? "s" : ""}</p>
            <p className="text-xs mt-1 opacity-80">Las imagenes sin alt son invisibles para los rastreadores de IA.</p>
          </div>
          <div className="mt-2 space-y-0.5 max-h-32 overflow-auto">
            {imgIssues.map((i: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between py-1 text-xs">
                <span className="truncate text-[var(--text-muted)]">{i.url}</span>
                <span className="shrink-0 ml-2 font-medium">{i.message?.match(/(\d+)/)?.[1] || "?"} imgs</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SEO Issues */}
      {seoIssues.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">SEO ({seoIssues.length})</h4>
          <div className="max-h-48 overflow-auto">{seoIssues.map((i: any, idx: number) => <IssueItem key={idx} issue={i} />)}</div>
        </div>
      )}

      {/* Indexability */}
      {indexIssues.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Indexabilidad ({indexIssues.length})</h4>
          <div className="max-h-48 overflow-auto">{indexIssues.map((i: any, idx: number) => <IssueItem key={idx} issue={i} />)}</div>
        </div>
      )}

      {/* Performance */}
      {perfIssues.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Rendimiento ({perfIssues.length})</h4>
          <div className="max-h-48 overflow-auto">{perfIssues.map((i: any, idx: number) => <IssueItem key={idx} issue={i} />)}</div>
        </div>
      )}

      {/* Robots & AI bots */}
      {robotsIssues.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Robots.txt / Bots IA ({robotsIssues.length})</h4>
          <div className="max-h-48 overflow-auto">{robotsIssues.map((i: any, idx: number) => <IssueItem key={idx} issue={i} />)}</div>
        </div>
      )}

      {/* Redirects */}
      {redirectIssues.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Redirecciones ({redirectIssues.length})</h4>
          <div className="max-h-48 overflow-auto">{redirectIssues.map((i: any, idx: number) => <IssueItem key={idx} issue={i} />)}</div>
        </div>
      )}
    </div>
  );
}

function RobotsSitemapView({ data }: { data: any }) {
  if (!data) return <ErrorState />;
  const r = data.robots || {};
  const sm = data.sitemap || {};
  const [showAllUrls, setShowAllUrls] = useState(false);
  const sitemapUrls = sm.urls || [];
  const visibleUrls = showAllUrls ? sitemapUrls : sitemapUrls.slice(0, 10);
  return (
    <div className="space-y-5">
      <ToolHeader title="Robots.txt & Sitemap" score={data.score} />
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Robots.txt" value={r.found ? "Encontrado" : "No encontrado"} color={r.found ? "green" : "red"} />
        <StatCard label="Sitemap" value={sm.found ? `${sm.urls_count} URLs` : "No encontrado"} color={sm.found ? "green" : "red"} />
      </div>

      {/* Sitemap link */}
      {sm.found && sm.url && (
        <div className="bg-green-50 border border-green-100 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-800">Sitemap encontrado</p>
              <p className="text-xs text-green-600 mt-0.5">{sm.urls_count} URLs indexadas {sm.is_index ? "(sitemap index)" : ""}</p>
            </div>
            <a href={sm.url} target="_blank" rel="noopener noreferrer"
              className="bg-white border border-green-200 px-3 py-1.5 rounded-lg text-xs font-medium text-green-700 hover:bg-green-50 shrink-0">
              Ver sitemap &rarr;
            </a>
          </div>
        </div>
      )}

      {/* Child sitemaps if index */}
      {sm.is_index && sm.child_sitemaps?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Sub-sitemaps ({sm.child_sitemaps.length})</h4>
          <div className="space-y-1 max-h-32 overflow-auto">
            {sm.child_sitemaps.map((url: string, i: number) => (
              <div key={i} className="flex items-center justify-between py-1 text-xs border-b border-gray-50">
                <a href={url} target="_blank" rel="noopener noreferrer" className="text-[var(--primary)] hover:underline truncate">{url}</a>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sitemap URLs list */}
      {sitemapUrls.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold text-sm">URLs en el sitemap ({sm.urls_count})</h4>
            {sitemapUrls.length > 10 && (
              <button onClick={() => setShowAllUrls(!showAllUrls)}
                className="text-xs text-[var(--primary)] hover:underline">
                {showAllUrls ? "Mostrar menos" : `Ver todas (${sitemapUrls.length})`}
              </button>
            )}
          </div>
          <div className={`space-y-0.5 ${showAllUrls ? "max-h-96" : "max-h-none"} overflow-auto`}>
            {visibleUrls.map((u: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-1.5 text-xs border-b border-gray-50 gap-2">
                <a href={u.loc} target="_blank" rel="noopener noreferrer"
                  className="text-[var(--primary)] hover:underline truncate min-w-0 flex-1">{u.loc}</a>
                <div className="flex items-center gap-2 shrink-0">
                  {u.lastmod && <span className="text-gray-400">{u.lastmod.slice(0, 10)}</span>}
                  {u.priority && <span className="text-gray-300">P:{u.priority}</span>}
                </div>
              </div>
            ))}
          </div>
          {!showAllUrls && sitemapUrls.length > 10 && (
            <p className="text-xs text-gray-400 mt-2">Mostrando 10 de {sitemapUrls.length} URLs</p>
          )}
        </div>
      )}

      {r.ai_bots?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Bots de IA</h4>
          <div className="space-y-1">
            {r.ai_bots.map((bot: any) => (
              <div key={bot.name} className="flex items-center justify-between py-1.5 text-xs border-b border-gray-50">
                <div>
                  <span className="font-medium">{bot.name}</span>
                  <span className="text-[var(--text-muted)] ml-2">{bot.engine}</span>
                </div>
                <StatusBadge allowed={bot.allowed} />
              </div>
            ))}
          </div>
        </div>
      )}
      <Suggestions items={r.suggestions} />
    </div>
  );
}

function AIPresenceView({ data }: { data: any }) {
  if (!data) return <ErrorState />;
  const engines = data.engine_results || [];
  const hasRealData = engines.length > 0;
  return (
    <div className="space-y-5">
      <ToolHeader title="AI Search Presence" score={data.score} subtitle={`Marca: ${data.brand_name}`} />

      {/* Real engine results */}
      {hasRealData && (
        <div>
          <h4 className="font-semibold text-sm mb-3">Presencia real en motores de IA</h4>
          <div className="space-y-3">
            {engines.map((eng: any, i: number) => (
              <div key={i} className={`border rounded-xl p-4 ${
                eng.mentioned || eng.domain_cited ? "border-green-200 bg-green-50/50" :
                eng.status === "error" ? "border-gray-200 bg-gray-50" : "border-red-200 bg-red-50/50"
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">{eng.engine}</span>
                    {eng.query_used && <span className="text-[10px] text-gray-400 italic">{eng.query_used.substring(0, 40)}...</span>}
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                    eng.mentioned || eng.domain_cited ? "bg-green-100 text-green-700" :
                    eng.status === "error" ? "bg-gray-100 text-gray-500" : "bg-red-100 text-red-700"
                  }`}>
                    {eng.mentioned ? "MENCIONADO" : eng.domain_cited ? "CITADO" :
                     eng.status === "error" ? "ERROR" : "NO ENCONTRADO"}
                  </span>
                </div>
                {eng.snippet && (
                  <p className="text-xs text-gray-600 bg-white/80 rounded p-2 mt-1 italic">&ldquo;{eng.snippet}&rdquo;</p>
                )}
                {eng.response_preview && !eng.snippet && (
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{eng.response_preview}</p>
                )}
                {eng.citations?.length > 0 && (
                  <div className="mt-2">
                    <span className="text-[10px] uppercase text-gray-400">Fuentes citadas:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {eng.citations.map((c: string, j: number) => (
                        <span key={j} className="text-[10px] bg-white border border-gray-200 px-1.5 py-0.5 rounded truncate max-w-xs">{c}</span>
                      ))}
                    </div>
                  </div>
                )}
                {eng.error && <p className="text-xs text-gray-400 mt-1">Error: {eng.error}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* On-page signals */}
      {data.signals?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Senales on-page</h4>
          <div className="space-y-1">
            {data.signals.map((s: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 text-xs border-b border-gray-50">
                <div className="min-w-0 flex-1">
                  <span className="font-medium">{s.name}</span>
                  <span className="text-[var(--text-muted)] ml-2">{s.details}</span>
                </div>
                <span className={`px-2 py-0.5 rounded-full font-medium shrink-0 ml-2 ${
                  s.status === "pass" ? "bg-green-50 text-green-700" :
                  s.status === "warning" ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700"
                }`}>{s.status === "pass" ? "OK" : s.status === "warning" ? "Mejorar" : "Falta"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <Suggestions items={data.suggestions} />
    </div>
  );
}

function CitationsView({ data }: { data: any }) {
  if (!data) return <ErrorState />;
  const cited = data.cited_sources || {};
  return (
    <div className="space-y-5">
      <ToolHeader title="AI Citation Tracker" score={data.score} subtitle={`${data.pages_analyzed || 0} paginas, ${data.topics?.length || 0} topics`} />

      {/* Per-engine scores */}
      {data.engine_scores?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-3">Presencia por motor de IA</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {data.engine_scores.map((es: any) => (
              <div key={es.engine} className="bg-white border border-gray-100 rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-sm">{es.engine}</span>
                  <span className={`text-lg font-bold ${
                    es.score >= 60 ? "text-green-600" : es.score >= 35 ? "text-amber-600" : "text-red-500"
                  }`}>{es.score}</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2 mb-3">
                  <div className={`h-2 rounded-full ${
                    es.score >= 60 ? "bg-green-500" : es.score >= 35 ? "bg-amber-500" : "bg-red-400"
                  }`} style={{ width: `${es.score}%` }} />
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-400">Mencion</span>
                    <p className="font-bold">{es.mention_rate}% <span className="font-normal text-gray-400">({es.mentioned_count}/{es.queries_tested})</span></p>
                  </div>
                  <div>
                    <span className="text-gray-400">Citacion</span>
                    <p className="font-bold">{es.cite_rate}% <span className="font-normal text-gray-400">({es.cited_count}/{es.queries_tested})</span></p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Citation results per query */}
      {data.citation_results?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Resultados por consulta</h4>
          <div className="space-y-2 max-h-96 overflow-auto">
            {data.citation_results.map((cr: any, i: number) => (
              <div key={i} className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-mono text-xs font-medium">{cr.query}</span>
                  <span className="text-[10px] uppercase bg-white border border-gray-200 px-1.5 py-0.5 rounded text-gray-400">{cr.type}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {cr.engines?.map((eng: any, j: number) => (
                    <span key={j} className={`px-2 py-1 rounded text-[11px] font-medium ${
                      eng.mentioned || eng.cited ? "bg-green-100 text-green-700" :
                      eng.error ? "bg-gray-100 text-gray-400" : "bg-red-100 text-red-600"
                    }`}>
                      {eng.engine}: {eng.cited ? "Citado" : eng.mentioned ? "Mencionado" : eng.error ? "Error" : "No"}
                    </span>
                  ))}
                </div>
                {cr.engines?.some((e: any) => e.snippet) && (
                  <p className="text-xs text-gray-500 mt-1 italic line-clamp-1">
                    {cr.engines.find((e: any) => e.snippet)?.snippet}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Competitor sources */}
      {cited.competitor_sources?.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold text-sm">Fuentes citadas junto a ti</h4>
            <span className="text-xs text-gray-400">Tu dominio citado {cited.our_citation_count} veces</span>
          </div>
          <div className="space-y-1">
            {cited.competitor_sources.map((cs: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-1.5 text-xs border-b border-gray-50">
                <span className="text-gray-700">{cs.domain}</span>
                <span className="text-gray-400">{cs.count} citas</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <Suggestions items={data.suggestions} />
    </div>
  );
}

function AlertsView({ data }: { data: any }) {
  if (!data) return <ErrorState />;
  const aiMentions = data.ai_mentions || [];
  const serpMentions = data.serp_mentions || [];
  return (
    <div className="space-y-5">
      <ToolHeader title="Monitoreo de Marca" score={data.score} subtitle={`Marca: ${data.brand}`} />

      {/* Real AI mentions */}
      {aiMentions.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-3">Menciones reales en motores de IA</h4>
          <div className="space-y-2">
            {aiMentions.map((m: any, i: number) => (
              <div key={i} className={`border rounded-lg p-3 ${
                m.mentioned || m.domain_cited ? "border-green-200 bg-green-50/50" :
                m.error ? "border-gray-200 bg-gray-50" : "border-red-200 bg-red-50/50"
              }`}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs">{m.engine}</span>
                    <span className="text-[10px] bg-white border border-gray-200 px-1.5 py-0.5 rounded text-gray-400">{m.query_type}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    m.mentioned || m.domain_cited ? "bg-green-100 text-green-700" :
                    m.error ? "bg-gray-100 text-gray-500" : "bg-red-100 text-red-700"
                  }`}>
                    {m.mentioned ? "MENCIONADO" : m.domain_cited ? "CITADO" : m.error ? "ERROR" : "NO ENCONTRADO"}
                  </span>
                </div>
                <p className="text-[10px] text-gray-400 mb-1">{m.query}</p>
                {m.snippet && <p className="text-xs text-gray-600 italic">&ldquo;{m.snippet}&rdquo;</p>}
                {m.error && <p className="text-[10px] text-gray-400">{m.error}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SERP mentions */}
      {serpMentions.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Menciones en Google</h4>
          <div className="space-y-2">
            {serpMentions.map((sm: any, i: number) => (
              <div key={i} className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs font-mono font-medium mb-1">{sm.query}</p>
                {sm.error ? (
                  <p className="text-[10px] text-gray-400">{sm.error}</p>
                ) : (
                  <>
                    <p className="text-[10px] text-gray-400 mb-1">{sm.total_results} resultados</p>
                    {sm.results?.map((r: any, j: number) => (
                      <div key={j} className="py-1 text-xs border-b border-gray-100 last:border-0">
                        <a href={r.link} target="_blank" rel="noopener noreferrer"
                          className="text-[var(--primary)] hover:underline font-medium">{r.title}</a>
                        {r.snippet && <p className="text-gray-400 text-[10px] line-clamp-1">{r.snippet}</p>}
                      </div>
                    ))}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Visibility signals */}
      {data.visibility_signals?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Senales de visibilidad</h4>
          <div className="space-y-1">
            {data.visibility_signals.map((s: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 text-xs border-b border-gray-50">
                <div>
                  <span className="font-medium">{s.name}</span>
                  <span className="text-gray-400 ml-2">{s.detail}</span>
                </div>
                <span className={`px-2 py-0.5 rounded-full font-medium shrink-0 ${
                  s.status === "pass" ? "bg-green-50 text-green-700" :
                  s.status === "warning" ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700"
                }`}>{s.status === "pass" ? "OK" : s.status === "warning" ? "Mejorar" : "Falta"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Monitoring config */}
      {data.channels?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Canales de monitoreo</h4>
          <div className="space-y-1">
            {data.channels.map((ch: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 text-xs border-b border-gray-50">
                <div>
                  <span className="font-medium">{ch.name}</span>
                  <span className="text-gray-400 ml-2">{ch.description}</span>
                </div>
                {ch.setup_url && (
                  <a href={ch.setup_url} target="_blank" rel="noopener noreferrer"
                    className="text-[var(--primary)] hover:underline shrink-0">Configurar &rarr;</a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {data.alert_rules?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Reglas de alerta</h4>
          {data.alert_rules.map((r: any, i: number) => (
            <div key={i} className="flex items-center justify-between py-2 text-xs border-b border-gray-50">
              <div><span className="font-medium">{r.name}</span> - {r.trigger}</div>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                r.priority === "critica" ? "bg-red-50 text-red-700" :
                r.priority === "alta" ? "bg-amber-50 text-amber-700" : "bg-blue-50 text-blue-700"
              }`}>{r.frequency}</span>
            </div>
          ))}
        </div>
      )}

      <Suggestions items={data.suggestions} />
    </div>
  );
}

function AIOverviewView({ data }: { data: any }) {
  if (!data) return <ErrorState />;
  const imp = data.impact || {};
  const serpResults = data.serp_results || [];
  const hasSerp = !imp.no_api_key;
  return (
    <div className="space-y-5">
      <ToolHeader title="AI Overview Impact" score={data.score} subtitle={`${data.queries_tested || 0} consultas, ${data.pages_analyzed || 0} paginas`} />

      {/* Impact summary */}
      {hasSerp ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="AI Overview rate" value={`${imp.ai_overview_rate || 0}%`} color={imp.ai_overview_rate > 50 ? "red" : imp.ai_overview_rate > 0 ? "yellow" : "green"} />
          <StatCard label="Citado en AIO" value={imp.domain_in_ai_overview || 0} color={imp.domain_in_ai_overview > 0 ? "green" : "red"} />
          <StatCard label="En organicos" value={`${imp.organic_presence_rate || 0}%`} color={imp.organic_presence_rate > 50 ? "green" : "yellow"} />
          <StatCard label="Pos. promedio" value={imp.avg_organic_position || "—"} color={imp.avg_organic_position && imp.avg_organic_position <= 5 ? "green" : "yellow"} />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <StatCard label="Keywords extraidas" value={data.total_keywords || 0} />
          <StatCard label="Consultas generadas" value={serpResults.length} />
        </div>
      )}

      {/* SERP results per query */}
      {serpResults.length > 0 && hasSerp && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Resultados SERP por consulta</h4>
          <div className="space-y-2 max-h-[500px] overflow-auto">
            {serpResults.map((sr: any, i: number) => (
              <div key={i} className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-medium">{sr.query}</span>
                    <span className="text-[10px] uppercase bg-white border border-gray-200 px-1.5 py-0.5 rounded text-gray-400">{sr.type}</span>
                  </div>
                  {sr.error ? (
                    <span className="text-[10px] text-gray-400">Error</span>
                  ) : (
                    <div className="flex items-center gap-2">
                      {sr.has_ai_overview && (
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          sr.domain_in_ai_overview ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
                        }`}>
                          AIO {sr.domain_in_ai_overview ? "— CITADO" : "— sin citar"}
                        </span>
                      )}
                      {!sr.has_ai_overview && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-500">Sin AIO</span>
                      )}
                      {sr.organic_position && (
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          sr.organic_position <= 3 ? "bg-green-100 text-green-700" :
                          sr.organic_position <= 10 ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-500"
                        }`}>
                          #{sr.organic_position}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {sr.ai_overview_preview && (
                  <p className="text-xs text-gray-500 bg-white/80 rounded p-2 mb-2 line-clamp-2 italic">{sr.ai_overview_preview}</p>
                )}

                {sr.top_results?.length > 0 && (
                  <div className="space-y-0.5">
                    {sr.top_results.map((tr: any, j: number) => (
                      <div key={j} className="flex items-center gap-2 text-[11px] py-0.5">
                        <span className={`w-5 text-center font-bold ${
                          sr.domain_in_organic && tr.domain && data.domain && tr.domain.includes(data.domain)
                            ? "text-green-600" : "text-gray-300"
                        }`}>{tr.position}</span>
                        <span className={`truncate ${
                          tr.domain && data.domain && tr.domain.includes(data.domain) ? "text-green-700 font-semibold" : "text-gray-600"
                        }`}>{tr.title}</span>
                        <span className="text-gray-300 shrink-0 text-[10px]">{tr.domain}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <Suggestions items={data.suggestions} />
    </div>
  );
}

function DuplicatesView({ data }: { data: any }) {
  if (!data) return <ErrorState />;
  const s = data.summary || {};
  return (
    <div className="space-y-5">
      <ToolHeader title="Contenido Duplicado" score={data.score} subtitle={`${data.pages_analyzed || 0} paginas analizadas`} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Paginas unicas" value={`${s.uniqueness_pct || 0}%`} color="green" />
        <StatCard label="Duplicados exactos" value={s.exact_duplicates || 0} color="red" />
        <StatCard label="Pares similares" value={s.similar_pairs || 0} color="yellow" />
        <StatCard label="Promedio palabras" value={s.avg_words_per_page || 0} />
      </div>
      {data.duplicates?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Duplicados exactos</h4>
          {data.duplicates.map((d: any, i: number) => (
            <div key={i} className="bg-red-50 p-3 rounded-lg mb-2 text-xs">
              <p className="font-medium text-red-700">{d.count} paginas con contenido identico:</p>
              {d.urls.map((u: string, j: number) => <p key={j} className="text-red-600 truncate">{u}</p>)}
            </div>
          ))}
        </div>
      )}
      {data.similar_pages?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-2">Paginas similares</h4>
          <div className="space-y-1 max-h-48 overflow-auto">
            {data.similar_pages.slice(0, 10).map((sp: any, i: number) => (
              <div key={i} className="py-2 text-xs border-b border-gray-50">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{sp.similarity_pct}% similar</span>
                </div>
                <p className="text-[var(--text-muted)] truncate">{sp.url_a}</p>
                <p className="text-[var(--text-muted)] truncate">{sp.url_b}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      <Suggestions items={data.suggestions} />
    </div>
  );
}

/* ──── Actions View ──── */

const TOOL_LABELS: Record<string, string> = {
  crawlability: "Crawlability",
  robots_sitemap: "Robots & Sitemap",
  schema: "Schema",
  axp: "AXP",
  ai_presence: "AI Presence",
  citations: "Citations",
  freshness: "Freshness",
  ai_overview: "AI Overview",
  duplicates: "Duplicados",
  alerts: "Alerts",
};

const PRIORITY_ORDER: Record<string, number> = {
  critica: 0, alta: 1, media: 2, baja: 3, info: 4,
};

function ActionsView({ data }: { data: any }) {
  // Collect all suggestions from all tools
  const allActions: { priority: string; message: string; detail?: string; source: string; score: number }[] = [];

  const toolKeys = Object.keys(TOOL_LABELS);
  for (const key of toolKeys) {
    const toolData = data[key];
    if (!toolData || toolData.error) continue;

    const score = toolData.score ?? 0;
    const suggestions = toolData.suggestions || [];

    for (const s of suggestions) {
      allActions.push({
        priority: s.priority || "info",
        message: s.message || "",
        detail: s.detail,
        source: TOOL_LABELS[key] || key,
        score,
      });
    }

    // Also add issues from crawlability as actions
    if (key === "crawlability" && toolData.issues) {
      const critical = toolData.issues.filter((i: any) => i.severity === "critical");
      if (critical.length > 0) {
        allActions.push({
          priority: "critica",
          message: `${critical.length} problema(s) critico(s) de crawlability encontrado(s)`,
          detail: critical.map((i: any) => i.message).join(". "),
          source: "Crawlability",
          score,
        });
      }
    }
  }

  // Sort by priority (critica first)
  allActions.sort((a, b) => (PRIORITY_ORDER[a.priority] ?? 5) - (PRIORITY_ORDER[b.priority] ?? 5));

  const priorityStyles: Record<string, { bg: string; text: string; border: string; label: string }> = {
    critica: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", label: "CRITICO" },
    alta: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200", label: "ALTA" },
    media: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200", label: "MEDIA" },
    baja: { bg: "bg-gray-50", text: "text-gray-600", border: "border-gray-200", label: "BAJA" },
    info: { bg: "bg-green-50", text: "text-green-700", border: "border-green-200", label: "INFO" },
  };

  return (
    <div className="space-y-5">
      <div className="pb-4 border-b border-gray-100">
        <h3 className="text-xl font-bold">Acciones a Ejecutar</h3>
        <p className="text-sm text-[var(--text-muted)] mt-0.5">
          {allActions.length} acciones ordenadas por prioridad. Empieza por las criticas.
        </p>
      </div>

      {/* Summary counts */}
      <div className="flex gap-3 flex-wrap">
        {["critica", "alta", "media", "baja", "info"].map((p) => {
          const count = allActions.filter((a) => a.priority === p).length;
          if (count === 0) return null;
          const s = priorityStyles[p];
          return (
            <span key={p} className={`${s.bg} ${s.text} ${s.border} border px-3 py-1 rounded-lg text-xs font-bold`}>
              {s.label}: {count}
            </span>
          );
        })}
      </div>

      {/* Action list */}
      <div className="space-y-2">
        {allActions.map((action, i) => {
          const s = priorityStyles[action.priority] || priorityStyles.info;
          return (
            <div key={i} className={`${s.bg} ${s.border} border rounded-xl p-4`}>
              <div className="flex items-start gap-3">
                <span className="text-base mt-0.5">
                  {action.priority === "critica" || action.priority === "alta" ? "●" : "○"}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-bold uppercase ${s.text}`}>{s.label}</span>
                    <span className="text-[10px] text-[var(--text-muted)] bg-white px-1.5 py-0.5 rounded">{action.source}</span>
                  </div>
                  <p className={`text-sm font-medium ${s.text}`}>{action.message}</p>
                  {action.detail && <p className="text-xs mt-1 opacity-80">{action.detail}</p>}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {allActions.length === 0 && (
        <div className="text-center py-12 text-[var(--text-muted)]">No hay acciones pendientes.</div>
      )}
    </div>
  );
}

/* ──── Shared sub-components ──── */

function ToolHeader({ title, score, subtitle }: { title: string; score?: number; subtitle?: string }) {
  return (
    <div className="flex items-center justify-between pb-4 border-b border-gray-100">
      <div>
        <h3 className="text-xl font-bold">{title}</h3>
        {subtitle && <p className="text-sm text-[var(--text-muted)] mt-0.5">{subtitle}</p>}
      </div>
      {score !== undefined && <ScoreCircle score={score} size="sm" />}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  const colors: Record<string, { text: string; bg: string; border: string }> = {
    green: { text: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-100" },
    red: { text: "text-red-700", bg: "bg-red-50", border: "border-red-100" },
    yellow: { text: "text-amber-700", bg: "bg-amber-50", border: "border-amber-100" },
    blue: { text: "text-blue-700", bg: "bg-blue-50", border: "border-blue-100" },
  };
  const c = color ? colors[color] : null;
  return (
    <div className={`rounded-xl p-4 border ${c ? `${c.bg} ${c.border}` : "bg-gray-50 border-gray-100"}`}>
      <p className="text-xs text-[var(--text-muted)] mb-1">{label}</p>
      <p className={`text-xl font-bold ${c ? c.text : "text-foreground"}`}>{value}</p>
    </div>
  );
}

function Suggestions({ items }: { items?: any[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <h4 className="font-semibold text-sm mb-2">Sugerencias</h4>
      <div className="space-y-2">{items.map((s, i) => <SuggestionItem key={i} suggestion={s} />)}</div>
    </div>
  );
}

function Issues({ items }: { items?: any[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <h4 className="font-semibold text-sm mb-2">Problemas ({items.length})</h4>
      <div className="max-h-48 overflow-auto">{items.map((issue, i) => <IssueItem key={i} issue={issue} />)}</div>
    </div>
  );
}

function ErrorState() {
  return <div className="text-center py-12 text-[var(--text-muted)]">Error al cargar datos de esta herramienta.</div>;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}
