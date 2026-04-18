"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSimulationStore } from "@/store/useSimulationStore";

export function MissionOverview() {
  const collisionEvents = useSimulationStore((state) => state.collisionEvents);
  const satellites = useSimulationStore((state) => state.satellites);
  const selectedCollisionId = useSimulationStore((state) => state.selectedCollisionId);
  const selectedEntityId = useSimulationStore((state) => state.selectedEntityId);
  const propagationMode = useSimulationStore((state) => state.propagationMode);
  const lastUpdatedIso = useSimulationStore((state) => state.lastUpdatedIso);
  const mlStatus = useSimulationStore((state) => state.mlStatus);
  const setSelectedEntityId = useSimulationStore((state) => state.setSelectedEntityId);
  const setSelectedCollisionId = useSimulationStore((state) => state.setSelectedCollisionId);

  const leadEvent =
    collisionEvents.find((event) => event.id === selectedCollisionId) ??
    collisionEvents[0] ??
    null;
  const selectedSatellite =
    (selectedEntityId && satellites[selectedEntityId]) ||
    (leadEvent ? satellites[leadEvent.primaryObjectId] : null) ||
    Object.values(satellites)[0] ||
    null;

  return (
    <Card className="pointer-events-auto overflow-hidden">
      <CardHeader className="border-b border-white/8 pb-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <p className="section-kicker">Mission Synopsis</p>
            <CardTitle className="max-w-2xl text-left text-[1.2rem] font-semibold tracking-[0.08em] text-white sm:text-[1.45rem]">
              Enterprise orbital risk console with live conjunction scoring, predictive analytics, and operator-focused visualization.
            </CardTitle>
          </div>
          <div className="flex flex-wrap gap-2">
            <div className="metric-chip">
              <span className="metric-chip__label">Propagator</span>
              <span className="telemetry-value">{propagationMode}</span>
            </div>
            <div className="metric-chip">
              <span className="metric-chip__label">ML Source</span>
              <span className="telemetry-value">{mlStatus?.selectedModel ?? mlStatus?.source ?? "pending"}</span>
            </div>
            <div className="metric-chip">
              <span className="metric-chip__label">Generated</span>
              <span className="telemetry-value">{lastUpdatedIso ? new Date(lastUpdatedIso).toISOString().slice(11, 19) : "--:--:--"}</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4 pt-5 lg:grid-cols-[1.4fr_0.95fr]">
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="summary-tile">
              <span className="summary-tile__label">Tracked Assets</span>
              <span className="summary-tile__value">{Object.keys(satellites).length.toString().padStart(2, "0")}</span>
            </div>
            <div className="summary-tile">
              <span className="summary-tile__label">Active Alerts</span>
              <span className="summary-tile__value">{collisionEvents.length.toString().padStart(2, "0")}</span>
            </div>
            <div className="summary-tile">
              <span className="summary-tile__label">Lead TCA</span>
              <span className="summary-tile__value">
                {leadEvent ? `${Math.max(0, Math.round(leadEvent.leadTimeMinutes))}m` : "--"}
              </span>
            </div>
          </div>

          <div className="rounded-sm border border-white/10 bg-white/4 p-4">
            <p className="section-kicker">Primary Incident</p>
            {leadEvent ? (
              <>
                <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-white">
                      {leadEvent.primaryObjectId} vs {leadEvent.secondaryObjectId}
                    </p>
                    <p className="mt-1 max-w-xl text-sm text-slate-300/82">
                      Predicted miss distance {leadEvent.missDistanceKm.toFixed(2)} km at{" "}
                      {new Date(leadEvent.timeOfClosestApproachIso).toISOString()} with relative velocity{" "}
                      {leadEvent.relativeVelocityKms.toFixed(2)} km/s.
                    </p>
                  </div>
                  <div className="threat-pulse">
                    <span className="telemetry-value">{(leadEvent.probability * 100).toFixed(1)}%</span>
                    <small>collision probability</small>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    onClick={() => {
                      setSelectedCollisionId(leadEvent.id);
                      setSelectedEntityId(leadEvent.primaryObjectId);
                    }}
                  >
                    Track Primary Asset
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setSelectedCollisionId(leadEvent.id);
                      setSelectedEntityId(leadEvent.secondaryObjectId);
                    }}
                  >
                    Track Secondary Asset
                  </Button>
                </div>
              </>
            ) : (
              <p className="mt-2 text-sm text-slate-300/80">No conjunctions are currently inside the modeled analysis window.</p>
            )}
          </div>
        </div>

        <div className="rounded-sm border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] p-4">
          <p className="section-kicker">Selection Focus</p>
          {selectedSatellite ? (
            <div className="mt-3 space-y-3">
              <div>
                <p className="text-base font-semibold text-white">{selectedSatellite.name}</p>
                <p className="telemetry-value mt-1 text-sm text-slate-300/80">NORAD {selectedSatellite.noradId}</p>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm text-slate-300/82">
                <div>
                  <p className="section-kicker">Altitude</p>
                  <p className="telemetry-value mt-1 text-base text-white">
                    {selectedSatellite.telemetry.at(-1)?.altitudeKm.toFixed(1) ?? "--"} km
                  </p>
                </div>
                <div>
                  <p className="section-kicker">Velocity</p>
                  <p className="telemetry-value mt-1 text-base text-white">{selectedSatellite.velocityKms.toFixed(2)} km/s</p>
                </div>
                <div>
                  <p className="section-kicker">Inclination</p>
                  <p className="telemetry-value mt-1 text-base text-white">{selectedSatellite.inclinationDeg.toFixed(2)}°</p>
                </div>
                <div>
                  <p className="section-kicker">Period</p>
                  <p className="telemetry-value mt-1 text-base text-white">{selectedSatellite.orbitalPeriodMinutes.toFixed(1)} min</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-300/80">Select an asset to inspect its orbital profile.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
