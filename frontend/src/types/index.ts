export type RiskBand = "low" | "moderate" | "high" | "critical";
export type ApiConnectionState = "connecting" | "online" | "degraded" | "offline";
export type MlPredictionSource = "selected-model" | "ensemble" | "heuristic-fallback";

export interface GeodeticPoint {
  latitudeDeg: number;
  longitudeDeg: number;
  altitudeKm: number;
}

export interface TelemetrySample extends GeodeticPoint {
  timestampIso: string;
  velocityKms: number;
}

export interface TleOrbitalElements {
  line1: string;
  line2: string;
  inclinationDeg: number;
  raanDeg: number;
  eccentricity: number;
  argPerigeeDeg: number;
  meanAnomalyDeg: number;
  meanMotionRevPerDay: number;
}

export interface OrbitData {
  id: string;
  name: string;
  noradId: string;
  telemetry: TelemetrySample[];
  status: "active" | "inactive" | "maneuvering";
  riskBand: RiskBand;
  riskScore: number;
  velocityKms: number;
  inclinationDeg: number;
  orbitalPeriodMinutes: number;
  updatedAtIso: string;
}

export interface CollisionRisk {
  id: string;
  primaryObjectId: string;
  secondaryObjectId: string;
  probability: number;
  riskBand: RiskBand;
  severityScore: number;
  missDistanceKm: number;
  currentDistanceKm: number;
  relativeVelocityKms: number;
  timeOfClosestApproachIso: string;
  leadTimeMinutes: number;
  vectorStart: GeodeticPoint;
  vectorEnd: GeodeticPoint;
  riskZoneRadiusKm: number;
  uncertaintyKm: number;
  predictionSource: MlPredictionSource;
  modelName: string;
}

export interface MlRuntimeStatus {
  available: boolean;
  source: MlPredictionSource;
  selectedModel: string | null;
  candidateModels: string[];
  metadata: Record<string, unknown> | null;
}

export interface MissionSnapshot {
  generatedAtIso: string;
  propagationMode: string;
  satellites: OrbitData[];
  collisionEvents: CollisionRisk[];
  apiLatencyMs: number;
}

export interface BackendTelemetryPoint {
  timestamp: string;
  lat: number;
  lon: number;
  alt_km: number;
  velocity_km_s: number;
}

export interface BackendSatelliteSummary {
  id: string;
  name: string;
  norad_id: string;
  status: "active" | "inactive" | "maneuvering";
  risk: "safe" | "warning" | "danger";
  risk_score: number;
  lat: number;
  lon: number;
  alt_km: number;
  velocity_km_s: number;
  inclination_deg: number;
  orbital_period_minutes: number;
  updated_at: string;
  telemetry: BackendTelemetryPoint[];
}

export interface BackendVectorEnvelope {
  lat: number;
  lon: number;
  alt_km: number;
}

export interface BackendCollisionSummary {
  id: string;
  satellite_1: string;
  satellite_2: string;
  distance_km: number;
  current_distance_km: number;
  risk: "safe" | "warning" | "danger";
  risk_score: number;
  timestamp: string;
  lead_time_minutes: number;
  relative_velocity_km_s: number;
  collision_probability_proxy: number;
  risk_zone_radius_km: number;
  vector_start: BackendVectorEnvelope;
  vector_end: BackendVectorEnvelope;
}

export interface BackendPredictionSummary {
  id: string;
  satellite_1: string;
  satellite_2: string;
  predicted_min_distance_km: number;
  predicted_risk: "safe" | "warning" | "danger";
  collision_probability: number;
  uncertainty_km: number;
  prediction_source: MlPredictionSource;
  model_name: string;
}

export interface BackendDashboardSnapshot {
  generated_at: string;
  propagation_mode: string;
  satellites: BackendSatelliteSummary[];
  collisions: BackendCollisionSummary[];
}

export interface BackendMlStatus {
  available: boolean;
  source: MlPredictionSource;
  model_path: string;
  metadata: Record<string, unknown> | null;
  candidate_models: string[];
  selected_model: string | null;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  username: string;
  role: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
}

export interface SystemMetrics {
  fps: number;
  apiLatencyMs: number;
  trackedObjectCount: number;
  activeAlertCount: number;
  wsConnected: boolean;
}
