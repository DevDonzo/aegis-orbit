"use client";

import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSimulationStore } from "@/store/useSimulationStore";

const WINDOW_MS = 4 * 60 * 60 * 1000;

function colorForRisk(riskBand: "low" | "moderate" | "high" | "critical") {
  if (riskBand === "critical") return "rgba(255, 93, 120, 0.95)";
  if (riskBand === "high") return "rgba(255, 156, 125, 0.88)";
  if (riskBand === "moderate") return "rgba(255, 211, 110, 0.9)";
  return "rgba(99, 245, 228, 0.82)";
}

export function TimelineScrubber() {
  const currentTimeIso = useSimulationStore((state) => state.currentTimeIso);
  const collisionEvents = useSimulationStore((state) => state.collisionEvents);
  const setCurrentTimeIso = useSimulationStore((state) => state.setCurrentTimeIso);
  const setSelectedCollisionId = useSimulationStore((state) => state.setSelectedCollisionId);
  const setSelectedEntityId = useSimulationStore((state) => state.setSelectedEntityId);

  const [startMs, endMs] = useMemo(() => {
    if (collisionEvents.length === 0) {
      const now = Date.now();
      return [now - WINDOW_MS / 2, now + WINDOW_MS / 2];
    }
    const eventTimes = collisionEvents.map((event) => new Date(event.timeOfClosestApproachIso).getTime());
    const min = Math.min(...eventTimes);
    const max = Math.max(...eventTimes);
    return [min - 45 * 60 * 1000, max + 45 * 60 * 1000];
  }, [collisionEvents]);

  const currentMs = new Date(currentTimeIso).getTime();
  const safeCurrentMs = Number.isFinite(currentMs) ? currentMs : startMs;
  const timelineSpan = Math.max(1, endMs - startMs);
  const nextEvents = collisionEvents.slice(0, 3);

  return (
    <Card className="pointer-events-auto">
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="section-kicker">Conjunction Window</p>
            <CardTitle className="mt-1 text-left">Simulation Timeline</CardTitle>
          </div>
          <div className="flex flex-wrap gap-2">
            {nextEvents.map((event) => (
              <Button
                key={event.id}
                size="sm"
                variant="secondary"
                onClick={() => {
                  setCurrentTimeIso(event.timeOfClosestApproachIso);
                  setSelectedCollisionId(event.id);
                  setSelectedEntityId(event.primaryObjectId);
                }}
              >
                Jump {event.primaryObjectId}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="relative">
          <input
            type="range"
            min={startMs}
            max={endMs}
            step={30_000}
            value={safeCurrentMs}
            onChange={(event) => setCurrentTimeIso(new Date(Number(event.target.value)).toISOString())}
            className="timeline-range"
            aria-label="Simulation timeline scrubber"
          />
          <div className="pointer-events-none absolute left-0 right-0 top-0 h-4">
            {collisionEvents.map((event) => {
              const eventMs = new Date(event.timeOfClosestApproachIso).getTime();
              const leftPct = ((eventMs - startMs) / timelineSpan) * 100;
              if (!Number.isFinite(leftPct) || leftPct < 0 || leftPct > 100) return null;
              return (
                <span
                  key={event.id}
                  className="absolute top-[1px] h-3 w-[3px] rounded-full"
                  style={{ left: `calc(${leftPct}% - 1px)`, background: colorForRisk(event.riskBand) }}
                />
              );
            })}
          </div>
        </div>
        <div className="grid grid-cols-1 gap-2 text-xs text-slate-300/82 md:grid-cols-2">
          <p className="telemetry-value">Simulation time: {new Date(safeCurrentMs).toISOString()}</p>
          <p className="telemetry-value text-left md:text-right">
            Window: {new Date(startMs).toISOString()} → {new Date(endMs).toISOString()}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
