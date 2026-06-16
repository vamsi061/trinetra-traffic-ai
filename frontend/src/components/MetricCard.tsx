interface Props {
  label: string
  value: string | number
  icon?: React.ReactNode
  color?: string
}

const colorMap: Record<string, { border: string; hex: string }> = {
  red: { border: 'border-red-500', hex: '#ef4444' },
  green: { border: 'border-green-500', hex: '#22c55e' },
  blue: { border: 'border-blue-500', hex: '#3b82f6' },
  amber: { border: 'border-amber-500', hex: '#f59e0b' },
  orange: { border: 'border-orange-500', hex: '#f97316' },
  purple: { border: 'border-purple-500', hex: '#a855f7' },
}

export default function MetricCard({ label, value, icon, color = 'red' }: Props) {
  const c = colorMap[color] || colorMap.red

  return (
    <div
      className="glass rounded-xl p-4 border-l-4 transition-all duration-300 hover:scale-105"
      style={{ borderLeftColor: c.hex }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs sm:text-sm text-trinetra-muted">{label}</span>
        {icon && <span className="text-trinetra-muted">{icon}</span>}
      </div>
      <div className="text-xl sm:text-3xl font-bold text-white">{value}</div>
    </div>
  )
}
