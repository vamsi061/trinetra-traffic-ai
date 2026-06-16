interface Props {
  label: string
  value: string | number
  icon?: React.ReactNode
  color?: string
}

export default function MetricCard({ label, value, icon, color = 'red' }: Props) {
  const borderColor = color === 'red' ? 'border-red-500' : color === 'green' ? 'border-green-500' : 'border-blue-500'
  const glowColor = color === 'red' ? 'rgba(239,68,68,0.15)' : color === 'green' ? 'rgba(34,197,94,0.15)' : 'rgba(59,130,246,0.15)'

  return (
    <div
      className="glass rounded-xl p-6 border-l-4 transition-all duration-300 hover:scale-105"
      style={{ borderLeftColor: color === 'red' ? '#ef4444' : color === 'green' ? '#22c55e' : '#3b82f6' }}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-trinetra-muted">{label}</span>
        {icon && <span className="text-trinetra-muted">{icon}</span>}
      </div>
      <div className="text-3xl font-bold text-white">{value}</div>
    </div>
  )
}
