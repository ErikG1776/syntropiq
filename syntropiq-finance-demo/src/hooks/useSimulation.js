import { useState, useCallback, useRef, useEffect } from 'react'

const SPEEDS = { 1: 600, 2: 300, 4: 150, 8: 75 }

export function useSimulation(data) {
  const [currentWeek, setCurrentWeek] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [introComplete, setIntroComplete] = useState(false)
  const intervalRef = useRef(null)

  const totalWeeks = data?.timeline?.length || 0

  const play = useCallback(() => {
    if (currentWeek >= totalWeeks) setCurrentWeek(0)
    setIsPlaying(true)
  }, [currentWeek, totalWeeks])

  const pause = useCallback(() => setIsPlaying(false), [])

  const reset = useCallback(() => {
    setIsPlaying(false)
    setCurrentWeek(0)
  }, [])

  const stepForward = useCallback((n = 1) => {
    setCurrentWeek(w => Math.min(w + n, totalWeeks))
  }, [totalWeeks])

  const stepBack = useCallback((n = 1) => {
    setCurrentWeek(w => Math.max(w - n, 0))
  }, [])

  const seekTo = useCallback((week) => {
    setCurrentWeek(Math.max(0, Math.min(week, totalWeeks)))
  }, [totalWeeks])

  const jumpToRegimeShift = useCallback(() => {
    const regimeWeek = data?.summary?.regime_shift_week || 53
    seekTo(regimeWeek - 1)
  }, [data, seekTo])

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    if (isPlaying && currentWeek < totalWeeks) {
      intervalRef.current = setInterval(() => {
        setCurrentWeek(w => {
          if (w >= totalWeeks) { setIsPlaying(false); return w }
          return w + 1
        })
      }, SPEEDS[speed] || 600)
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [isPlaying, speed, totalWeeks, currentWeek])

  // Current slice of timeline up to currentWeek
  const visibleTimeline = data?.timeline?.slice(0, currentWeek) || []
  const currentData = currentWeek > 0 ? data?.timeline?.[currentWeek - 1] : null

  // Collect all events up to current week
  const visibleEvents = []
  for (let i = 0; i < currentWeek && i < (data?.timeline?.length || 0); i++) {
    const weekData = data.timeline[i]
    if (weekData.events) visibleEvents.push(...weekData.events)
  }

  // Count governance events up to current week
  const governanceEventCount = visibleEvents.filter(
    e => e.type !== 'trust_increase' && e.type !== 'trust_decrease'
  ).length

  return {
    currentWeek,
    currentData,
    visibleTimeline,
    visibleEvents,
    governanceEventCount,
    totalWeeks,
    isPlaying,
    speed,
    introComplete,
    setIntroComplete,
    play,
    pause,
    reset,
    stepForward,
    stepBack,
    seekTo,
    setSpeed,
    jumpToRegimeShift,
  }
}
