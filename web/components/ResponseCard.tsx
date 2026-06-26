"use client";

import { useState } from "react";
import type { Brief, Investor, RecommendedParcel } from "@/lib/types";

const PREVIEW_INVESTOR_COUNT = 3;

const TYPE_INITIALS: Record<string, string> = {
  private_equity: "PE",
  sovereign_fund: "SF",
  family_office: "FO",
  institutional: "IN",
  developer: "DV",
  reit: "RE",
  hnwi: "HN",
};

function highlight(text: string, district: string) {
  if (district && text.includes(district)) {
    const parts = text.split(district);
    return (
      <>
        {parts.map((p, i) => (
          <span key={i}>
            {p}
            {i < parts.length - 1 && (
              <span className="text-goldDeep">{district}</span>
            )}
          </span>
        ))}
      </>
    );
  }
  return text;
}

function investorName(inv: Investor): string {
  const itype = String(inv.investor_type ?? "");
  return itype
    ? itype.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : inv.investor_id ?? "Investor";
}

function investorInitials(inv: Investor): string {
  const itype = String(inv.investor_type ?? "");
  return TYPE_INITIALS[itype] ?? (itype.slice(0, 2).toUpperCase() || "IN");
}

function PinIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="10" r="2.4" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function ParcelCard({ p }: { p: RecommendedParcel }) {
  const size =
    typeof p.parcel_size_sqm === "number"
      ? `${p.parcel_size_sqm.toLocaleString()} m²`
      : "—";
  const value =
    typeof p.estimated_value_aed === "number"
      ? `AED ${p.estimated_value_aed.toLocaleString()}`
      : "—";
  const kpis = [
    ["size", size],
    ["land use", String(p.land_use ?? "—")],
    ["potential", String(p.development_potential_score ?? "—")],
    ["est. value", value],
  ];
  return (
    <div className="border border-line rounded-lg p-3.5 bg-cardAlt">
      <div className="flex items-center justify-between mb-2.5">
        <div className="font-semibold text-sm">
          Parcel <span className="text-goldDeep">{p.parcel_id}</span> ·{" "}
          {p.district}
        </div>
        <span className="font-mono text-[10px] font-semibold bg-gold text-onGold px-2 py-0.5 rounded tracking-wide">
          recommended
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {kpis.map(([l, v]) => (
          <div key={l}>
            <div className="font-mono text-[9px] text-ink3 tracking-wide uppercase">
              {l}
            </div>
            <div className="font-mono text-[13px] mt-0.5">{v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function InvestorRow({
  inv,
  onClick,
}: {
  inv: Investor;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-2 border border-line rounded-md px-2.5 py-2 text-left hover:border-gold hover:bg-cardAlt transition-colors"
    >
      <div className="w-6 h-6 rounded bg-ink text-bg font-mono text-[9px] font-semibold flex items-center justify-center flex-none">
        {investorInitials(inv)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="font-semibold text-[11px] truncate">
          {investorName(inv)}
        </div>
        <div className="font-mono text-[10px] text-goldDeep truncate">
          {inv.investor_id}
          {typeof inv.strategic_fit_score === "number"
            ? ` · ${inv.strategic_fit_score}% fit`
            : ""}
        </div>
      </div>
      <span className="font-mono text-[12px] text-ink3 flex-none">›</span>
    </button>
  );
}

function BackIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M15 6l-6 6 6 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function InvestorModal({
  inv,
  onClose,
  onBack,
}: {
  inv: Investor;
  onClose: () => void;
  onBack?: () => void;
}) {
  const rows: [string, string][] = [
    ["investor id", String(inv.investor_id ?? "—")],
    ["type", investorName(inv)],
    ["preferred sector", String(inv.preferred_sector ?? "—")],
    ["preferred district", String(inv.preferred_district ?? "—")],
    ["capital range", String(inv.capital_range_aed ?? "—")],
    ["risk profile", String(inv.risk_profile ?? "—")],
    ["investment horizon", String(inv.investment_horizon ?? "—")],
    [
      "strategic fit",
      typeof inv.strategic_fit_score === "number"
        ? `${inv.strategic_fit_score} / 100`
        : "—",
    ],
  ];
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-line rounded-xl2 p-5 w-full max-w-sm shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          {onBack ? (
            <button
              type="button"
              onClick={onBack}
              className="inline-flex items-center gap-1 font-mono text-[11px] text-ink2 hover:text-goldDeep transition-colors"
              aria-label="Back to list"
            >
              <BackIcon />
              Back
            </button>
          ) : (
            <span />
          )}
          <button
            type="button"
            onClick={onClose}
            className="font-mono text-ink3 hover:text-ink text-lg leading-none"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <div className="flex items-center gap-2.5 mb-4">
          <div className="w-8 h-8 rounded-md bg-ink text-bg font-mono text-[11px] font-semibold flex items-center justify-center">
            {investorInitials(inv)}
          </div>
          <div>
            <div className="font-serif font-semibold text-[16px] leading-none">
              {investorName(inv)}
            </div>
            <div className="font-mono text-[10px] text-goldDeep mt-1">
              {inv.investor_id}
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          {rows.map(([k, v]) => (
            <div
              key={k}
              className="flex items-center justify-between border-b border-hair pb-1.5 last:border-0"
            >
              <span className="font-mono text-[10px] text-ink3 tracking-wide uppercase">
                {k}
              </span>
              <span className="font-mono text-[12px] text-ink">{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function InvestorListModal({
  investors,
  onClose,
  onSelect,
}: {
  investors: Investor[];
  onClose: () => void;
  onSelect: (inv: Investor) => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-line rounded-xl2 p-5 w-full max-w-md shadow-xl flex flex-col max-h-[min(80vh,640px)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4 flex-none">
          <div>
            <div className="font-serif font-semibold text-[18px] leading-none">
              Matched investors
            </div>
            <div className="font-mono text-[10px] text-ink3 mt-1">
              {investors.length} mandates · tap for details
            </div>
          </div>
          <button
            onClick={onClose}
            className="font-mono text-ink3 hover:text-ink text-lg leading-none"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <div className="flex flex-col gap-2 overflow-y-auto pr-0.5">
          {investors.map((inv, i) => (
            <InvestorRow
              key={inv.investor_id ?? i}
              inv={inv}
              onClick={() => onSelect(inv)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function ResponseCard({
  brief,
  onViewOnMap,
  active = false,
}: {
  brief: Brief;
  onViewOnMap?: () => void;
  active?: boolean;
}) {
  const [selected, setSelected] = useState<Investor | null>(null);
  const [showAllInvestors, setShowAllInvestors] = useState(false);
  const [detailFromList, setDetailFromList] = useState(false);

  function openInvestorFromPreview(inv: Investor) {
    setDetailFromList(false);
    setSelected(inv);
  }

  function openInvestorFromList(inv: Investor) {
    setDetailFromList(true);
    setSelected(inv);
  }

  function closeInvestorDetail() {
    setSelected(null);
    setDetailFromList(false);
    setShowAllInvestors(false);
  }

  function backToInvestorList() {
    setSelected(null);
  }

  const previewInvestors = brief.matched_investors.slice(
    0,
    PREVIEW_INVESTOR_COUNT
  );
  const hasMoreInvestors =
    brief.matched_investors.length > PREVIEW_INVESTOR_COUNT;

  return (
    <div className="bg-surface border border-line rounded-xl2 p-5 sm:p-6 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="font-mono text-[11px] text-ink3 tracking-wide mb-1.5">
            recommendation
          </div>
          <div className="font-serif font-semibold text-[22px] leading-tight tracking-tight">
            {highlight(brief.headline, brief.district)}
          </div>
        </div>
        {onViewOnMap && (
          <button
            onClick={onViewOnMap}
            disabled={active}
            className={`inline-flex items-center gap-1.5 font-mono text-[11px] rounded-md px-2.5 py-1 border transition-colors flex-none ${
              active
                ? "border-gold text-goldDeep bg-goldTint cursor-default"
                : "border-line text-ink2 hover:border-gold hover:text-goldDeep"
            }`}
          >
            <PinIcon />
            {active ? "on map" : "view on map"}
          </button>
        )}
      </div>

      {brief.recommended_parcel && (
        <ParcelCard p={brief.recommended_parcel} />
      )}

      {brief.matched_investors.length > 0 && (
        <div>
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="font-mono text-[11px] text-ink3 tracking-wide">
              matched investors · tap for details
            </div>
            {hasMoreInvestors && (
              <button
                type="button"
                onClick={() => setShowAllInvestors(true)}
                className="font-mono text-[11px] text-goldDeep hover:text-gold transition-colors"
              >
                view more ({brief.matched_investors.length})
              </button>
            )}
          </div>
          <div className="flex flex-col gap-2">
            {previewInvestors.map((inv, i) => (
              <InvestorRow
                key={inv.investor_id ?? i}
                inv={inv}
                onClick={() => openInvestorFromPreview(inv)}
              />
            ))}
          </div>
        </div>
      )}

      {brief.live_reconciliation && (
        <div className="border border-gold bg-goldTint rounded-lg px-3.5 py-2.5 font-sans text-[12px] leading-snug">
          Live reconciliation: median{" "}
          <b>AED {brief.live_reconciliation.live_median.toLocaleString()}/sqm</b>{" "}
          vs synthetic baseline{" "}
          <b>
            AED{" "}
            {brief.live_reconciliation.synthetic_baseline.toLocaleString()}/sqm
          </b>{" "}
          ({brief.live_reconciliation.pct_delta > 0 ? "+" : ""}
          {brief.live_reconciliation.pct_delta}%) ·{" "}
          {brief.live_reconciliation.n_listings} listings ·{" "}
          {brief.live_reconciliation.n_mislabeled_rent_vs_sale} mislabeled
          rent/sale.
        </div>
      )}

      {showAllInvestors && !selected && (
        <InvestorListModal
          investors={brief.matched_investors}
          onClose={() => setShowAllInvestors(false)}
          onSelect={openInvestorFromList}
        />
      )}

      {selected && (
        <InvestorModal
          inv={selected}
          onClose={closeInvestorDetail}
          onBack={detailFromList ? backToInvestorList : undefined}
        />
      )}
    </div>
  );
}
