"use client";

import { Popup } from "react-map-gl/maplibre";
import type { AmenityPoint, RecommendedParcel } from "@/lib/types";
import {
  amenityBrainstormQuestion,
  districtBrainstormQuestion,
  parcelBrainstormQuestion,
} from "@/lib/map-brainstorm";

export type MapSelection =
  | { type: "amenity"; amenity: AmenityPoint; index: number }
  | {
      type: "parcel";
      parcel: RecommendedParcel;
      latitude: number;
      longitude: number;
    }
  | {
      type: "district";
      district: string;
      metricLabel: string;
      layerTitle: string;
      unit: string;
      value: number | null;
      latitude: number;
      longitude: number;
    };

function formatCoord(n: number) {
  return n.toFixed(5);
}

function amenityDisplayName(a: AmenityPoint) {
  const name = (a.name ?? "").trim();
  if (name && !name.toLowerCase().includes("unnamed")) return name;
  return "Unnamed POI";
}

export function MapSelectionPopup({
  selection,
  contextDistrict,
  onClose,
  onAskQuestion,
}: {
  selection: MapSelection;
  contextDistrict: string | null;
  onClose: () => void;
  onAskQuestion?: (question: string) => void;
}) {
  const lat =
    selection.type === "amenity"
      ? selection.amenity.latitude
      : selection.latitude;
  const lon =
    selection.type === "amenity"
      ? selection.amenity.longitude
      : selection.longitude;

  if (lat == null || lon == null) return null;

  const question =
    selection.type === "amenity"
      ? amenityBrainstormQuestion(selection.amenity, contextDistrict)
      : selection.type === "parcel"
        ? parcelBrainstormQuestion(selection.parcel)
        : districtBrainstormQuestion(
            selection.district,
            selection.metricLabel,
            selection.layerTitle,
            selection.unit
          );

  const title =
    selection.type === "amenity"
      ? amenityDisplayName(selection.amenity)
      : selection.type === "parcel"
        ? `Parcel ${selection.parcel.parcel_id}`
        : selection.district;

  const kind =
    selection.type === "amenity"
      ? "amenity"
      : selection.type === "parcel"
        ? "recommended parcel"
        : "district";

  return (
    <Popup
      longitude={lon}
      latitude={lat}
      anchor="bottom"
      offset={12}
      closeOnClick={false}
      onClose={onClose}
      className="qarar-map-popup"
    >
      <div className="w-[280px] font-sans text-ink">
        <div className="font-mono text-[9px] text-ink3 tracking-wide uppercase mb-1">
          {kind}
        </div>
        <div className="font-serif font-semibold text-[15px] leading-snug mb-2">
          {title}
        </div>

        <div className="flex flex-col gap-1.5 mb-3">
          {selection.type === "amenity" && (
            <>
              <Row label="category" value={selection.amenity.category || "—"} />
              {contextDistrict && (
                <Row label="district" value={contextDistrict} />
              )}
              <Row
                label="coordinates"
                value={`${formatCoord(selection.amenity.latitude)}, ${formatCoord(selection.amenity.longitude)}`}
              />
            </>
          )}

          {selection.type === "parcel" && (
            <>
              <Row
                label="district"
                value={String(selection.parcel.district ?? "—")}
              />
              <Row
                label="land use"
                value={String(selection.parcel.land_use ?? "—")}
              />
              {selection.parcel.current_status != null && (
                <Row
                  label="status"
                  value={String(selection.parcel.current_status).replace(
                    /_/g,
                    " "
                  )}
                />
              )}
              <Row
                label="potential"
                value={
                  selection.parcel.development_potential_score != null
                    ? `${selection.parcel.development_potential_score} / 100`
                    : "—"
                }
              />
              {typeof selection.parcel.parcel_size_sqm === "number" && (
                <Row
                  label="size"
                  value={`${selection.parcel.parcel_size_sqm.toLocaleString()} m²`}
                />
              )}
              {typeof selection.parcel.estimated_value_aed === "number" && (
                <Row
                  label="est. value"
                  value={`AED ${selection.parcel.estimated_value_aed.toLocaleString()}`}
                />
              )}
            </>
          )}

          {selection.type === "district" && (
            <>
              <Row label="layer" value={selection.layerTitle} />
              <Row
                label={selection.unit}
                value={
                  selection.metricLabel !== "—"
                    ? selection.metricLabel
                    : "No data"
                }
              />
              {selection.value != null && (
                <Row label="raw value" value={String(selection.value)} />
              )}
            </>
          )}
        </div>

        {onAskQuestion && (
          <button
            type="button"
            onClick={() => {
              onAskQuestion(question);
              onClose();
            }}
            className="w-full font-mono text-[11px] font-medium bg-gold text-onGold rounded-lg px-3 py-2 hover:opacity-90 transition-opacity"
          >
            Brainstorm with Qarar
          </button>
        )}
      </div>
    </Popup>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-2 text-[12px]">
      <span className="font-mono text-[10px] text-ink3 uppercase tracking-wide flex-none">
        {label}
      </span>
      <span className="text-ink2 text-right leading-snug">{value}</span>
    </div>
  );
}
