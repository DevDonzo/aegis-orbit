"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as Cesium from "cesium";
import { useSceneManager } from "@/components/cesium/useSceneManager";
import { getArcGisToken, getCesiumIonToken, getGlobeImageryMode } from "@/lib/env";
import { useSimulationStore } from "@/store/useSimulationStore";

type ViewerReadyState = "booting" | "ready" | "error";

async function buildImageryProvider(): Promise<Cesium.ImageryProvider> {
  const imageryMode = getGlobeImageryMode();
  const ionToken = getCesiumIonToken();
  const arcGisToken = getArcGisToken();

  if (imageryMode === "cesium-ion") {
    if (ionToken) {
      Cesium.Ion.defaultAccessToken = ionToken;
    }
    if (Cesium.Ion.defaultAccessToken && Cesium.Ion.defaultAccessToken.length > 0) {
      return Cesium.createWorldImageryAsync({
        style: Cesium.IonWorldImageryStyle.AERIAL_WITH_LABELS
      });
    }
  }

  if (imageryMode !== "osm") {
    try {
      if (arcGisToken) {
        Cesium.ArcGisMapService.defaultAccessToken = arcGisToken;
      }
      return await Cesium.ArcGisMapServerImageryProvider.fromBasemapType(Cesium.ArcGisBaseMapType.SATELLITE);
    } catch {
      // Fall through to OSM fallback when ArcGIS imagery is unavailable.
    }
  }

  return new Cesium.OpenStreetMapImageryProvider({
    url: "https://tile.openstreetmap.org/"
  });
}

export default function CesiumViewer() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const [readyState, setReadyState] = useState<ViewerReadyState>("booting");

  const satellitesMap = useSimulationStore((state) => state.satellites);
  const collisionEvents = useSimulationStore((state) => state.collisionEvents);
  const selectedEntityId = useSimulationStore((state) => state.selectedEntityId);
  const selectedCollisionId = useSimulationStore((state) => state.selectedCollisionId);
  const setSelectedEntityId = useSimulationStore((state) => state.setSelectedEntityId);
  const setMetrics = useSimulationStore((state) => state.setMetrics);
  const currentTimeIso = useSimulationStore((state) => state.currentTimeIso);
  const setCurrentTimeIso = useSimulationStore((state) => state.setCurrentTimeIso);

  const satellites = useMemo(() => Object.values(satellitesMap), [satellitesMap]);

  useSceneManager({
    viewer: viewerRef.current,
    satellites,
    collisionEvents,
    selectedEntityId,
    selectedCollisionId
  });

  useEffect(() => {
    let cancelled = false;
    let onTickDisposer: (() => void) | null = null;
    let postRenderDisposer: (() => void) | null = null;

    async function initializeViewer() {
      try {
        if (typeof window !== "undefined") {
          (window as Window & { CESIUM_BASE_URL?: string }).CESIUM_BASE_URL = "/cesium";
        }
        if (!containerRef.current || cancelled) return;

        const imageryProvider = await buildImageryProvider();
        const ionToken = getCesiumIonToken();
        const useIonTerrain = Boolean(ionToken && ionToken.length > 0);

        const viewer = new Cesium.Viewer(containerRef.current, {
          baseLayer: new Cesium.ImageryLayer(imageryProvider),
          timeline: false,
          animation: false,
          geocoder: false,
          baseLayerPicker: false,
          sceneModePicker: false,
          navigationHelpButton: false,
          fullscreenButton: false,
          infoBox: false,
          selectionIndicator: false,
          shouldAnimate: true,
          scene3DOnly: true,
          useBrowserRecommendedResolution: false,
          msaaSamples: 4,
          terrain: useIonTerrain
            ? Cesium.Terrain.fromWorldTerrain({
                requestVertexNormals: true,
                requestWaterMask: true
              })
            : undefined,
          terrainProvider: useIonTerrain ? undefined : new Cesium.EllipsoidTerrainProvider()
        });
        viewerRef.current = viewer;
        viewer.scene.globe.enableLighting = true;
        viewer.scene.globe.dynamicAtmosphereLighting = true;
        viewer.scene.globe.dynamicAtmosphereLightingFromSun = true;
        viewer.scene.globe.showGroundAtmosphere = true;
        viewer.scene.globe.depthTestAgainstTerrain = false;
        viewer.scene.globe.maximumScreenSpaceError = 0.7;
        viewer.scene.globe.tileCacheSize = 2_500;
        viewer.scene.highDynamicRange = true;
        viewer.scene.postProcessStages.fxaa.enabled = true;
        viewer.scene.sunBloom = true;
        if (viewer.scene.skyAtmosphere) {
          viewer.scene.skyAtmosphere.brightnessShift = -0.12;
          viewer.scene.skyAtmosphere.saturationShift = -0.15;
        }
        viewer.shadows = true;
        viewer.resolutionScale = Math.min(2, window.devicePixelRatio || 1);
        viewer.scene.screenSpaceCameraController.maximumTiltAngle = Cesium.Math.toRadians(89.0);
        viewer.scene.screenSpaceCameraController.inertiaTranslate = 0.88;
        viewer.scene.screenSpaceCameraController.inertiaSpin = 0.9;
        viewer.scene.screenSpaceCameraController.inertiaZoom = 0.85;
        viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(-35.0, 26.0, 18_500_000),
          orientation: {
            heading: Cesium.Math.toRadians(16),
            pitch: Cesium.Math.toRadians(-32),
            roll: 0
          }
        });
        viewer.clock.multiplier = 90;
        setReadyState("ready");

        let lastTickUpdate = 0;
        const onTick = () => {
          const now = performance.now();
          if (now - lastTickUpdate < 250) return;
          lastTickUpdate = now;
          const iso = Cesium.JulianDate.toDate(viewer.clock.currentTime).toISOString();
          setCurrentTimeIso(iso);
        };
        viewer.clock.onTick.addEventListener(onTick);
        onTickDisposer = () => viewer.clock.onTick.removeEventListener(onTick);

        let lastFrameTime = performance.now();
        const postRender = () => {
          const frameNow = performance.now();
          const fps = 1000 / Math.max(1, frameNow - lastFrameTime);
          lastFrameTime = frameNow;
          setMetrics({ fps });
        };
        viewer.scene.postRender.addEventListener(postRender);
        postRenderDisposer = () => viewer.scene.postRender.removeEventListener(postRender);

        viewer.selectedEntityChanged.addEventListener((entity) => {
          const nextId = entity?.id;
          if (typeof nextId === "string" && nextId.startsWith("satellite:")) {
            setSelectedEntityId(nextId.replace("satellite:", ""));
          }
        });
      } catch {
        setReadyState("error");
      }
    }

    initializeViewer();

    return () => {
      cancelled = true;
      onTickDisposer?.();
      postRenderDisposer?.();
      viewerRef.current?.destroy();
      viewerRef.current = null;
    };
  }, [setCurrentTimeIso, setMetrics, setSelectedEntityId]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !selectedEntityId) return;

    const entity = viewer.entities.getById(`satellite:${selectedEntityId}`);
    if (!entity) return;

    viewer.flyTo(entity, {
      duration: 0.9,
      offset: new Cesium.HeadingPitchRange(Cesium.Math.toRadians(18), Cesium.Math.toRadians(-28), 1_250_000)
    }).catch(() => undefined);
  }, [selectedEntityId]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !selectedCollisionId) return;

    const entity = viewer.entities.getById(`collision-line:${selectedCollisionId}`);
    if (!entity) return;

    viewer.flyTo(entity, {
      duration: 0.9,
      offset: new Cesium.HeadingPitchRange(Cesium.Math.toRadians(12), Cesium.Math.toRadians(-25), 1_600_000)
    }).catch(() => undefined);
  }, [selectedCollisionId]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    const target = Cesium.JulianDate.fromDate(new Date(currentTimeIso));
    const delta = Math.abs(Cesium.JulianDate.secondsDifference(target, viewer.clock.currentTime));
    if (delta > 0.5) {
      viewer.clock.currentTime = target;
    }
  }, [currentTimeIso]);

  return (
    <div className="absolute inset-0">
      <div ref={containerRef} className="h-full w-full" />
      {readyState === "booting" ? (
        <div className="absolute inset-0 flex items-center justify-center bg-cosmic-950/35">
          <div className="hud-panel px-6 py-4 text-sm text-slate-200">
            <p className="section-kicker">Scene Initialization</p>
            <p className="mt-2 text-base font-medium text-white">Bootstrapping orbital renderer...</p>
          </div>
        </div>
      ) : null}
      {readyState === "error" ? (
        <div className="absolute inset-x-0 top-4 mx-auto w-fit rounded-sm border border-red-400/60 bg-red-500/15 px-4 py-3 text-sm text-red-100">
          Cesium initialization failed. Verify WebGL support, tokens, and static asset paths.
        </div>
      ) : null}
    </div>
  );
}
