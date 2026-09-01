"use client";

import { useEffect } from "react";
import MapView from "@/components/MapView";

export default function Home() {
  useEffect(() => {
    document.body.classList.add("no-scroll");
    return () => {
      document.body.classList.remove("no-scroll");
    };
  }, []);

  return (
    <main style={{ width: "100%", height: "100vh" }}>
      <MapView />
    </main>
  );
}
