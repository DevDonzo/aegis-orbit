"use client";

import { CesiumWrapper } from "@/components/cesium/CesiumWrapper";
import { CollisionAlerts } from "@/components/dashboard/CollisionAlerts";
import { MissionOverview } from "@/components/dashboard/MissionOverview";
import { SystemStatus } from "@/components/dashboard/SystemStatus";
import { TelemetryPanel } from "@/components/dashboard/TelemetryPanel";
import { TimelineScrubber } from "@/components/dashboard/TimelineScrubber";
import { useSimulationPolling } from "@/hooks/useSimulationPolling";
import { useSimulationStore } from "@/store/useSimulationStore";

export default function MissionControlPage() {
  useSimulationPolling();

  const metrics = useSimulationStore((state) => state.metrics);
  const connectionState = useSimulationStore((state) => state.connectionState);

  return (
    <main className="relative min-h-screen overflow-hidden bg-cosmic-950">
      <CesiumWrapper />
      <div className="pointer-events-none absolute inset-0 z-10 bg-[radial-gradient(circle_at_50%_120%,rgba(5,9,20,0),rgba(5,9,20,0.82))]" />
      <div className="pointer-events-none absolute inset-0 z-10 grid-overlay opacity-55" />
      <div className="mission-scan pointer-events-none absolute inset-0 z-10" />

      <div className="absolute inset-0 z-20 p-4 md:p-5 lg:p-6">
        <div className="grid h-full grid-cols-12 grid-rows-[auto_auto_minmax(0,1fr)_auto] gap-4">
          <header className="pointer-events-auto col-span-12 flex flex-wrap items-start justify-between gap-4">
            <div className="hud-panel px-4 py-3 md:px-5">
              <p className="section-kicker">Orbital Command</p>
              <h1 className="mt-1 text-xl font-semibold tracking-[0.08em] text-white md:text-2xl">
                On-Orbit Collision Predictor
              </h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-300/82">
                Tactical visualization, conjunction scoring, and machine-learning-backed distance forecasting for a live
                orbital catalog.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <div className="metric-chip">
                <span className="metric-chip__label">Renderer</span>
                <span className="telemetry-value">{metrics.fps.toFixed(1)} FPS</span>
              </div>
              <div className="metric-chip">
                <span className="metric-chip__label">Alerts</span>
                <span className="telemetry-value">{metrics.activeAlertCount.toString().padStart(2, "0")}</span>
              </div>
              <div className="metric-chip">
                <span className="metric-chip__label">Link</span>
                <span className={`status-dot status-dot--${connectionState}`} />
                <span className="telemetry-value capitalize">{connectionState}</span>
              </div>
            </div>
          </header>

          <section className="col-span-12 lg:col-span-8">
            <MissionOverview />
          </section>

          <section className="col-span-12 lg:col-span-4">
            <SystemStatus />
          </section>

          <section className="col-span-12 md:col-span-6 lg:col-span-4 lg:self-start">
            <TelemetryPanel />
          </section>

          <div className="col-span-12 hidden lg:col-span-4 lg:block" />

          <section className="col-span-12 md:col-span-6 lg:col-span-4 lg:self-start">
            <CollisionAlerts />
          </section>

          <section className="col-span-12">
            <TimelineScrubber />
          </section>
        </div>
      </div>
    </main>
  );
}
