import type { AmenityPoint, RecommendedParcel } from "./types";

function amenityLabel(a: AmenityPoint): string {
  const name = (a.name ?? "").trim();
  if (name && !name.toLowerCase().includes("unnamed")) return name;
  return `${a.category || "OSM"} amenity`;
}

export function amenityBrainstormQuestion(
  amenity: AmenityPoint,
  district: string | null
): string {
  const label = amenityLabel(amenity);
  const where = district ? ` in ${district}` : " in this district";
  return `Brainstorm with me: there's a ${amenity.category || "community"} POI (${label})${where}. How does this fit the local service gap, and what should we build or fund nearby?`;
}

export function parcelBrainstormQuestion(parcel: RecommendedParcel): string {
  const district = parcel.district ?? "this district";
  const landUse = parcel.land_use ?? "mixed";
  const potential = parcel.development_potential_score ?? "—";
  const size =
    typeof parcel.parcel_size_sqm === "number"
      ? `${parcel.parcel_size_sqm.toLocaleString()} m²`
      : "unknown size";
  return `Brainstorm with me about parcel ${parcel.parcel_id} in ${district}: ${landUse} land (${size}), ${potential}/100 development potential. Who should invest and what should we develop here?`;
}

export function districtBrainstormQuestion(
  district: string,
  metricLabel: string,
  layerTitle: string,
  unit: string
): string {
  const metric =
    metricLabel && metricLabel !== "—"
      ? ` (${metricLabel} ${unit})`
      : "";
  return `What should we do about ${district}${metric}? Brainstorm the service gaps, development opportunities, and who should invest in this district.`;
}
