import { useEffect, useState } from 'react'
import { Shield, CheckCircle, AlertTriangle, Eye, ThumbsUp } from 'lucide-react'
import { getViolations, getStats, getEvidenceUrl, type ViolationRecord, type ViolationStats } from '../api/client'

export default function Validation() {
  const [records, setRecords] = useState<ViolationRecord[]>([])
  const [stats, setStats] = useState<ViolationStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getViolations({ limit: 50 }),
      getStats(),
    ]).then(([v, s]) => {
      setRecords(v.violations)
      setStats(s)
    }).finally(() => setLoading(false))
  }, [])

  const totalImages = records.length
  const detectionRate = totalImages > 0 ? (records.filter(r => r.confidence > 0).length / totalImages * 100).toFixed(0) : '0'
  const needReviewCount = records.filter(r => r.confidence < 0.8).length
  const reviewRate = totalImages > 0 ? (needReviewCount / totalImages * 100).toFixed(0) : '0'

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
          <Shield className="w-5 h-5 text-emerald-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Validation Results</h1>
          <p className="text-trinetra-muted text-sm">Analysis history and detection performance</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="glass rounded-xl p-4 border-l-4 border-l-blue-500">
          <div className="text-xs text-trinetra-muted mb-1">Images Tested</div>
          <div className="text-2xl font-bold text-white">{totalImages}</div>
        </div>
        <div className="glass rounded-xl p-4 border-l-4 border-l-green-500">
          <div className="text-xs text-trinetra-muted mb-1">Violation Detection Rate</div>
          <div className="text-2xl font-bold text-white">{detectionRate}%</div>
        </div>
        <div className="glass rounded-xl p-4 border-l-4 border-l-yellow-500">
          <div className="text-xs text-trinetra-muted mb-1">Review Recommendation Rate</div>
          <div className="text-2xl font-bold text-white">{reviewRate}%</div>
        </div>
        <div className="glass rounded-xl p-4 border-l-4 border-l-red-500">
          <div className="text-xs text-trinetra-muted mb-1">Total Violations</div>
          <div className="text-2xl font-bold text-white">{stats?.total || 0}</div>
        </div>
      </div>

      {/* Results Table */}
      <div className="glass rounded-xl overflow-hidden">
        <div className="p-4 border-b border-trinetra-border">
          <h3 className="font-semibold text-white">Recent Analysis Results</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-trinetra-border text-trinetra-muted">
                <th className="text-left py-3 px-4">Image</th>
                <th className="text-left py-3 px-4">Violation</th>
                <th className="text-center py-3 px-4">Confidence</th>
                <th className="text-center py-3 px-4">Review Status</th>
                <th className="text-right py-3 px-4">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="text-center py-8 text-trinetra-muted">Loading...</td></tr>
              ) : records.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-8 text-trinetra-muted">No analysis results yet.</td></tr>
              ) : records.map((r, i) => (
                <tr key={i} className="border-b border-trinetra-border/50 hover:bg-[#1a2040]/50">
                  <td className="py-3 px-4">
                    {r.evidence_path ? (
                      <img src={getEvidenceUrl(r.evidence_path)} alt="evidence" className="w-16 h-12 rounded object-cover" />
                    ) : (
                      <span className="text-trinetra-muted text-xs">No image</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-white capitalize">{r.violation_type.replace(/_/g, ' ').toLowerCase()}</span>
                    {r.vehicle_number && <span className="text-trinetra-muted text-xs block">{r.vehicle_number}</span>}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                      r.confidence >= 0.8 ? 'bg-green-500/20 text-green-300' :
                      r.confidence >= 0.6 ? 'bg-yellow-500/20 text-yellow-300' :
                      'bg-orange-500/20 text-orange-300'
                    }`}>
                      {(r.confidence * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    {r.confidence >= 0.8 ? (
                      <span className="flex items-center justify-center gap-1 text-xs text-green-400">
                        <ThumbsUp className="w-3 h-3" /> Auto
                      </span>
                    ) : (
                      <span className="flex items-center justify-center gap-1 text-xs text-yellow-400">
                        <Eye className="w-3 h-3" /> Review
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right text-trinetra-muted text-xs">
                    {r.timestamp?.slice(0, 10)} {r.timestamp?.slice(11, 16)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
