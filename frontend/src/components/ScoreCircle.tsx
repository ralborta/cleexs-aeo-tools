interface Props {
  score: number;
  size?: "sm" | "md" | "lg";
}

export default function ScoreCircle({ score, size = "md" }: Props) {
  const sizes = { sm: 80, md: 128, lg: 160 };
  const s = sizes[size];
  const radius = (s / 2) - 10;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const getColor = () => {
    if (score >= 80) return "var(--success)";
    if (score >= 50) return "var(--warning)";
    return "var(--critical)";
  };

  const getLabel = () => {
    if (score >= 80) return "Excelente";
    if (score >= 60) return "Bueno";
    if (score >= 40) return "Regular";
    return "Critico";
  };

  const textSize = size === "sm" ? "text-xl" : size === "lg" ? "text-4xl" : "text-3xl";
  const subSize = size === "sm" ? "text-[10px]" : "text-xs";

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: s, height: s }}>
        <svg className="-rotate-90" style={{ width: s, height: s }} viewBox={`0 0 ${s} ${s}`}>
          <circle cx={s / 2} cy={s / 2} r={radius} fill="none" stroke="#E5E7EB" strokeWidth="8" />
          <circle
            cx={s / 2} cy={s / 2} r={radius} fill="none"
            stroke={getColor()} strokeWidth="8" strokeLinecap="round"
            strokeDasharray={circumference} strokeDashoffset={offset}
            className="animate-score-fill"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${textSize} font-extrabold`} style={{ color: getColor() }}>{score}</span>
          <span className={`${subSize} text-[var(--text-muted)]`}>/ 100</span>
        </div>
      </div>
      <span className="mt-1 text-sm font-semibold" style={{ color: getColor() }}>{getLabel()}</span>
    </div>
  );
}
