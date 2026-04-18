"use client";

import { useMemo, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useSimulationStore } from "@/store/useSimulationStore";
import type { CollisionRisk, RiskBand } from "@/types";

const riskOrder: Record<RiskBand, number> = {
  critical: 4,
  high: 3,
  moderate: 2,
  low: 1
};

function sortEventsDescending(left: CollisionRisk, right: CollisionRisk) {
  const byRisk = riskOrder[right.riskBand] - riskOrder[left.riskBand];
  if (byRisk !== 0) return byRisk;
  return right.probability - left.probability;
}

export function CollisionAlerts() {
  const collisionEvents = useSimulationStore((state) => state.collisionEvents);
  const selectedCollisionId = useSimulationStore((state) => state.selectedCollisionId);
  const setSelectedCollisionId = useSimulationStore((state) => state.setSelectedCollisionId);
  const setSelectedEntityId = useSimulationStore((state) => state.setSelectedEntityId);
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return collisionEvents
      .filter((event) =>
        normalized.length === 0
          ? true
          : `${event.primaryObjectId} ${event.secondaryObjectId}`.toLowerCase().includes(normalized)
      )
      .sort(sortEventsDescending);
  }, [collisionEvents, query]);

  const leadEvent = filtered[0] ?? null;

  return (
    <Card className="pointer-events-auto h-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="section-kicker">Threat Ladder</p>
            <CardTitle className="mt-1 flex items-center gap-2 text-left">
              <AlertTriangle className="h-4 w-4 text-neon-coral" />
              Collision Alerts
            </CardTitle>
          </div>
          <Badge variant={leadEvent?.riskBand ?? "neutral"}>{leadEvent?.riskBand ?? "stable"}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="summary-tile">
            <span className="summary-tile__label">Lead Probability</span>
            <span className="summary-tile__value">{leadEvent ? `${(leadEvent.probability * 100).toFixed(1)}%` : "--"}</span>
          </div>
          <div className="summary-tile">
            <span className="summary-tile__label">Lead Miss</span>
            <span className="summary-tile__value">{leadEvent ? `${leadEvent.missDistanceKm.toFixed(2)} km` : "--"}</span>
          </div>
          <div className="summary-tile">
            <span className="summary-tile__label">Model</span>
            <span className="summary-tile__value text-[0.9rem]">{leadEvent?.modelName ?? "--"}</span>
          </div>
        </div>

        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter by object pair"
          aria-label="Search collision events"
        />

        <div className="max-h-[34vh] space-y-2 overflow-auto pr-1 xl:max-h-[40vh]">
          {filtered.length === 0 ? (
            <p className="text-sm text-slate-300/80">No conjunctions found in the current analysis window.</p>
          ) : (
            filtered.map((event) => {
              const isSelected = selectedCollisionId === event.id;
              return (
                <button
                  key={event.id}
                  className={`w-full rounded-sm border p-3 text-left transition ${
                    isSelected
                      ? "border-neon-coral/65 bg-neon-coral/10"
                      : "border-white/10 bg-[rgba(6,11,20,0.72)] hover:border-white/18 hover:bg-white/6"
                  }`}
                  onClick={() => {
                    setSelectedCollisionId(event.id);
                    setSelectedEntityId(event.primaryObjectId);
                  }}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">
                        {event.primaryObjectId} vs {event.secondaryObjectId}
                      </p>
                      <p className="telemetry-value mt-1 text-[11px] text-slate-400">
                        TCA {new Date(event.timeOfClosestApproachIso).toISOString()}
                      </p>
                    </div>
                    <Badge variant={event.riskBand}>{event.riskBand}</Badge>
                  </div>

                  <div className="mt-3 space-y-2">
                    <div className="h-1.5 overflow-hidden rounded-sm bg-white/8">
                      <div
                        className="h-full rounded-sm bg-[linear-gradient(90deg,rgba(255,110,140,0.6),rgba(255,214,117,0.82),rgba(99,245,228,0.9))]"
                        style={{ width: `${Math.max(6, Math.min(100, event.probability * 100))}%` }}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300/80">
                      <p className="telemetry-value">P {(event.probability * 100).toFixed(2)}%</p>
                      <p className="telemetry-value text-right">{event.missDistanceKm.toFixed(2)} km miss</p>
                      <p className="telemetry-value">{event.relativeVelocityKms.toFixed(2)} km/s rel vel</p>
                      <p className="telemetry-value text-right">{event.uncertaintyKm.toFixed(2)} km sigma</p>
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
