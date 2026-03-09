export default function Navbar() {
  return (
    <header className="w-full flex justify-center pt-6 px-4 relative z-50">
      <nav className="bg-white rounded-2xl shadow-sm px-6 py-3 flex items-center justify-center gap-2">
        <div className="w-8 h-8 bg-[var(--primary)] rounded-lg flex items-center justify-center">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18" /><path d="M9 21V9" />
          </svg>
        </div>
        <span className="font-bold text-lg tracking-tight">Cleexs</span>
        <span className="text-xs text-[var(--text-muted)] ml-1 border-l border-gray-200 pl-2">
          AEO Toolkit
        </span>
      </nav>
    </header>
  );
}
