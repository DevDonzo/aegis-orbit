"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAuthToken } from "@/lib/auth";
import { buildWebSocketUrl } from "@/lib/env";
import { fetchMissionSnapshot, fetchMlStatus, fetchPredictions } from "@/services/simulationService";
import { useSimulationStore } from "@/store/useSimulationStore";

export function useSimulationPolling() {
  const setMissionSnapshot = useSimulationStore((state) => state.setMissionSnapshot);
  const applyPredictions = useSimulationStore((state) => state.applyPredictions);
  const setConnectionState = useSimulationStore((state) => state.setConnectionState);
  const setMetrics = useSimulationStore((state) => state.setMetrics);
  const setMlStatus = useSimulationStore((state) => state.setMlStatus);

  const snapshotQuery = useQuery({
    queryKey: ["mission", "snapshot"],
    queryFn: fetchMissionSnapshot,
    refetchInterval: 12_000
  });

  const predictionsQuery = useQuery({
    queryKey: ["mission", "predictions"],
    queryFn: fetchPredictions,
    refetchInterval: 10_000
  });

  const mlStatusQuery = useQuery({
    queryKey: ["mission", "ml-status"],
    queryFn: fetchMlStatus,
    refetchInterval: 30_000
  });

  useEffect(() => {
    if (snapshotQuery.data) {
      setMissionSnapshot(snapshotQuery.data);
    }
  }, [snapshotQuery.data, setMissionSnapshot]);

  useEffect(() => {
    if (predictionsQuery.data && predictionsQuery.data.length > 0) {
      applyPredictions(predictionsQuery.data);
    }
  }, [predictionsQuery.data, applyPredictions]);

  useEffect(() => {
    if (mlStatusQuery.data !== undefined) {
      setMlStatus(mlStatusQuery.data);
    }
  }, [mlStatusQuery.data, setMlStatus]);

  useEffect(() => {
    if (snapshotQuery.isLoading || predictionsQuery.isLoading) {
      setConnectionState("connecting");
      return;
    }
    if (snapshotQuery.isError || predictionsQuery.isError) {
      setConnectionState("offline");
      return;
    }
    if (snapshotQuery.isFetching || predictionsQuery.isFetching || mlStatusQuery.isFetching) {
      setConnectionState("degraded");
      return;
    }
    setConnectionState("online");
  }, [
    snapshotQuery.isLoading,
    snapshotQuery.isError,
    snapshotQuery.isFetching,
    predictionsQuery.isLoading,
    predictionsQuery.isError,
    predictionsQuery.isFetching,
    mlStatusQuery.isFetching,
    setConnectionState
  ]);

  useEffect(() => {
    const token = getAuthToken();
    const url = new URL(buildWebSocketUrl("/ws/system-status"));
    if (token) {
      url.searchParams.set("token", token);
    }

    let isMounted = true;
    let socket: WebSocket | null = null;

    try {
      socket = new WebSocket(url.toString());
    } catch {
      setMetrics({ wsConnected: false });
      return;
    }

    socket.onopen = () => {
      if (!isMounted) return;
      setMetrics({ wsConnected: true });
    };
    socket.onerror = () => {
      if (!isMounted) return;
      setMetrics({ wsConnected: false });
    };
    socket.onclose = () => {
      if (!isMounted) return;
      setMetrics({ wsConnected: false });
    };

    return () => {
      isMounted = false;
      socket?.close();
    };
  }, [setMetrics]);
}
