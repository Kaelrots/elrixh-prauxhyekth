// Opt-in machine-readable progress for the local world-sync launcher.
export function buildProgress(phase: string, total: number) {
  let done = 0
  let previous = -1
  const emit = () => {
    if (process.env.WORLD_SYNC_PROGRESS !== "1") return
    const percent = total === 0 ? 100 : Math.floor((done / total) * 100)
    if (percent === previous) return
    previous = percent
    console.log(`WORLD_SYNC_PROGRESS ${JSON.stringify({ phase, done, total })}`)
  }
  emit()
  return () => {
    done++
    emit()
  }
}
