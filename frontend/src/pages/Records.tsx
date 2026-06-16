import { useEffect, useState } from 'react'
import { Search, Download, AlertTriangle } from 'lucide-react'
import { getViolations, getStats, ViolationRecord, ViolationStats } from '../api/client'

export default function Records() {
  const [records, setRecords] = useState<ViolationRecord[]>([])
  const [stats, setStats] = useState<ViolationStats | null>(null)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getStats().then(setStats)
    loadRecords()
  }, [])

  async function loadRecords(s?: string, t?: string) {
    setLoading(true)
    try {
      const res = await getViolations({
        vehicle_number: s || undefined,
        violation_type: t || undefined,
        limit: 200,
      })
      setRecords(res.violations)
    } finally {
      setLoading(false)
    }
  }

  function handleSearch() {
    loadRecords(search, typeFilter)
  }

  function downloadCSV() {
    const headers = ['ID,Vehicle Number,Vehicle Type,Violation Type,Confidence,Timestamp']
    const rows = records.map(r =>
      `${r.id},"${r.vehicle_number}","${r.vehicle_type}","${r.violation_type}",${r.confidence},"${r.timestamp}"`
    )
    const csv = [...headers, ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'violations.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-2">Violation Records</h1>
      <p className="text-trinetra-muted mb-8">Search and review all detected traffic violations</p>

      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Total', value: stats.total, color: 'border-l-red-500' },
            { label: 'No Helmet', value: stats.no_helmet, color: 'border-l-red-500' },
            { label: 'Triple Riding', value: stats.triple_riding, color: 'border-l-amber-500' },
            { label: 'Unique Vehicles', value: stats.unique_vehicles, color: 'border-l-blue-500' },
          ].map(s => (
            <div key={s.label} className={`glass rounded-xl p-4 border-l-4 ${s.color}`}>
              <div className="text-sm text-trinetra-muted">{s.label}</div>
              <div className="text-2xl font-bold text-white mt-1">{s.value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="glass rounded-xl p-6 mb-8">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="text-sm text-trinetra-muted mb-1 block">Search Vehicle Number</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-trinetra-muted" />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="e.g. KA-01-AB-1234"
                className="w-full bg-[#1a2040] border border-trinetra-border rounded-lg py-2.5 pl-10 pr-4 text-white text-sm focus:outline-none focus:border-red-500/50"
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
              />
            </div>
          </div>
          <div className="w-48">
            <label className="text-sm text-trinetra-muted mb-1 block">Violation Type</label>
            <select
              value={typeFilter}
              onChange={e => { setTypeFilter(e.target.value); loadRecords(search, e.target.value) }}
              className="w-full bg-[#1a2040] border border-trinetra-border rounded-lg py-2.5 px-4 text-white text-sm focus:outline-none focus:border-red-500/50"
            >
              <option value="">All Types</option>
              <option value="NO_HELMET">No Helmet</option>
              <option value="TRIPLE_RIDING">Triple Riding</option>
            </select>
          </div>
          <button onClick={handleSearch} className="px-6 py-2.5 bg-red-500 hover:bg-red-600 rounded-lg text-white text-sm font-medium transition-colors">
            Search
          </button>
          <button onClick={downloadCSV} className="px-4 py-2.5 bg-[#1a2040] hover:bg-[#243050] rounded-lg text-trinetra-text text-sm transition-colors flex items-center gap-2">
            <Download className="w-4 h-4" /> CSV
          </button>
        </div>
      </div>

      <div className="glass rounded-xl overflow-hidden">
        <div className="p-4 border-b border-trinetra-border flex items-center justify-between">
          <span className="text-sm text-trinetra-muted">Found {records.length} record(s)</span>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <div className="w-8 h-8 border-2 border-red-500 border-t-transparent rounded-full animate-spin mx-auto" />
          </div>
        ) : records.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-trinetra-muted uppercase border-b border-trinetra-border">
                  <th className="text-left p-4">ID</th>
                  <th className="text-left p-4">Vehicle</th>
                  <th className="text-left p-4">Type</th>
                  <th className="text-left p-4">Violation</th>
                  <th className="text-left p-4">Confidence</th>
                  <th className="text-left p-4">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {records.map(r => (
                  <tr key={r.id} className="border-b border-trinetra-border/50 hover:bg-[#1a2040] transition-colors">
                    <td className="p-4 text-white text-sm">{r.id}</td>
                    <td className="p-4 text-white text-sm font-mono">{r.vehicle_number || '—'}</td>
                    <td className="p-4 text-trinetra-text text-sm capitalize">{r.vehicle_type || '—'}</td>
                    <td className="p-4">
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                        r.violation_type === 'NO_HELMET'
                          ? 'bg-red-500/10 text-red-400'
                          : 'bg-amber-500/10 text-amber-400'
                      }`}>
                        {r.violation_type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-4 text-trinetra-text text-sm">{(r.confidence * 100).toFixed(1)}%</td>
                    <td className="p-4 text-trinetra-text text-sm">{r.timestamp.slice(0, 19)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center text-trinetra-muted">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No violations found matching your criteria.</p>
          </div>
        )}
      </div>
    </div>
  )
}
