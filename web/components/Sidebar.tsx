"use client";

export function Sidebar({
  dark,
  onToggleDark,
}: {
  dark: boolean;
  onToggleDark: () => void;
}) {
  return (
    <aside className="flex flex-col justify-between w-[210px] flex-none bg-surface border border-line rounded-xl2 p-4">
      <div>
        <div className="flex items-center gap-2.5 px-1 mb-6">
          <Mark />
          <div>
            <div className="font-serif font-semibold text-[19px] leading-none">
              Qarar
            </div>
            <div className="font-arabic text-[12px] text-goldDeep leading-none mt-1">
              قرار
            </div>
          </div>
        </div>

        <nav className="flex flex-col gap-1">
          <div className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-left font-sans text-[13px] bg-goldTint text-goldDeep border border-gold">
            <span className="text-goldDeep">
              <ChatIcon />
            </span>
            Copilot
          </div>
        </nav>
      </div>

      <div className="flex flex-col gap-3">
        <div className="font-mono text-[10px] text-ink3 px-1 leading-relaxed">
          Abu Dhabi · decision intelligence
        </div>
        <button
          onClick={onToggleDark}
          className="flex items-center gap-2 font-mono text-[11px] text-ink2 border border-line rounded-md px-2.5 py-1.5 hover:border-gold hover:text-goldDeep transition-colors text-left"
        >
          <span className="text-ink3">{dark ? <SunIcon /> : <MoonIcon />}</span>
          {dark ? "Light mode" : "Dark mode"}
        </button>
      </div>
    </aside>
  );
}

function Mark() {
  return (
    <span className="relative w-[28px] h-[28px] rounded-[7px] border-[2.4px] border-ink flex-none">
      <span className="absolute left-[58%] top-[12%] w-[36%] h-[36%] bg-gold rotate-45" />
    </span>
  );
}

function MoonIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path
        d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M19.1 4.9l-1.8 1.8M6.7 17.3l-1.8 1.8"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path
        d="M4 5h16v11H8l-4 3V5z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

