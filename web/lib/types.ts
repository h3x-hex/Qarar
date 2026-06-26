export interface MapCentroid {
  latitude: number | null;
  longitude: number | null;
  district: string;
}

export interface AmenityPoint {
  latitude: number;
  longitude: number;
  name: string;
  category: string;
}

export interface ParcelPin {
  latitude: number;
  longitude: number;
  parcel_id: string;
}

export interface MapLayers {
  centroid: MapCentroid;
  amenities: AmenityPoint[];
  parcel_pin: ParcelPin | null;
}

export interface RecommendedParcel {
  parcel_id?: string;
  district?: string;
  land_use?: string;
  current_status?: string;
  parcel_size_sqm?: number;
  development_potential_score?: number;
  estimated_value_aed?: number;
  [key: string]: unknown;
}

export interface ParcelPoint extends RecommendedParcel {
  latitude: number;
  longitude: number;
}

export interface Investor {
  investor_id?: string;
  investor_type?: string;
  preferred_sector?: string;
  preferred_district?: string;
  capital_range_aed?: string;
  risk_profile?: string;
  investment_horizon?: string;
  strategic_fit_score?: number;
  [key: string]: unknown;
}

export interface LiveReconciliation {
  live_median: number;
  synthetic_baseline: number;
  pct_delta: number;
  n_listings: number;
  n_mislabeled_rent_vs_sale: number;
}

export interface Brief {
  headline: string;
  district: string;
  reasoning_steps: string[];
  recommended_parcel: RecommendedParcel | null;
  matched_investors: Investor[];
  map_layers: MapLayers;
  sources: string[];
  live_reconciliation: LiveReconciliation | null;
  mode: "deterministic" | "ai_agent";
  tool_call_count: number;
}

export interface HealthResponse {
  status: string;
  llm_available: boolean;
  provider: string;
}

export interface GapStat {
  district: string;
  gap_score: number;
}

export interface ScenarioResult {
  baseline_worst: GapStat;
  scenario_worst: GapStat;
  focus_district: string | null;
  focus_before: GapStat | null;
  focus_after: GapStat | null;
  scenario_top: GapStat[];
  map_layers: MapLayers;
  focus_used: string;
}

export interface SimulateRequest {
  district?: string | null;
  population_delta?: number;
  build_parcel?: boolean;
  add_amenity_category?: string | null;
  add_amenity_count?: number;
}

export interface OverviewRow {
  district: string;
  service_demand: number;
  amenity_count: number;
  amenity_per_capita: number;
  gap_score: number;
  vacant_parcels: number;
  base_sale_aed_sqm: number | null;
  population_total: number;
}

export interface OverviewResponse {
  rows: OverviewRow[];
  worst: OverviewRow | null;
}

export interface MapLayerMeta {
  id: string;
  label: string;
  year_aware: boolean;
}

export interface MapFeatureProps {
  district: string;
  value: number | null;
  value_norm: number;
  has_value: number;
  label: string;
  is_highlight: number;
  centroid: [number, number];
}

export interface MapFeature {
  type: "Feature";
  properties: MapFeatureProps;
  geometry:
    | { type: "Polygon"; coordinates: number[][][] }
    | { type: "Point"; coordinates: [number, number] };
}

export interface MapData {
  geometry_mode: "polygon" | "circle";
  layer: string;
  year: number | null;
  feature_collection: { type: "FeatureCollection"; features: MapFeature[] };
  legend: {
    title: string;
    unit: string;
    min: number | null;
    max: number | null;
    year_aware: boolean;
  };
  center: { longitude: number; latitude: number; zoom: number };
  highlight_district: string | null;
  layers: MapLayerMeta[];
  available_years: number[];
}
