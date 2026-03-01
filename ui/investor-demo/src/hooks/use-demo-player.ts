"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import type {
  DomainId,
  CycleData,
  GovernanceEvent,
  CumulativeStats,
  DomainConfig,
} from "@/lib/demo-data";
import { DOMAINS, deriveEvents, getCumulativeStats } from "@/lib/demo-data";
import { DEMO_DATASETS } from "@/lib/demo-datasets";

export type PlayState = "idle" | "playing" | "paused" | "finished";
export type PlaySpeed = 1 | 2 | 3;

interface DemoPlayerState {
  domain: DomainId;
  domainConfig: DomainConfig;
  playState: PlayState;
  speed: PlaySpeed;
  currentCycleIndex: number;
  currentCycle: CycleData | null;
  timeline: CycleData[];
  events: GovernanceEvent[];
  visibleEvents: GovernanceEvent[];
  stats: CumulativeStats;
  trustHistory: Array<{ cycle: number } & Record<string, number>>;
  thresholdHistory: Array<{
    cycle: number;
    trust_threshold: number;
    suppression_threshold: number;
  }>;
}

interface DemoPlayerActions {
  play: () => void;
  pause: () => void;
  reset: () => void;
  setSpeed: (speed: PlaySpeed) => void;
  setDomain: (domain: DomainId) => void;
  skipTo: (cycleIndex: number) => void;
}

const SPEED_MS: Record<PlaySpeed, number> = {
  1: 2000,
  2: 1200,
  3: 600,
};

export function useDemoPlayer(): DemoPlayerState & DemoPlayerActions {
  const [domain, setDomainState] = useState<DomainId>("fraud");
  const [playState, setPlayState] = useState<PlayState>("idle");
  const [speed, setSpeed] = useState<PlaySpeed>(1);
  const [currentCycleIndex, setCurrentCycleIndex] = useState(-1);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const speedRef = useRef(speed);

  const dataset = DEMO_DATASETS[domain];
  const domainConfig = DOMAINS[domain];
  const timeline = dataset.timeline;
  const allEvents = deriveEvents(timeline, domainConfig);

  // Keep speed ref current
  useEffect(() => {
    speedRef.current = speed;
  }, [speed]);

  // Clear timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const currentCycle =
    currentCycleIndex >= 0 && currentCycleIndex < timeline.length
      ? timeline[currentCycleIndex]
      : null;

  const currentCycleNumber = currentCycle?.cycle ?? -1;

  const visibleEvents = allEvents.filter((e) => e.cycle <= currentCycleNumber);

  const stats = getCumulativeStats(timeline, currentCycleNumber, domainConfig);

  // Build trust history up to current cycle
  const trustHistory = timeline
    .filter((c) => c.cycle <= currentCycleNumber && c.status !== "circuit_breaker")
    .map((c) => ({
      cycle: c.cycle,
      ...c.trust_scores,
    }));

  // Build threshold history
  const thresholdHistory = timeline
    .filter(
      (c) =>
        c.cycle <= currentCycleNumber &&
        c.trust_threshold !== undefined &&
        c.status !== "circuit_breaker"
    )
    .map((c) => ({
      cycle: c.cycle,
      trust_threshold: c.trust_threshold!,
      suppression_threshold: c.suppression_threshold!,
    }));

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startTimer = useCallback(() => {
    stopTimer();
    timerRef.current = setInterval(() => {
      setCurrentCycleIndex((prev) => {
        const next = prev + 1;
        if (next >= timeline.length) {
          stopTimer();
          setPlayState("finished");
          return prev;
        }
        return next;
      });
    }, SPEED_MS[speedRef.current]);
  }, [timeline.length, stopTimer]);

  const play = useCallback(() => {
    if (currentCycleIndex >= timeline.length - 1) {
      // Reset if finished
      setCurrentCycleIndex(0);
    } else if (currentCycleIndex < 0) {
      setCurrentCycleIndex(0);
    }
    setPlayState("playing");
    startTimer();
  }, [currentCycleIndex, timeline.length, startTimer]);

  const pause = useCallback(() => {
    setPlayState("paused");
    stopTimer();
  }, [stopTimer]);

  const reset = useCallback(() => {
    stopTimer();
    setCurrentCycleIndex(-1);
    setPlayState("idle");
  }, [stopTimer]);

  const setSpeedAction = useCallback(
    (newSpeed: PlaySpeed) => {
      setSpeed(newSpeed);
      speedRef.current = newSpeed;
      if (playState === "playing") {
        startTimer();
      }
    },
    [playState, startTimer]
  );

  const setDomain = useCallback(
    (newDomain: DomainId) => {
      stopTimer();
      setDomainState(newDomain);
      setCurrentCycleIndex(-1);
      setPlayState("idle");
    },
    [stopTimer]
  );

  const skipTo = useCallback(
    (idx: number) => {
      const clamped = Math.max(0, Math.min(idx, timeline.length - 1));
      setCurrentCycleIndex(clamped);
      if (playState !== "playing") {
        setPlayState("paused");
      }
    },
    [timeline.length, playState]
  );

  return {
    domain,
    domainConfig,
    playState,
    speed,
    currentCycleIndex,
    currentCycle,
    timeline,
    events: allEvents,
    visibleEvents,
    stats,
    trustHistory,
    thresholdHistory,
    play,
    pause,
    reset,
    setSpeed: setSpeedAction,
    setDomain,
    skipTo,
  };
}
