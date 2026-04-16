const state = {
  accessToken: null,
};

const byId = (id) => document.getElementById(id);

const elements = {
  baseUrl: byId("baseUrl"),
  username: byId("username"),
  password: byId("password"),
  tokenBtn: byId("tokenBtn"),
  presetBtn: byId("presetBtn"),
  tokenStatus: byId("tokenStatus"),
  predictBtn: byId("predictBtn"),
  predictStatus: byId("predictStatus"),
  probabilityGauge: byId("probabilityGauge"),
  probabilityValue: byId("probabilityValue"),
  riskBand: byId("riskBand"),
  modelVersion: byId("modelVersion"),
};

const fields = [
  "a_object_id",
  "a_eccentricity",
  "a_inclination_deg",
  "a_raan_deg",
  "a_arg_perigee_deg",
  "a_mean_anomaly_deg",
  "a_mean_motion_rev_per_day",
  "b_object_id",
  "b_eccentricity",
  "b_inclination_deg",
  "b_raan_deg",
  "b_arg_perigee_deg",
  "b_mean_anomaly_deg",
  "b_mean_motion_rev_per_day",
  "closest_approach_km",
  "relative_velocity_kms",
];

const numberFields = new Set([
  "a_eccentricity",
  "a_inclination_deg",
  "a_raan_deg",
  "a_arg_perigee_deg",
  "a_mean_anomaly_deg",
  "a_mean_motion_rev_per_day",
  "b_eccentricity",
  "b_inclination_deg",
  "b_raan_deg",
  "b_arg_perigee_deg",
  "b_mean_anomaly_deg",
  "b_mean_motion_rev_per_day",
  "closest_approach_km",
  "relative_velocity_kms",
]);

function setStatus(node, message, kind = "neutral") {
  node.textContent = message;
  node.className = `status ${kind}`;
}

function normalizeBaseUrl(raw) {
  return raw.replace(/\/+$/, "");
}

function setGauge(probability) {
  const p = Math.max(0, Math.min(1, probability));
  const degrees = Math.round(p * 360);
  elements.probabilityGauge.style.background = `conic-gradient(var(--accent) ${degrees}deg, rgba(152, 173, 221, 0.2) ${degrees}deg)`;
  elements.probabilityValue.textContent = `${(p * 100).toFixed(2)}%`;
}

function setRiskBand(riskBand) {
  const band = String(riskBand || "low").toLowerCase();
  elements.riskBand.textContent = band.toUpperCase();
  elements.riskBand.className = `risk-pill risk-${band}`;
}

function getPayload() {
  const values = {};
  for (const field of fields) {
    const value = byId(field).value.trim();
    values[field] = numberFields.has(field) ? Number(value) : value;
  }

  return {
    object_a: {
      object_id: values.a_object_id,
      eccentricity: values.a_eccentricity,
      inclination_deg: values.a_inclination_deg,
      raan_deg: values.a_raan_deg,
      arg_perigee_deg: values.a_arg_perigee_deg,
      mean_anomaly_deg: values.a_mean_anomaly_deg,
      mean_motion_rev_per_day: values.a_mean_motion_rev_per_day,
    },
    object_b: {
      object_id: values.b_object_id,
      eccentricity: values.b_eccentricity,
      inclination_deg: values.b_inclination_deg,
      raan_deg: values.b_raan_deg,
      arg_perigee_deg: values.b_arg_perigee_deg,
      mean_anomaly_deg: values.b_mean_anomaly_deg,
      mean_motion_rev_per_day: values.b_mean_motion_rev_per_day,
    },
    closest_approach_km: values.closest_approach_km,
    relative_velocity_kms: values.relative_velocity_kms,
  };
}

function applySampleData() {
  const sample = {
    a_object_id: "SAT-ALPHA",
    a_eccentricity: 0.0012,
    a_inclination_deg: 97.84,
    a_raan_deg: 121.13,
    a_arg_perigee_deg: 247.2,
    a_mean_anomaly_deg: 12.8,
    a_mean_motion_rev_per_day: 14.21,
    b_object_id: "SAT-BETA",
    b_eccentricity: 0.0021,
    b_inclination_deg: 97.49,
    b_raan_deg: 122.08,
    b_arg_perigee_deg: 244.9,
    b_mean_anomaly_deg: 9.4,
    b_mean_motion_rev_per_day: 14.33,
    closest_approach_km: 0.84,
    relative_velocity_kms: 12.9,
  };
  for (const [key, value] of Object.entries(sample)) {
    byId(key).value = String(value);
  }
  setStatus(elements.predictStatus, "Sample telemetry loaded.", "neutral");
}

async function fetchToken() {
  const baseUrl = normalizeBaseUrl(elements.baseUrl.value.trim());
  const body = new URLSearchParams({
    username: elements.username.value.trim(),
    password: elements.password.value,
  });

  setStatus(elements.tokenStatus, "Authenticating...", "neutral");
  elements.tokenBtn.disabled = true;

  try {
    const response = await fetch(`${baseUrl}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Authentication failed.");
    }
    state.accessToken = data.access_token;
    setStatus(elements.tokenStatus, "Authenticated successfully.", "success");
  } catch (error) {
    state.accessToken = null;
    setStatus(elements.tokenStatus, error.message, "error");
  } finally {
    elements.tokenBtn.disabled = false;
  }
}

async function predictRisk() {
  if (!state.accessToken) {
    setStatus(elements.predictStatus, "Get an access token first.", "error");
    return;
  }

  const baseUrl = normalizeBaseUrl(elements.baseUrl.value.trim());
  const payload = getPayload();

  setStatus(elements.predictStatus, "Predicting collision probability...", "neutral");
  elements.predictBtn.disabled = true;

  try {
    const response = await fetch(`${baseUrl}/v1/predict`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${state.accessToken}`,
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Prediction request failed.");
    }

    const probability = Number(data.collision_probability || 0);
    setGauge(probability);
    setRiskBand(data.collision_risk_band || "low");
    elements.modelVersion.textContent = data.model_version || "--";
    setStatus(elements.predictStatus, "Prediction complete.", "success");
  } catch (error) {
    setStatus(elements.predictStatus, error.message, "error");
  } finally {
    elements.predictBtn.disabled = false;
  }
}

elements.tokenBtn.addEventListener("click", fetchToken);
elements.predictBtn.addEventListener("click", predictRisk);
elements.presetBtn.addEventListener("click", applySampleData);

applySampleData();
