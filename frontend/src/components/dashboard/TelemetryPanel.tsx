"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useSimulationStore } from "@/store/useSimulationStore";

export function TelemetryPanel() {
  const satellites = useSimulationStore((state) => state.satellites);
  const selectedEntityId = useSimulationStore((state) => state.selectedEntityId);
  const setSelectedEntityId = useSimulationStore((state) => state.setSelectedEntityId);
  const setSelectedCollisionId = useSimulationStore((state) => state.setSelectedCollisionId);
  const [query, setQuery] = useState("");

  const catalog = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return Object.values(satellites)
      .filter((satellite) =>
        normalized.length === 0
          ? true
          : `${satellite.id} ${satellite.name} ${satellite.noradId}`.toLowerCase().includes(normalized)
      )
      .sort((left, right) => right.riskScore - left.riskScore || left.id.localeCompare(right.id));
  }, [satellites, query]);

  const selectedSatellite = selectedEntityId ? satellites[selectedEntityId] : catalog[0] ?? null;

  return (
    <Card className="pointer-events-auto h-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="section-kicker">Orbital Catalog</p>
            <CardTitle className="mt-1 text-left">Tracked Assets</CardTitle>
          </div>
          <Badge variant="neutral">{catalog.length.toString().padStart(2, "0")} live</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-sm border border-white/10 bg-white/4 p-4">
          <p className="section-kicker">Selection</p>
          {selectedSatellite ? (
            <div className="mt-2 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold text-white">{selectedSatellite.name}</p>
                  <p className="telemetry-value mt-1 text-sm text-slate-300/80">NORAD {selectedSatellite.noradId}</p>
                </div>
                <Badge variant={selectedSatellite.riskBand}>{selectedSatellite.riskBand}</Badge>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm text-slate-300/82">
                <div>
                  <p className="section-kicker">Altitude</p>
                  <p className="telemetry-value mt-1 text-white">
                    {selectedSatellite.telemetry.at(-1)?.altitudeKm.toFixed(1) ?? "--"} km
                  </p>
                </div>
                <div>
                  <p className="section-kicker">Velocity</p>
                  <p className="telemetry-value mt-1 text-white">{selectedSatellite.velocityKms.toFixed(2)} km/s</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="mt-2 text-sm text-slate-300/80">No satellite data available.</p>
          )}
        </div>

        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400/85" />
          <Input
            className="pl-9"
            placeholder="Search object / NORAD"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="Search tracked objects"
          />
        </div>

        <div className="max-h-[34vh] space-y-2 overflow-auto pr-1 xl:max-h-[40vh]">
          {catalog.map((satellite) => (
            <button
              key={satellite.id}
              onClick={() => {
                setSelectedEntityId(satellite.id);
                setSelectedCollisionId(null);
              }}
              className={`w-full rounded-sm border p-3 text-left transition ${
                selectedEntityId === satellite.id
                  ? "border-neon-cyan/70 bg-neon-cyan/10"
                  : "border-white/10 bg-[rgba(6,11,20,0.72)] hover:border-white/18 hover:bg-white/6"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">{satellite.id}</p>
                  <p className="mt-0.5 text-xs text-slate-300/75">{satellite.name}</p>
                </div>
                <Badge variant={satellite.riskBand}>{satellite.riskBand}</Badge>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-slate-300/78">
                <div>
                  <p className="section-kicker">ALT</p>
                  <p className="telemetry-value mt-1">{satellite.telemetry.at(-1)?.altitudeKm.toFixed(1) ?? "--"} km</p>
                </div>
                <div>
                  <p className="section-kicker">INC</p>
                  <p className="telemetry-value mt-1">{satellite.inclinationDeg.toFixed(1)}°</p>
                </div>
                <div>
                  <p className="section-kicker">PERIOD</p>
                  <p className="telemetry-value mt-1">{satellite.orbitalPeriodMinutes.toFixed(1)}m</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
