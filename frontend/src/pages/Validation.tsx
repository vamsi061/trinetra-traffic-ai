import { useEffect, useState } from 'react'
import { Shield, CheckCircle, AlertTriangle, Eye, ThumbsUp, X, Check, Ban } from 'lucide-react'
import { getViolations, getStats, getEvidenceUrl, getUploadUrl, updateReviewStatus, type ViolationRecord, type ViolationStats } from '../api/client'

export default function Validation() {
  const [records, setRecords] = useState<ViolationRecord[]>([])
  const [stats, setStats] = useState<ViolationStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<ViolationRecord | null>(null)
  const [updating, setUpdating] = useState<number | null>(null)

  const load = () => {
    setLoading(true)
    Promise.all([
      getViolations({ limit: 50 }),
      getStats(),
    ]).then(([v, s]) => {
      setRecords(v.violations)
      setStats(s)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const totalImages = records.length
  const detectionRate = totalImages > 0 ? (records.filter(r => r.confidence > 0).length / totalImages * 100).toFixed(0) : '0'
  const needReviewCount = records.filter(r => r.confidence < 0.8).length
  const reviewRate = totalImages > 0 ? (needReviewCount / totalImages * 100).toFixed(0) : '0'

  const handleReview = async (id: number, status: 'approved' | 'rejected') => {
    setUpdating(id)
    try {
      await updateReviewStatus(id, status)
      setRecords(prev => prev.map(r => r.id === id ? { ...r, review_status: status } : r))
      if (selected?.id === id) setSelected(prev => prev ? { ...prev, review_status: status } : null)
    } finally {
      setUpdating(null)
    }
  }

  const uploadFilename = (path: string) => {
    return path?.split('/').pop() || ''
  }

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
                <tr
                  key={r.id || i}
                  className="border-b border-trinetra-border/50 hover:bg-[#1a2040]/50 cursor-pointer"
                  onClick={() => setSelected(r)}
                >
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
                    {r.review_status === 'approved' ? (
                      <span className="flex items-center justify-center gap-1 text-xs text-green-400">
                        <CheckCircle className="w-3 h-3" /> Approved
                      </span>
                    ) : r.review_status === 'rejected' ? (
                      <span className="flex items-center justify-center gap-1 text-xs text-red-400">
                        <Ban className="w-3 h-3" /> Rejected
                      </span>
                    ) : r.confidence >= 0.8 ? (
                      <span className="flex items-center justify-center gap-1 text-xs text-green-400">
                        <ThumbsUp className="w-3 h-3" /> Auto
                      </span>
                    ) : (
                      <span className="flex items-center justify-center gap-1 text-xs text-yellow-400">
                        <Eye className="w-3 h-3" /> Pending
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

      {/* Detail Modal */}
      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setSelected(null)}>
          <div className="bg-[#0d1225] border border-trinetra-border rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto mx-4" onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-trinetra-border">
              <div>
                <h2 className="text-lg font-bold text-white capitalize">{selected.violation_type.replace(/_/g, ' ').toLowerCase()}</h2>
                {selected.vehicle_number && (
                  <p className="text-trinetra-muted text-sm">{selected.vehicle_number}</p>
                )}
              </div>
              <button onClick={() => setSelected(null)} className="p-2 hover:bg-white/5 rounded-lg text-trinetra-muted">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Images */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-5">
              <div>
                <p className="text-xs text-trinetra-muted mb-2 font-medium">Original Upload</p>
                {selected.image_path ? (
                  <img
                    src={getUploadUrl(uploadFilename(selected.image_path))}
                    alt="original"
                    className="w-full rounded-lg border border-trinetra-border object-cover max-h-72"
                  />
                ) : (
                  <div className="w-full h-48 rounded-lg border border-trinetra-border flex items-center justify-center text-trinetra-muted text-sm">
                    No original image
                  </div>
                )}
              </div>
              <div>
                <p className="text-xs text-trinetra-muted mb-2 font-medium">Annotated Evidence</p>
                {selected.evidence_path ? (
                  <img
                    src={getEvidenceUrl(selected.evidence_path)}
                    alt="evidence"
                    className="w-full rounded-lg border border-trinetra-border object-cover max-h-72"
                  />
                ) : (
                  <div className="w-full h-48 rounded-lg border border-trinetra-border flex items-center justify-center text-trinetra-muted text-sm">
                    No evidence image
                  </div>
                )}
              </div>
            </div>

            {/* Details */}
            <div className="px-5 pb-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="glass rounded-lg p-3">
                <p className="text-xs text-trinetra-muted">Confidence</p>
                <p className="text-white font-bold">{(selected.confidence * 100).toFixed(0)}%</p>
              </div>
              <div className="glass rounded-lg p-3">
                <p className="text-xs text-trinetra-muted">Vehicle Type</p>
                <p className="text-white font-bold capitalize">{selected.vehicle_type || 'N/A'}</p>
              </div>
              <div className="glass rounded-lg p-3">
                <p className="text-xs text-trinetra-muted">Location</p>
                <p className="text-white font-bold truncate">{selected.location || 'N/A'}</p>
              </div>
              <div className="glass rounded-lg p-3">
                <p className="text-xs text-trinetra-muted">Timestamp</p>
                <p className="text-white font-bold text-sm">{selected.timestamp?.slice(0, 10)}</p>
              </div>
            </div>

            {/* Approve / Reject */}
            {!selected.review_status && selected.confidence < 0.8 && (
              <div className="px-5 pb-5">
                <p className="text-sm text-yellow-400 mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Manual verification required for this violation
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleReview(selected.id, 'approved')}
                    disabled={updating === selected.id}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-green-500/20 text-green-300 hover:bg-green-500/30 border border-green-500/30 font-medium disabled:opacity-50"
                  >
                    {updating === selected.id ? '...' : <><Check className="w-4 h-4" /> Approve</>}
                  </button>
                  <button
                    onClick={() => handleReview(selected.id, 'rejected')}
                    disabled={updating === selected.id}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-red-500/20 text-red-300 hover:bg-red-500/30 border border-red-500/30 font-medium disabled:opacity-50"
                  >
                    {updating === selected.id ? '...' : <><Ban className="w-4 h-4" /> Reject</>}
                  </button>
                </div>
              </div>
            )}

            {/* Already reviewed */}
            {selected.review_status === 'approved' && (
              <div className="px-5 pb-5">
                <p className="text-sm text-green-400 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  This violation has been approved
                </p>
              </div>
            )}
            {selected.review_status === 'rejected' && (
              <div className="px-5 pb-5">
                <p className="text-sm text-red-400 flex items-center gap-2">
                  <Ban className="w-4 h-4" />
                  This violation has been rejected
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}