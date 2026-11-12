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

const STATUS_COLORS: Record<string, string> = {
  operational: "#4CAF50",
  broken: "#F44336",
  unknown: "#9E9E9E",
  abandoned: "#795548",
};

const TYPE_COLORS: Record<string, string> = {
  tap: "#2196F3",
  well: "#4CAF50",
  borehole: "#FF9800",
  waterworks: "#795548",
  spring: "#9C27B0",
  rainwater: "#00BCD4",
  other: "#607D8B",
};

const SOURCE_COLORS: Record<string, string> = {
  grid: "#7E57C2",
  osm: "#1976D2",
  sample: "#FF9800",
  crowdsourced: "#4CAF50",
};

interface Summary {
  total_water_points: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  by_source: Record<string, number>;
  operational_rate: number;
  operational_recorded: number;
  broken_recorded: number;
  status_assessed: number;
  status_unknown: number;
  status_estimated: number;
  estimated_assessed: number;
  estimated_operational: number;
  estimated_broken: number;
  estimated_operational_rate: number;
  pending_submissions: number;
  unresolved_reports: number;
}

interface Breakdown {
  status_chart: { label: string; value: number }[];
  status_chart_recorded: { label: string; value: number }[];
  status_chart_estimated: { label: string; value: number }[];
  type_chart: { label: string; value: number }[];
  source_chart: { label: string; value: number }[];
}

interface Coverage {
  study_area_km2: number;
  total_points: number;
  density_per_km2: number;
  average_nearest_neighbor_m: number;
  min_nearest_neighbor_m: number;
  max_nearest_neighbor_m: number;
  nearest_neighbor_distribution: {
    within_500m: number;
    between_500m_1km: number;
    between_1km_2km: number;
    beyond_2km: number;
  };
}

interface DataQuality {
  total_points: number;
  named_points: number;
  unnamed_points: number;
  valid_coordinates: number;
  invalid_coordinates: number;
  verified_points: number;
  unverified_points: number;
  quality_score: number;
}

function StatCard({ title, value, subtitle, color = "#1976D2" }: {
  title: string; value: string | number; subtitle?: string; color?: string;
}) {
  return (
    <div style={{
      background: "white", borderRadius: 12, padding: "20px 24px",
      boxShadow: "0 2px 8px rgba(0,0,0,0.08)", flex: "1 1 200px", minWidth: 180,
    }}>
      <div style={{ fontSize: 12, color: "#666", fontWeight: 500, marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 32, fontWeight: 700, color, lineHeight: 1.2 }}>{value}</div>
      {subtitle && <div style={{ fontSize: 11, color: "#999", marginTop: 4 }}>{subtitle}</div>}
    </div>
  );
}

function BarChart({ data, colors, title }: {
  data: { label: string; value: number }[];
  colors: Record<string, string>;
  title: string;
}) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div style={{
      background: "white", borderRadius: 12, padding: "20px 24px",
      boxShadow: "0 2px 8px rgba(0,0,0,0.08)", flex: "1 1 300px",
    }}>
      <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>{title}</h3>
      {data.map((item) => (
        <div key={item.label} style={{ marginBottom: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 3 }}>
            <span style={{ textTransform: "capitalize", fontWeight: 500 }}>{item.label}</span>
            <span style={{ color: "#666" }}>{item.value}</span>
          </div>
          <div style={{ background: "#f0f0f0", borderRadius: 6, height: 20, overflow: "hidden" }}>
            <div style={{
              width: `${(item.value / max) * 100}%`,
              height: "100%",
              background: colors[item.label] || "#9E9E9E",
              borderRadius: 6,
              transition: "width 0.5s ease",
            }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function DonutChart({ data, colors, title }: {
  data: { label: string; value: number }[];
  colors: Record<string, string>;
  title: string;
}) {
  const total = data.reduce((sum, d) => sum + d.value, 0) || 1;
  let cumulative = 0;

  const segments = data.map((item) => {
    const pct = (item.value / total) * 100;
    const start = cumulative;
    cumulative += pct;
    return { ...item, start, pct };
  });

  const gradientParts: string[] = [];
  let pos = 0;
  segments.forEach((seg) => {
    gradientParts.push(`${colors[seg.label] || "#9E9E9E"} ${pos}% ${pos + seg.pct}%`);
    pos += seg.pct;
  });

  return (
    <div style={{
      background: "white", borderRadius: 12, padding: "20px 24px",
      boxShadow: "0 2px 8px rgba(0,0,0,0.08)", flex: "1 1 280px",
    }}>
      <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>{title}</h3>
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <div style={{
          width: 120, height: 120, borderRadius: "50%",
          background: `conic-gradient(${gradientParts.join(", ")})`,
          flexShrink: 0,
        }}>
          <div style={{
            width: 120, height: 120, borderRadius: "50%", background: "white",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 20, fontWeight: 700, color: "#333",
          }}>
            {total}
          </div>
        </div>
        <div style={{ flex: 1 }}>
          {segments.map((seg) => (
            <div key={seg.label} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, fontSize: 12 }}>
              <span style={{
                width: 12, height: 12, borderRadius: 3, flexShrink: 0,
                background: colors[seg.label] || "#9E9E9E",
              }} />
              <span style={{ flex: 1, textTransform: "capitalize" }}>{seg.label}</span>
              <span style={{ fontWeight: 600 }}>{seg.value}</span>
              <span style={{ color: "#999", fontSize: 11 }}>({seg.pct.toFixed(0)}%)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ProximityBar({ label, value, maxVal, total }: {
  label: string; value: number; maxVal: number; total: number;
}) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 2 }}>
        <span>{label}</span>
        <span style={{ fontWeight: 600 }}>
          {value} {total > 0 && <span style={{ color: "#999", fontWeight: 400 }}>({((value / total) * 100).toFixed(0)}%)</span>}
        </span>
      </div>
      <div style={{ background: "#f0f0f0", borderRadius: 4, height: 14, overflow: "hidden" }}>
        <div style={{
          width: `${(value / maxVal) * 100}%`, height: "100%",
          background: "#1976D2", borderRadius: 4, minWidth: value > 0 ? 4 : 0,
        }} />
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [breakdown, setBreakdown] = useState<Breakdown | null>(null);
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [dataQuality, setDataQuality] = useState<DataQuality | null>(null);
  const [loading, setLoading] = useState(true);
  const isMobile = useMediaQuery("(max-width: 768px)");

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/api/analytics/summary`).then((r) => r.json()),
      fetch(`${API_URL}/api/analytics/breakdown`).then((r) => r.json()),
      fetch(`${API_URL}/api/analytics/coverage`).then((r) => r.json()),
      fetch(`${API_URL}/api/analytics/data-quality`).then((r) => r.json()),
    ])
      .then(([s, b, c, q]) => {
        setSummary(s);
        setBreakdown(b);
        setCoverage(c);
        setDataQuality(q);
      })
      .catch((err) => console.error("Failed to load analytics:", err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: "center", fontFamily: "system-ui, sans-serif" }}>
        <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
        <div>Loading analytics...</div>
      </div>
    );
  }

  const sourceSubtitle = summary
    ? Object.entries(summary.by_source)
        .sort((a, b) => b[1] - a[1])
        .map(([label, count]) => `${count} ${label}`)
        .join(" · ")
    : "";

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", background: "#f5f5f5", minHeight: "100vh" }}>
      {/* Header */}
      <div style={{
        background: "white", padding: "16px 20px",
        boxShadow: "0 1px 4px rgba(0,0,0,0.1)", display: "flex",
        alignItems: "center", justifyContent: "space-between",
        flexWrap: "wrap", gap: 10,
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>📊 Analytics Dashboard</h1>
          <div style={{ fontSize: 12, color: "#666", marginTop: 2 }}>Water Access Mapper — Lagos State</div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link href="/water-quality" style={{
            padding: "8px 16px", background: "#00897B", color: "white",
            borderRadius: 6, textDecoration: "none", fontSize: 13, fontWeight: 600,
          }}>
            💧 Water Quality
          </Link>
          <Link href="/lga" style={{
            padding: "8px 16px", background: "#607D8B", color: "white",
            borderRadius: 6, textDecoration: "none", fontSize: 13, fontWeight: 600,
          }}>
            🏛️ LGA Analytics
          </Link>
          <Link href="/" style={{
            padding: "8px 16px", background: "#1976D2", color: "white",
            borderRadius: 6, textDecoration: "none", fontSize: 13, fontWeight: 600,
          }}>
            🗺️ Map
          </Link>
        </div>
      </div>

      <div style={{ padding: isMobile ? "16px 12px" : "24px 32px", maxWidth: 1400, margin: "0 auto" }}>
        {/* Summary Cards */}
        {summary && (
          <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
            <StatCard title="Total Water Points" value={summary.total_water_points} color="#1976D2" />
            <StatCard
              title="Operational"
              value={summary.by_status.operational || 0}
              subtitle={
                summary.status_assessed > 0
                  ? `${summary.operational_recorded} recorded + ${summary.estimated_operational} modelled`
                  : "no status recorded"
              }
              color="#4CAF50"
            />
            <StatCard
              title="Broken"
              value={summary.by_status.broken || 0}
              subtitle={
                summary.status_assessed > 0
                  ? `${summary.broken_recorded} recorded + ${summary.estimated_broken} modelled`
                  : "reported non-functional"
              }
              color="#F44336"
            />
            <StatCard
              title="Modelled Status"
              value={summary.status_estimated}
              subtitle={
                summary.estimated_assessed > 0
                  ? `~${summary.estimated_operational_rate}% assumed operational (GRID)`
                  : "none"
              }
              color="#FFA000"
            />
            <StatCard
              title="Recorded Rate"
              value={summary.status_assessed > 0 ? `${summary.operational_rate}%` : "—"}
              subtitle={
                summary.status_assessed > 0
                  ? `operational, of ${summary.status_assessed} with a recorded status`
                  : "no recorded status"
              }
              color="#00897B"
            />
            <StatCard
              title="Status Unknown"
              value={summary.status_unknown}
              subtitle="source dataset has no status field"
              color="#9E9E9E"
            />
            <StatCard
              title="Data Sources"
              value={Object.keys(summary.by_source).length}
              subtitle={sourceSubtitle}
              color="#FF9800"
            />
            <StatCard title="Pending Reviews" value={summary.pending_submissions} subtitle={`${summary.unresolved_reports} unresolved reports`} color="#9C27B0" />
          </div>
        )}

        {summary && summary.status_assessed > 0 && (
          <div style={{
            background: "#FFF8E1", border: "1px solid #FFE082", borderRadius: 12,
            padding: "10px 14px", marginBottom: 20, fontSize: 12, color: "#6D4C41",
          }}>
            <strong>{summary.status_assessed}</strong> of <strong>{summary.total_water_points}</strong>{" "}
            points have a status <em>recorded in the source data</em>, and the recorded
            operational rate (<strong>{summary.operational_rate}%</strong>) is calculated over
            those only. A further <strong>{summary.status_estimated}</strong> points have a{" "}
            <em>modelled</em> status — the GRID dataset records no functionality, so a{" "}
            {summary.estimated_operational_rate}% operational assumption is applied and flagged
            <code> status_estimated </code>(<strong>{summary.estimated_operational}</strong> assumed
            operational, <strong>{summary.estimated_broken}</strong> assumed broken). The remaining{" "}
            {summary.status_unknown} points have no status at all and are counted as <em>unknown</em>,
            not broken. Modelled values are not field measurements.
          </div>
        )}

        {/* Charts Row 1 */}
        {breakdown && (
          <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
            <DonutChart data={breakdown.status_chart} colors={STATUS_COLORS} title="By Status" />
            <DonutChart data={breakdown.source_chart} colors={SOURCE_COLORS} title="By Source" />
            <BarChart data={breakdown.type_chart} colors={TYPE_COLORS} title="By Water Type" />
            <BarChart
              data={[
                {
                  label: "recorded",
                  value: breakdown.status_chart_recorded.reduce((sum, d) => sum + d.value, 0),
                },
                {
                  label: "modelled",
                  value: breakdown.status_chart_estimated.reduce((sum, d) => sum + d.value, 0),
                },
              ]}
              colors={{ recorded: "#00897B", modelled: "#FFA000" }}
              title="Status Provenance"
            />
          </div>
        )}

        {/* Coverage Analysis */}
        {coverage && (
          <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
            <div style={{
              background: "white", borderRadius: 12, padding: "20px 24px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.08)", flex: "1 1 300px",
            }}>
              <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>🗺️ Coverage Analysis</h3>
              <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 12, fontSize: 13 }}>
                <div>
                  <div style={{ color: "#666", fontSize: 11 }}>Study Area</div>
                  <div style={{ fontWeight: 700, fontSize: 20 }}>{coverage.study_area_km2} km²</div>
                </div>
                <div>
                  <div style={{ color: "#666", fontSize: 11 }}>Density</div>
                  <div style={{ fontWeight: 700, fontSize: 20 }}>{coverage.density_per_km2} /km²</div>
                </div>
                <div>
                  <div style={{ color: "#666", fontSize: 11 }}>Avg Nearest Neighbor</div>
                  <div style={{ fontWeight: 700, fontSize: 20 }}>{coverage.average_nearest_neighbor_m} m</div>
                </div>
                <div>
                  <div style={{ color: "#666", fontSize: 11 }}>Min Distance</div>
                  <div style={{ fontWeight: 700, fontSize: 20 }}>{coverage.min_nearest_neighbor_m} m</div>
                </div>
              </div>
            </div>

            <div style={{
              background: "white", borderRadius: 12, padding: "20px 24px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.08)", flex: "1 1 300px",
            }}>
              <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>📍 Nearest Neighbour Distance</h3>
              <div style={{ fontSize: 12, color: "#666", marginBottom: 12 }}>
                How far each point is from the closest other point (n = {coverage.total_points})
              </div>
              <ProximityBar label="Within 500m" value={coverage.nearest_neighbor_distribution.within_500m} maxVal={Math.max(...Object.values(coverage.nearest_neighbor_distribution), 1)} total={coverage.total_points} />
              <ProximityBar label="500m — 1km" value={coverage.nearest_neighbor_distribution.between_500m_1km} maxVal={Math.max(...Object.values(coverage.nearest_neighbor_distribution), 1)} total={coverage.total_points} />
              <ProximityBar label="1km — 2km" value={coverage.nearest_neighbor_distribution.between_1km_2km} maxVal={Math.max(...Object.values(coverage.nearest_neighbor_distribution), 1)} total={coverage.total_points} />
              <ProximityBar label="Beyond 2km" value={coverage.nearest_neighbor_distribution.beyond_2km} maxVal={Math.max(...Object.values(coverage.nearest_neighbor_distribution), 1)} total={coverage.total_points} />
              <div style={{ fontSize: 11, color: "#999", marginTop: 10 }}>
                Furthest nearest-neighbour gap: {coverage.max_nearest_neighbor_m} m
              </div>
            </div>
          </div>
        )}

        {/* Data Quality */}
        {dataQuality && (
          <div style={{
            background: "white", borderRadius: 12, padding: "20px 24px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.08)", marginBottom: 24,
          }}>
            <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>✅ Data Quality</h3>
            <div style={{ display: "flex", gap: 32, flexWrap: "wrap", fontSize: 13 }}>
              <div>
                <div style={{ color: "#666", fontSize: 11, marginBottom: 4 }}>Quality Score</div>
                <div style={{
                  width: 80, height: 80, borderRadius: "50%", display: "flex",
                  alignItems: "center", justifyContent: "center",
                  background: `conic-gradient(#4CAF50 ${dataQuality.quality_score}%, #f0f0f0 ${dataQuality.quality_score}%)`,
                }}>
                  <div style={{
                    width: 60, height: 60, borderRadius: "50%", background: "white",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontWeight: 700, fontSize: 18,
                  }}>
                    {dataQuality.quality_score}
                  </div>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 12 }}>
                <div>
                  <div style={{ color: "#666", fontSize: 11 }}>Named Points</div>
                  <div style={{ fontWeight: 700 }}>{dataQuality.named_points} / {dataQuality.total_points}</div>
                </div>
                <div>
                  <div style={{ color: "#666", fontSize: 11 }}>Unnamed Points</div>
                  <div style={{ fontWeight: 700 }}>{dataQuality.unnamed_points}</div>
                </div>
                <div>
                  <div style={{ color: "#666", fontSize: 11 }}>Valid Coordinates</div>
                  <div style={{ fontWeight: 700 }}>{dataQuality.valid_coordinates} / {dataQuality.total_points}</div>
                </div>
                <div>
                  <div style={{ color: "#666", fontSize: 11 }}>Verified Points</div>
                  <div style={{ fontWeight: 700 }}>{dataQuality.verified_points} / {dataQuality.total_points}</div>
                </div>
              </div>
            </div>
            <div style={{ fontSize: 11, color: "#999", marginTop: 12 }}>
              Named = has a specific place name rather than a generic label. Verified = confirmed
              through the crowdsourcing workflow; points imported from GRID and OSM are unverified
              by design, which is why the verified count is low.
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ textAlign: "center", fontSize: 11, color: "#999", padding: "16px 0" }}>
          Water Access Mapper — Phase 9 Analytics · Data sources: GRID baseline + OpenStreetMap + sample + crowdsourced
        </div>
      </div>
    </div>
  );
}
