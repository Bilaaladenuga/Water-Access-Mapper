"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const WATER_TYPE_COLORS: Record<string, string> = {
  tap: "#2196F3",
  well: "#4CAF50",
  borehole: "#FF9800",
  spring: "#9C27B0",
  rainwater: "#00BCD4",
  other: "#607D8B",
};

const STATUS_COLORS: Record<string, string> = {
  operational: "#4CAF50",
  broken: "#F44336",
  unknown: "#9E9E9E",
  abandoned: "#795548",
};

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const [colorBy, setColorBy] = useState<"type" | "status">("type");
  const [filterType, setFilterType] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [stats, setStats] = useState<any>(null);
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null);
  const [routing, setRouting] = useState(false);

  // Store water points data for filtering
  const waterPointsData = useRef<any>(null);

  useEffect(() => {
    if (!mapContainer.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [3.4, 6.5],
      zoom: 11,
    });

    map.current.addControl(new maplibregl.NavigationControl(), "top-right");

    map.current.on("load", () => {
      loadStudyArea();
      loadWaterPoints();
    });

    return () => {
      map.current?.remove();
    };
  }, []);

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

        map.current!.addSource("study-area", { type: "geojson", data });

        map.current!.addLayer({
          id: "study-area-fill",
          type: "fill",
          source: "study-area",
          paint: { "fill-color": "#f59e0b", "fill-opacity": 0.12 },
        });

        map.current!.addLayer({
          id: "study-area-outline",
          type: "line",
          source: "study-area",
          paint: { "line-color": "#b45309", "line-width": 2.5 },
        });
      })
      .catch((err) => console.error("Failed to load study area:", err));
  }

  function loadWaterPoints() {
    if (!map.current) return;

    fetch(`${API_URL}/api/water-points/geojson`)
      .then((res) => res.json())
      .then((data) => {
        waterPointsData.current = data;
        map.current!.addSource("water-points", { type: "geojson", data });

        map.current!.addLayer({
          id: "water-points-circle",
          type: "circle",
          source: "water-points",
          paint: {
            "circle-radius": 7,
            "circle-stroke-width": 2,
            "circle-stroke-color": "#ffffff",
            "circle-color": [
              "match",
              ["get", colorBy === "type" ? "water_type" : "status"],
              ...Object.entries(
                colorBy === "type" ? WATER_TYPE_COLORS : STATUS_COLORS
              ).flatMap(([key, color]) => [key, color]),
              "#9E9E9E",
            ],
            "circle-opacity": 0.9,
          },
        });

        // Popup on click
        const popup = new maplibregl.Popup({
          closeButton: true,
          closeOnClick: false,
          maxWidth: "320px",
        });
        popupRef.current = popup;

        map.current!.on("click", "water-points-circle", (e) => {
          if (!e.features || !e.features.length) return;
          const feature = e.features[0];
          const props = feature.properties as any;
          const coords = (feature.geometry as any).coordinates;

          const sourceBadge =
            props.source === "osm"
              ? '<span style="background:#1976D2;color:white;padding:1px 6px;border-radius:10px;font-size:10px;">OSM</span>'
              : '<span style="background:#FF9800;color:white;padding:1px 6px;border-radius:10px;font-size:10px;">Sample</span>';

          const html = `
            <div style="font-family:system-ui,sans-serif;padding:4px;">
              <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">
                <h3 style="margin:0;font-size:14px;font-weight:600;flex:1;">${props.name}</h3>
                ${sourceBadge}
              </div>
              <div style="display:grid;grid-template-columns:auto 1fr;gap:3px 8px;font-size:12px;margin-bottom:10px;">
                <span style="font-weight:500;color:#666;">Type:</span>
                <span>
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${WATER_TYPE_COLORS[props.water_type] || "#9E9E9E"};margin-right:4px;"></span>
                  ${props.water_type}
                </span>
                <span style="font-weight:500;color:#666;">Status:</span>
                <span>
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${STATUS_COLORS[props.status] || "#9E9E9E"};margin-right:4px;"></span>
                  ${props.status}
                </span>
                <span style="font-weight:500;color:#666;">Coords:</span>
                <span>${props.latitude?.toFixed(4)}, ${props.longitude?.toFixed(4)}</span>
              </div>
              <button id="route-btn" style="
                width:100%;padding:8px;background:#1976D2;color:white;border:none;border-radius:6px;
                cursor:pointer;font-size:12px;font-weight:600;
              ">📍 Get Walking Route</button>
            </div>
          `;

          popup.setLngLat(coords).setHTML(html).addTo(map.current!);

          // Attach route button handler after popup renders
          setTimeout(() => {
            const btn = document.getElementById("route-btn");
            if (btn) {
              btn.onclick = () => getRoute(props.id, coords);
            }
          }, 50);
        });

        map.current!.on("mouseenter", "water-points-circle", () => {
          if (map.current) map.current.getCanvas().style.cursor = "pointer";
        });
        map.current!.on("mouseleave", "water-points-circle", () => {
          if (map.current) map.current.getCanvas().style.cursor = "";
        });
      })
      .catch((err) => console.error("Failed to load water points:", err));
  }

  const getRoute = useCallback(
    async (targetId: string, targetCoords: [number, number]) => {
      if (!map.current) return;
      setRouting(true);

      // Use user location or default (Ikeja)
      const lat = userLocation?.[1] || 6.6018;
      const lon = userLocation?.[0] || 3.3515;

      try {
        const res = await fetch(
          `${API_URL}/api/routing/to-point?lat=${lat}&lon=${lon}&target_id=${targetId}`
        );
        if (!res.ok) throw new Error("Routing failed");
        const data = await res.json();

        // Remove old route if exists
        if (map.current!.getSource("route")) {
          map.current!.removeLayer("route-line");
          map.current!.removeSource("route");
        }

        // Add route line
        map.current!.addSource("route", {
          type: "geojson",
          data: data.route_geometry,
        });

        map.current!.addLayer({
          id: "route-line",
          type: "line",
          source: "route",
          paint: {
            "line-color": "#1976D2",
            "line-width": 4,
            "line-opacity": 0.85,
          },
        });

        // Show route info in popup
        if (popupRef.current) {
          const infoHtml = `
            <div style="font-family:system-ui,sans-serif;padding:4px;">
              <h3 style="margin:0 0 8px;font-size:14px;font-weight:600;">🗺️ Route Found</h3>
              <div style="display:grid;grid-template-columns:auto 1fr;gap:3px 8px;font-size:12px;">
                <span style="font-weight:500;color:#666;">Destination:</span>
                <span>${data.nearest_point_name || "Water Point"}</span>
                <span style="font-weight:500;color:#666;">Walk distance:</span>
                <span><b>${(data.network_distance_meters / 1000).toFixed(2)} km</b></span>
                <span style="font-weight:500;color:#666;">Straight line:</span>
                <span>${(data.straight_line_distance_meters / 1000).toFixed(2)} km</span>
                <span style="font-weight:500;color:#666;">Walk time:</span>
                <span><b>~${data.walking_time_minutes} min</b></span>
              </div>
              <button id="clear-route-btn" style="
                width:100%;padding:6px;margin-top:8px;background:#F44336;color:white;border:none;border-radius:6px;
                cursor:pointer;font-size:11px;font-weight:600;
              ">✕ Clear Route</button>
            </div>
          `;
          popupRef.current.setHTML(infoHtml);
          setTimeout(() => {
            const btn = document.getElementById("clear-route-btn");
            if (btn) btn.onclick = () => clearRoute();
          }, 50);
        }

        // Fit map to route bounds
        const coords = data.route_geometry.coordinates;
        const bounds = new maplibregl.LngLatBounds();
        coords.forEach((c: [number, number]) => bounds.extend(c));
        map.current!.fitBounds(bounds, { padding: 80 });
      } catch (err) {
        console.error("Routing error:", err);
        alert("Could not calculate route. The OSRM service may be unavailable.");
      } finally {
        setRouting(false);
      }
    },
    [userLocation]
  );

  function clearRoute() {
    if (!map.current) return;
    if (map.current.getSource("route")) {
      map.current.removeLayer("route-line");
      map.current.removeSource("route");
    }
    popupRef.current?.remove();
  }

  function locateUser() {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { longitude, latitude } = pos.coords;
        setUserLocation([longitude, latitude]);

        if (map.current) {
          // Remove old marker
          const oldMarker = document.getElementById("user-location-marker");
          if (oldMarker) oldMarker.remove();

          // Add user marker
          const el = document.createElement("div");
          el.id = "user-location-marker";
          el.style.cssText =
            "width:16px;height:16px;background:#1976D2;border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.3);";

          new maplibregl.Marker({ element: el })
            .setLngLat([longitude, latitude])
            .setPopup(
              new maplibregl.Popup().setHTML(
                '<b>Your Location</b><br>Click a water point to get a route.'
              )
            )
            .addTo(map.current);

          map.current.flyTo({ center: [longitude, latitude], zoom: 14 });
        }
      },
      () => {
        alert("Unable to get your location. Please enable location access.");
      }
    );
  }

  function applyFilter() {
    if (!map.current || !waterPointsData.current) return;

    const filtered = {
      ...waterPointsData.current,
      features: waterPointsData.current.features.filter((f: any) => {
        const matchType =
          filterType === "all" || f.properties.water_type === filterType;
        const matchStatus =
          filterStatus === "all" || f.properties.status === filterStatus;
        return matchType && matchStatus;
      }),
    };

    (map.current.getSource("water-points") as maplibregl.GeoJSONSource)?.setData(filtered);
  }

  useEffect(() => {
    applyFilter();
  }, [filterType, filterStatus]);

  function updateColors() {
    if (!map.current || !map.current.getLayer("water-points-circle")) return;
    map.current.setPaintProperty("water-points-circle", "circle-color", [
      "match",
      ["get", colorBy === "type" ? "water_type" : "status"],
      ...Object.entries(
        colorBy === "type" ? WATER_TYPE_COLORS : STATUS_COLORS
      ).flatMap(([key, color]) => [key, color]),
      "#9E9E9E",
    ]);
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

      {/* Controls Panel */}
      <div
        style={{
          position: "absolute",
          top: 10,
          right: 60,
          background: "white",
          borderRadius: 8,
          padding: "10px 14px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          fontSize: 12,
          zIndex: 10,
          display: "flex",
          gap: 10,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
          Color:
          <select
            value={colorBy}
            onChange={(e) => setColorBy(e.target.value as "type" | "status")}
            style={{ padding: "2px 4px", borderRadius: 4, border: "1px solid #ccc" }}
          >
            <option value="type">Water Type</option>
            <option value="status">Status</option>
          </select>
        </label>

        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          style={{ padding: "2px 4px", borderRadius: 4, border: "1px solid #ccc" }}
        >
          <option value="all">All Types</option>
          <option value="tap">Tap</option>
          <option value="well">Well</option>
          <option value="borehole">Borehole</option>
          <option value="spring">Spring</option>
        </select>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          style={{ padding: "2px 4px", borderRadius: 4, border: "1px solid #ccc" }}
        >
          <option value="all">All Status</option>
          <option value="operational">Operational</option>
          <option value="broken">Broken</option>
          <option value="unknown">Unknown</option>
        </select>

        <button
          onClick={locateUser}
          style={{
            padding: "4px 10px",
            borderRadius: 4,
            border: "1px solid #1976D2",
            background: "#1976D2",
            color: "white",
            cursor: "pointer",
            fontSize: 11,
            fontWeight: 600,
          }}
        >
          📍 My Location
        </button>

        {routing && (
          <span style={{ color: "#1976D2", fontSize: 11 }}>Calculating route...</span>
        )}
      </div>

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
        <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 13 }}>
          Study Area
        </div>
        <div style={{ color: "#666", marginBottom: 8, fontSize: 11 }}>
          Lagos State, Nigeria
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
          <span
            style={{
              width: 14,
              height: 10,
              background: "#f59e0b",
              opacity: 0.5,
              border: "1.5px solid #b45309",
              borderRadius: 2,
              flexShrink: 0,
            }}
          />
          <span>State boundary</span>
        </div>
        {userLocation && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#1976D2",
                border: "2px solid white",
                flexShrink: 0,
              }}
            />
            <span>Your location</span>
          </div>
        )}
        <div style={{ borderTop: "1px solid #e5e7eb", margin: "6px 0", paddingTop: 6 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>
            {colorBy === "type" ? "Water Type" : "Status"}
          </div>
          {Object.entries(
            colorBy === "type" ? WATER_TYPE_COLORS : STATUS_COLORS
          ).map(([key, color]) => (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
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
          ))}
        </div>
      </div>
    </div>
  );
}
