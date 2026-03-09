"use client";

import { useState, useEffect, useCallback } from "react";
import Navbar from "@/components/Navbar";
import Dashboard from "@/components/Dashboard";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  /* eslint-disable @typescript-eslint/no-explicit-any */
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [url, setUrl] = useState("");
  const [history, setHistory] = useState<any[]>([]);

  const fetchHistory = useCallback(async () => {
    try {
      const resp = await fetch(`${API_URL}/api/history?limit=10`);
      if (resp.ok) {
        const items = await resp.json();
        setHistory(items);
      }
    } catch {
      // History not critical
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const loadPastAnalysis = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_URL}/api/history/${id}`);
      if (resp.ok) {
        const item = await resp.json();
        setData(item.results);
      }
    } catch {
      setError("Error al cargar analisis");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async (inputUrl: string) => {
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const resp = await fetch(`${API_URL}/api/analyze-all`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: inputUrl }),
      });
      if (!resp.ok) {
        const d = await resp.json();
        throw new Error(d.detail || "Error al analizar");
      }
      const result = await resp.json();
      setData(result);
      fetchHistory(); // Refresh history after new analysis
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de conexion");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) handleAnalyze(url.trim());
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        {!data && !loading && (
          <section className="flex flex-col items-center justify-center px-4 pt-20 pb-16">
            <p className="text-[var(--primary)] font-semibold text-sm tracking-wide uppercase mb-4">
              10 Herramientas Gratuitas
            </p>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-center leading-tight mb-4 max-w-3xl">
              Tu sitio, listo para los{" "}
              <span className="relative inline-block">
                <span className="relative z-10">motores de IA</span>
                <span className="absolute bottom-1 left-0 w-full h-3 bg-[var(--primary)]/20 rounded-sm" />
              </span>
              ?
            </h1>
            <p className="text-[var(--text-muted)] text-lg text-center max-w-xl mb-10">
              Analiza tu sitio con 10 herramientas de AEO en una sola busqueda.
              Schema, robots.txt, sitemap, presencia en IA, contenido duplicado y mas.
            </p>

            <form onSubmit={handleSubmit} className="w-full max-w-xl mb-6">
              <div className="bg-white rounded-full shadow-lg flex items-center p-2 pl-5 gap-2">
                <svg className="w-5 h-5 text-[var(--text-muted)] shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" /><path d="M2 12h20" />
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                </svg>
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://tusitio.com"
                  className="flex-1 outline-none text-base bg-transparent placeholder:text-gray-400"
                />
                <button type="submit" className="bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white font-semibold px-6 py-3 rounded-full transition-colors text-sm whitespace-nowrap cursor-pointer">
                  Analizar todo
                </button>
              </div>
            </form>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm max-w-xl w-full text-center">
                {error}
              </div>
            )}

            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 max-w-3xl w-full mt-12">
              {[
                "Crawlability", "Robots & Sitemap", "Schema", "AXP", "AI Presence",
                "Citations", "Alerts", "Freshness", "AI Overview", "Duplicados",
              ].map((name, i) => (
                <div key={name} className="bg-white rounded-xl p-3 shadow-sm flex items-center gap-2">
                  <span className="w-5 h-5 rounded-md bg-primary/10 text-primary text-[10px] font-bold flex items-center justify-center shrink-0">{i + 1}</span>
                  <p className="text-xs font-medium text-[var(--text-muted)]">{name}</p>
                </div>
              ))}
            </div>

            {/* Recent analyses history */}
            {history.length > 0 && (
              <div className="w-full max-w-xl mt-12">
                <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">Analisis recientes</h3>
                <div className="bg-white rounded-xl shadow-sm divide-y divide-gray-50">
                  {history.map((item: any) => (
                    <button
                      key={item.id}
                      onClick={() => loadPastAnalysis(item.id)}
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors text-left cursor-pointer"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">{item.domain}</p>
                        <p className="text-[10px] text-gray-400">{new Date(item.created_at).toLocaleString()}</p>
                      </div>
                      <div className={`text-sm font-bold shrink-0 ml-3 ${
                        item.overall_score >= 70 ? "text-green-600" :
                        item.overall_score >= 40 ? "text-amber-600" : "text-red-500"
                      }`}>{item.overall_score}/100</div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {loading && (
          <section className="flex flex-col items-center justify-center px-4 pt-32 pb-16">
            <div className="relative mb-8">
              <div className="w-20 h-20 rounded-full border-4 border-[var(--primary)]/20" />
              <div className="absolute inset-0 w-20 h-20 rounded-full border-4 border-transparent border-t-[var(--primary)] animate-spin-slow" />
            </div>
            <h2 className="text-2xl font-bold mb-3">Analizando tu sitio...</h2>
            <p className="text-[var(--text-muted)] text-center max-w-md mb-8">
              Ejecutando 10 herramientas. Esto puede tomar entre 30 y 60 segundos.
            </p>
            <div className="flex flex-col gap-2 w-full max-w-sm">
              {["Crawlability", "Robots & Sitemap", "Schema", "AXP", "AI Presence",
                "Citations", "Alerts", "Freshness", "AI Overview", "Duplicados"].map((step, i) => (
                <div key={step} className="flex items-center gap-3 animate-fade-in-up" style={{ animationDelay: `${i * 0.15}s`, opacity: 0 }}>
                  <div className="w-2 h-2 bg-[var(--primary)] rounded-full animate-pulse" />
                  <span className="text-sm text-[var(--text-muted)]">{step}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {data && (
          <Dashboard
            data={data}
            onReset={() => { setData(null); setError(null); }}
          />
        )}
      </main>

      <footer className="py-6 text-center">
        <p className="text-xs text-[var(--text-muted)]">
          Herramienta gratuita de <span className="font-semibold text-[var(--foreground)]">Cleexs</span> &middot; 10 analisis AEO en uno
        </p>
      </footer>
    </div>
  );
}
