import type {
  Brief,
  HealthResponse,
  MapData,
  OverviewResponse,
  ParcelPoint,
  ScenarioResult,
  SimulateRequest,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_QARAR_API ?? "http://localhost:8000";

export const HERO_QUESTION =
  "Where is Abu Dhabi most underserved, and what should we do about it?";

export const SUGGESTED_QUERIES = [
  "Which districts have the most unmet service demand?",
  "Which vacant land should we develop first?",
  "Which investors match hospitality in Yas Island?",
  "How do live prices compare in Al Reem Island?",
  "What should we do about Zayed City?",
] as const;

export async function fetchAnswer(question: string): Promise<Brief> {
  const res = await fetch(`${API_BASE}/api/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return (await res.json()) as Brief;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return (await res.json()) as HealthResponse;
}

export async function fetchDistricts(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/districts`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  const data = (await res.json()) as { districts: string[] };
  return data.districts;
}

export async function fetchSimulate(
  req: SimulateRequest
): Promise<ScenarioResult> {
  const res = await fetch(`${API_BASE}/api/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return (await res.json()) as ScenarioResult;
}

export async function fetchParcels(district: string): Promise<ParcelPoint[]> {
  const res = await fetch(
    `${API_BASE}/api/parcels?district=${encodeURIComponent(district)}`
  );
  if (!res.ok) throw new Error(`API error ${res.status}`);
  const data = (await res.json()) as { parcels: ParcelPoint[] };
  return data.parcels;
}

export async function fetchOverview(): Promise<OverviewResponse> {
  const res = await fetch(`${API_BASE}/api/overview`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return (await res.json()) as OverviewResponse;
}

export async function fetchMap(
  layer: string,
  year?: number | null,
  highlight?: string | null
): Promise<MapData> {
  const params = new URLSearchParams({ layer });
  if (year) params.set("year", String(year));
  if (highlight) params.set("highlight", highlight);
  const res = await fetch(`${API_BASE}/api/map?${params.toString()}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return (await res.json()) as MapData;
}
