"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface LGAData {
  lga_name: string;
  area_km2: number;
  total_points: number;
  operational: number;
  broken: number;
  unknown_status: number;
  density_per_km2: number;
  operational_rate_pct: number;
  taps: number;
  wells: number;
  boreholes: number;
  springs: number;
  osm_points: number;
  sample_points: number;
  crowdsourced_points: number;
}

interface LGASummary {
  total_lgas: number;
  total_points: number;
  avg_points_per_lga: number;
  min_points: number;
  max_points: number;
  lgas_with_no_data: string[];
}

const TYPE_COLORS: Record<string, string> = {
  taps: "#2196F3",
  wells: "#4CAF50",
  boreholes: "#FF9800",
  springs: "#9C27B0",
};

const STATUS_COLORS: Record<string, string> = {
  operational: "#4CAF50",
  broken: "#F44336",
  unknown: "#9E9E9E",
};

export default function LGAAnalytics() {
  const [lgas, setLgas] = useState<LGAData[]>([]);
  const [summary, setSummary] = useState<LGASummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<string>("total_points");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/api/lga/analytics`).then((r) => r.json()),
      fetch(`${API_URL}/api/lga/summary`).then((r) => r.json()),
    ]).then(([lgaData, summaryData]) => {
      setLgas(lgaData.lgas);
      setSummary(summaryData);
      setLoading(false);
    });
  }, []);

  const sorted = [...lgas].sort((a: any, b: any) => {
    const valA = a[sortBy] ?? 0;
    const valB = b[sortBy] ?? 0;
    return sortDir === "desc" ? valB - valA : valA - valB;
  });

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortDir(sortDir === "desc" ? "asc" : "desc");
    } else {
      setSortBy(field);
      setSortDir("desc");
    }
  };

  const maxPoints = Math.max(...lgas.map((l) => l.total_points), 1);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", fontFamily: "system-ui, sans-serif" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>⏳</div>
          <div>Loading LGA analytics...</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 1200, margin: "0 auto", padding: "24px 16px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>🏛️ LGA-Level Analytics</h1>
          <p style={{ color: "#666", margin: "4px 0 0", fontSize: 14 }}>
            Water access breakdown across {summary?.total_lgas} Local Government Areas in Lagos State
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Link href="/analytics" style={{ padding: "8px 16px", background: "#607D8B", color: "white", borderRadius: 6, textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
            📊 General Analytics
          </Link>
          <Link href="/" style={{ padding: "8px 16px", background: "#2196F3", color: "white", borderRadius: 6, textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
            🗺️ Back to Map
          </Link>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 24 }}>
          <StatCard label="Total LGAs" value={summary.total_lgas} icon="🏛️" color="#2196F3" />
          <StatCard label="Total Points" value={summary.total_points} icon="💧" color="#4CAF50" />
          <StatCard label="Avg per LGA" value={summary.avg_points_per_lga} icon="📊" color="#FF9800" />
          <StatCard label="Max in one LGA" value={summary.max_points} icon="🏆" color="#9C27B0" />
          <StatCard label="Min in one LGA" value={summary.min_points ?? 0} icon="📉" color="#F44336" />
        </div>
      )}

      {/* Bar Chart: Points by LGA */}
      <div style={{ background: "white", borderRadius: 12, padding: 20, marginBottom: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>📊 Water Points by LGA</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {sorted.map((lga) => (
            <div key={lga.lga_name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 130, fontSize: 12, fontWeight: 500, textAlign: "right", flexShrink: 0 }}>
                {lga.lga_name}
              </div>
              <div style={{ flex: 1, height: 22, background: "#f0f0f0", borderRadius: 4, overflow: "hidden", position: "relative" }}>
                {/* Operational portion */}
                <div style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  height: "100%",
                  width: `${(lga.operational / maxPoints) * 100}%`,
                  background: STATUS_COLORS.operational,
                  borderRadius: "4px 0 0 4px",
                }} />
                {/* Broken portion */}
                <div style={{
                  position: "absolute",
                  left: `${(lga.operational / maxPoints) * 100}%`,
                  top: 0,
                  height: "100%",
                  width: `${(lga.broken / maxPoints) * 100}%`,
                  background: STATUS_COLORS.broken,
                }} />
                {/* Unknown portion */}
                <div style={{
                  position: "absolute",
                  left: `${((lga.operational + lga.broken) / maxPoints) * 100}%`,
                  top: 0,
                  height: "100%",
                  width: `${(lga.unknown_status / maxPoints) * 100}%`,
                  background: STATUS_COLORS.unknown,
                  borderRadius: "0 4px 4px 0",
                }} />
              </div>
              <div style={{ width: 40, fontSize: 12, fontWeight: 600, textAlign: "right" }}>
                {lga.total_points}
              </div>
            </div>
          ))}
        </div>
        {/* Legend */}
        <div style={{ display: "flex", gap: 16, marginTop: 12, justifyContent: "center" }}>
          {Object.entries(STATUS_COLORS).map(([key, color]) => (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11 }}>
              <div style={{ width: 12, height: 12, borderRadius: 2, background: color }} />
              <span style={{ textTransform: "capitalize" }}>{key}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Data Table */}
      <div style={{ background: "white", borderRadius: 12, padding: 20, marginBottom: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.1)", overflowX: "auto" }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>📋 Detailed LGA Data</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e0e0e0" }}>
              <th style={thStyle}>#</th>
              {[
                ["lga_name", "LGA Name"],
                ["area_km2", "Area (km²)"],
                ["total_points", "Total"],
                ["operational", "Operational"],
                ["broken", "Broken"],
                ["density_per_km2", "Density/km²"],
                ["operational_rate_pct", "Op. Rate"],
                ["taps", "Taps"],
                ["wells", "Wells"],
                ["boreholes", "Boreholes"],
              ].map(([key, label]) => (
                <th
                  key={key}
                  style={{ ...thStyle, cursor: "pointer", userSelect: "none" }}
                  onClick={() => handleSort(key)}
                >
                  {label} {sortBy === key ? (sortDir === "desc" ? "↓" : "↑") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((lga, i) => (
              <tr key={lga.lga_name} style={{ borderBottom: "1px solid #f0f0f0" }}>
                <td style={tdStyle}>{i + 1}</td>
                <td style={{ ...tdStyle, fontWeight: 600 }}>{lga.lga_name}</td>
                <td style={tdStyle}>{lga.area_km2.toFixed(1)}</td>
                <td style={{ ...tdStyle, fontWeight: 600 }}>{lga.total_points}</td>
                <td style={{ ...tdStyle, color: STATUS_COLORS.operational }}>{lga.operational}</td>
                <td style={{ ...tdStyle, color: STATUS_COLORS.broken }}>{lga.broken}</td>
                <td style={tdStyle}>{lga.density_per_km2.toFixed(2)}</td>
                <td style={tdStyle}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: 10,
                    fontSize: 11,
                    fontWeight: 600,
                    background: lga.operational_rate_pct >= 70 ? "#E8F5E9" : lga.operational_rate_pct >= 40 ? "#FFF3E0" : "#FFEBEE",
                    color: lga.operational_rate_pct >= 70 ? "#2E7D32" : lga.operational_rate_pct >= 40 ? "#E65100" : "#C62828",
                  }}>
                    {lga.operational_rate_pct}%
                  </span>
                </td>
                <td style={tdStyle}>{lga.taps}</td>
                <td style={tdStyle}>{lga.wells}</td>
                <td style={tdStyle}>{lga.boreholes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Density Heatmap Grid */}
      <div style={{ background: "white", borderRadius: 12, padding: 20, marginBottom: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>🗺️ LGA Density Comparison</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 8 }}>
          {[...lgas]
            .sort((a, b) => b.density_per_km2 - a.density_per_km2)
            .map((lga) => {
              const maxDensity = Math.max(...lgas.map((l) => l.density_per_km2), 0.01);
              const intensity = lga.density_per_km2 / maxDensity;
              return (
                <div
                  key={lga.lga_name}
                  style={{
                    padding: 12,
                    borderRadius: 8,
                    background: `rgba(33, 150, 243, ${0.1 + intensity * 0.6})`,
                    border: `1px solid rgba(33, 150, 243, ${0.2 + intensity * 0.5})`,
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{lga.lga_name}</div>
                  <div style={{ fontSize: 20, fontWeight: 700, margin: "4px 0" }}>
                    {lga.density_per_km2.toFixed(2)}
                  </div>
                  <div style={{ fontSize: 10, color: "#666" }}>points/km²</div>
                </div>
              );
            })}
        </div>
      </div>

      {/* Export Buttons */}
      <div style={{ background: "white", borderRadius: 12, padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>📥 Export Data</h2>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <a
            href={`${API_URL}/api/export/geojson`}
            download="water_points_lagos.geojson"
            style={{ padding: "10px 20px", background: "#4CAF50", color: "white", borderRadius: 6, textDecoration: "none", fontSize: 13, fontWeight: 600 }}
          >
            📥 Download GeoJSON
          </a>
          <a
            href={`${API_URL}/api/export/csv`}
            download="water_points_lagos.csv"
            style={{ padding: "10px 20px", background: "#FF9800", color: "white", borderRadius: 6, textDecoration: "none", fontSize: 13, fontWeight: 600 }}
          >
            📥 Download CSV
          </a>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: number; icon: string; color: string }) {
  return (
    <div style={{ background: "white", borderRadius: 12, padding: 16, boxShadow: "0 1px 3px rgba(0,0,0,0.1)", borderLeft: `4px solid ${color}` }}>
      <div style={{ fontSize: 24, marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 12, color: "#666" }}>{label}</div>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: "8px 10px",
  textAlign: "left",
  fontSize: 12,
  fontWeight: 600,
  color: "#666",
  whiteSpace: "nowrap",
};

const tdStyle: React.CSSProperties = {
  padding: "8px 10px",
  fontSize: 13,
  whiteSpace: "nowrap",
};
