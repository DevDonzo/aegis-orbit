import { create } from "zustand";
import { devtools, subscribeWithSelector } from "zustand/middleware";
import type { ApiConnectionState, CollisionRisk, MlRuntimeStatus, MissionSnapshot, OrbitData, SystemMetrics } from "@/types";

interface SimulationState {
  currentTimeIso: string;
  lastUpdatedIso: string | null;
  propagationMode: string;
  satellites: Record<string, OrbitData>;
  collisionEvents: CollisionRisk[];
  selectedEntityId: string | null;
  selectedCollisionId: string | null;
  connectionState: ApiConnectionState;
  mlStatus: MlRuntimeStatus | null;
  metrics: SystemMetrics;
}

interface SimulationActions {
  setCurrentTimeIso: (timeIso: string) => void;
  setMissionSnapshot: (snapshot: MissionSnapshot) => void;
  applyPredictions: (predictions: Array<Pick<CollisionRisk, "id" | "probability" | "missDistanceKm" | "riskBand" | "uncertaintyKm" | "predictionSource" | "modelName">>) => void;
  setSelectedEntityId: (entityId: string | null) => void;
  setSelectedCollisionId: (collisionId: string | null) => void;
  setConnectionState: (state: ApiConnectionState) => void;
  setMlStatus: (status: MlRuntimeStatus | null) => void;
  setMetrics: (partial: Partial<SystemMetrics>) => void;
  setSatellites: (satellites: Record<string, OrbitData>) => void;
  reset: () => void;
}

type SimulationStore = SimulationState & SimulationActions;

const defaultState: SimulationState = {
  currentTimeIso: new Date().toISOString(),
  lastUpdatedIso: null,
  propagationMode: "skyfield",
  satellites: {},
  collisionEvents: [],
  selectedEntityId: null,
  selectedCollisionId: null,
  connectionState: "connecting",
  mlStatus: null,
  metrics: {
    fps: 0,
    apiLatencyMs: 0,
    trackedObjectCount: 0,
    activeAlertCount: 0,
    wsConnected: false
  }
};

export const useSimulationStore = create<SimulationStore>()(
  subscribeWithSelector(
    devtools(
      (set) => ({
        ...defaultState,
        setCurrentTimeIso: (currentTimeIso) =>
          set(
            () => ({ currentTimeIso }),
            false,
            "simulation/setCurrentTimeIso"
          ),
        setMissionSnapshot: (snapshot) =>
          set(
            (state) => {
              const satellites = Object.fromEntries(snapshot.satellites.map((satellite) => [satellite.id, satellite]));
              const hasSelectedCollision = snapshot.collisionEvents.some((event) => event.id === state.selectedCollisionId);
              const hasSelectedEntity =
                state.selectedEntityId !== null && Object.prototype.hasOwnProperty.call(satellites, state.selectedEntityId);
              const nextSelectedCollisionId = hasSelectedCollision ? state.selectedCollisionId : (snapshot.collisionEvents[0]?.id ?? null);
              const collisionPrimary =
                nextSelectedCollisionId !== null
                  ? snapshot.collisionEvents.find((event) => event.id === nextSelectedCollisionId)?.primaryObjectId ?? null
                  : null;
              const nextSelectedEntityId = hasSelectedEntity
                ? state.selectedEntityId
                : collisionPrimary && Object.prototype.hasOwnProperty.call(satellites, collisionPrimary)
                  ? collisionPrimary
                  : (snapshot.satellites[0]?.id ?? null);

              return {
                satellites,
                collisionEvents: snapshot.collisionEvents,
                propagationMode: snapshot.propagationMode,
                lastUpdatedIso: snapshot.generatedAtIso,
                selectedEntityId: nextSelectedEntityId,
                selectedCollisionId: nextSelectedCollisionId,
                metrics: {
                  ...state.metrics,
                  apiLatencyMs: snapshot.apiLatencyMs,
                  trackedObjectCount: snapshot.satellites.length,
                  activeAlertCount: snapshot.collisionEvents.length
                }
              };
            },
            false,
            "simulation/setMissionSnapshot"
          ),
        applyPredictions: (predictions) =>
          set(
            (state) => ({
              collisionEvents: state.collisionEvents.map((event) => {
                const prediction = predictions.find((candidate) => candidate.id === event.id);
                if (!prediction) return event;
                return {
                  ...event,
                  probability: prediction.probability,
                  missDistanceKm: prediction.missDistanceKm,
                  riskBand: prediction.riskBand,
                  uncertaintyKm: prediction.uncertaintyKm,
                  predictionSource: prediction.predictionSource,
                  modelName: prediction.modelName
                };
              })
            }),
            false,
            "simulation/applyPredictions"
          ),
        setSelectedEntityId: (selectedEntityId) =>
          set(
            () => ({ selectedEntityId }),
            false,
            "simulation/setSelectedEntityId"
          ),
        setSelectedCollisionId: (selectedCollisionId) =>
          set(
            () => ({ selectedCollisionId }),
            false,
            "simulation/setSelectedCollisionId"
          ),
        setConnectionState: (connectionState) =>
          set(
            () => ({ connectionState }),
            false,
            "simulation/setConnectionState"
          ),
        setMlStatus: (mlStatus) =>
          set(
            () => ({ mlStatus }),
            false,
            "simulation/setMlStatus"
          ),
        setMetrics: (partial) =>
          set(
            (state) => ({
              metrics: { ...state.metrics, ...partial }
            }),
            false,
            "simulation/setMetrics"
          ),
        setSatellites: (satellites) =>
          set(
            () => ({ satellites }),
            false,
            "simulation/setSatellites"
          ),
        reset: () =>
          set(
            () => ({ ...defaultState }),
            false,
            "simulation/reset"
          )
      }),
      { name: "simulation-store" }
    )
  )
);
