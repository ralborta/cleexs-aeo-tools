interface Props {
  label: string;
  score?: number;
  status: "idle" | "loading" | "done" | "error";
  active: boolean;
  onClick: () => void;
}

export default function ToolCard({ label, score, status, active, onClick }: Props) {
  const getScoreColor = () => {
    if (score === undefined) return "";
    if (score >= 80) return "text-[var(--success)]";
    if (score >= 50) return "text-[var(--warning)]";
    return "text-[var(--critical)]";
  };

  return (
    <button
      onClick={onClick}
      className={`text-left px-3 py-2.5 rounded-xl text-xs font-medium transition-all cursor-pointer flex items-center justify-between gap-2 ${
        active
          ? "bg-[var(--primary)] text-white shadow-md"
          : "bg-white text-[var(--foreground)] hover:bg-gray-50 shadow-sm"
      }`}
    >
      <span className="truncate">{label}</span>
      {status === "loading" && (
        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin shrink-0" />
      )}
      {status === "done" && score !== undefined && (
        <span className={`font-bold text-xs ${active ? "text-white" : getScoreColor()}`}>
          {score}
        </span>
      )}
      {status === "error" && (
        <span className="text-red-400 text-xs">!</span>
      )}
    </button>
  );
}
