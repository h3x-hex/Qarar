"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { CopilotView } from "@/components/CopilotView";

export default function Home() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  return (
    <main className="h-screen bg-bg text-ink p-4 flex gap-4 max-w-[1440px] mx-auto">
      <Sidebar dark={dark} onToggleDark={() => setDark((d) => !d)} />
      <section className="flex-1 min-w-0 h-full overflow-hidden">
        <CopilotView dark={dark} />
      </section>
    </main>
  );
}
