import type {
  BackendCollisionSummary,
  BackendDashboardSnapshot,
  BackendMlStatus,
  BackendPredictionSummary,
  BackendSatelliteSummary,
  CollisionRisk,
  MissionSnapshot,
  MlRuntimeStatus,
  OrbitData,
  RiskBand,
  TelemetrySample
} from "@/types";
import { HttpError, apiRequest } from "@/services/apiClient";
import { mockCollisionEvents, mockSatellites } from "@/services/mockData";

function normalizeRisk(risk: "safe" | "warning" | "danger", score = 0): RiskBand {
  if (risk === "danger") return "critical";
  if (risk === "warning") return "high";
  if (score >= 0.35) return "moderate";
  return "low";
}

function mapTelemetry(sample: BackendSatelliteSummary["telemetry"][number]): TelemetrySample {
  return {
    timestampIso: sample.timestamp,
    latitudeDeg: sample.lat,
    longitudeDeg: sample.lon,
    altitudeKm: sample.alt_km,
    velocityKms: sample.velocity_km_s
  };
}

function mapSatellite(summary: BackendSatelliteSummary): OrbitData {
  return {
    id: summary.id,
    name: summary.name,
    noradId: summary.norad_id,
    telemetry: summary.telemetry.map(mapTelemetry),
    status: summary.status,
    riskBand: normalizeRisk(summary.risk, summary.risk_score),
    riskScore: summary.risk_score,
    velocityKms: summary.velocity_km_s,
    inclinationDeg: summary.inclination_deg,
    orbitalPeriodMinutes: summary.orbital_period_minutes,
    updatedAtIso: summary.updated_at
  };
}

function mapCollision(summary: BackendCollisionSummary): CollisionRisk {
  return {
    id: summary.id,
    primaryObjectId: summary.satellite_1,
    secondaryObjectId: summary.satellite_2,
    probability: summary.collision_probability_proxy,
    riskBand: normalizeRisk(summary.risk, summary.risk_score),
    severityScore: summary.risk_score,
    missDistanceKm: summary.distance_km,
    currentDistanceKm: summary.current_distance_km,
    relativeVelocityKms: summary.relative_velocity_km_s,
    timeOfClosestApproachIso: summary.timestamp,
    leadTimeMinutes: summary.lead_time_minutes,
    vectorStart: {
      latitudeDeg: summary.vector_start.lat,
      longitudeDeg: summary.vector_start.lon,
      altitudeKm: summary.vector_start.alt_km
    },
    vectorEnd: {
      latitudeDeg: summary.vector_end.lat,
      longitudeDeg: summary.vector_end.lon,
      altitudeKm: summary.vector_end.alt_km
    },
    riskZoneRadiusKm: summary.risk_zone_radius_km,
    uncertaintyKm: 0,
    predictionSource: "heuristic-fallback",
    modelName: "baseline-proxy"
  };
}

export async function fetchMissionSnapshot(): Promise<MissionSnapshot> {
  const startedAt = performance.now();

  try {
    const response = await apiRequest<BackendDashboardSnapshot>("/dashboard", {
      method: "GET",
      requiresAuth: false
    });

    return {
      generatedAtIso: response.generated_at,
      propagationMode: response.propagation_mode,
      satellites: response.satellites.map(mapSatellite),
      collisionEvents: response.collisions.map(mapCollision),
      apiLatencyMs: Math.max(1, Math.round(performance.now() - startedAt))
    };
  } catch (error) {
    if (error instanceof HttpError && (error.status === 404 || error.status === 503)) {
      return {
        generatedAtIso: new Date().toISOString(),
        propagationMode: "mock",
        satellites: mockSatellites,
        collisionEvents: mockCollisionEvents,
        apiLatencyMs: Math.max(1, Math.round(performance.now() - startedAt))
      };
    }
    throw error;
  }
}

export async function fetchPredictions() {
  try {
    const response = await apiRequest<BackendPredictionSummary[]>("/predict", {
      method: "GET",
      requiresAuth: false
    });

    return response.map((prediction) => ({
      id: prediction.id,
      probability: prediction.collision_probability,
      missDistanceKm: prediction.predicted_min_distance_km,
      riskBand: normalizeRisk(prediction.predicted_risk),
      uncertaintyKm: prediction.uncertainty_km,
      predictionSource: prediction.prediction_source,
      modelName: prediction.model_name
    }));
  } catch (error) {
    if (error instanceof HttpError && (error.status === 404 || error.status === 503 || error.status === 401)) {
      return [];
    }
    throw error;
  }
}

export async function fetchMlStatus(): Promise<MlRuntimeStatus | null> {
  try {
    const status = await apiRequest<BackendMlStatus>("/ml/status", {
      method: "GET",
      requiresAuth: false
    });

    return {
      available: status.available,
      source: status.source,
      selectedModel: status.selected_model,
      candidateModels: status.candidate_models,
      metadata: status.metadata
    };
  } catch (error) {
    if (error instanceof HttpError && (error.status === 404 || error.status === 503 || error.status === 401)) {
      return null;
    }
    throw error;
  }
}
