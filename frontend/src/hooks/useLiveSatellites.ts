import { useEffect } from "react";
import * as satellite from "satellite.js";
import { useSimulationStore } from "@/store/useSimulationStore";
import { apiRequest } from "@/services/apiClient";

/**
 * Periodically fetches live TLE data, parses it, and populates the simulation store.
 * Updates every 15 seconds (adjustable). Supports `refresh=true` query param to bypass cache.
 */
export function useLiveSatellites(refreshIntervalMs: number = 15_000) {
  const setSatellites = useSimulationStore((state) => state.setSatellites);

  useEffect(() => {
    let cancelled = false;
    const fetchAndUpdate = async () => {
      try {
        // Force fresh fetch on first load
        const response = await apiRequest<any>("/satellites/live?refresh=true", {
          method: "GET",
          requiresAuth: false
        });
        // Expected shape: { records: [{ name, norad_id, line1, line2, fetched_at, source_type }], source: {...} }
        const records = response.records ?? [];
        const satellitesMap: Record<string, any> = {};
        const now = new Date();
        records.forEach((rec: any) => {
          try {
            const satrec = satellite.twoline2satrec(rec.line1, rec.line2);
            const positionAndVelocity = satellite.propagate(satrec, now);
            if (!positionAndVelocity.position) return;
            const gmst = satellite.gstime(now);
            const geodetic = satellite.eciToGeodetic(positionAndVelocity.position, gmst);
            const latitudeDeg = satellite.degreesLat(geodetic.lat);
            const longitudeDeg = satellite.degreesLong(geodetic.lon);
            const altitudeKm = geodetic.height / 1000;
            const telemetrySample = {
              timestampIso: now.toISOString(),
              latitudeDeg,
              longitudeDeg,
              altitudeKm,
              velocityKms: Math.sqrt(
                positionAndVelocity.velocity?.x ** 2 +
                positionAndVelocity.velocity?.y ** 2 +
                positionAndVelocity.velocity?.z ** 2
              ) / 1000 // convert m/s to km/s
            };
            const orbitData = {
              id: String(rec.norad_id),
              name: rec.name ?? `SAT-${rec.norad_id}`,
              noradId: rec.norad_id,
              telemetry: [telemetrySample],
              status: "live",
              riskBand: "low",
              riskScore: 0,
              velocityKms: telemetrySample.velocityKms,
              inclinationDeg: satrec.inclo,
              orbitalPeriodMinutes: 0,
              updatedAtIso: rec.fetched_at || now.toISOString()
            };
            satellitesMap[orbitData.id] = orbitData;
          } catch {}
        });
        if (!cancelled) {
          setSatellites(satellitesMap);
        }
      } catch (e) {
        // ignore fetch errors – keep existing data
      }
    };

    fetchAndUpdate();
    const interval = setInterval(fetchAndUpdate, refreshIntervalMs);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [setSatellites, refreshIntervalMs]);
}
