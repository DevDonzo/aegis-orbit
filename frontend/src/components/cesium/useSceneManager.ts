"use client";

import { useEffect, useRef } from "react";
import * as Cesium from "cesium";
import { toCartesian3 } from "@/lib/cesiumCoordinates";
import type { CollisionRisk, OrbitData } from "@/types";

interface SceneManagerOptions {
  viewer: Cesium.Viewer | null;
  satellites: OrbitData[];
  collisionEvents: CollisionRisk[];
  selectedEntityId: string | null;
  selectedCollisionId: string | null;
}

function colorForRisk(riskBand: CollisionRisk["riskBand"]) {
  if (riskBand === "critical") return Cesium.Color.fromCssColorString("#ff5d78");
  if (riskBand === "high") return Cesium.Color.fromCssColorString("#ff9c7d");
  if (riskBand === "moderate") return Cesium.Color.fromCssColorString("#ffd36e");
  return Cesium.Color.fromCssColorString("#63f5e4");
}

function lineWidthForRisk(riskBand: CollisionRisk["riskBand"], selected: boolean) {
  const width = riskBand === "critical" ? 5.4 : riskBand === "high" ? 4.0 : riskBand === "moderate" ? 2.9 : 2.0;
  return selected ? width + 1.4 : width;
}

function buildSampledPositionProperty(telemetry: OrbitData["telemetry"]) {
  const property = new Cesium.SampledPositionProperty();
  telemetry.forEach((sample) => {
    property.addSample(Cesium.JulianDate.fromDate(new Date(sample.timestampIso)), toCartesian3(Cesium, sample));
  });
  property.setInterpolationOptions({
    interpolationAlgorithm: Cesium.HermitePolynomialApproximation,
    interpolationDegree: 2
  });
  return property;
}

export function useSceneManager({
  viewer,
  satellites,
  collisionEvents,
  selectedEntityId,
  selectedCollisionId
}: SceneManagerOptions) {
  const satelliteEntityIds = useRef<Set<string>>(new Set());
  const collisionEntityIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!viewer) return;

    const nextSatelliteIds = new Set<string>();
    satellites.forEach((satellite) => {
      if (satellite.telemetry.length === 0) return;

      const id = `satellite:${satellite.id}`;
      const isSelected = selectedEntityId === satellite.id;
      nextSatelliteIds.add(id);
      const telemetryPositions = satellite.telemetry.map((sample) => toCartesian3(Cesium, sample));
      const sampledPosition = buildSampledPositionProperty(satellite.telemetry);
      const orbitColor = isSelected
        ? Cesium.Color.fromCssColorString("#ffd36e").withAlpha(0.96)
        : colorForRisk(satellite.riskBand).withAlpha(satellite.riskBand === "low" ? 0.42 : 0.68);
      const orbitMaterial =
        satellite.riskBand === "low" && !isSelected
          ? new Cesium.ColorMaterialProperty(orbitColor)
          : new Cesium.PolylineGlowMaterialProperty({
              glowPower: isSelected ? 0.28 : 0.18,
              color: orbitColor
            });
      const existing = viewer.entities.getById(id);

      const pathEntity = {
        id,
        name: satellite.id,
        availability: new Cesium.TimeIntervalCollection([
          new Cesium.TimeInterval({
            start: Cesium.JulianDate.fromDate(new Date(satellite.telemetry[0].timestampIso)),
            stop: Cesium.JulianDate.fromDate(new Date(satellite.telemetry.at(-1)?.timestampIso ?? satellite.telemetry[0].timestampIso))
          })
        ]),
        position: sampledPosition,
        polyline: {
          positions: telemetryPositions,
          width: isSelected ? 4.0 : 2.6,
          material: orbitMaterial,
          depthFailMaterial: new Cesium.ColorMaterialProperty(orbitColor.withAlpha(isSelected ? 0.42 : 0.18))
        },
        point: {
          pixelSize: isSelected ? 12 : 8,
          color: orbitColor,
          outlineWidth: isSelected ? 3 : 1.6,
          outlineColor: Cesium.Color.fromCssColorString("#02060d"),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          scaleByDistance: new Cesium.NearFarScalar(3_000_000, 1.0, 22_000_000, 0.42),
          translucencyByDistance: new Cesium.NearFarScalar(3_000_000, 1.0, 22_000_000, 0.34)
        },
        ellipsoid: {
          radii: new Cesium.Cartesian3(isSelected ? 28_000 : 18_000, isSelected ? 28_000 : 18_000, isSelected ? 28_000 : 18_000),
          material: orbitColor.withAlpha(isSelected ? 0.12 : 0.08),
          outline: isSelected,
          outlineColor: orbitColor.withAlpha(0.38)
        },
        label: {
          text: satellite.id,
          font: isSelected ? "600 12px 'JetBrains Mono', monospace" : "500 11px 'JetBrains Mono', monospace",
          fillColor: Cesium.Color.fromCssColorString("#edf6ff"),
          showBackground: true,
          backgroundColor: Cesium.Color.fromCssColorString("#08101c").withAlpha(isSelected ? 0.82 : 0.52),
          pixelOffset: new Cesium.Cartesian2(12, -14),
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          outlineColor: Cesium.Color.fromCssColorString("#02060e"),
          outlineWidth: 2,
          distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0.0, 26_000_000.0),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          scaleByDistance: new Cesium.NearFarScalar(2_500_000, 1.0, 22_000_000, 0.55),
          translucencyByDistance: new Cesium.NearFarScalar(2_500_000, 1.0, 22_000_000, 0.32),
          show: isSelected || satellite.riskBand === "critical" || satellite.riskBand === "high"
        }
      };

      if (!existing) {
        viewer.entities.add(pathEntity);
      } else {
        viewer.entities.removeById(id);
        viewer.entities.add(pathEntity);
      }
    });

    satelliteEntityIds.current.forEach((id) => {
      if (!nextSatelliteIds.has(id)) {
        viewer.entities.removeById(id);
      }
    });
    satelliteEntityIds.current = nextSatelliteIds;
  }, [viewer, satellites, selectedEntityId]);

  useEffect(() => {
    if (!viewer) return;

    const nextCollisionIds = new Set<string>();

    collisionEvents.forEach((event) => {
      const lineId = `collision-line:${event.id}`;
      const labelId = `collision-label:${event.id}`;
      const zoneId = `collision-zone:${event.id}`;
      const isSelected = selectedCollisionId === event.id;
      nextCollisionIds.add(lineId);
      nextCollisionIds.add(labelId);

      const start = toCartesian3(Cesium, event.vectorStart);
      const end = toCartesian3(Cesium, event.vectorEnd);
      const center = Cesium.Cartesian3.midpoint(start, end, new Cesium.Cartesian3());
      const color = colorForRisk(event.riskBand);
      const shouldRenderVolume = event.riskBand !== "low";
      const lineMaterial =
        event.riskBand === "low" && !isSelected
          ? new Cesium.ColorMaterialProperty(color.withAlpha(0.42))
          : new Cesium.PolylineGlowMaterialProperty({
              glowPower: isSelected ? 0.32 : event.riskBand === "critical" ? 0.22 : 0.16,
              color: color.withAlpha(isSelected ? 0.95 : 0.84)
            });

      const lineEntity = {
        id: lineId,
        polyline: {
          positions: [start, end],
          width: lineWidthForRisk(event.riskBand, isSelected),
          material: lineMaterial,
          depthFailMaterial: new Cesium.ColorMaterialProperty(color.withAlpha(0.24))
        }
      };

      if (!viewer.entities.getById(lineId)) {
        viewer.entities.add(lineEntity);
      } else {
        viewer.entities.removeById(lineId);
        viewer.entities.add(lineEntity);
      }

      const labelEntity = {
        id: labelId,
        position: center,
        label: {
          text: `${event.primaryObjectId} / ${event.secondaryObjectId}\n${event.missDistanceKm.toFixed(2)} km`,
          font: "500 10px 'JetBrains Mono', monospace",
          fillColor: Cesium.Color.fromCssColorString("#f3f7ff"),
          showBackground: true,
          backgroundColor: Cesium.Color.fromCssColorString("#09111d").withAlpha(0.72),
          pixelOffset: new Cesium.Cartesian2(0, -14),
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          outlineColor: Cesium.Color.fromCssColorString("#02060e"),
          outlineWidth: 2,
          show: isSelected || event.riskBand === "critical"
        }
      };
      if (!viewer.entities.getById(labelId)) {
        viewer.entities.add(labelEntity);
      } else {
        viewer.entities.removeById(labelId);
        viewer.entities.add(labelEntity);
      }

      if (shouldRenderVolume) {
        nextCollisionIds.add(zoneId);
        const radiusMeters = Math.max(24_000, Math.min(160_000, event.riskZoneRadiusKm * 550));
        const zoneEntity = {
          id: zoneId,
          position: center,
          ellipsoid: {
            radii: new Cesium.Cartesian3(radiusMeters, radiusMeters, radiusMeters * 0.55),
            material: color.withAlpha(isSelected ? 0.16 : 0.1),
            outline: true,
            outlineColor: color.withAlpha(isSelected ? 0.78 : 0.45)
          }
        };
        if (!viewer.entities.getById(zoneId)) {
          viewer.entities.add(zoneEntity);
        } else {
          viewer.entities.removeById(zoneId);
          viewer.entities.add(zoneEntity);
        }
      }
    });

    collisionEntityIds.current.forEach((id) => {
      if (!nextCollisionIds.has(id)) {
        viewer.entities.removeById(id);
      }
    });
    collisionEntityIds.current = nextCollisionIds;
  }, [viewer, collisionEvents, selectedCollisionId]);
}
