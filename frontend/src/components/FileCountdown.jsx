import { useEffect, useMemo, useState } from 'react'

function formatSeconds(totalSeconds) {
  if (totalSeconds <= 0) return '00:00'
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (hours > 0) {
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  }
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export default function FileCountdown({ expiresAt, onExpire }) {
  const target = useMemo(() => new Date(expiresAt).getTime(), [expiresAt])
  const [secondsLeft, setSecondsLeft] = useState(() => Math.max(0, Math.floor((target - Date.now()) / 1000)))

  useEffect(() => {
    if (!Number.isFinite(target)) return undefined

    const timer = setInterval(() => {
      const next = Math.max(0, Math.floor((target - Date.now()) / 1000))
      setSecondsLeft(next)
      if (next <= 0) {
        clearInterval(timer)
        if (onExpire) onExpire()
      }
    }, 1000)

    return () => clearInterval(timer)
  }, [target, onExpire])

  if (secondsLeft <= 0) {
    return 'Срок хранения истёк'
  }

  return formatSeconds(secondsLeft)
}
