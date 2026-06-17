import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload as UploadIcon, AlertTriangle, CheckCircle, Search, Users, Shield, FileText, Eye, ThumbsUp, Bug, ChevronDown, ChevronUp, BarChart3, Activity } from 'lucide-react'
import { uploadImage, getEvidenceUrl } from '../api/client'
import type { DetectResponse, ReliabilityBadge } from '../api/client'

function ConfidenceBadge({ band, label }: { band: string; label: string }) {
  const colors: Record<string, string> = {
    high: 'bg-green-500/20 text-green-300 border-green-500/30',
    medium: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    low: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  }
  return (
    <span className={`text-xs font-bold px-3 py-1 rounded-full border ${colors[band] || colors.low}`}>
      {label}
    </span>
  )
}

function ReliabilityBadge({ badge }: { badge: ReliabilityBadge }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${badge.color}`}>
      Reliability: {badge.label}
    </span>
  )
}

function ReviewBadge({ status }: { status: string }) {
  const config: Record<string, { icon: React.ReactNode; label: string; className: string }> = {
    auto_confirmed: { icon: <ThumbsUp className="w-3 h-3" />, label: 'Auto Confirmed', className: 'bg-green-500/20 text-green-300' },
    human_review_recommended: { icon: <Eye className="w-3 h-3" />, label: 'Human Review Recommended', className: 'bg-yellow-500/20 text-yellow-300' },
    manual_verification_required: { icon: <AlertTriangle className="w-3 h-3" />, label: 'Manual Verification Required', className: 'bg-red-500/20 text-red-300' },
  }
  const c = config[status] || config.manual_verification_required
  return <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${c.className}`}>{c.icon} {c.label}</span>
}

function ExecutiveSummaryCard({ result }: { result: DetectResponse }) {
  const vehiclesDetected = result.detections.filter(d =>
    ['motorcycle', 'car', 'bus', 'truck'].includes(d.label)
  ).length
  const totalOccupants = result.motorcycle_riders?.reduce((s, mr) => s + mr.rider_count, 0) || 0
  const violations = result.violations.length
  const needsReview = result.violations.some(v => v.human_review_status !== 'auto_confirmed')
  const topRec = result.violations[0]?.enforcement_recommendation?.split('.')[0] || 'No action required'

  return (
    <div className="glass rounded-xl p-5 border-l-4 border-l-blue-500">
      <h3 className="text-sm font-semibold text-blue-400 mb-4 flex items-center gap-2">
        <BarChart3 className="w-4 h-4" /> Executive Summary
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Vehicles Detected</div>
          <div className="text-xl font-bold text-white">{vehiclesDetected}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Estimated Occupants</div>
          <div className="text-xl font-bold text-white">{totalOccupants}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Potential Violations</div>
          <div className={`text-xl font-bold ${violations > 0 ? 'text-red-400' : 'text-green-400'}`}>{violations}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Risk Level</div>
          <div className={`text-xl font-bold ${
            result.risk_status === 'CRITICAL' ? 'text-red-300' :
            result.risk_status === 'HIGH' ? 'text-orange-300' : 'text-yellow-300'
          }`}>{result.risk_status || 'NONE'}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Review Status</div>
          <div className={`text-sm font-bold ${needsReview ? 'text-yellow-400' : 'text-green-400'}`}>
            {needsReview ? 'Needs Review' : 'Auto-Confirmed'}
          </div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Recommended Action</div>
          <div className="text-xs font-medium text-blue-300 leading-tight">{topRec}</div>
        </div>
      </div>
    </div>
  )
}

export default function Upload() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DetectResponse | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showDebug, setShowDebug] = useState(false)

  const onDrop = useCallback(async (accepted: File[]) => {
    const file = accepted[0]
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setResult(null)
    setError(null)
    setLoading(true)
    try {
      const res = await uploadImage(file)
      // Debug logging for dashboard data flow
      const motorcycles = res.detections.filter(d => d.label === 'motorcycle')
      const persons = res.detections.filter(d => d.label === 'person')
      const totalOccupants = res.motorcycle_riders?.reduce((s, mr) => s + mr.rider_count, 0) || 0
      console.log('=== TRINETRA DASHBOARD DEBUG ===')
      console.log('detected_motorcycles:', motorcycles.length)
      console.log('detected_persons:', persons.length)
      console.log('estimated_occupants:', totalOccupants)
      console.log('detected_violations:', res.violations.length)
      console.log('risk_score:', res.risk_score)
      console.log('risk_status:', res.risk_status)
      console.log('crowded_scene:', res.crowded_scene)
      console.log('ai_review_recommended:', res.ai_review_recommended)
      if (res.violations.length > 0) {
        console.log('violation_details:', res.violations.map(v => ({
          type: v.type,
          confidence: v.confidence,
          band: v.confidence_band,
          label: v.confidence_label,
          review: v.human_review_status,
          reliability: v.reliability_badge?.label,
        })))
      }
      if (res.motorcycle_riders && res.motorcycle_riders.length > 0) {
        console.log('rider_details:', res.motorcycle_riders.map(mr => ({
          count: mr.rider_count,
          estimate: mr.occupancy_estimate,
        })))
      }
      console.log('================================')
      setResult(res)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Analysis failed. Check backend connection.')
    } finally {
      setLoading(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.bmp', '.webp'] },
    maxFiles: 1,
  })

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-2">Traffic Image Analysis</h1>
      <p className="text-trinetra-muted mb-8">Upload a traffic image for AI-powered enforcement intelligence</p>

      <div
        {...getRootProps()}
        className={`glass rounded-2xl p-6 sm:p-12 text-center cursor-pointer transition-all border-2 border-dashed ${
          isDragActive ? 'border-red-500 bg-red-500/5' : 'border-trinetra-border hover:border-red-500/50'
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-3 sm:gap-4">
          <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-2xl bg-red-500/10 flex items-center justify-center">
            <UploadIcon className="w-6 h-6 sm:w-8 sm:h-8 text-red-400" />
          </div>
          {isDragActive ? (
            <p className="text-base sm:text-lg text-red-400">Drop image here ...</p>
          ) : (
            <>
              <p className="text-sm sm:text-lg text-trinetra-text text-center px-4">
                Drag & drop a traffic image, or <span className="text-red-400 underline cursor-pointer">browse</span>
              </p>
              <p className="text-xs sm:text-sm text-trinetra-muted">Supports JPG, PNG, BMP, WebP</p>
            </>
          )}
        </div>
      </div>

      {preview && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
          <div className="glass rounded-xl p-4">
            <h3 className="text-sm font-medium text-trinetra-muted mb-3">Source Image</h3>
            <img src={preview} alt="Uploaded" className="w-full rounded-lg object-cover max-h-96" />
          </div>
          {result?.evidence_path && (
            <div className="glass rounded-xl p-4">
              <h3 className="text-sm font-medium text-trinetra-muted mb-3">Analysis Result</h3>
              <img
                src={getEvidenceUrl(result.evidence_path)}
                alt="Analysis"
                className="w-full rounded-lg object-cover max-h-96"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
              />
            </div>
          )}
        </div>
      )}

      {loading && (
        <div className="glass rounded-xl p-8 mt-8 text-center">
          <div className="w-10 h-10 border-2 border-red-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-trinetra-muted">Analyzing image with AI engine...</p>
        </div>
      )}

      {error && (
        <div className="mt-8 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          {error}
        </div>
      )}

      {result && !loading && (
        <div className="space-y-6 mt-8">
          {/* Executive Summary */}
          <ExecutiveSummaryCard result={result} />

          {/* Debug Toggle */}
          <button
            onClick={() => setShowDebug(!showDebug)}
            className="flex items-center gap-2 text-xs text-trinetra-muted hover:text-trinetra-text transition-colors"
          >
            <Bug className="w-3 h-3" />
            {showDebug ? 'Hide' : 'Show'} Developer Diagnostics
            {showDebug ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          {/* Developer Diagnostics Panel */}
          {showDebug && (
            <div className="glass rounded-xl p-6 border border-yellow-500/20">
              <h3 className="text-sm font-semibold text-yellow-400 mb-3 flex items-center gap-2">
                <Bug className="w-4 h-4" /> Developer Diagnostics Mode
              </h3>
              {result.detections.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-xs text-trinetra-muted mb-2">All Detected Objects</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {result.detections.map((d, i) => (
                      <div key={i} className="bg-[#1a2040] rounded-lg p-2 flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="text-trinetra-muted font-mono">{d.instance_id}</span>
                          <span className="text-white capitalize">{d.label}</span>
                        </div>
                        <span className="text-trinetra-muted">{(d.confidence * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {result.motorcycle_riders?.length > 0 && (
                <div>
                  <h4 className="text-xs text-trinetra-muted mb-2">Association Details</h4>
                  {result.motorcycle_riders.map((mr, i) => (
                    <div key={i} className="bg-[#1a2040] rounded-lg p-3 mb-2 text-xs">
                      <div className="text-amber-400 font-mono mb-1">{mr.motorcycle_id}</div>
                      <div className="text-trinetra-text">Occupants: {mr.riders.join(', ') || 'None'} | Score: {mr.rider_count}</div>
                      {mr.assignment_scores && Object.keys(mr.assignment_scores).length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {Object.entries(mr.assignment_scores).map(([rid, sc]) => (
                            <span key={rid} className="bg-yellow-500/10 text-yellow-400 px-1.5 py-0.5 rounded font-mono">
                              {rid}: {(sc as number * 100).toFixed(0)}%
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {result.ai_review_recommended && (
                <div className="mt-3 p-2 rounded bg-amber-500/10 text-amber-300 text-xs">
                  AI Review Flagged: {result.crowded_scene ? 'Crowded scene' : 'Needs human verification'}
                </div>
              )}
            </div>
          )}

          {/* Violation Report */}
          <div className="glass rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Violation Report</h3>
              {result.risk_score !== undefined && result.risk_score > 0 && (
                <span className={`text-sm font-semibold px-3 py-1 rounded-full ${
                  result.risk_status === 'CRITICAL' ? 'bg-red-500/20 text-red-300' :
                  result.risk_status === 'HIGH' ? 'bg-orange-500/20 text-orange-300' :
                  'bg-yellow-500/20 text-yellow-300'
                }`}>
                  Risk Score: {result.risk_score}
                </span>
              )}
            </div>

            {result.ai_review_recommended && (
              <div className="mb-4 p-3 rounded-lg border bg-amber-500/10 border-amber-500/30 text-amber-300 text-sm flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{result.crowded_scene ? 'Crowded scene detected — Manual verification required before enforcement action.' : 'Some violations require human review.'}</span>
              </div>
            )}

            {result.violations.length > 0 ? (
              <div className="space-y-4">
                {result.violations.map((v, i) => (
                  <div key={i} className={`rounded-lg border ${
                    v.type === 'NO_HELMET' ? 'border-red-500/30 bg-red-500/5' :
                    v.type === 'TRIPLE_RIDING' ? 'border-amber-500/30 bg-amber-500/5' :
                    v.type === 'MOTORCYCLE_OVERLOADING' ? 'border-rose-500/30 bg-rose-500/5' :
                    v.type === 'MOTORCYCLE_EXTREME_OVERLOADING' ? 'border-pink-500/30 bg-pink-500/5' :
                    v.type === 'WRONG_SIDE_DRIVING' ? 'border-purple-500/30 bg-purple-500/5' :
                    'border-trinetra-border'
                  }`}>
                    <div className="p-4">
                      {/* Header row */}
                      <div className="flex items-start justify-between flex-wrap gap-2 mb-3">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-white text-sm">
                            {v.type === 'NO_HELMET' ? 'No Helmet' :
                             v.type === 'TRIPLE_RIDING' ? 'Triple Riding' :
                             v.type === 'MOTORCYCLE_OVERLOADING' ? 'Overloading' :
                             v.type === 'MOTORCYCLE_EXTREME_OVERLOADING' ? 'Extreme Overloading' :
                             v.type === 'WRONG_SIDE_DRIVING' ? 'Wrong-Side Driving' :
                             v.type.replace(/_/g, ' ')}
                          </span>
                          <ConfidenceBadge band={v.confidence_band} label={v.confidence_label} />
                          {v.severity_score && v.severity_score > 0 && (
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                              v.severity_score >= 95 ? 'bg-red-500/20 text-red-300' :
                              v.severity_score >= 75 ? 'bg-orange-500/20 text-orange-300' :
                              'bg-yellow-500/20 text-yellow-300'
                            }`}>Risk: {v.severity_score}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <ReviewBadge status={v.human_review_status} />
                          {v.reliability_badge && <ReliabilityBadge badge={v.reliability_badge} />}
                        </div>
                      </div>

                      {/* Occupancy estimate */}
                      {v.occupancy_estimate && (
                        <div className="mb-3 text-sm">
                          <span className="bg-[#0d1225] text-trinetra-text px-3 py-1 rounded">
                            <Users className="w-3.5 h-3.5 inline mr-1.5" />
                            {v.occupancy_estimate}
                          </span>
                        </div>
                      )}

                      {/* Explanation */}
                      {v.explainable_reason && (
                        <div className="mb-3 p-3 rounded-lg bg-[#0d1225] border border-trinetra-border">
                          <div className="flex items-center gap-1.5 text-xs text-trinetra-muted mb-1">
                            <FileText className="w-3 h-3" /> Analysis
                          </div>
                          <p className="text-sm text-trinetra-text">{v.explainable_reason}</p>
                        </div>
                      )}

                      {/* Recommendation */}
                      {v.enforcement_recommendation && (
                        <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                          <div className="flex items-center gap-1.5 text-xs text-blue-400 mb-1">
                            <Shield className="w-3 h-3" /> Recommended Action
                          </div>
                          <p className="text-sm text-trinetra-text">{v.enforcement_recommendation}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-3 text-green-400">
                <CheckCircle className="w-5 h-5" />
                <span>No violations detected</span>
              </div>
            )}
          </div>

          {/* License Plate */}
          {result.license_plate && (
            <div className="glass rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">License Plate</h3>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                  <Search className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-white tracking-wider">{result.license_plate.number}</div>
                  <div className="text-sm text-trinetra-muted">OCR Confidence: {(result.license_plate.confidence * 100).toFixed(0)}%</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
