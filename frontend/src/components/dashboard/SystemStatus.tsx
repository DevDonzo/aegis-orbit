"use client";

import { Activity, BrainCircuit, Radar, Satellite } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSimulationStore } from "@/store/useSimulationStore";

function mapStateToBadgeVariant(state: ReturnType<typeof useSimulationStore.getState>["connectionState"]) {
  if (state === "online") return "low" as const;
  if (state === "degraded") return "moderate" as const;
  if (state === "offline") return "critical" as const;
  return "neutral" as const;
}

export function SystemStatus() {
  const connectionState = useSimulationStore((state) => state.connectionState);
  const metrics = useSimulationStore((state) => state.metrics);
  const propagationMode = useSimulationStore((state) => state.propagationMode);
  const mlStatus = useSimulationStore((state) => state.mlStatus);
  const selectedEntityId = useSimulationStore((state) => state.selectedEntityId);
  const selectedCollisionId = useSimulationStore((state) => state.selectedCollisionId);
  const satellites = useSimulationStore((state) => state.satellites);
  const collisionEvents = useSimulationStore((state) => state.collisionEvents);

  const selectedSatellite = selectedEntityId ? satellites[selectedEntityId] : null;
  const selectedCollision = collisionEvents.find((event) => event.id === selectedCollisionId) ?? collisionEvents[0] ?? null;

  return (
    <Card className="pointer-events-auto h-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="section-kicker">System Matrix</p>
            <CardTitle className="mt-1 text-left">Runtime Status</CardTitle>
          </div>
          <Badge variant={mapStateToBadgeVariant(connectionState)}>{connectionState}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-slate-200">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="summary-tile">
            <span className="summary-tile__label">Renderer</span>
            <span className="summary-tile__value">{metrics.fps.toFixed(1)} FPS</span>
          </div>
          <div className="summary-tile">
            <span className="summary-tile__label">API Latency</span>
            <span className="summary-tile__value">{metrics.apiLatencyMs} ms</span>
          </div>
          <div className="summary-tile">
            <span className="summary-tile__label">Tracked Objects</span>
            <span className="summary-tile__value">{metrics.trackedObjectCount.toString().padStart(2, "0")}</span>
          </div>
          <div className="summary-tile">
            <span className="summary-tile__label">WebSocket</span>
            <span className="summary-tile__value">{metrics.wsConnected ? "live" : "polling"}</span>
          </div>
        </div>

        <div className="space-y-3 rounded-sm border border-white/10 bg-white/4 p-4">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-2 text-slate-200">
              <BrainCircuit className="h-4 w-4 text-neon-cyan" />
              Model Registry
            </span>
            <Badge variant={mlStatus?.available ? "low" : "moderate"}>{mlStatus?.source ?? "pending"}</Badge>
          </div>
          <div className="grid gap-2 text-[13px] text-slate-300/82">
            <div className="flex items-center justify-between">
              <span>Selected model</span>
              <span className="telemetry-value">{mlStatus?.selectedModel ?? "heuristic-fallback"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Candidate set</span>
              <span className="telemetry-value">{mlStatus?.candidateModels.join(", ") || "pending"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Propagation mode</span>
              <span className="telemetry-value">{propagationMode}</span>
            </div>
          </div>
        </div>

        <div className="space-y-3 rounded-sm border border-white/10 bg-white/4 p-4">
          <div className="flex items-center gap-2 text-slate-100">
            <Satellite className="h-4 w-4 text-neon-amber" />
            <span className="font-medium">Tracked Focus</span>
          </div>
          {selectedSatellite ? (
            <div className="grid gap-2 text-[13px] text-slate-300/82">
              <div className="flex items-center justify-between">
                <span>Asset</span>
                <span className="telemetry-value">{selectedSatellite.id}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Risk band</span>
                <Badge variant={selectedSatellite.riskBand}>{selectedSatellite.riskBand}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span>Orbital period</span>
                <span className="telemetry-value">{selectedSatellite.orbitalPeriodMinutes.toFixed(1)} min</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-300/80">Select a tracked asset to inspect orbital context.</p>
          )}
        </div>

        <div className="space-y-3 rounded-sm border border-white/10 bg-white/4 p-4">
          <div className="flex items-center gap-2 text-slate-100">
            <Radar className="h-4 w-4 text-neon-coral" />
            <span className="font-medium">Lead Incident</span>
          </div>
          {selectedCollision ? (
            <div className="grid gap-2 text-[13px] text-slate-300/82">
              <div className="flex items-center justify-between">
                <span>Pair</span>
                <span className="telemetry-value">
                  {selectedCollision.primaryObjectId} / {selectedCollision.secondaryObjectId}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Probability</span>
                <span className="telemetry-value">{(selectedCollision.probability * 100).toFixed(2)}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Lead time</span>
                <span className="telemetry-value">{Math.round(selectedCollision.leadTimeMinutes)} min</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-300/80">No active conjunction event is selected.</p>
          )}
        </div>

        <div className="flex items-center justify-between rounded-sm border border-white/10 bg-white/4 px-4 py-3">
          <span className="inline-flex items-center gap-2 text-slate-200">
            <Activity className="h-4 w-4 text-neon-cyan" />
            Runtime health
          </span>
          <span className="telemetry-value">{metrics.wsConnected ? "push + polling" : "polling only"}</span>
        </div>
      </CardContent>
    </Card>
  );
}
