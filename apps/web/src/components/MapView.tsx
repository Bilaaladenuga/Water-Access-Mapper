"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);
  return matches;
}

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
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const isMobile = useMediaQuery("(max-width: 768px)");
  const [submitMode, setSubmitMode] = useState(false);
  const [submitForm, setSubmitForm] = useState<{
    show: boolean;
    lat: number;
    lon: number;
    name: string;
    water_type: string;
    description: string;
  }>({ show: false, lat: 0, lon: 0, name: "", water_type: "tap", description: "" });

  // Search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<
    { display_name: string; lat: number; lon: number }[]
  >([]);

  // Store water points data for filtering
  const waterPointsData = useRef<any>(null);
  const submitModeRef = useRef(false);

  // Keep refs in sync with state
  useEffect(() => { submitModeRef.current = submitMode; }, [submitMode]);
  const userLocationRef = useRef<[number, number] | null>(null);
  useEffect(() => { userLocationRef.current = userLocation; }, [userLocation]);

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
      loadLGABoundaries();
      loadWaterPoints();
    });

    // Handle map click for submit mode
    map.current.on("click", (e) => {
      if (!submitModeRef.current) return;
      const { lng, lat } = e.lngLat;
      setSubmitForm({ show: true, lat, lon: lng, name: "", water_type: "tap", description: "" });
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

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    try {
      const q = encodeURIComponent(searchQuery + ", Lagos, Nigeria");
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${q}&limit=5&countrycodes=ng`,
        { headers: { "User-Agent": "WaterAccessMapper/1.0" } }
      );
      const results = await res.json();
      setSearchResults(
        results.map((r: any) => ({
          display_name: r.display_name,
          lat: parseFloat(r.lat),
          lon: parseFloat(r.lon),
        }))
      );
      if (results.length === 1) {
        map.current?.flyTo({
          center: [parseFloat(results[0].lon), parseFloat(results[0].lat)],
          zoom: 15,
        });
        setSearchQuery(results[0].display_name);
      }
    } catch (err) {
      console.error("Search failed:", err);
    }
  }

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

  function loadLGABoundaries() {
    if (!map.current) return;

    fetch(`${API_URL}/api/lga/boundaries`)
      .then((res) => res.json())
      .then((data) => {
        if (!data.features || data.features.length === 0) return;
        if (map.current!.getSource("lga-boundaries")) return;

        map.current!.addSource("lga-boundaries", { type: "geojson", data });

        // LGA fill — subtle blue tint
        map.current!.addLayer({
          id: "lga-fill",
          type: "fill",
          source: "lga-boundaries",
          paint: { "fill-color": "#3b82f6", "fill-opacity": 0.06 },
        });

        // LGA labels
        map.current!.addLayer({
          id: "lga-labels",
          type: "symbol",
          source: "lga-boundaries",
          layout: {
            "text-field": ["get", "name"],
            "text-size": 10,
            "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
            "text-allow-overlap": false,
          },
          paint: {
            "text-color": "#1e3a5f",
            "text-halo-color": "white",
            "text-halo-width": 1.5,
          },
        });

        // LGA outline on hover
        map.current!.addLayer({
          id: "lga-outline",
          type: "line",
          source: "lga-boundaries",
          paint: {
            "line-color": "#3b82f6",
            "line-width": 1,
            "line-opacity": 0.5,
          },
        });
      })
      .catch((err) => console.error("Failed to load LGA boundaries:", err));
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
            ] as any,
            "circle-opacity": 0.9,
          },
        });

        // Add heatmap layer (hidden by default)
        map.current!.addLayer({
          id: "water-points-heatmap",
          type: "heatmap",
          source: "water-points",
          layout: { visibility: "none" },
          maxzoom: 15,
          paint: {
            "heatmap-weight": [
              "interpolate",
              ["linear"],
              ["get", "importance"],
              0, 0,
              6, 1,
            ],
            "heatmap-intensity": [
              "interpolate",
              ["linear"],
              ["zoom"],
              0, 1,
              15, 3,
            ],
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0, "rgba(33,102,174,0)",
              0.2, "rgb(103,169,205)",
              0.4, "rgb(209,229,240)",
              0.6, "rgb(253,219,199)",
              0.8, "rgb(244,109,67)",
              1, "rgb(165,0,38)",
            ],
            "heatmap-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              0, 2,
              15, 20,
            ],
            "heatmap-opacity": [
              "interpolate",
              ["linear"],
              ["zoom"],
              14, 0.8,
              15, 0,
            ],
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
              <div style="display:flex;gap:6px;margin-top:8px;">
                <button id="route-btn" style="
                  flex:1;padding:8px;background:#1976D2;color:white;border:none;border-radius:6px;
                  cursor:pointer;font-size:12px;font-weight:600;
                ">📍 Route</button>
                <button id="report-btn" style="
                  flex:1;padding:8px;background:#F44336;color:white;border:none;border-radius:6px;
                  cursor:pointer;font-size:12px;font-weight:600;
                ">⚠️ Report</button>
              </div>
            </div>
          `;

          popup.setLngLat(coords).setHTML(html).addTo(map.current!);

          // Fetch water quality data and add to popup
          fetch(`${API_URL}/api/water-quality/point/${props.id}`)
            .then((r) => r.json())
            .then((qData) => {
              if (qData.count > 0 && popupRef.current) {
                const q = qData.quality[0]; // latest result
                const statusColor = q.status === "good" ? "#4CAF50" : q.status === "moderate" ? "#FF9800" : "#F44336";
                const qualityHtml = `
                  <div style="margin-top:8px;padding-top:8px;border-top:1px solid #e5e7eb;">
                    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
                      <span style="font-weight:600;font-size:12px;">💧 Water Quality</span>
                      <span style="background:${statusColor};color:white;padding:1px 6px;border-radius:10px;font-size:10px;text-transform:capitalize;">${q.status}</span>
                    </div>
                    <div style="display:grid;grid-template-columns:auto 1fr;gap:2px 8px;font-size:11px;color:#555;">
                      <span>pH:</span><span>${q.ph?.toFixed(1) ?? "—"}</span>
                      <span>Turbidity:</span><span>${q.turbidity?.toFixed(1) ?? "—"} NTU</span>
                      <span>Coliform:</span><span>${q.coliform_count ?? "—"} CFU/100ml</span>
                      <span>Tested:</span><span>${q.test_date ?? "—"}</span>
                    </div>
                  </div>
                `;
                // Append quality section to the popup
                const popupEl = popupRef.current.getElement();
                const contentEl = popupEl?.querySelector('.maplibregl-popup-content');
                if (contentEl) {
                  const div = document.createElement('div');
                  div.innerHTML = qualityHtml;
                  contentEl.appendChild(div);
                }
              }
            })
            .catch(() => {}); // Ignore errors — quality data is optional

          // Attach button handlers after popup renders
          setTimeout(() => {
            const routeBtn = document.getElementById("route-btn");
            if (routeBtn) routeBtn.onclick = () => getRoute(props.id, coords);
            const reportBtn = document.getElementById("report-btn");
            if (reportBtn) reportBtn.onclick = () => showReportForm(props.id, props.name);
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
      const loc = userLocationRef.current;
      const lat = loc?.[1] || 6.6018;
      const lon = loc?.[0] || 3.3515;

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
    []
  );

  function clearRoute() {
    if (!map.current) return;
    if (map.current.getSource("route")) {
      map.current.removeLayer("route-line");
      map.current.removeSource("route");
    }
    popupRef.current?.remove();
  }

  function showReportForm(pointId: string, pointName: string) {
    setSubmitForm({ show: true, lat: 0, lon: 0, name: "", water_type: "", description: "" });
    // Show report form in popup
    if (popupRef.current) {
      const html = `
        <div style="font-family:system-ui,sans-serif;padding:4px;">
          <h3 style="margin:0 0 8px;font-size:14px;font-weight:600;">⚠️ Report Issue</h3>
          <p style="margin:0 0 8px;font-size:12px;color:#666;">${pointName}</p>
          <select id="report-type" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;margin-bottom:8px;font-size:12px;">
            <option value="broken">Broken / Not working</option>
            <option value="incorrect_location">Incorrect location</option>
            <option value="needs_repair">Needs repair</option>
            <option value="contaminated">Contaminated</option>
            <option value="other">Other</option>
          </select>
          <textarea id="report-desc" placeholder="Additional details (optional)" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;margin-bottom:8px;font-size:12px;height:60px;resize:vertical;"></textarea>
          <button id="submit-report-btn" style="
            width:100%;padding:8px;background:#F44336;color:white;border:none;border-radius:6px;
            cursor:pointer;font-size:12px;font-weight:600;
          ">Submit Report</button>
        </div>
      `;
      popupRef.current.setHTML(html);
      setTimeout(() => {
        const btn = document.getElementById("submit-report-btn");
        if (btn) btn.onclick = () => submitReport(pointId);
      }, 50);
    }
  }

  async function submitReport(pointId: string) {
    const typeEl = document.getElementById("report-type") as HTMLSelectElement;
    const descEl = document.getElementById("report-desc") as HTMLTextAreaElement;
    if (!typeEl) return;

    try {
      const res = await fetch(`${API_URL}/api/crowd/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          water_point_id: pointId,
          report_type: typeEl.value,
          description: descEl?.value || "",
          reported_by: "map_user",
        }),
      });
      if (!res.ok) throw new Error("Report failed");
      if (popupRef.current) {
        popupRef.current.setHTML(
          `<div style="font-family:system-ui,sans-serif;padding:8px;text-align:center;">
            <div style="font-size:24px;margin-bottom:4px;">✅</div>
            <b>Report submitted!</b>
            <p style="margin:4px 0 0;font-size:12px;color:#666;">Thank you for your report.</p>
          </div>`
        );
      }
    } catch (err) {
      alert("Failed to submit report. Please try again.");
    }
  }

  async function submitNewWaterPoint() {
    if (!submitForm.name) {
      alert("Please enter a name for the water point.");
      return;
    }
    try {
      const res = await fetch(`${API_URL}/api/crowd/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: submitForm.name,
          water_type: submitForm.water_type,
          latitude: submitForm.lat,
          longitude: submitForm.lon,
          description: submitForm.description,
          submitted_by: "map_user",
        }),
      });
      if (!res.ok) throw new Error("Submission failed");
      setSubmitForm({ show: false, lat: 0, lon: 0, name: "", water_type: "tap", description: "" });
      setSubmitMode(false);
      alert("Water point submitted for review! Thank you.");
    } catch (err) {
      alert("Failed to submit. Please try again.");
    }
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

      {/* Search Bar */}
      <div
        style={{
          position: "absolute",
          top: 10,
          left: isMobile ? 10 : 50,
          right: isMobile ? 10 : undefined,
          zIndex: 10,
          display: "flex",
          gap: 0,
        }}
      >
        <input
          type="text"
          placeholder={isMobile ? "🔍 Search..." : "🔍 Search location in Lagos..."}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSearch();
          }}
          style={{
            width: isMobile ? "100%" : 280,
            padding: "8px 12px",
            borderRadius: "6px 0 0 6px",
            border: "1px solid #ccc",
            fontSize: 13,
            outline: "none",
          }}
        />
        <button
          onClick={handleSearch}
          style={{
            padding: "8px 12px",
            borderRadius: "0 6px 6px 0",
            border: "1px solid #ccc",
            borderLeft: "none",
            background: "#2196F3",
            color: "white",
            cursor: "pointer",
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          Go
        </button>
      </div>

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div
          style={{
            position: "absolute",
            top: 45,
            left: 50,
            zIndex: 11,
            background: "white",
            borderRadius: 6,
            boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
            maxHeight: 200,
            overflowY: "auto",
            width: 280,
          }}
        >
          {searchResults.map((r, i) => (
            <div
              key={i}
              onClick={() => {
                map.current?.flyTo({ center: [r.lon, r.lat], zoom: 15 });
                setSearchResults([]);
                setSearchQuery(r.display_name);
              }}
              style={{
                padding: "8px 12px",
                cursor: "pointer",
                borderBottom: "1px solid #f0f0f0",
                fontSize: 12,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#f5f5f5")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "white")}
            >
              {r.display_name}
            </div>
          ))}
        </div>
      )}

      {/* Stats Bar */}
      {stats && !isMobile && (
        <div
          style={{
            position: "absolute",
            top: 55,
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
          <a
            href="/analytics"
            style={{ color: "#1976D2", fontSize: 11, textDecoration: "none", fontWeight: 500, display: "block" }}
          >
            📊 View Analytics →
          </a>
          <a
            href="/lga"
            style={{ color: "#7B1FA2", fontSize: 11, textDecoration: "none", fontWeight: 500, display: "block", marginTop: 2 }}
          >
            🏛️ LGA Breakdown →
          </a>
          <a
            href="/water-quality"
            style={{ color: "#00897B", fontSize: 11, textDecoration: "none", fontWeight: 500, display: "block", marginTop: 2 }}
          >
            💧 Water Quality →
          </a>
        </div>
      )}

      {/* Mobile Compact Stats */}
      {stats && isMobile && (
        <div
          style={{
            position: "absolute",
            bottom: 10,
            left: 10,
            right: 10,
            background: "white",
            borderRadius: 8,
            padding: "8px 12px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
            fontSize: 11,
            zIndex: 10,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontWeight: 600 }}>💧 {stats.total} points</span>
          <div style={{ display: "flex", gap: 10 }}>
            <a href="/analytics" style={{ color: "#1976D2", textDecoration: "none", fontWeight: 500 }}>📊</a>
            <a href="/lga" style={{ color: "#7B1FA2", textDecoration: "none", fontWeight: 500 }}>🏛️</a>
            <a href="/water-quality" style={{ color: "#00897B", textDecoration: "none", fontWeight: 500 }}>💧</a>
          </div>
        </div>
      )}

      {/* Mobile Menu Toggle */}
      {isMobile && (
        <button
          onClick={() => setShowMobileMenu(!showMobileMenu)}
          style={{
            position: "absolute",
            top: 10,
            right: 10,
            zIndex: 11,
            width: 40,
            height: 40,
            borderRadius: 8,
            border: "none",
            background: "white",
            boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
            fontSize: 20,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {showMobileMenu ? "✕" : "☰"}
        </button>
      )}

      {/* Controls Panel */}
      <div
        style={{
          position: "absolute",
          top: isMobile ? 60 : 10,
          right: isMobile ? 10 : 60,
          ...(isMobile ? { left: 10 } : {}),
          background: "white",
          borderRadius: 8,
          padding: "10px 14px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          fontSize: 12,
          zIndex: isMobile ? 11 : 10,
          display: isMobile && !showMobileMenu ? "none" : "flex",
          flexDirection: isMobile ? "column" : "row",
          gap: isMobile ? 8 : 10,
          alignItems: isMobile ? "stretch" : "center",
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

        <button
          onClick={() => {
            const next = !showHeatmap;
            setShowHeatmap(next);
            if (map.current) {
              map.current.setLayoutProperty(
                "water-points-heatmap",
                "visibility",
                next ? "visible" : "none"
              );
              map.current.setLayoutProperty(
                "water-points-circle",
                "visibility",
                next ? "none" : "visible"
              );
            }
          }}
          style={{
            padding: "4px 10px",
            borderRadius: 4,
            border: showHeatmap ? "1px solid #F44336" : "1px solid #607D8B",
            background: showHeatmap ? "#F44336" : "#607D8B",
            color: "white",
            cursor: "pointer",
            fontSize: 11,
            fontWeight: 600,
          }}
        >
          {showHeatmap ? "🔥 Heatmap ON" : "🗺️ Points"}
        </button>

        <button
          onClick={() => {
            setSubmitMode(!submitMode);
            if (submitMode) setSubmitForm({ show: false, lat: 0, lon: 0, name: "", water_type: "tap", description: "" });
          }}
          style={{
            padding: "4px 10px",
            borderRadius: 4,
            border: submitMode ? "1px solid #4CAF50" : "1px solid #FF9800",
            background: submitMode ? "#4CAF50" : "#FF9800",
            color: "white",
            cursor: "pointer",
            fontSize: 11,
            fontWeight: 600,
          }}
        >
          {submitMode ? "✓ Click map" : "+ Submit Point"}
        </button>

        {routing && (
          <span style={{ color: "#1976D2", fontSize: 11 }}>Calculating route...</span>
        )}

        <div style={{ borderTop: "1px solid #e0e0e0", margin: "6px 0" }} />

        <a
          href={`${API_URL}/api/export/geojson`}
          download="water_points_lagos.geojson"
          style={{
            display: "block",
            padding: "4px 10px",
            borderRadius: 4,
            border: "1px solid #4CAF50",
            background: "#4CAF50",
            color: "white",
            cursor: "pointer",
            fontSize: 11,
            fontWeight: 600,
            textDecoration: "none",
            textAlign: "center",
            marginBottom: 4,
          }}
        >
          📥 Export GeoJSON
        </a>
        <a
          href={`${API_URL}/api/export/csv`}
          download="water_points_lagos.csv"
          style={{
            display: "block",
            padding: "4px 10px",
            borderRadius: 4,
            border: "1px solid #FF9800",
            background: "#FF9800",
            color: "white",
            cursor: "pointer",
            fontSize: 11,
            fontWeight: 600,
            textDecoration: "none",
            textAlign: "center",
          }}
        >
          📥 Export CSV
        </a>
      </div>

      {/* Legend */}
      <div
        style={{
          position: "absolute",
          bottom: isMobile ? 55 : 30,
          left: 10,
          background: "white",
          borderRadius: 8,
          padding: isMobile ? "8px 10px" : "12px 16px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          fontSize: isMobile ? 10 : 12,
          zIndex: 10,
          minWidth: isMobile ? 100 : 140,
          maxWidth: isMobile ? 120 : undefined,
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

      {/* Submit Water Point Form Overlay */}
      {submitForm.show && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            background: "white",
            borderRadius: 12,
            padding: "20px 24px",
            boxShadow: "0 4px 20px rgba(0,0,0,0.25)",
            zIndex: 100,
            width: 320,
            fontFamily: "system-ui, sans-serif",
          }}
        >
          <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>
            ➕ Submit Water Point
          </h3>
          <p style={{ margin: "0 0 12px", fontSize: 12, color: "#666" }}>
            Location: {submitForm.lat.toFixed(4)}, {submitForm.lon.toFixed(4)}
          </p>

          <label style={{ display: "block", marginBottom: 8, fontSize: 12, fontWeight: 500 }}>
            Name *
            <input
              type="text"
              value={submitForm.name}
              onChange={(e) => setSubmitForm({ ...submitForm, name: e.target.value })}
              placeholder="e.g. Surulere Community Well"
              style={{
                width: "100%", padding: 8, marginTop: 4, border: "1px solid #ccc",
                borderRadius: 6, fontSize: 13, boxSizing: "border-box",
              }}
            />
          </label>

          <label style={{ display: "block", marginBottom: 8, fontSize: 12, fontWeight: 500 }}>
            Water Type
            <select
              value={submitForm.water_type}
              onChange={(e) => setSubmitForm({ ...submitForm, water_type: e.target.value })}
              style={{
                width: "100%", padding: 8, marginTop: 4, border: "1px solid #ccc",
                borderRadius: 6, fontSize: 13, boxSizing: "border-box",
              }}
            >
              <option value="tap">Tap</option>
              <option value="well">Well</option>
              <option value="borehole">Borehole</option>
              <option value="spring">Spring</option>
              <option value="rainwater">Rainwater</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label style={{ display: "block", marginBottom: 12, fontSize: 12, fontWeight: 500 }}>
            Description (optional)
            <textarea
              value={submitForm.description}
              onChange={(e) => setSubmitForm({ ...submitForm, description: e.target.value })}
              placeholder="Any additional details..."
              style={{
                width: "100%", padding: 8, marginTop: 4, border: "1px solid #ccc",
                borderRadius: 6, fontSize: 13, height: 60, resize: "vertical",
                boxSizing: "border-box",
              }}
            />
          </label>

          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setSubmitForm({ show: false, lat: 0, lon: 0, name: "", water_type: "tap", description: "" })}
              style={{
                flex: 1, padding: 10, background: "#e5e7eb", border: "none",
                borderRadius: 6, cursor: "pointer", fontSize: 13, fontWeight: 600,
              }}
            >
              Cancel
            </button>
            <button
              onClick={submitNewWaterPoint}
              style={{
                flex: 1, padding: 10, background: "#4CAF50", color: "white",
                border: "none", borderRadius: 6, cursor: "pointer",
                fontSize: 13, fontWeight: 600,
              }}
            >
              Submit
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
