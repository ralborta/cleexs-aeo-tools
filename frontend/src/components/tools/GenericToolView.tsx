/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import ScoreCircle from "../ScoreCircle";

interface Props {
  title: string;
  description: string;
  data: any;
  score: number;
}

export default function GenericToolView({ title, description, data, score }: Props) {
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-6">
        <ScoreCircle score={score} size="sm" />
        <div>
          <h3 className="text-lg font-bold">{title}</h3>
          <p className="text-sm text-[var(--text-muted)]">{description}</p>
        </div>
      </div>

      {/* Suggestions */}
      {data.suggestions && data.suggestions.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-3">Sugerencias</h4>
          <div className="space-y-2">
            {data.suggestions.map((s: any, i: number) => (
              <SuggestionItem key={i} suggestion={s} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function SuggestionItem({ suggestion: s }: { suggestion: any }) {
  const priorityStyles: Record<string, string> = {
    critica: "bg-red-50 text-red-700 border-red-200",
    alta: "bg-amber-50 text-amber-700 border-amber-200",
    media: "bg-blue-50 text-blue-700 border-blue-200",
    baja: "bg-gray-50 text-gray-600 border-gray-200",
    info: "bg-green-50 text-green-700 border-green-200",
  };

  return (
    <div className={`p-3 rounded-lg border text-sm ${priorityStyles[s.priority] || priorityStyles.info}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs font-semibold uppercase">{s.priority}</span>
      </div>
      <p className="font-medium">{s.message}</p>
      {s.detail && <p className="text-xs mt-1 opacity-80">{s.detail}</p>}
      {s.action && <p className="text-xs mt-1 font-medium">Accion: {s.action}</p>}
    </div>
  );
}

export function StatusBadge({ allowed }: { allowed: boolean }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
      allowed ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
    }`}>
      {allowed ? "Permitido" : "Bloqueado"}
    </span>
  );
}

export function IssueItem({ issue }: { issue: any }) {
  const dot = issue.severity === "critical" ? "bg-red-500" : issue.severity === "warning" ? "bg-amber-500" : "bg-blue-500";
  return (
    <div className="flex items-start gap-2 py-2">
      <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${dot}`} />
      <div className="min-w-0">
        <p className="text-sm">{issue.message}</p>
        {issue.url && <p className="text-xs text-[var(--primary)] truncate">{issue.url}</p>}
        {issue.details && <p className="text-xs text-[var(--text-muted)]">{issue.details}</p>}
      </div>
    </div>
  );
}
