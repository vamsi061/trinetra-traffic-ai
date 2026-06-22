import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload as UploadIcon, AlertTriangle, CheckCircle, Search, Shield, FileText, Eye, ThumbsUp, Bug, ChevronDown, ChevronUp, BarChart3, Activity, Presentation, Download, Loader2, Settings, ChevronRight, Gauge, Server, TrendingUp, MapPin, BarChart4, Zap, Cpu } from 'lucide-react'
import { uploadImage, getEvidenceUrl, getEvidenceReportUrl, getRuntimeMetrics, getFalsePositiveStats, getSystemHealth } from '../api/client'
import type { DetectResponse, ReliabilityBadge, RuntimeMetrics } from '../api/client'

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
  const compliant = result.compliance_status === 'COMPLIANT'

  const avgConf = result.violations.length > 0
    ? result.violations.reduce((s, v) => s + v.confidence, 0) / result.violations.length
    : (result.detections.length > 0 ? result.detections.reduce((s, d) => s + d.confidence, 0) / result.detections.length : 0)
  const crowded = result.crowded_scene
  const qualityGood = result.image_quality?.score === 'Excellent' || result.image_quality?.score === 'Good'
  let reliability = 'High', reliabilityReason = 'Clear detection with strong confidence.'
  if (crowded) { reliability = 'Limited'; reliabilityReason = 'Crowded scene with overlapping occupants.' }
  else if (avgConf < 0.6) { reliability = 'Low'; reliabilityReason = 'Low detection confidence. Verification recommended.' }
  else if (avgConf < 0.8 && !compliant && !qualityGood) { reliability = 'Medium'; reliabilityReason = 'Moderate detection confidence.' }
  else if (compliant && qualityGood) { reliability = 'High'; reliabilityReason = 'Compliant vehicle with clear image quality.' }

  const topRec = result.violations[0]?.enforcement_recommendation?.split('.')[0] || (compliant ? 'No action required' : 'No action required')
  const qualityScore = result.image_quality?.score || 'N/A'
  const pedestrianCount = result.pedestrians?.count || 0
  const qualityColor = qualityScore === 'Excellent' ? 'text-green-400' : qualityScore === 'Good' ? 'text-blue-400' : qualityScore === 'Fair' ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className={`glass rounded-xl p-5 border-l-4 ${compliant ? 'border-l-emerald-500' : 'border-l-blue-500'}`}>
      <h3 className={`text-sm font-semibold ${compliant ? 'text-emerald-400' : 'text-blue-400'} mb-4 flex items-center gap-2`}>
        <BarChart3 className="w-4 h-4" /> Traffic Intelligence Summary
        {compliant && (
          <span className="ml-2 text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full">COMPLIANT VEHICLE</span>
        )}
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
          <div className={`text-sm font-bold ${compliant ? 'text-emerald-400' : needsReview ? 'text-yellow-400' : 'text-green-400'}`}>
            {compliant ? 'Auto-Confirmed' : needsReview ? 'Needs Review' : 'Auto-Confirmed'}
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

function PipelineStatus() {
  const steps = [
    'Automatic Image Enhancement',
    'Object Detection',
    'Traffic Violation Analysis',
    'AI Scene Understanding',
    'Evidence Report Generation',
  ]
  return (
    <div className="glass rounded-xl p-6">
      <h3 className="text-sm font-semibold text-white mb-4">Analysis Pipeline</h3>
      <div className="space-y-2">
        {steps.map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <CheckCircle className="w-4 h-4 text-green-400 shrink-0" />
            <span className="text-trinetra-text">{s}</span>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 border-t border-trinetra-border flex items-center gap-2 text-sm">
        <span className="w-2 h-2 rounded-full bg-green-400" />
        <span className="text-green-400 font-medium">Status: Ready</span>
      </div>
    </div>
  )
}

function AdvancedSettingsPanel({
  engine,
  onEngineChange,
  showDiagnostics,
  onDiagnosticsChange,
  benchmarkMode,
  onBenchmarkChange,
  devLogs,
  onDevLogsChange,
}: {
  engine: string
  onEngineChange: (v: string) => void
  showDiagnostics: boolean
  onDiagnosticsChange: (v: boolean) => void
  benchmarkMode: boolean
  onBenchmarkChange: (v: boolean) => void
  devLogs: boolean
  onDevLogsChange: (v: boolean) => void
}) {
  const [open, setOpen] = useState(false)

  return (
    <div className="glass rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 text-sm text-trinetra-muted hover:text-white transition-colors"
      >
        <span className="flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Advanced Settings
        </span>
        <ChevronRight className={`w-4 h-4 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs text-trinetra-muted">Detection Engine</label>
            <select
              value={engine}
              onChange={e => onEngineChange(e.target.value)}
              className="text-xs bg-[#1a2040] border border-trinetra-border rounded-lg px-2 py-1 text-white focus:outline-none focus:border-red-500/50"
            >
              <option value="auto">Auto (recommended)</option>
              <option value="yolo">YOLOv8</option>
              <option value="locateanything">HF Inference</option>
              <option value="owlvit_local">OwlViT Local</option>
              <option value="locateanything_gradio">Gradio</option>
            </select>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-xs text-trinetra-muted">Show Diagnostics</label>
            <button
              onClick={() => onDiagnosticsChange(!showDiagnostics)}
              className={`w-9 h-5 rounded-full transition-colors ${
                showDiagnostics ? 'bg-red-500' : 'bg-[#1a2040] border border-trinetra-border'
              }`}
            >
              <div className={`w-3.5 h-3.5 rounded-full bg-white transition-transform ${
                showDiagnostics ? 'translate-x-[18px]' : 'translate-x-[2px]'
              }`} />
            </button>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-xs text-trinetra-muted">Benchmark Mode</label>
            <button
              onClick={() => onBenchmarkChange(!benchmarkMode)}
              className={`w-9 h-5 rounded-full transition-colors ${
                benchmarkMode ? 'bg-red-500' : 'bg-[#1a2040] border border-trinetra-border'
              }`}
            >
              <div className={`w-3.5 h-3.5 rounded-full bg-white transition-transform ${
                benchmarkMode ? 'translate-x-[18px]' : 'translate-x-[2px]'
              }`} />
            </button>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-xs text-trinetra-muted">Developer Logs</label>
            <button
              onClick={() => onDevLogsChange(!devLogs)}
              className={`w-9 h-5 rounded-full transition-colors ${
                devLogs ? 'bg-red-500' : 'bg-[#1a2040] border border-trinetra-border'
              }`}
            >
              <div className={`w-3.5 h-3.5 rounded-full bg-white transition-transform ${
                devLogs ? 'translate-x-[18px]' : 'translate-x-[2px]'
              }`} />
            </button>
          </div>
        </div>
      )}
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
  const [fileSelected, setFileSelected] = useState<File | null>(null)

  // Advanced settings defaults
  const [advEngine, setAdvEngine] = useState('auto')
  const [advDiagnostics, setAdvDiagnostics] = useState(false)
  const [advBenchmark, setAdvBenchmark] = useState(false)
  const [advDevLogs, setAdvDevLogs] = useState(false)
  const [runtimeMetrics, setRuntimeMetrics] = useState<RuntimeMetrics | null>(null)
  const [fpStats, setFpStats] = useState<any>(null)
  const [systemHealth, setSystemHealth] = useState<any>(null)

  const runAnalysis = useCallback(async () => {
    if (!fileSelected) return
    setResult(null)
    setError(null)
    setLoading(true)
    try {
      const res = await uploadImage(fileSelected)
      const motorcycles = res.detections.filter(d => d.label === 'motorcycle')
      const persons = res.detections.filter(d => d.label === 'person')
      const totalOccupants = res.motorcycle_riders?.reduce((s, mr) => s + mr.rider_count, 0) || 0
      console.log('=== TRINETRA ANALYSIS ===')
      console.log('detected_motorcycles:', motorcycles.length)
      console.log('detected_persons:', persons.length)
      console.log('estimated_occupants:', totalOccupants)
      console.log('detected_violations:', res.violations.length)
      console.log('risk_score:', res.risk_score)
      console.log('crowded_scene:', res.crowded_scene)
      console.log('================================')
      setResult(res)
      getRuntimeMetrics().then(setRuntimeMetrics).catch(() => {})
      getFalsePositiveStats().then(setFpStats).catch(() => {})
      getSystemHealth().then(setSystemHealth).catch(() => {})
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Analysis failed.')
    } finally {
      setLoading(false)
    }
  }, [fileSelected])

  const onDrop = useCallback(async (accepted: File[]) => {
    const file = accepted[0]
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setFileSelected(file)
    setResult(null)
    setError(null)
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
          {result?.detection_model && (
            <div className="mt-1 flex items-center gap-2">
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                result.detection_model.active_mode === 'yolo' ? 'bg-yellow-500/10 text-yellow-300 border-yellow-500/30' :
                result.detection_model.active_mode?.startsWith('hf_inference') ? 'bg-purple-500/10 text-purple-300 border-purple-500/30' :
                result.detection_model.active_mode === 'owlvit_local' ? 'bg-blue-500/10 text-blue-300 border-blue-500/30' :
                'bg-green-500/10 text-green-300 border-green-500/30'
              }`}>
                {result.detection_model.engine_label || result.detection_model.active_mode}
              </span>
              {result.helmet_model && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#1a2040] text-trinetra-muted border border-trinetra-border flex items-center gap-1">
                  Helmet: {result.helmet_model.loaded ? result.helmet_model.model_name : 'HSV fallback'}
                  {result.helmet_model.beta && (
                    <span className="text-[9px] px-1 py-0.5 rounded bg-yellow-500/20 text-yellow-300 font-bold">BETA</span>
                  )}
                </span>
              )}
            </div>
          )}
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

      {/* Pipeline + Analyze — shown after file is selected */}
      {fileSelected && !result && !loading && (
        <div className="space-y-4 mt-6">
          <PipelineStatus />
          <AdvancedSettingsPanel
            engine={advEngine}
            onEngineChange={setAdvEngine}
            showDiagnostics={advDiagnostics}
            onDiagnosticsChange={setAdvDiagnostics}
            benchmarkMode={advBenchmark}
            onBenchmarkChange={setAdvBenchmark}
            devLogs={advDevLogs}
            onDevLogsChange={setAdvDevLogs}
          />
          <button
            onClick={runAnalysis}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-red-600 text-white rounded-xl hover:bg-red-500 transition-all text-sm font-semibold shadow-lg shadow-red-600/20"
          >
            <Activity className="w-4 h-4" />
            Analyze Image
          </button>
        </div>
      )}

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
          <p className="text-trinetra-muted">Running analysis pipeline...</p>
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
          {judgeMode && (
            <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30">
              <Presentation className="w-6 h-6 text-purple-400 mx-auto mb-2" />
              <h2 className="text-lg font-bold text-white text-center">TRINETRA AI — Processing Breakdown</h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                <div className="bg-purple-500/5 rounded-lg p-3 text-center border border-purple-500/20">
                  <div className="text-[10px] text-purple-300 font-semibold mb-1">1. Image Enhancement</div>
                  <div className="text-xs text-trinetra-muted">CLAHE + Denoise + Dehaze</div>
                  <div className="text-[10px] text-green-400 mt-1">✓ Complete</div>
                </div>
                <div className="bg-purple-500/5 rounded-lg p-3 text-center border border-purple-500/20">
                  <div className="text-[10px] text-purple-300 font-semibold mb-1">2. Object Detection</div>
                  <div className="text-xs text-trinetra-muted">YOLOv8s / OwlViT</div>
                  <div className="text-[10px] text-green-400 mt-1">✓ {result.detections.length} objects</div>
                </div>
                <div className="bg-purple-500/5 rounded-lg p-3 text-center border border-purple-500/20">
                  <div className="text-[10px] text-purple-300 font-semibold mb-1">3. Violation Analysis</div>
                  <div className="text-xs text-trinetra-muted">{result.violations.length} violations found</div>
                  <div className="text-[10px] text-green-400 mt-1">✓ Complete</div>
                </div>
                <div className="bg-purple-500/5 rounded-lg p-3 text-center border border-purple-500/20">
                  <div className="text-[10px] text-purple-300 font-semibold mb-1">4. License Plate OCR</div>
                  <div className="text-xs text-trinetra-muted">{result.license_plate?.number || 'Not detected'}</div>
                  <div className={`text-[10px] mt-1 ${result.license_plate ? 'text-green-400' : 'text-yellow-400'}`}>
                    {result.license_plate ? '✓ Read' : '○ Not found'}
                  </div>
                </div>
                <div className="bg-purple-500/5 rounded-lg p-3 text-center border border-purple-500/20">
                  <div className="text-[10px] text-purple-300 font-semibold mb-1">5. Scene Understanding</div>
                  <div className="text-xs text-trinetra-muted truncate">{result.scene_understanding?.narrative?.slice(0, 40) || 'N/A'}...</div>
                  <div className="text-[10px] text-green-400 mt-1">✓ Florence-2</div>
                </div>
                <div className="bg-purple-500/5 rounded-lg p-3 text-center border border-purple-500/20">
                  <div className="text-[10px] text-purple-300 font-semibold mb-1">6. AI Verification</div>
                  <div className="text-xs text-trinetra-muted">{result.ai_review_panel?.verified_count || 0} verified findings</div>
                  <div className="text-[10px] text-green-400 mt-1">✓ Cross-validated</div>
                </div>
                <div className="bg-purple-500/5 rounded-lg p-3 text-center border border-purple-500/20">
                  <div className="text-[10px] text-purple-300 font-semibold mb-1">7. Evidence Generation</div>
                  <div className="text-xs text-trinetra-muted">PDF + Annotated Image</div>
                  <div className="text-[10px] text-green-400 mt-1">✓ Ready</div>
                </div>
                <div className="bg-purple-500/5 rounded-lg p-3 text-center border border-purple-500/20">
                  <div className="text-[10px] text-purple-300 font-semibold mb-1">8. Intelligence Report</div>
                  <div className="text-xs text-trinetra-muted">Risk Score: {result.risk_score || 0}</div>
                  <div className="text-[10px] text-green-400 mt-1">✓ Complete</div>
                </div>
              </div>
              {result.performance && (
                <div className="mt-3 text-center text-xs text-purple-300">
                  Total pipeline: {result.performance.total_time.toFixed(1)}s | {result.performance.detection_time.toFixed(1)}s detection | {result.performance.reasoning_time.toFixed(1)}s reasoning
                </div>
              )}
            </div>
          )}

          <ExecutiveSummaryCard result={result} />

          {result.performance && (
            <div className="glass rounded-xl p-5">
              <h3 className="text-sm font-semibold text-trinetra-text mb-3 flex items-center gap-2">
                <Gauge className="w-4 h-4" /> Pipeline Performance
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: 'Enhancement', value: result.performance.enhancement_time, unit: 's' },
                  { label: 'Detection', value: result.performance.detection_time, unit: 's' },
                  { label: 'OCR', value: result.performance.ocr_time, unit: 's' },
                  { label: 'Reasoning', value: result.performance.reasoning_time, unit: 's' },
                ].map((m, i) => (
                  <div key={i} className="bg-[#1a2040] rounded-lg p-3 text-center">
                    <div className="text-xs text-trinetra-muted mb-1">{m.label}</div>
                    <div className="text-lg font-bold text-white">{m.value.toFixed(1)}<span className="text-xs text-trinetra-muted ml-0.5">{m.unit}</span></div>
                  </div>
                ))}
              </div>
              <div className="mt-3 pt-3 border-t border-trinetra-border flex justify-between items-center">
                <span className="text-xs text-trinetra-muted">Total Processing Time</span>
                <span className="text-sm font-bold text-green-400">{result.performance.total_time.toFixed(1)}s</span>
              </div>
            </div>
          )}

          {systemHealth && (
            <div className="glass rounded-xl p-5">
              <h3 className="text-sm font-semibold text-trinetra-text mb-3 flex items-center gap-2">
                <Server className="w-4 h-4" /> System Health
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {Object.entries(systemHealth.models || {}).map(([name, status], i) => (
                  <div key={i} className="bg-[#1a2040] rounded-lg p-3 text-center">
                    <div className="text-xs text-trinetra-muted mb-1 capitalize">{name.replace(/_/g, ' ')}</div>
                    <div className={`text-sm font-bold flex items-center justify-center gap-1.5 ${
                      status === 'loaded' || status === 'paddleocr' ? 'text-green-400' : 'text-yellow-400'
                    }`}>
                      <span className={`w-2 h-2 rounded-full ${
                        status === 'loaded' || status === 'paddleocr' ? 'bg-green-400' : 'bg-yellow-400'
                      }`} />
                      {(status === 'loaded' || status === 'paddleocr') ? 'ONLINE' : status === 'fallback' ? 'FALLBACK' : String(status).toUpperCase()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {fpStats && (
            <div className="glass rounded-xl p-5">
              <h3 className="text-sm font-semibold text-trinetra-text mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4" /> Validation Insights
              </h3>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-[#1a2040] rounded-lg p-3 text-center">
                  <div className="text-xs text-trinetra-muted mb-1">FP Corrected</div>
                  <div className="text-lg font-bold text-green-400">{fpStats.reviewed_candidates || 0}</div>
                </div>
                <div className="bg-[#1a2040] rounded-lg p-3 text-center">
                  <div className="text-xs text-trinetra-muted mb-1">Most Common Type</div>
                  <div className="text-sm font-bold text-red-400 truncate">{fpStats.top_violation_type || 'N/A'}</div>
                </div>
                <div className="bg-[#1a2040] rounded-lg p-3 text-center">
                  <div className="text-xs text-trinetra-muted mb-1">Total Candidates</div>
                  <div className="text-lg font-bold text-white">{fpStats.total_candidates || 0}</div>
                </div>
              </div>
            </div>
          )}

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

                      {v.explainable_reason && (
                        <div className="mb-3 p-3 rounded-lg bg-[#0d1225] border border-trinetra-border">
                          <div className="flex items-center gap-1.5 text-xs text-trinetra-muted mb-1">
                            <FileText className="w-3 h-3" /> Reason
                          </div>
                          <p className="text-sm text-trinetra-text">{v.explainable_reason}</p>
                        </div>
                      )}

                      {v.enforcement_recommendation && (
                        <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                          <div className="flex items-center gap-1.5 text-xs text-blue-400 mb-1">
                            <Shield className="w-3 h-3" /> Recommended Response
                          </div>
                          <p className="text-sm text-trinetra-text">{v.enforcement_recommendation}</p>
                        </div>
                      )}

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
              <div className={`rounded-lg border ${result.compliance_status === 'COMPLIANT' ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-trinetra-border'}`}>
                <div className="p-6 text-center">
                  {result.compliance_status === 'COMPLIANT' ? (
                    <>
                      <div className="w-14 h-14 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-3">
                        <ThumbsUp className="w-7 h-7 text-emerald-400" />
                      </div>
                      <h3 className="text-lg font-bold text-emerald-400 mb-1">COMPLIANT VEHICLE</h3>
                      <p className="text-sm text-trinetra-muted mb-4">{result.compliance_reason || 'All observed vehicles appear compliant with traffic regulations.'}</p>
                      <span className="inline-flex items-center gap-1.5 text-xs bg-emerald-500/20 text-emerald-300 px-3 py-1.5 rounded-full">
                        <CheckCircle className="w-3.5 h-3.5" /> No Action Required
                      </span>
                      {judgeMode && (
                        <div className="mt-4 p-4 rounded-lg bg-purple-500/5 border border-purple-500/20 text-left">
                          <div className="flex items-center gap-1.5 text-xs text-purple-400 mb-2">
                            <Presentation className="w-3 h-3" /> Business Value
                          </div>
                          <p className="text-sm text-trinetra-text">
                            TRINETRA AI correctly identified a <strong className="text-white">compliant vehicle</strong> —
                            demonstrating the platform's ability to recognize both violations <strong className="text-white">and safe road behavior</strong>.
                            This reduces false positives and builds <strong className="text-white">trust in AI-assisted traffic enforcement</strong>.
                          </p>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="flex items-center justify-center gap-3 text-green-400">
                      <CheckCircle className="w-5 h-5" />
                      <span>No violations detected</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {result.primary_finding && (
            <div className="glass rounded-xl p-5">
              <h3 className="text-sm font-semibold text-trinetra-text mb-3 flex items-center gap-2">
                <MapPin className="w-4 h-4" /> Analysis Summary
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-[#1a2040] rounded-lg p-3 text-center">
                  <div className="text-xs text-trinetra-muted mb-1">Primary Finding</div>
                  <div className="text-sm font-bold text-white truncate">{result.primary_finding.type || 'N/A'}</div>
                </div>
                <div className="bg-[#1a2040] rounded-lg p-3 text-center">
                  <div className="text-xs text-trinetra-muted mb-1">Confidence</div>
                  <div className={`text-lg font-bold ${
                    (result.primary_finding.confidence || 0) >= 0.7 ? 'text-green-400' : 'text-yellow-400'
                  }`}>{(result.primary_finding.confidence || 0) * 100}%</div>
                </div>
                <div className="bg-[#1a2040] rounded-lg p-3 text-center">
                  <div className="text-xs text-trinetra-muted mb-1">Evidence</div>
                  <div className={`text-lg font-bold ${
                    (result.primary_finding.evidence_score || 0) >= 0.6 ? 'text-green-400' : 'text-yellow-400'
                  }`}>{((result.primary_finding.evidence_score || 0) * 100).toFixed(0)}%</div>
                </div>
                <div className="bg-[#1a2040] rounded-lg p-3 text-center">
                  <div className="text-xs text-trinetra-muted mb-1">Enforcement</div>
                  <div className="text-[11px] font-medium text-blue-300 leading-tight">{result.primary_finding.enforcement_recommendation?.split('.')[0] || 'Review'}</div>
                </div>
              </div>
            </div>
          )}

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

          {result.detection_model && (
            <div className="glass rounded-xl p-4">
              <h3 className="text-xs font-semibold text-trinetra-muted mb-2 flex items-center gap-1.5">
                <Activity className="w-3 h-3" /> Detection Engine
              </h3>
              <div className="flex flex-wrap gap-2">
                <span className={`text-xs font-mono px-2 py-1 rounded-full border ${
                  result.detection_model.active_mode === 'yolo'
                    ? 'bg-yellow-500/10 text-yellow-300 border-yellow-500/30'
                    : result.detection_model.active_mode === 'hf_inference_api_owlvit'
                    ? 'bg-purple-500/10 text-purple-300 border-purple-500/30'
                    : result.detection_model.active_mode === 'owlvit_local'
                    ? 'bg-blue-500/10 text-blue-300 border-blue-500/30'
                    : result.detection_model.active_mode?.startsWith('locateanything')
                    ? 'bg-green-500/10 text-green-300 border-green-500/30'
                    : 'bg-gray-500/10 text-gray-300 border-gray-500/30'
                }`}>
                  {result.detection_model.engine_label || result.detection_model.active_mode}
                </span>
                {result.helmet_model && (
                  <span className="text-xs font-mono px-2 py-1 rounded-full bg-[#1a2040] text-trinetra-muted border border-trinetra-border flex items-center gap-1">
                    Helmet: {result.helmet_model.loaded ? result.helmet_model.model_name : 'HSV fallback'}
                    {result.helmet_model.beta && (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-yellow-500/20 text-yellow-300 font-bold">BETA</span>
                    )}
                  </span>
                )}
              </div>
            </div>
          )}

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
