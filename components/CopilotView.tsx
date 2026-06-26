"use client";

import { useEffect, useRef, useState } from "react";
import { ResponseCard } from "./ResponseCard";
import { ChoroplethMap } from "./ChoroplethMap";
import {
  fetchAnswer,
  fetchDistricts,
  HERO_QUESTION,
  SUGGESTED_QUERIES,
} from "@/lib/api";
import type { Brief } from "@/lib/types";

type Msg =
  | { role: "user"; text: string }
  | { role: "assistant"; brief: Brief }
  | { role: "assistant"; error: string };

export function CopilotView({ dark }: { dark: boolean }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [pending, setPending] = useState(false);
  const [input, setInput] = useState("");
  const [activeBrief, setActiveBrief] = useState<Brief | null>(null);
  const [districts, setDistricts] = useState<string[]>([]);

  // map filters
  const [mapLayer, setMapLayer] = useState("unmet_demand");
  const [mapYear, setMapYear] = useState(2026);
  const [districtFilter, setDistrictFilter] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchDistricts()
      .then(setDistricts)
      .catch(() => setDistricts([]));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, pending]);

  async function ask(question: string) {
    const display = question.trim();
    if (!display || pending) return;

    // the active district filter scopes the question for the agent
    let apiQuestion = display;
    if (
      districtFilter &&
      !display.toLowerCase().includes(districtFilter.toLowerCase())
    ) {
      apiQuestion = `${display} in ${districtFilter}`;
    }

    setInput("");
    setMessages((m) => [...m, { role: "user", text: display }]);
    setPending(true);
    try {
      const brief = await fetchAnswer(apiQuestion);
      setMessages((m) => [...m, { role: "assistant", brief }]);
      setActiveBrief(brief);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          error:
            "Could not reach the Qarar API. Start it with: uvicorn api:app --app-dir qarar --port 8000",
        },
      ]);
    } finally {
      setPending(false);
    }
  }

  // explicit district filter wins; otherwise the active reply drives the map
  const highlight = districtFilter ?? activeBrief?.district ?? null;
  const amenities = activeBrief?.map_layers.amenities ?? [];
  const isEmpty = messages.length === 0 && !pending;

  const inputBar = (
    <div className="flex items-center gap-3 bg-surface border border-line rounded-xl2 px-4 py-2.5 focus-within:border-gold transition-colors">
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") ask(input);
        }}
        placeholder={HERO_QUESTION}
        className="flex-1 bg-transparent outline-none font-sans text-sm text-ink placeholder:text-ink3"
      />
      <button
        onClick={() => ask(input)}
        disabled={pending}
        className="font-mono text-xs font-medium bg-gold text-onGold rounded-lg px-4 py-2 disabled:opacity-60 hover:opacity-90 transition-opacity"
      >
        {pending ? "Analyzing…" : "↵ Ask"}
      </button>
    </div>
  );

  return (
    <div className="h-full grid grid-rows-[260px_1fr] lg:grid-rows-1 lg:grid-cols-[1.1fr_1fr] gap-4">
      {/* persistent map with filters on top */}
      <div className="min-h-0">
        <ChoroplethMap
          layer={mapLayer}
          year={mapYear}
          highlightDistrict={highlight}
          parcelPin={activeBrief?.map_layers.parcel_pin ?? null}
          recommendedParcel={activeBrief?.recommended_parcel ?? null}
          amenities={amenities}
          dark={dark}
          showControls
          onLayerChange={setMapLayer}
          onYearChange={setMapYear}
          districts={districts}
          selectedDistrict={districtFilter}
          onDistrictChange={setDistrictFilter}
          onResetFilters={() => {
            setMapLayer("unmet_demand");
            setMapYear(2026);
            setDistrictFilter(null);
          }}
          onAskQuestion={ask}
        />
      </div>

      {/* chat thread */}
      <div className="flex flex-col h-full min-h-0">
        {isEmpty ? (
          <div className="flex-1 flex items-center justify-center px-4">
            <div className="w-full max-w-[460px] flex flex-col gap-5">
              <div className="text-center">
                <h2 className="font-serif font-semibold text-[22px] tracking-tight">
                  Ask Qarar
                </h2>
                <p className="font-sans text-[13px] text-ink2 mt-1">
                  Decision intelligence for Abu Dhabi — where to invest, what to
                  build, and who to bring in.
                </p>
              </div>
              {inputBar}
              <div className="flex flex-col gap-2">
                <p className="font-mono text-[10px] text-ink3 tracking-wide uppercase text-center">
                  Recommended queries
                </p>
                {[HERO_QUESTION, ...SUGGESTED_QUERIES].map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => ask(q)}
                    disabled={pending}
                    className="text-left font-sans text-[13px] leading-snug border border-line rounded-lg px-3.5 py-2.5 text-ink2 hover:border-gold hover:text-goldDeep hover:bg-cardAlt disabled:opacity-50 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-auto pr-1">
              <div className="flex flex-col gap-5 pb-4">
                {messages.map((m, i) =>
                  m.role === "user" ? (
                    <div key={i} className="flex justify-end">
                      <div className="bg-ink text-bg rounded-xl2 rounded-br-md px-4 py-2.5 font-sans text-[14px] max-w-[85%] leading-snug">
                        {m.text}
                      </div>
                    </div>
                  ) : "brief" in m ? (
                    <ResponseCard
                      key={i}
                      brief={m.brief}
                      active={activeBrief === m.brief}
                      onViewOnMap={() => setActiveBrief(m.brief)}
                    />
                  ) : (
                    <div
                      key={i}
                      className="bg-surface border border-gold rounded-xl2 p-4 font-mono text-[12px] text-goldDeep"
                    >
                      {m.error}
                    </div>
                  )
                )}

                {pending && (
                  <div className="flex items-center gap-2 text-ink3 font-mono text-[12px] px-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-gold animate-pulse" />
                    Qarar is analyzing…
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            </div>

            <div className="pt-3 flex flex-col gap-2">
              <div className="flex gap-2 overflow-x-auto pb-0.5 -mx-0.5 px-0.5">
                {SUGGESTED_QUERIES.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => ask(q)}
                    disabled={pending}
                    className="flex-none max-w-[240px] text-left font-sans text-[12px] leading-snug border border-line rounded-lg px-3 py-2 text-ink2 hover:border-gold hover:text-goldDeep hover:bg-cardAlt disabled:opacity-50 disabled:pointer-events-none transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
              {inputBar}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
