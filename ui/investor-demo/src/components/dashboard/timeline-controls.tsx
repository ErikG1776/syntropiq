"use client";

import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
    <Card>
      <CardContent className="py-3 px-5">
        <div className="flex items-center gap-4">
          {/* Play / Pause / Reset */}
          <div className="flex items-center gap-1.5">
            {playState === "playing" ? (
              <Button variant="secondary" size="icon" onClick={onPause}>
                <Pause className="w-4 h-4" />
              </Button>
            ) : (
              <Button size="icon" onClick={onPlay}>
                <Play className="w-4 h-4" />
              </Button>
            )}
            <Button variant="ghost" size="icon" onClick={onReset}>
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
          </div>

          {/* Speed selector */}
          <div className="flex items-center gap-0.5 bg-muted rounded-lg p-0.5">
            {([1, 2, 3] as PlaySpeed[]).map((s) => (
              <button
                key={s}
                onClick={() => onSetSpeed(s)}
                className={cn(
                  "px-2.5 py-1 rounded-md text-xs font-mono transition-all cursor-pointer",
                  speed === s
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {s}x
              </button>
            ))}
            <FastForward className="w-3 h-3 text-muted-foreground mx-1" />
          </div>

          {/* Progress bar */}
          <div className="flex-1 mx-2">
            <div
              className="relative h-1.5 bg-muted rounded-full cursor-pointer overflow-hidden group"
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const pct = (e.clientX - rect.left) / rect.width;
                onSkipTo(Math.floor(pct * totalCycles));
              }}
            >
              <div
                className="absolute inset-y-0 left-0 bg-primary rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
              <div
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-foreground rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ left: `calc(${progress}% - 6px)` }}
              />
            </div>
          </div>

          {/* Cycle info */}
          <div className="text-right shrink-0">
            <span className="text-sm font-mono tabular-nums">
              {Math.max(0, currentCycleIndex + 1)}{" "}
              <span className="text-muted-foreground">/ {totalCycles}</span>
            </span>
            <p className="text-[10px] text-muted-foreground truncate max-w-[160px]">
              {currentPhase}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
