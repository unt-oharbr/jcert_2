interface ProgressBarProps {
  label: string
  fraction: number // 0..1
}

export function ProgressBar({ label, fraction }: ProgressBarProps) {
  const percent = Math.round(Math.min(Math.max(fraction, 0), 1) * 100)
  return (
    <div className="progress-bar">
      <div className="progress-bar-label">
        <span>{label}</span>
        <strong>{percent}%</strong>
      </div>
      <div className="progress-bar-track">
        <div className="progress-bar-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}
