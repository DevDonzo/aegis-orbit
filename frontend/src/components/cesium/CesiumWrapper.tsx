"use client";

import dynamic from "next/dynamic";

const CesiumViewer = dynamic(() => import("@/components/cesium/CesiumViewer"), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 flex items-center justify-center bg-cosmic-950/75">
      <div className="hud-panel px-5 py-3">
        <p className="hud-title">Scene Initialization</p>
        <p className="mt-1 text-sm text-slate-200">Bootstrapping orbital renderer...</p>
      </div>
    </div>
  )
});

export function CesiumWrapper() {
  return <CesiumViewer />;
}
