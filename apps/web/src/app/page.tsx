"use client";

import { useEffect, useState } from "react";

interface HealthStatus {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export default function Home() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiBase}/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch((err) =>
        setError(
          `Could not reach backend at ${apiBase}. Make sure the API server is running.`
        )
      );
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-2xl rounded-lg border border-gray-200 bg-white p-8 shadow-lg dark:border-gray-700 dark:bg-gray-800">
        <h1 className="mb-2 text-3xl font-bold text-gray-900 dark:text-white">
          🗺️ Water Access Mapper
        </h1>
        <p className="mb-6 text-gray-600 dark:text-gray-300">
          A geospatial web application for mapping, analyzing, and improving
          water point accessibility in underserved communities.
        </p>

        {/* Backend connection status */}
        <div className="mb-6 rounded-md border p-4">
          {health ? (
            <div>
              <p className="font-semibold text-green-700">
                ✅ Backend connected
              </p>
              <p className="text-sm text-gray-600">
                {health.service} v{health.version} — status: {health.status}
              </p>
              <p className="text-xs text-gray-400">
                Last checked: {new Date(health.timestamp).toLocaleString()}
              </p>
            </div>
          ) : (
            <div>
              <p className="font-semibold text-yellow-600">
                ⏳ Connecting to backend...
              </p>
              {error && (
                <p className="mt-1 text-sm text-red-600">{error}</p>
              )}
            </div>
          )}
        </div>

        {/* Map placeholder */}
        <div className="mb-6 h-64 rounded-md border-2 border-dashed border-gray-300 bg-gray-100 flex items-center justify-center dark:border-gray-600 dark:bg-gray-700">
          <span className="text-gray-400 dark:text-gray-500">
            🌍 Interactive map coming in Phase 4
          </span>
        </div>

        {/* Tech stack cards */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-md bg-blue-50 p-3 dark:bg-blue-900/20">
            <span className="font-semibold text-blue-700 dark:text-blue-300">
              GIS + PostGIS
            </span>
            <p className="text-blue-600 dark:text-blue-400">
              Spatial analysis & queries
            </p>
          </div>
          <div className="rounded-md bg-green-50 p-3 dark:bg-green-900/20">
            <span className="font-semibold text-green-700 dark:text-green-300">
              OSRM Routing
            </span>
            <p className="text-green-600 dark:text-green-400">
              Walking route calculation
            </p>
          </div>
          <div className="rounded-md bg-purple-50 p-3 dark:bg-purple-900/20">
            <span className="font-semibold text-purple-700 dark:text-purple-300">
              Python + GeoPandas
            </span>
            <p className="text-purple-600 dark:text-purple-400">
              Geospatial data processing
            </p>
          </div>
          <div className="rounded-md bg-orange-50 p-3 dark:bg-orange-900/20">
            <span className="font-semibold text-orange-700 dark:text-orange-300">
              Next.js + FastAPI
            </span>
            <p className="text-orange-600 dark:text-orange-400">
              Full-stack architecture
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
