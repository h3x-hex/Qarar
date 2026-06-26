"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Map, {
  Source,
  Layer,
  Marker,
  type MapLayerMouseEvent,
  type MapRef,
} from "react-map-gl/maplibre";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { fetchMap, fetchParcels } from "@/lib/api";
import type {
  MapData,
  AmenityPoint,
  RecommendedParcel,
  MapFeatureProps,
  ParcelPoint,
} from "@/lib/types";
import {
  MapSelectionPopup,
  type MapSelection,
} from "./MapSelectionPopup";

export interface ParcelPin {
  latitude: number;
  longitude: number;
  parcel_id: string;
}

function basemapStyle(dark: boolean): StyleSpecification {
  const tiles = dark
    ? "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
    : "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
  return {
    version: 8,
    sources: {
      carto: {
        type: "raster",
        tiles: [tiles],
        tileSize: 256,
        attribution: "© OpenStreetMap contributors © CARTO",
      },
    },
    layers: [{ id: "carto", type: "raster", source: "carto" }],
  };
}

const RAMP = {
  light: { lo: "#f4e9c9", hi: "#a87f22", neutral: "#ebe9e2", border: "#d8d6cf" },
  dark: { lo: "#4a3c18", hi: "#f0c24b", neutral: "#26261f", border: "#33332d" },
};

// Below this zoom the centroids overlap, so we render compact dots and only
// reveal the full name/metric box for hovered, selected, or highlighted
// districts. Zoom past it and every label appears.
const LABEL_ZOOM = 10.9;

function districtSelection(
  props: MapFeatureProps,
  legend: MapData["legend"]
): MapSelection {
  const [lon, lat] = props.centroid;
  return {
    type: "district",
    district: props.district,
    metricLabel: props.label,
    layerTitle: legend.title,
    unit: legend.unit,
    value: props.value,
    latitude: lat,
    longitude: lon,
  };
}

function districtLayerId(isPolygon: boolean) {
  return isPolygon ? "district-fill" : "district-circle";
}

export function ChoroplethMap({
  layer,
  year = null,
  highlightDistrict = null,
  parcelPin = null,
  recommendedParcel = null,
  amenities = [],
  dark,
  showControls = false,
  onLayerChange,
  onYearChange,
  onAskQuestion,
  districts,
  selectedDistrict: controlledDistrict = null,
  onDistrictChange,
  onResetFilters,
}: {
  layer: string;
  year?: number | null;
  highlightDistrict?: string | null;
  parcelPin?: ParcelPin | null;
  recommendedParcel?: RecommendedParcel | null;
  amenities?: AmenityPoint[];
  dark: boolean;
  showControls?: boolean;
  onLayerChange?: (layer: string) => void;
  onYearChange?: (year: number) => void;
  onAskQuestion?: (question: string) => void;
  districts?: string[];
  selectedDistrict?: string | null;
  onDistrictChange?: (district: string | null) => void;
  onResetFilters?: () => void;
}) {
  const [data, setData] = useState<MapData | null>(null);
  const [error, setError] = useState(false);
  const [selection, setSelection] = useState<MapSelection | null>(null);
  const [zoom, setZoom] = useState(9.6);
  const [hoveredDistrict, setHoveredDistrict] = useState<string | null>(null);
  const [focusedDistrict, setFocusedDistrict] = useState<string | null>(null);
  const [districtParcels, setDistrictParcels] = useState<ParcelPoint[]>([]);
  const mapRef = useRef<MapRef | null>(null);

  useEffect(() => {
    setSelection(null);
    setFocusedDistrict(null);
    setDistrictParcels([]);
  }, [highlightDistrict, parcelPin?.parcel_id, amenities.length, layer, year]);

  useEffect(() => {
    let cancelled = false;
    fetchMap(layer, year, highlightDistrict)
      .then((d) => !cancelled && (setData(d), setError(false)))
      .catch(() => !cancelled && setError(true));
    return () => {
      cancelled = true;
    };
  }, [layer, year, highlightDistrict]);

  useEffect(() => {
    if (!data || !mapRef.current) return;
    setZoom(data.center.zoom);
    mapRef.current.flyTo({
      center: [data.center.longitude, data.center.latitude],
      zoom: data.center.zoom,
      duration: 900,
    });
  }, [data]);

  const c = dark ? RAMP.dark : RAMP.light;
  const goldPin = dark ? "#f0c24b" : "#a87f22";
  const amenityDot = dark ? "#c9c5b8" : "#5c5a52";
  const amenityActive = dark ? "#f0c24b" : "#a87f22";

  const fc = data?.feature_collection ?? {
    type: "FeatureCollection" as const,
    features: [],
  };
  const isPolygon = data?.geometry_mode === "polygon";
  const districtLayer = districtLayerId(isPolygon);

  const popupDistrict =
    selection?.type === "district" ? selection.district : null;
  const selectedDistrict = popupDistrict ?? controlledDistrict;

  const defaultLayer = data?.layers[0]?.id;
  const latestYear = data?.available_years[data.available_years.length - 1];
  const filtersActive =
    !!data &&
    (layer !== defaultLayer ||
      controlledDistrict != null ||
      (data.legend.year_aware && (year ?? latestYear) !== latestYear));

  const selectedAmenityIndex =
    selection?.type === "amenity" ? selection.index : -1;

  const selectedParcelId =
    selection?.type === "parcel"
      ? (selection.parcel.parcel_id ?? null)
      : null;

  const focusDistrict = useCallback(
    (props: MapFeatureProps) => {
      if (!data) return;
      const district = props.district;
      setSelection(districtSelection(props, data.legend));
      setFocusedDistrict(district);
      setDistrictParcels([]);
      const [lon, lat] = props.centroid;
      mapRef.current?.flyTo({
        center: [lon, lat],
        zoom: 12.8,
        duration: 900,
      });
      fetchParcels(district)
        .then(setDistrictParcels)
        .catch(() => setDistrictParcels([]));
    },
    [data]
  );

  const districtParcelGeoJSON = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: districtParcels.map((p, index) => ({
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [p.longitude, p.latitude],
        },
        properties: {
          index,
          parcel_id: p.parcel_id ?? "",
          vacant:
            String(p.current_status ?? "").toLowerCase() === "vacant" ? 1 : 0,
        },
      })),
    }),
    [districtParcels]
  );

  const amenityGeoJSON = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: amenities.map((a, index) => ({
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [a.longitude, a.latitude],
        },
        properties: {
          index,
          name: a.name ?? "",
          category: a.category ?? "",
        },
      })),
    }),
    [amenities]
  );

  const fillColor: any = [
    "case",
    ["==", ["get", "has_value"], 0],
    c.neutral,
    ["interpolate", ["linear"], ["get", "value_norm"], 0, c.lo, 1, c.hi],
  ];

  const initial = data?.center ?? {
    longitude: 54.51,
    latitude: 24.43,
    zoom: 9.6,
  };

  const handleMapClick = useCallback(
    (e: MapLayerMouseEvent) => {
      const parcelHit = e.features?.find(
        (f) => f.layer.id === "district-parcel-hit"
      );
      if (parcelHit?.properties != null) {
        const idx = Number(parcelHit.properties.index);
        const parcel = districtParcels[idx];
        if (parcel) {
          setSelection({
            type: "parcel",
            parcel,
            latitude: parcel.latitude,
            longitude: parcel.longitude,
          });
        }
        return;
      }

      const amenityHit = e.features?.find((f) => f.layer.id === "amenity-hit");
      if (amenityHit?.properties != null) {
        const idx = Number(amenityHit.properties.index);
        const amenity = amenities[idx];
        if (amenity) {
          setSelection({ type: "amenity", amenity, index: idx });
        }
        return;
      }

      const districtHit = e.features?.find((f) => f.layer.id === districtLayer);
      if (districtHit?.properties && data) {
        const props = districtHit.properties as unknown as MapFeatureProps;
        if (props.district) {
          focusDistrict(props);
        }
        return;
      }

      setSelection(null);
    },
    [amenities, districtParcels, districtLayer, data, focusDistrict]
  );

  const handleMouseMove = useCallback(
    (e: MapLayerMouseEvent) => {
      const canvas = mapRef.current?.getCanvas();
      if (!canvas) return;
      const interactive = e.features?.some(
        (f) =>
          f.layer.id === "amenity-hit" ||
          f.layer.id === "district-parcel-hit" ||
          f.layer.id === districtLayer
      );
      canvas.style.cursor = interactive ? "pointer" : "";
    },
    [districtLayer]
  );

  const interactiveLayerIds = useMemo(() => {
    const ids = [districtLayer];
    if (amenities.length > 0) ids.unshift("amenity-hit");
    if (districtParcels.length > 0) ids.unshift("district-parcel-hit");
    return ids;
  }, [districtLayer, amenities.length, districtParcels.length]);

  const parcelForPin = recommendedParcel ?? {
    parcel_id: parcelPin?.parcel_id,
    district: highlightDistrict ?? undefined,
  };

  return (
    <div className="h-full w-full overflow-hidden rounded-xl2 border border-line relative">
      <Map
        ref={mapRef}
        key={dark ? "dark" : "light"}
        initialViewState={initial}
        mapStyle={basemapStyle(dark)}
        attributionControl={true}
        interactiveLayerIds={interactiveLayerIds}
        onClick={handleMapClick}
        onMouseMove={handleMouseMove}
        onZoom={(e) => setZoom(e.viewState.zoom)}
        style={{ width: "100%", height: "100%" }}
      >
        {isPolygon ? (
          <Source id="districts" type="geojson" data={fc}>
            <Layer
              id="district-fill"
              type="fill"
              paint={{
                "fill-color": fillColor,
                // Strong choropleth at city level; fade as we zoom into a single
                // district so the basemap, parcel pin, and amenities stay legible.
                "fill-opacity": [
                  "interpolate",
                  ["linear"],
                  ["zoom"],
                  9.5,
                  0.65,
                  11.5,
                  0.3,
                  13,
                  0.16,
                ] as any,
              }}
            />
            <Layer
              id="district-border"
              type="line"
              paint={{
                "line-color": [
                  "case",
                  [
                    "any",
                    ["==", ["get", "is_highlight"], 1],
                    ["==", ["get", "district"], selectedDistrict ?? ""],
                  ],
                  goldPin,
                  c.border,
                ] as any,
                "line-width": [
                  "case",
                  ["==", ["get", "district"], selectedDistrict ?? ""],
                  3,
                  ["==", ["get", "is_highlight"], 1],
                  2.6,
                  0.6,
                ] as any,
              }}
            />
          </Source>
        ) : (
          <Source id="districts" type="geojson" data={fc}>
            <Layer
              id="district-circle"
              type="circle"
              paint={{
                "circle-radius": [
                  "interpolate",
                  ["linear"],
                  ["get", "value_norm"],
                  0,
                  7,
                  1,
                  26,
                ] as any,
                "circle-color": fillColor,
                "circle-opacity": 0.78,
                "circle-stroke-color": [
                  "case",
                  [
                    "any",
                    ["==", ["get", "is_highlight"], 1],
                    ["==", ["get", "district"], selectedDistrict ?? ""],
                  ],
                  goldPin,
                  c.border,
                ] as any,
                "circle-stroke-width": [
                  "case",
                  ["==", ["get", "district"], selectedDistrict ?? ""],
                  3,
                  ["==", ["get", "is_highlight"], 1],
                  2.4,
                  0.8,
                ] as any,
              }}
            />
          </Source>
        )}

        {amenities.length > 0 && (
          <Source id="amenities" type="geojson" data={amenityGeoJSON}>
            <Layer
              id="amenity-dots"
              type="circle"
              paint={{
                "circle-radius": [
                  "case",
                  ["==", ["get", "index"], selectedAmenityIndex],
                  5,
                  3.2,
                ] as any,
                "circle-color": [
                  "case",
                  ["==", ["get", "index"], selectedAmenityIndex],
                  amenityActive,
                  amenityDot,
                ] as any,
                "circle-opacity": 0.92,
                "circle-stroke-color": dark ? "#0a0a0a" : "#ffffff",
                "circle-stroke-width": 1,
              }}
            />
            <Layer
              id="amenity-hit"
              type="circle"
              paint={{
                "circle-radius": 12,
                "circle-opacity": 0,
              }}
            />
          </Source>
        )}

        {districtParcels.length > 0 && (
          <Source
            id="district-parcels"
            type="geojson"
            data={districtParcelGeoJSON}
          >
            <Layer
              id="district-parcel-dots"
              type="circle"
              paint={{
                "circle-radius": [
                  "case",
                  ["==", ["get", "parcel_id"], selectedParcelId ?? ""],
                  7,
                  4.5,
                ] as any,
                "circle-color": [
                  "case",
                  ["==", ["get", "vacant"], 1],
                  goldPin,
                  dark ? "#8a8780" : "#9a988f",
                ] as any,
                "circle-opacity": 0.95,
                "circle-stroke-color": dark ? "#0a0a0a" : "#ffffff",
                "circle-stroke-width": 1.4,
              }}
            />
            <Layer
              id="district-parcel-hit"
              type="circle"
              paint={{
                "circle-radius": 13,
                "circle-opacity": 0,
              }}
            />
          </Source>
        )}

        {fc.features.map((f) => {
          const [lon, lat] = f.properties.centroid;
          const hl = f.properties.is_highlight === 1;
          const selected =
            selectedDistrict != null &&
            f.properties.district === selectedDistrict;
          const hovered = hoveredDistrict === f.properties.district;
          const active = hl || selected;
          const showLabel = active || hovered || zoom >= LABEL_ZOOM;
          return (
            <Marker
              key={f.properties.district}
              longitude={lon}
              latitude={lat}
              anchor="center"
              style={{ zIndex: showLabel ? 2 : 1 }}
            >
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  focusDistrict(f.properties);
                }}
                onMouseEnter={() => setHoveredDistrict(f.properties.district)}
                onMouseLeave={() =>
                  setHoveredDistrict((d) =>
                    d === f.properties.district ? null : d
                  )
                }
                className="group cursor-pointer text-center flex items-center justify-center"
                style={{ background: "none", border: "none", padding: 0 }}
                aria-label={`District ${f.properties.district}`}
              >
                {showLabel ? (
                  <div
                    className={`rounded-md px-1.5 py-1 border backdrop-blur-md transition-transform group-hover:scale-105 ${
                      active
                        ? "text-onGold bg-gold/88 border-gold font-semibold shadow-sm"
                        : "text-ink bg-surface/55 border-line/70 shadow-sm group-hover:border-gold group-hover:bg-surface/70"
                    }`}
                  >
                    <div
                      className={`font-sans text-[10px] leading-tight whitespace-nowrap max-w-[120px] truncate ${
                        active ? "text-black" : ""
                      }`}
                    >
                      {f.properties.district}
                    </div>
                    <div
                      className={`font-mono text-[9px] leading-none mt-0.5 ${
                        active ? "text-onGold/90" : "text-ink3"
                      }`}
                    >
                      {f.properties.label}
                      {data?.legend.unit ? ` ${data.legend.unit}` : ""}
                    </div>
                  </div>
                ) : (
                  <span
                    className="block rounded-full transition-transform group-hover:scale-150"
                    style={{
                      width: 7,
                      height: 7,
                      background: dark ? "#d8d4c7" : "#3b3a34",
                      border: `1.5px solid ${dark ? "#0a0a0a" : "#ffffff"}`,
                      boxShadow: `0 0 0 1px ${c.border}`,
                    }}
                  />
                )}
              </button>
            </Marker>
          );
        })}

        {parcelPin && (
          <Marker
            longitude={parcelPin.longitude}
            latitude={parcelPin.latitude}
            anchor="bottom"
          >
            <button
              type="button"
              aria-label={`Parcel ${parcelPin.parcel_id}`}
              onClick={(e) => {
                e.stopPropagation();
                setSelection({
                  type: "parcel",
                  parcel: parcelForPin,
                  latitude: parcelPin.latitude,
                  longitude: parcelPin.longitude,
                });
              }}
              className="group cursor-pointer"
              style={{
                background: "none",
                border: "none",
                padding: 0,
              }}
            >
              <div
                className="w-5 h-5 rounded-full border-2 transition-transform group-hover:scale-110"
                style={{
                  background: goldPin,
                  borderColor: dark ? "#0a0a0a" : "#ffffff",
                  boxShadow:
                    selection?.type === "parcel"
                      ? `0 0 0 3px ${goldPin}55`
                      : `0 0 0 1px ${goldPin}`,
                }}
              />
            </button>
          </Marker>
        )}

        {selection && (
          <MapSelectionPopup
            selection={selection}
            contextDistrict={
              selection.type === "district"
                ? selection.district
                : highlightDistrict
            }
            onClose={() => setSelection(null)}
            onAskQuestion={onAskQuestion}
          />
        )}
      </Map>

      {showControls && data && (
        <div className="absolute left-3 top-3 right-3 flex flex-wrap items-center gap-1.5 pointer-events-none">
          <div className="flex flex-wrap items-center gap-1.5 pointer-events-auto">
            {data.layers.map((l) => (
              <button
                key={l.id}
                onClick={() =>
                  onLayerChange?.(l.id === layer ? data.layers[0].id : l.id)
                }
                title={
                  l.id === layer && l.id !== data.layers[0].id
                    ? "Click to reset to default layer"
                    : undefined
                }
                className={`font-mono text-[11px] px-2.5 py-1 rounded-md border transition-colors ${
                  l.id === layer
                    ? "bg-gold text-onGold border-gold"
                    : "bg-surface/95 text-ink2 border-line hover:border-gold"
                }`}
              >
                {l.label}
              </button>
            ))}
            {data.legend.year_aware && (
              <select
                value={year ?? data.available_years[data.available_years.length - 1]}
                onChange={(e) => onYearChange?.(Number(e.target.value))}
                className="font-mono text-[11px] bg-surface/95 border border-line rounded-md px-2 py-1 text-ink outline-none focus:border-gold"
              >
                {data.available_years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            )}
            {districts && districts.length > 0 && (
              <select
                value={selectedDistrict ?? ""}
                onChange={(e) =>
                  onDistrictChange?.(e.target.value === "" ? null : e.target.value)
                }
                className="font-mono text-[11px] bg-surface/95 border border-line rounded-md px-2 py-1 text-ink outline-none focus:border-gold"
              >
                <option value="">All districts</option>
                {districts.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            )}
            {onResetFilters && (
              <button
                type="button"
                onClick={onResetFilters}
                disabled={!filtersActive}
                className="font-mono text-[11px] px-2.5 py-1 rounded-md border border-line bg-surface/95 text-ink2 hover:border-gold hover:text-goldDeep disabled:opacity-40 disabled:pointer-events-none transition-colors"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
      )}

      {data && (
        <div className="absolute left-3 bottom-3 bg-surface/95 border border-line rounded-md px-3 py-2 pointer-events-none">
          <div className="font-mono text-[10px] text-ink3 tracking-wide mb-1">
            {data.legend.title.toLowerCase()}
            {data.year ? ` · ${data.year}` : ""}
          </div>
          <div className="flex items-center gap-2">
            <span
              className="h-2 w-20 rounded-sm"
              style={{
                background: `linear-gradient(to right, ${c.lo}, ${c.hi})`,
              }}
            />
            <span className="font-mono text-[9px] text-ink3">
              {data.legend.unit}
            </span>
          </div>
          <div className="font-mono text-[9px] text-ink3 mt-1.5">
            {focusedDistrict && districtParcels.length > 0
              ? `· ${focusedDistrict}: ${districtParcels.length} parcels — tap a dot`
              : "· tap a district to zoom in & see parcels"}
            {amenities.length > 0 && ` · ${amenities.length} amenities`}
          </div>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-surface/90 font-mono text-[11px] text-goldDeep text-center p-4">
          Could not load the map layer. Start the API: uvicorn api:app --app-dir
          qarar --port 8000
        </div>
      )}
    </div>
  );
}
