import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload as UploadIcon, AlertTriangle, CheckCircle, Search, Users, Shield, FileText, Eye, ThumbsUp, Bug, ChevronDown, ChevronUp, BarChart3, Activity, Presentation, Download } from 'lucide-react'
import { uploadImage, getEvidenceUrl, getEvidenceReportUrl } from '../api/client'
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

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    'URGENT REVIEW': 'bg-red-500/20 text-red-300 border-red-500/30',
    'HIGH PRIORITY': 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    'MEDIUM PRIORITY': 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    'LOW PRIORITY': 'bg-green-500/20 text-green-300 border-green-500/30',
  }
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${colors[priority] || colors['MEDIUM PRIORITY']}`}>
      {priority}
    </span>
  )
}

function occupantRange(riders: { rider_count: number }[]): string {
  const total = riders?.reduce((s, mr) => s + mr.rider_count, 0) || 0
  if (total <= 0) return '0'
  if (total <= 2) return `${total}`
  if (total <= 3) return '3'
  if (total <= 5) return '4-5'
  if (total <= 8) return '6-8'
  return '10-12'
}

function ExecutiveSummaryCard({ result }: { result: DetectResponse }) {
  const vehiclesDetected = result.detections.filter(d =>
    ['motorcycle', 'car', 'bus', 'truck'].includes(d.label)
  ).length
  const occRange = occupantRange(result.motorcycle_riders || [])
  const violations = result.violations.length
  const needsReview = result.violations.some(v => v.human_review_status !== 'auto_confirmed')
  const helmetCount = result.violations.filter(v => v.type === 'NO_HELMET').length

  // Compute reliability from results
  const avgConf = result.violations.length > 0
    ? result.violations.reduce((s, v) => s + v.confidence, 0) / result.violations.length
    : (result.detections.length > 0 ? result.detections.reduce((s, d) => s + d.confidence, 0) / result.detections.length : 0)
  const crowded = result.crowded_scene
  let reliability = 'High', reliabilityReason = 'Clear detection with strong confidence.'
  if (crowded) { reliability = 'Limited'; reliabilityReason = 'Crowded scene with overlapping occupants.' }
  else if (avgConf < 0.6) { reliability = 'Low'; reliabilityReason = 'Low detection confidence. Verification recommended.' }
  else if (avgConf < 0.8) { reliability = 'Medium'; reliabilityReason = 'Moderate detection confidence.' }

  const topRec = result.violations[0]?.enforcement_recommendation?.split('.')[0] || 'No action required'
  const qualityScore = result.image_quality?.score || 'N/A'
  const pedestrianCount = result.pedestrians?.count || 0
  const qualityColor = qualityScore === 'Excellent' ? 'text-green-400' : qualityScore === 'Good' ? 'text-blue-400' : qualityScore === 'Fair' ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="glass rounded-xl p-5 border-l-4 border-l-blue-500">
      <h3 className="text-sm font-semibold text-blue-400 mb-4 flex items-center gap-2">
        <BarChart3 className="w-4 h-4" /> Traffic Intelligence Summary
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-10 gap-3">
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Motorcycles</div>
          <div className="text-xl font-bold text-white">{result.detections.filter(d => d.label === 'motorcycle').length}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Pedestrians</div>
          <div className="text-xl font-bold text-white">{pedestrianCount}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Est. Occupants</div>
          <div className="text-xl font-bold text-white">{occRange}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Image Quality</div>
          <div className={`text-sm font-bold ${qualityColor}`}>{qualityScore}</div>
          <div className="text-[10px] text-trinetra-muted mt-0.5 truncate max-w-[80px]">{result.image_quality?.issues?.join(', ') || 'Clear'}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Violations</div>
          <div className={`text-xl font-bold ${violations > 0 ? 'text-red-400' : 'text-green-400'}`}>{violations}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Helmet</div>
          <div className={`text-xl font-bold ${helmetCount > 0 ? 'text-orange-400' : 'text-green-400'}`}>{helmetCount}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Risk</div>
          <div className={`text-sm font-bold ${
            result.risk_status === 'CRITICAL' ? 'text-red-300' :
            result.risk_status === 'HIGH' ? 'text-orange-300' :
            result.risk_status === 'MODERATE' ? 'text-yellow-300' :
            'text-green-300'
          }`}>{result.risk_status || 'NONE'}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Review</div>
          <div className={`text-sm font-bold ${needsReview ? 'text-yellow-400' : 'text-green-400'}`}>
            {needsReview ? 'Needs Review' : 'Auto-Confirmed'}
          </div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Reliability</div>
          <div className={`text-sm font-bold ${
            reliability === 'High' ? 'text-green-400' :
            reliability === 'Medium' ? 'text-yellow-400' :
            reliability === 'Limited' ? 'text-orange-400' : 'text-red-400'
          }`}>{reliability}</div>
          <div className="text-[10px] text-trinetra-muted mt-0.5 truncate max-w-[80px]">{reliabilityReason}</div>
        </div>
        <div className="bg-[#1a2040] rounded-lg p-3 text-center">
          <div className="text-xs text-trinetra-muted mb-1">Recommended</div>
          <div className="text-[10px] font-medium text-blue-300 leading-tight">{topRec}</div>
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
  const [judgeMode, setJudgeMode] = useState(false)

  const onDrop = useCallback(async (accepted: File[]) => {
    const file = accepted[0]
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setResult(null)
    setError(null)
    setLoading(true)
    try {
      const res = await uploadImage(file)
      const motorcycles = res.detections.filter(d => d.label === 'motorcycle')
      const persons = res.detections.filter(d => d.label === 'person')
      const totalOccupants = res.motorcycle_riders?.reduce((s, mr) => s + mr.rider_count, 0) || 0
      console.log('=== TRINETRA DASHBOARD DEBUG ===')
      console.log('detected_motorcycles:', motorcycles.length)
      console.log('detected_persons:', persons.length)
      console.log('estimated_occupants:', totalOccupants)
      console.log('detected_violations:', res.violations.length)
      console.log('risk_score:', res.risk_score)
      console.log('crowded_scene:', res.crowded_scene)
      console.log('ai_review_recommended:', res.ai_review_recommended)
      console.log('================================')
      setResult(res)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Analysis failed.')
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
      <div className="flex items-center justify-between mb-6">
        <div>
          <div>
            <h1 className="text-2xl font-bold text-white">TRINETRA AI</h1>
            <p className="text-trinetra-muted text-sm">AI-Powered Traffic Enforcement Intelligence Platform</p>
          </div>
        </div>
        {result && !loading && (
          <button
            onClick={() => setJudgeMode(!judgeMode)}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-all ${
              judgeMode ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-[#1a2040] text-trinetra-muted hover:text-white'
            }`}
          >
            <Presentation className="w-3.5 h-3.5" />
            {judgeMode ? 'Judge Mode ON' : 'Judge Mode'}
          </button>
        )}
      </div>

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
              <p className="text-xs sm:text-sm text-trinetra-muted">JPG, PNG, BMP, WebP supported</p>
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
        <div className={`space-y-6 mt-8 ${judgeMode ? 'p-4 rounded-2xl border-2 border-purple-500/30 bg-purple-500/[0.02]' : ''}`}>
          {/* Judge Mode banner */}
          {judgeMode && (
            <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30 text-center">
              <Presentation className="w-6 h-6 text-purple-400 mx-auto mb-2" />
              <h2 className="text-lg font-bold text-white">TRINETRA AI</h2>
              <p className="text-sm text-purple-300 mt-1">AI-Powered Traffic Enforcement Intelligence Platform</p>
              <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mt-3 text-xs text-trinetra-muted">
                <span>✓ Violation Detection</span>
                <span>✓ Explainable AI</span>
                <span>✓ Confidence Scoring</span>
                <span>✓ Human Review</span>
                <span>✓ Evidence Generation</span>
                <span>✓ Repeat Offender Intelligence</span>
                <span>✓ Hotspot Analytics</span>
                <span>✓ Officer Prioritization</span>
                <span>✓ Smart City Readiness</span>
              </div>
            </div>
          )}

          {/* Executive Summary — always shown */}
          <ExecutiveSummaryCard result={result} />

          {/* Developer Diagnostics — hidden by default (Officer Mode) */}
          {!judgeMode && (
            <button
              onClick={() => setShowDebug(!showDebug)}
              className="flex items-center gap-2 text-xs text-trinetra-muted hover:text-trinetra-text transition-colors"
            >
              <Bug className="w-3 h-3" />
              {showDebug ? 'Hide' : 'Show'} Developer Diagnostics
              {showDebug ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}

          {showDebug && !judgeMode && (
            <div className="glass rounded-xl p-6 border border-yellow-500/20">
              <h3 className="text-sm font-semibold text-yellow-400 mb-3 flex items-center gap-2">
                <Bug className="w-4 h-4" /> Developer Diagnostics
              </h3>
              {result.detections.map((d, i) => (
                <div key={i} className="bg-[#1a2040] rounded-lg p-2 flex items-center justify-between text-xs mb-1">
                  <span className="text-trinetra-muted font-mono">{d.instance_id}</span>
                  <span className="text-white capitalize">{d.label} ({(d.confidence * 100).toFixed(0)}%)</span>
                </div>
              ))}
              {result.ai_review_recommended && (
                <div className="mt-2 p-2 rounded bg-amber-500/10 text-amber-300 text-xs">
                  Flagged: {result.crowded_scene ? 'Crowded scene' : 'Needs verification'}
                </div>
              )}
            </div>
          )}

          {/* Violation Report */}
          <div className="glass rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Violation Report</h3>
              {result.risk_score !== undefined && result.risk_score > 0 && !judgeMode && (
                <span className={`text-sm font-semibold px-3 py-1 rounded-full ${
                  result.risk_status === 'CRITICAL' ? 'bg-red-500/20 text-red-300' :
                  result.risk_status === 'HIGH' ? 'bg-orange-500/20 text-orange-300' :
                  'bg-yellow-500/20 text-yellow-300'
                }`}>
                  Risk Score: {result.risk_score}
                </span>
              )}
            </div>

            {result.ai_review_recommended && !judgeMode && (
              <div className="mb-4 p-3 rounded-lg border bg-amber-500/10 border-amber-500/30 text-amber-300 text-sm flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{result.crowded_scene ? 'Crowded scene — Manual verification required.' : 'Some violations require review.'}</span>
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
                    'border-trinetra-border'
                  }`}>
                    <div className="p-4">
                      {/* Simplified header: Type + Confidence + Risk */}
                      <div className="flex items-start justify-between flex-wrap gap-2 mb-3">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-white text-sm">
                            {v.type === 'NO_HELMET' ? 'No Helmet' :
                             v.type === 'TRIPLE_RIDING' ? 'Triple Riding' :
                             v.type === 'MOTORCYCLE_OVERLOADING' ? 'Overloading' :
                             v.type === 'MOTORCYCLE_EXTREME_OVERLOADING' ? 'Extreme Overloading' :
                             v.type.replace(/_/g, ' ')}
                          </span>
                          <ConfidenceBadge band={v.confidence_band} label={v.confidence_label} />
                          <PriorityBadge priority={v.officer_priority || 'MEDIUM PRIORITY'} />
                          {v.severity_score && v.severity_score > 0 && !judgeMode && (
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                              v.severity_score >= 95 ? 'bg-red-500/20 text-red-300' :
                              v.severity_score >= 75 ? 'bg-orange-500/20 text-orange-300' :
                              'bg-yellow-500/20 text-yellow-300'
                            }`}>Risk: {v.severity_score}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 flex-wrap">
                          {!judgeMode && <ReviewBadge status={v.human_review_status} />}
                          {v.reliability_badge && <ReliabilityBadge badge={v.reliability_badge} />}
                        </div>
                      </div>

                      {/* Reason (Explainable) */}
                      {v.explainable_reason && (
                        <div className="mb-3 p-3 rounded-lg bg-[#0d1225] border border-trinetra-border">
                          <div className="flex items-center gap-1.5 text-xs text-trinetra-muted mb-1">
                            <FileText className="w-3 h-3" /> Reason
                          </div>
                          <p className="text-sm text-trinetra-text">{v.explainable_reason}</p>
                        </div>
                      )}

                      {/* Recommendation */}
                      {v.enforcement_recommendation && (
                        <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                          <div className="flex items-center gap-1.5 text-xs text-blue-400 mb-1">
                            <Shield className="w-3 h-3" /> Recommended Response
                          </div>
                          <p className="text-sm text-trinetra-text">{v.enforcement_recommendation}</p>
                        </div>
                      )}

                      {/* Judge Mode: show business value summary */}
                      {judgeMode && (
                        <div className="mt-3 p-3 rounded-lg bg-purple-500/5 border border-purple-500/20">
                          <div className="flex items-center gap-1.5 text-xs text-purple-400 mb-1">
                            <Presentation className="w-3 h-3" /> Business Value
                          </div>
                          <p className="text-sm text-trinetra-text">
                            AI-assisted detection enables <strong className="text-white">targeted enforcement</strong> with
                            {' '}{v.confidence_label} ({v.reliability_badge?.label || 'N/A'} reliability).
                            {' '}Estimated {v.occupancy_estimate || 'occupants unknown'}.
                            {' '}Risk level: <strong className="text-white">{v.severity_score || 'N/A'}</strong>.
                          </p>
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

          {result.license_plate && (
            <div className="glass rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">License Plate</h3>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                  <Search className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-white tracking-wider">{result.license_plate.number}</div>
                  <div className="text-sm text-trinetra-muted">Confidence: {(result.license_plate.confidence * 100).toFixed(0)}% | Visibility: {result.license_plate.visibility || 'N/A'}</div>
                </div>
              </div>
            </div>
          )}

          {result.evidence_report && (
            <div className="glass rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Download className="w-4 h-4" /> Evidence Report
              </h3>
              <p className="text-sm text-trinetra-muted mb-3">Download the full evidence package for officer review.</p>
              <a
                href={getEvidenceReportUrl(result.evidence_report)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/10 text-blue-300 border border-blue-500/30 rounded-lg hover:bg-blue-500/20 transition-colors text-sm"
              >
                <FileText className="w-4 h-4" />
                Download Evidence Report (PDF)
              </a>
            </div>
          )}

          {/* Image Quality Assessment */}
          {result.image_quality && (
            <div className="glass rounded-xl p-6">
              <h3 className="text-sm font-semibold text-trinetra-text mb-3 flex items-center gap-2">
                <Activity className="w-4 h-4" /> Image Quality Assessment
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-[#1a2040] rounded-lg p-3 text-center">
                  <div className="text-xs text-trinetra-muted mb-1">Quality</div>
                  <div className={`text-sm font-bold ${
                    result.image_quality.score === 'Excellent' ? 'text-green-400' :
                    result.image_quality.score === 'Good' ? 'text-blue-400' :
                    result.image_quality.score === 'Fair' ? 'text-yellow-400' : 'text-red-400'
                  }`}>{result.image_quality.score}</div>
                </div>
                <div className="bg-[#1a2040] rounded-lg p-3 text-center">
                  <div className="text-xs text-trinetra-muted mb-1">Issues</div>
                  <div className="text-sm text-white">{result.image_quality.issues?.join(', ') || 'None'}</div>
                </div>
                <div className="bg-[#1a2040] rounded-lg p-3 text-center">
                  <div className="text-xs text-trinetra-muted mb-1">Expected Impact</div>
                  <div className="text-sm text-white">{result.image_quality.expected_accuracy_impact}</div>
                </div>
                <div className="bg-[#1a2040] rounded-lg p-3 text-center">
                  <div className="text-xs text-trinetra-muted mb-1">Sharpness</div>
                  <div className="text-sm text-white">{result.image_quality.sharpness?.toFixed(0)}</div>
                </div>
              </div>
            </div>
          )}

          {/* AI Safety & Review — Human-in-the-Loop Panel */}
          <div className="glass rounded-xl p-6 border-l-4 border-l-emerald-500">
            <h3 className="text-sm font-semibold text-emerald-400 mb-3 flex items-center gap-2">
              <Shield className="w-4 h-4" /> AI Safety &amp; Review — Human-in-the-Loop
            </h3>
            <div className="space-y-2 text-sm text-trinetra-text">
              <p>TRINETRA AI prioritizes <strong className="text-white">explainability</strong> and <strong className="text-white">human oversight</strong> in all enforcement recommendations.</p>
              <ul className="list-disc list-inside space-y-1 text-trinetra-muted">
                <li>All detections include <strong className="text-white">confidence scoring</strong> — low-confidence results are flagged for review.</li>
                <li>Scenes flagged as <strong className="text-white">crowded</strong> or <strong className="text-white">ambiguous</strong> require manual verification.</li>
                <li>Enforcement decisions are <strong className="text-white">not automated</strong> — all recommendations require officer review.</li>
                <li>The system is designed as a <strong className="text-white">decision support tool</strong>, not an enforcement authority.</li>
              </ul>
              <p className="text-trinetra-muted text-xs mt-2">This demonstrates responsible AI usage in traffic enforcement intelligence.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
