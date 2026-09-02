"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

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

interface LGALevel {
  lga_name: string;
  points_tested: number;
  avg_ph: number | null;
  avg_turbidity: number | null;
  avg_coliform: number | null;
  by_status: { good: number; moderate: number; poor: number };
  points: {
    name: string;
    water_type: string;
    ph: number | null;
    turbidity: number | null;
    coliform_count: number;
    quality_status: string;
    test_date: string | null;
  }[];
}

interface Summary {
  total_tested_points: number;
  by_status: Record<string, number>;
  averages: {
    ph: number | null;
    turbidity: number | null;
    coliform_count: number | null;
    temperature: number | null;
  };
  latest_results: any[];
}

// WHO Guidelines
const WHO = {
  ph_min: 6.5,
  ph_max: 8.5,
  turbidity_max: 5, // NTU
  coliform_max: 0, // CFU/100ml — zero for safe drinking
};

const STATUS_COLORS: Record<string, string> = {
  good: "#4CAF50",
  moderate: "#FF9800",
  poor: "#F44336",
};

export default function WaterQualityPage() {
  const [lgaData, setLgaData] = useState<LGALevel[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedLGA, setSelectedLGA] = useState<string | null>(null);
  const isMobile = useMediaQuery("(max-width: 768px)");

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/api/water-quality/by-lga`).then((r) => r.json()),
      fetch(`${API_URL}/api/water-quality/summary`).then((r) => r.json()),
    ])
      .then(([lga, sum]) => {
        setLgaData(lga.lgas);
        setSummary(sum);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load water quality:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", fontFamily: "system-ui, sans-serif" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>💧</div>
          <div>Loading water quality data...</div>
        </div>
      </div>
    );
  }

  const allPoints = lgaData.flatMap((l) => l.points);
  const maxColiform = Math.max(...allPoints.map((p) => p.coliform_count), 1);
  const maxTurbidity = Math.max(...allPoints.map((p) => p.turbidity || 0), 1);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 1200, margin: "0 auto", padding: isMobile ? "12px 8px" : "24px 16px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, flexWrap: "wrap", gap: 10 }}>
        <div>
          <h1 style={{ fontSize: isMobile ? 20 : 28, fontWeight: 700, margin: 0 }}>💧 Water Quality Analysis</h1>
          <p style={{ color: "#666", margin: "4px 0 0", fontSize: 14 }}>
            Testing results across {lgaData.length} LGAs · WHO drinking water guidelines
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link href="/" style={{ padding: "8px 16px", background: "#2196F3", color: "white", borderRadius: 6, textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
            🗺️ Map
          </Link>
          <Link href="/analytics" style={{ padding: "8px 16px", background: "#607D8B", color: "white", borderRadius: 6, textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
            📊 Analytics
          </Link>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr 1fr" : "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 24 }}>
          <SummaryCard icon="🧪" label="Points Tested" value={summary.total_tested_points} color="#2196F3" />
          <SummaryCard icon="⚗️" label="Avg pH" value={summary.averages.ph ?? "N/A"} color={summary.averages.ph && summary.averages.ph >= WHO.ph_min && summary.averages.ph <= WHO.ph_max ? "#4CAF50" : "#F44336"} />
          <SummaryCard icon="🌫️" label="Avg Turbidity" value={summary.averages.turbidity ? `${summary.averages.turbidity} NTU` : "N/A"} color={summary.averages.turbidity && summary.averages.turbidity <= WHO.turbidity_max ? "#4CAF50" : "#F44336"} />
          <SummaryCard icon="🦠" label="Avg Coliform" value={summary.averages.coliform_count ?? "N/A"} color={summary.averages.coliform_count === 0 ? "#4CAF50" : "#F44336"} />
          <SummaryCard icon="🌡️" label="Avg Temp" value={summary.averages.temperature ? `${summary.averages.temperature}°C` : "N/A"} color="#607D8B" />
        </div>
      )}

      {/* WHO Guidelines Box */}
      <div style={{ background: "#FFF3E0", borderRadius: 12, padding: 16, marginBottom: 24, border: "1px solid #FFE0B2" }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15, fontWeight: 600 }}>📋 WHO Drinking Water Guidelines</h3>
        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr 1fr", gap: 12, fontSize: 13 }}>
          <div><strong>pH:</strong> 6.5 – 8.5 (acceptable range)</div>
          <div><strong>Turbidity:</strong> &lt; 5 NTU (lower is better)</div>
          <div><strong>Coliform:</strong> 0 CFU/100ml (zero tolerance)</div>
        </div>
      </div>

      {/* Quality Status Distribution */}
      {summary && (
        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 16, marginBottom: 24 }}>
          {/* Donut Chart */}
          <div style={{ background: "white", borderRadius: 12, padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
            <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>🎯 Quality Status Distribution</h3>
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 24 }}>
              <DonutChart data={summary.by_status} size={isMobile ? 120 : 160} />
              <div>
                {Object.entries(summary.by_status).map(([status, count]) => (
                  <div key={status} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <div style={{ width: 14, height: 14, borderRadius: 3, background: STATUS_COLORS[status] }} />
                    <span style={{ textTransform: "capitalize", fontSize: 13 }}>{status}: {count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Compliance Score */}
          <div style={{ background: "white", borderRadius: 12, padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
            <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>📊 WHO Compliance</h3>
            <ComplianceBar label="pH (6.5–8.5)" value={allPoints.filter((p) => p.ph && p.ph >= WHO.ph_min && p.ph <= WHO.ph_max).length} total={allPoints.length} />
            <ComplianceBar label="Turbidity (&lt;5 NTU)" value={allPoints.filter((p) => p.turbidity && p.turbidity <= WHO.turbidity_max).length} total={allPoints.length} />
            <ComplianceBar label="Coliform (0 CFU)" value={allPoints.filter((p) => p.coliform_count === 0).length} total={allPoints.length} />
            <ComplianceBar label="Overall Pass" value={allPoints.filter((p) =>
              p.ph && p.ph >= WHO.ph_min && p.ph <= WHO.ph_max &&
              p.turbidity && p.turbidity <= WHO.turbidity_max &&
              p.coliform_count === 0
            ).length} total={allPoints.length} />
          </div>
        </div>
      )}

      {/* pH Chart */}
      <div style={{ background: "white", borderRadius: 12, padding: 20, marginBottom: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
        <h3 style={{ margin: "0 0 4px", fontSize: 15, fontWeight: 600 }}>⚗️ pH Levels by Water Point</h3>
        <p style={{ margin: "0 0 16px", fontSize: 11, color: "#666" }}>Green zone = WHO acceptable range (6.5–8.5)</p>
        <div style={{ position: "relative", height: isMobile ? 300 : 350, marginBottom: 8 }}>
          {/* WHO acceptable range background */}
          <div style={{
            position: "absolute",
            left: `${(WHO.ph_min / 14) * 100}%`,
            right: `${100 - (WHO.ph_max / 14) * 100}%`,
            top: 0,
            bottom: 0,
            background: "rgba(76, 175, 80, 0.1)",
            borderLeft: "2px dashed #4CAF50",
            borderRight: "2px dashed #4CAF50",
          }} />
          {/* pH bars */}
          {allPoints.map((p, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", height: isMobile ? 18 : 22, gap: 8 }}>
              <div style={{ width: isMobile ? 80 : 140, fontSize: 10, textAlign: "right", flexShrink: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={p.name}>
                {p.name}
              </div>
              <div style={{ flex: 1, position: "relative", height: 14, background: "#f5f5f5", borderRadius: 3 }}>
                <div style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  height: "100%",
                  width: `${((p.ph ?? 0) / 14) * 100}%`,
                  background: p.ph && p.ph >= WHO.ph_min && p.ph <= WHO.ph_max ? "#4CAF50" : "#F44336",
                  borderRadius: 3,
                  transition: "width 0.3s",
                }} />
                <span style={{ position: "absolute", left: `${((p.ph ?? 0) / 14) * 100}%`, top: 0, transform: "translateX(4px)", fontSize: 10, fontWeight: 600, lineHeight: "14px" }}>
                  {p.ph}
                </span>
              </div>
            </div>
          ))}
          {/* pH axis */}
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#999", marginTop: 4, paddingLeft: isMobile ? 88 : 148 }}>
            {[0, 2, 4, 6, 6.5, 8, 8.5, 10, 12, 14].map((v) => (
              <span key={v} style={{ color: v === 6.5 || v === 8.5 ? "#4CAF50" : undefined, fontWeight: v === 6.5 || v === 8.5 ? 700 : 400 }}>{v}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Turbidity Chart */}
      <div style={{ background: "white", borderRadius: 12, padding: 20, marginBottom: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
        <h3 style={{ margin: "0 0 4px", fontSize: 15, fontWeight: 600 }}>🌫️ Turbidity (NTU) by Water Point</h3>
        <p style={{ margin: "0 0 16px", fontSize: 11, color: "#666" }}>Red line = WHO limit (5 NTU) · Lower is better</p>
        <div style={{ position: "relative" }}>
          {/* WHO limit line */}
          <div style={{
            position: "absolute",
            left: `${(WHO.turbidity_max / (maxTurbidity * 1.2)) * 100}%`,
            top: 0,
            bottom: 0,
            width: 2,
            background: "#F44336",
            zIndex: 1,
          }} />
          {allPoints.map((p, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", height: isMobile ? 18 : 22, gap: 8 }}>
              <div style={{ width: isMobile ? 80 : 140, fontSize: 10, textAlign: "right", flexShrink: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={p.name}>
                {p.name}
              </div>
              <div style={{ flex: 1, position: "relative", height: 14, background: "#f5f5f5", borderRadius: 3 }}>
                <div style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  height: "100%",
                  width: `${((p.turbidity ?? 0) / (maxTurbidity * 1.2)) * 100}%`,
                  background: p.turbidity && p.turbidity <= WHO.turbidity_max ? "#4CAF50" : "#FF9800",
                  borderRadius: 3,
                }} />
                <span style={{ position: "absolute", left: `${((p.turbidity ?? 0) / (maxTurbidity * 1.2)) * 100}%`, top: 0, transform: "translateX(4px)", fontSize: 10, fontWeight: 600, lineHeight: "14px" }}>
                  {p.turbidity}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Coliform Chart */}
      <div style={{ background: "white", borderRadius: 12, padding: 20, marginBottom: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
        <h3 style={{ margin: "0 0 4px", fontSize: 15, fontWeight: 600 }}>🦠 Coliform Count (CFU/100ml)</h3>
        <p style={{ margin: "0 0 16px", fontSize: 11, color: "#666" }}>WHO standard = 0 for safe drinking water · All bars exceed the limit</p>
        {allPoints.map((p, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", height: isMobile ? 18 : 22, gap: 8 }}>
            <div style={{ width: isMobile ? 80 : 140, fontSize: 10, textAlign: "right", flexShrink: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={p.name}>
              {p.name}
            </div>
            <div style={{ flex: 1, position: "relative", height: 14, background: "#f5f5f5", borderRadius: 3 }}>
              <div style={{
                position: "absolute",
                left: 0,
                top: 0,
                height: "100%",
                width: `${(p.coliform_count / (maxColiform * 1.1)) * 100}%`,
                background: p.coliform_count === 0 ? "#4CAF50" : p.coliform_count <= 50 ? "#FF9800" : "#F44336",
                borderRadius: 3,
              }} />
              <span style={{ position: "absolute", left: `${Math.min((p.coliform_count / (maxColiform * 1.1)) * 100 + 1, 90)}%`, top: 0, fontSize: 10, fontWeight: 600, lineHeight: "14px", color: "#333" }}>
                {p.coliform_count}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* LGA Breakdown Table */}
      <div style={{ background: "white", borderRadius: 12, padding: 20, marginBottom: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.1)", overflowX: "auto" }}>
        <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>📋 Quality by LGA</h3>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e0e0e0" }}>
              <th style={thStyle}>LGA</th>
              <th style={thStyle}>Tested</th>
              <th style={thStyle}>Avg pH</th>
              <th style={thStyle}>Avg Turbidity</th>
              <th style={thStyle}>Avg Coliform</th>
              <th style={thStyle}>Status</th>
            </tr>
          </thead>
          <tbody>
            {lgaData.map((lga) => (
              <tr
                key={lga.lga_name}
                style={{ borderBottom: "1px solid #f0f0f0", cursor: "pointer" }}
                onClick={() => setSelectedLGA(selectedLGA === lga.lga_name ? null : lga.lga_name)}
              >
                <td style={{ ...tdStyle, fontWeight: 600 }}>{lga.lga_name}</td>
                <td style={tdStyle}>{lga.points_tested}</td>
                <td style={{ ...tdStyle, color: lga.avg_ph && lga.avg_ph >= WHO.ph_min && lga.avg_ph <= WHO.ph_max ? "#4CAF50" : "#F44336" }}>
                  {lga.avg_ph}
                </td>
                <td style={{ ...tdStyle, color: lga.avg_turbidity && lga.avg_turbidity <= WHO.turbidity_max ? "#4CAF50" : "#FF9800" }}>
                  {lga.avg_turbidity} NTU
                </td>
                <td style={{ ...tdStyle, color: lga.avg_coliform === 0 ? "#4CAF50" : "#F44336" }}>
                  {lga.avg_coliform}
                </td>
                <td style={tdStyle}>
                  <div style={{ display: "flex", gap: 4 }}>
                    {lga.by_status.good > 0 && <StatusBadge status="good" count={lga.by_status.good} />}
                    {lga.by_status.moderate > 0 && <StatusBadge status="moderate" count={lga.by_status.moderate} />}
                    {lga.by_status.poor > 0 && <StatusBadge status="poor" count={lga.by_status.poor} />}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Expanded LGA Details */}
        {selectedLGA && lgaData.find((l) => l.lga_name === selectedLGA) && (
          <div style={{ marginTop: 12, padding: 16, background: "#f8f9fa", borderRadius: 8 }}>
            <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>{selectedLGA} — Individual Test Results</h4>
            {lgaData.find((l) => l.lga_name === selectedLGA)!.points.map((p, i) => (
              <div key={i} style={{ padding: "6px 0", borderBottom: "1px solid #eee", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                <div>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{p.name}</span>
                  <span style={{ color: "#999", fontSize: 11, marginLeft: 8 }}>({p.water_type} · {p.test_date})</span>
                </div>
                <div style={{ display: "flex", gap: 8, fontSize: 11 }}>
                  <span>pH: <strong>{p.ph}</strong></span>
                  <span>Turb: <strong>{p.turbidity}</strong></span>
                  <span>Coli: <strong>{p.coliform_count}</strong></span>
                  <StatusBadge status={p.quality_status} count={1} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────

function SummaryCard({ icon, label, value, color }: { icon: string; label: string; value: any; color: string }) {
  return (
    <div style={{ background: "white", borderRadius: 12, padding: 16, boxShadow: "0 1px 3px rgba(0,0,0,0.1)", borderLeft: `4px solid ${color}` }}>
      <div style={{ fontSize: 20, marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11, color: "#666" }}>{label}</div>
    </div>
  );
}

function DonutChart({ data, size }: { data: Record<string, number>; size: number }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (total === 0) return null;

  let cumulative = 0;
  const segments = Object.entries(data).map(([status, count]) => {
    const start = (cumulative / total) * 100;
    cumulative += count;
    const end = (cumulative / total) * 100;
    return `${STATUS_COLORS[status]} ${start}% ${end}%`;
  });

  return (
    <div style={{
      width: size,
      height: size,
      borderRadius: "50%",
      background: `conic-gradient(${segments.join(", ")})`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexShrink: 0,
    }}>
      <div style={{
        width: size * 0.6,
        height: size * 0.6,
        borderRadius: "50%",
        background: "white",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
      }}>
        <div style={{ fontSize: size * 0.15, fontWeight: 700 }}>{total}</div>
        <div style={{ fontSize: size * 0.07, color: "#666" }}>tested</div>
      </div>
    </div>
  );
}

function ComplianceBar({ label, value, total }: { label: string; value: number; total: number }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
        <span>{label}</span>
        <span style={{ fontWeight: 600, color: pct >= 80 ? "#4CAF50" : pct >= 50 ? "#FF9800" : "#F44336" }}>{pct}% ({value}/{total})</span>
      </div>
      <div style={{ height: 8, background: "#f0f0f0", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: pct >= 80 ? "#4CAF50" : pct >= 50 ? "#FF9800" : "#F44336", borderRadius: 4, transition: "width 0.5s" }} />
      </div>
    </div>
  );
}

function StatusBadge({ status, count }: { status: string; count: number }) {
  return (
    <span style={{
      padding: "1px 6px",
      borderRadius: 8,
      fontSize: 10,
      fontWeight: 600,
      background: STATUS_COLORS[status] || "#9E9E9E",
      color: "white",
    }}>
      {count} {status}
    </span>
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
