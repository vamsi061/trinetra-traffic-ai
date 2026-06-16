import { useEffect, useState } from 'react'
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  LineChart, Line, Area, AreaChart, ResponsiveContainer, Legend,
} from 'recharts'
import { getAnalytics, getStats, AnalyticsData, ViolationStats } from '../api/client'

const COLORS = ['#ef4444', '#f59e0b', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899']
const DARK_TOOLTIP = { contentStyle: { background: '#13182a', border: '1px solid #1e2a4a', borderRadius: '8px', color: '#e2e8f0' } }

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [stats, setStats] = useState<ViolationStats | null>(null)

  useEffect(() => {
    getStats().then(setStats)
    getAnalytics().then(setData)
  }, [])

  const typeData = (data?.by_type || []).map(d => ({ ...d, name: d.type === 'NO_HELMET' ? 'No Helmet' : 'Triple Riding' }))
  const dayData = data?.by_day || []
  const offenderData = (data?.repeat_offenders || []).filter(o => o.vehicle)
  const monthData = data?.monthly_trend || []

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-2">Violation Analytics</h1>
      <p className="text-trinetra-muted mb-8">Visual insights from traffic violation data</p>

      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-6 sm:mb-8">
          {[
            { label: 'Total Violations', value: stats.total },
            { label: 'No Helmet Cases', value: stats.no_helmet },
            { label: 'Triple Riding Cases', value: stats.triple_riding },
          ].map(s => (
            <div key={s.label} className="glass rounded-xl p-5 border-l-4 border-l-red-500">
              <div className="text-sm text-trinetra-muted">{s.label}</div>
              <div className="text-3xl font-bold text-white mt-1">{s.value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Pie Chart */}
        <div className="glass rounded-xl p-4 sm:p-6">
          <h3 className="text-sm sm:text-lg font-semibold text-white mb-4">Violations by Type</h3>
          {typeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={typeData} cx="50%" cy="50%" innerRadius={70} outerRadius={110}
                     dataKey="count" nameKey="name" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                     labelLine={false}>
                  {typeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip {...DARK_TOOLTIP} />
                <Legend wrapperStyle={{ color: '#e2e8f0' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-trinetra-muted text-center py-12">No data available</p>}
        </div>

        {/* Bar Chart */}
        <div className="glass rounded-xl p-4 sm:p-6">
          <h3 className="text-sm sm:text-lg font-semibold text-white mb-4">Violations by Type</h3>
          {typeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={typeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2a4a" />
                <XAxis dataKey="name" stroke="#8892b0" tick={{ fill: '#8892b0' }} />
                <YAxis stroke="#8892b0" tick={{ fill: '#8892b0' }} />
                <Tooltip {...DARK_TOOLTIP} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {typeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-trinetra-muted text-center py-12">No data available</p>}
        </div>

        {/* Daily Trend */}
        <div className="glass rounded-xl p-4 sm:p-6">
          <h3 className="text-sm sm:text-lg font-semibold text-white mb-4">Daily Trend (Last 30 Days)</h3>
          {dayData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={dayData}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2a4a" />
                <XAxis dataKey="day" stroke="#8892b0" tick={{ fill: '#8892b0', fontSize: 11 }} />
                <YAxis stroke="#8892b0" tick={{ fill: '#8892b0' }} />
                <Tooltip {...DARK_TOOLTIP} />
                <Area type="monotone" dataKey="count" stroke="#ef4444" fill="url(#colorCount)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : <p className="text-trinetra-muted text-center py-12">No data available</p>}
        </div>

        {/* Repeat Offenders */}
        <div className="glass rounded-xl p-4 sm:p-6">
          <h3 className="text-sm sm:text-lg font-semibold text-white mb-4">Top Repeat Offenders</h3>
          {offenderData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={offenderData.slice(0, 10)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2a4a" />
                <XAxis type="number" stroke="#8892b0" tick={{ fill: '#8892b0' }} />
                <YAxis type="category" dataKey="vehicle" stroke="#8892b0" tick={{ fill: '#8892b0', fontSize: 10 }} width={120} />
                <Tooltip {...DARK_TOOLTIP} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} fill="#ef4444" />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-trinetra-muted text-center py-12">No data available</p>}
        </div>

        {/* Monthly Trend */}
        <div className="glass rounded-xl p-4 sm:p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold text-white mb-4">Monthly Trend (Last 6 Months)</h3>
          {monthData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={monthData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2a4a" />
                <XAxis dataKey="month" stroke="#8892b0" tick={{ fill: '#8892b0' }} />
                <YAxis stroke="#8892b0" tick={{ fill: '#8892b0' }} />
                <Tooltip {...DARK_TOOLTIP} />
                <Line type="monotone" dataKey="count" stroke="#ef4444" strokeWidth={3} dot={{ fill: '#ef4444', r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : <p className="text-trinetra-muted text-center py-12">No data available</p>}
        </div>
      </div>
    </div>
  )
}
