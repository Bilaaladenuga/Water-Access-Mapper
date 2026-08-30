"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Color mapping for water types
const WATER_TYPE_COLORS: Record<string, string> = {
  tap: "#2196F3",
  well: "#4CAF50",
  borehole: "#FF9800",
  spring: "#9C27B0",
  rainwater: "#00BCD4",
  other: "#607D8B",
};

// Color mapping for status
const STATUS_COLORS: Record<string, string> = {
  operational: "#4CAF50",
  broken: "#F44336",
  unknown: "#9E9E9E",
  abandoned: "#795548",
};

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [colorBy, setColorBy] = useState<"type" | "status">("type");
  const [filterType, setFilterType] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    if (!mapContainer.current) return;

    // Initialize map centered on Lagos using OpenFreeMap (free, no API key)
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [3.4, 6.5], // Lagos center
      zoom: 11,
    });

    // Add navigation controls
    map.current.addControl(new maplibregl.NavigationControl(), "top-right");

    map.current.on("load", () => {
      loadStudyArea();
      loadWaterPoints();
    });

    return () => {
      map.current?.remove();
    };
  }, []);

  // Fetch stats
  useEffect(() => {
    fetch(`${API_URL}/api/water-points/stats`)
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch((err) => console.error("Failed to fetch stats:", err));
  }, []);

  function loadStudyArea() {
    if (!map.current) return;

    fetch(`${API_URL}/api/study-areas/geojson`)
      .then((res) => res.json())
      .then((data) => {
        if (!data.features || data.features.length === 0) return;
        if (map.current!.getSource("study-area")) return;

        map.current!.addSource("study-area", {
          type: "geojson",
          data: data,
        });

        map.current!.addLayer({
          id: "study-area-fill",
          type: "fill",
          source: "study-area",
          paint: {
            "fill-color": "#1e40af",
            "fill-opacity": 0.12,
          },
        });

    

      })
      .catch((err) => console.error("Failed to load study area:", err));
  }

  function loadWaterPoints() {
    if (!map.current) return;

    fetch(`${API_URL}/api/water-points/geojson`)
      .then((res) => res.json())
      .then((data) => {
        map.current!.addSource("water-points", {
          type: "geojson",
          data: data,
        });

        // Add circle layer
        map.current!.addLayer({
          id: "water-points-circle",
          type: "circle",
          source: "water-points",
          paint: {
            "circle-radius": 6,
            "circle-stroke-width": 2,
            "circle-stroke-color": "#ffffff",
            "circle-color": [
              "match",
              ["get", colorBy === "type" ? "water_type" : "status"],
              ...Object.entries(
                colorBy === "type" ? WATER_TYPE_COLORS : STATUS_COLORS
              ).flatMap(([key, color]) => [key, color]),
              "#9E9E9E", // default
            ],
            "circle-opacity": 0.85,
          },
        });

        // Add popup on click
        const popup = new maplibregl.Popup({
          closeButton: true,
          closeOnClick: false,
          maxWidth: "300px",
        });

        map.current!.on("click", "water-points-circle", (e) => {
          if (!e.features || !e.features.length) return;

          const feature = e.features[0];
          const props = feature.properties as any;

          const color =
            colorBy === "type"
              ? WATER_TYPE_COLORS[props.water_type] || "#9E9E9E"
              : STATUS_COLORS[props.status] || "#9E9E9E";

          const html = `
            <div style="font-family: system-ui, sans-serif; padding: 4px;">
              <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">
                ${props.name}
              </h3>
              <div style="display: grid; grid-template-columns: auto 1fr; gap: 4px 8px; font-size: 12px;">
                <span style="font-weight: 500; color: #666;">Type:</span>
                <span>
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${WATER_TYPE_COLORS[props.water_type] || "#9E9E9E"};margin-right:4px;"></span>
                  ${props.water_type}
                </span>
                <span style="font-weight: 500; color: #666;">Status:</span>
                <span>
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${STATUS_COLORS[props.status] || "#9E9E9E"};margin-right:4px;"></span>
                  ${props.status}
                </span>
                <span style="font-weight: 500; color: #666;">Source:</span>
                <span>${props.source === "osm" ? "OpenStreetMap" : "Sample Data"}</span>
                <span style="font-weight: 500; color: #666;">Coords:</span>
                <span>${props.latitude?.toFixed(4)}, ${props.longitude?.toFixed(4)}</span>
              </div>
            </div>
          `;

          popup
            .setLngLat((e as any).lngLat)
            .setHTML(html)
            .addTo(map.current!);
        });

        // Pointer cursor on hover
        map.current!.on("mouseenter", "water-points-circle", () => {
          if (map.current) map.current.getCanvas().style.cursor = "pointer";
        });

        map.current!.on("mouseleave", "water-points-circle", () => {
          if (map.current) map.current.getCanvas().style.cursor = "";
        });
      })
      .catch((err) => console.error("Failed to load water points:", err));
  }

  function updateColors() {
    if (!map.current || !map.current.getLayer("water-points-circle")) return;

    map.current.setPaintProperty(
      "water-points-circle",
      "circle-color",
      [
        "match",
        ["get", colorBy === "type" ? "water_type" : "status"],
        ...Object.entries(
          colorBy === "type" ? WATER_TYPE_COLORS : STATUS_COLORS
        ).flatMap(([key, color]) => [key, color]),
        "#9E9E9E",
      ]
    );
  }

  useEffect(() => {
    updateColors();
  }, [colorBy]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100vh" }}>
      <div ref={mapContainer} style={{ width: "100%", height: "100%" }} />

      {/* Stats Bar */}
      {stats && (
        <div
          style={{
            position: "absolute",
            top: 10,
            left: 10,
            background: "white",
            borderRadius: 8,
            padding: "12px 16px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
            fontSize: 13,
            zIndex: 10,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4 }}>
            💧 Water Points: {stats.total}
          </div>
          <div style={{ color: "#666", fontSize: 11 }}>
            {stats.by_source?.osm || 0} OSM · {stats.by_source?.sample || 0} Sample
          </div>
        </div>
      )}

      {/* Legend */}
      <div
        style={{
          position: "absolute",
          bottom: 30,
          left: 10,
          background: "white",
          borderRadius: 8,
          padding: "12px 16px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          fontSize: 12,
          zIndex: 10,
          minWidth: 140,
        }}
      >
        <div style={{ fontWeight: 600, marginBottom: 8 }}>
          {colorBy === "type" ? "Water Type" : "Status"}
        </div>
        {Object.entries(colorBy === "type" ? WATER_TYPE_COLORS : STATUS_COLORS).map(
          ([key, color]) => (
            <div
              key={key}
              style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}
            >
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: color,
                  flexShrink: 0,
                }}
              />
              <span style={{ textTransform: "capitalize" }}>{key}</span>
            </div>
          )
        )}
      </div>

      {/* Controls Panel */}
      <div
        style={{
          position: "absolute",
          top: 10,
          right: 60,
          background: "white",
          borderRadius: 8,
          padding: "12px 16px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          fontSize: 12,
          zIndex: 10,
          display: "flex",
          gap: 12,
          alignItems: "center",
        }}
      >
        <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
          Color by:
          <select
            value={colorBy}
            onChange={(e) => setColorBy(e.target.value as "type" | "status")}
            style={{ padding: "2px 4px", borderRadius: 4, border: "1px solid #ccc" }}
          >
            <option value="type">Water Type</option>
            <option value="status">Status</option>
          </select>
        </label>
      </div>
    </div>
  );
}
