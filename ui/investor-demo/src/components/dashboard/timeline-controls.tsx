"use client";

import { cn } from "@/lib/utils";
import { Play, Pause, RotateCcw, FastForward } from "lucide-react";
import type { PlayState, PlaySpeed } from "@/hooks/use-demo-player";

interface TimelineControlsProps {
  playState: PlayState;
  speed: PlaySpeed;
  currentCycleIndex: number;
  totalCycles: number;
  currentPhase: string;
  onPlay: () => void;
  onPause: () => void;
  onReset: () => void;
  onSetSpeed: (speed: PlaySpeed) => void;
  onSkipTo: (index: number) => void;
}

export function TimelineControls({
  playState,
  speed,
  currentCycleIndex,
  totalCycles,
  currentPhase,
  onPlay,
  onPause,
  onReset,
  onSetSpeed,
  onSkipTo,
}: TimelineControlsProps) {
  const progress =
    totalCycles > 0 ? ((currentCycleIndex + 1) / totalCycles) * 100 : 0;

  return (
    <div className="panel px-5 py-3">
      <div className="flex items-center gap-4">
        {/* Play / Pause / Reset */}
        <div className="flex items-center gap-1.5">
          {playState === "playing" ? (
            <button
              onClick={onPause}
              className="w-9 h-9 rounded-lg bg-white/[0.06] border border-border hover:bg-white/[0.1] flex items-center justify-center transition-colors cursor-pointer"
            >
              <Pause className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={onPlay}
              className="w-9 h-9 rounded-lg bg-blue-600 hover:bg-blue-500 flex items-center justify-center transition-colors cursor-pointer text-white"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={onReset}
            className="w-9 h-9 rounded-lg bg-white/[0.06] border border-border hover:bg-white/[0.1] flex items-center justify-center transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Speed selector */}
        <div className="flex items-center gap-1 bg-surface rounded-lg p-0.5 border border-border">
          {([1, 2, 3] as PlaySpeed[]).map((s) => (
            <button
              key={s}
              onClick={() => onSetSpeed(s)}
              className={cn(
                "px-2.5 py-1 rounded-md text-xs font-mono transition-all cursor-pointer",
                speed === s
                  ? "bg-white/[0.08] text-text-primary"
                  : "text-text-muted hover:text-text-secondary"
              )}
            >
              {s}x
            </button>
          ))}
          <FastForward className="w-3 h-3 text-text-muted mx-1" />
        </div>

        {/* Progress bar */}
        <div className="flex-1 mx-2">
          <div
            className="relative h-1.5 bg-white/[0.06] rounded-full cursor-pointer overflow-hidden group"
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const pct = (e.clientX - rect.left) / rect.width;
              onSkipTo(Math.floor(pct * totalCycles));
            }}
          >
            <div
              className="absolute inset-y-0 left-0 bg-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ left: `calc(${progress}% - 6px)` }}
            />
          </div>
        </div>

        {/* Cycle info */}
        <div className="text-right shrink-0">
          <span className="text-sm font-mono tabular-nums">
            {Math.max(0, currentCycleIndex + 1)}{" "}
            <span className="text-text-muted">/ {totalCycles}</span>
          </span>
          <p className="text-[10px] text-text-muted truncate max-w-[160px]">
            {currentPhase}
          </p>
        </div>
      </div>
    </div>
  );
}
