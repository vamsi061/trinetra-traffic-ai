import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload as UploadIcon, Image as ImageIcon, AlertTriangle, CheckCircle, Search, Users } from 'lucide-react'
import { uploadImage, DetectResponse, getEvidenceUrl } from '../api/client'

export default function Upload() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DetectResponse | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(async (accepted: File[]) => {
    const file = accepted[0]
    if (!file) return

    setPreview(URL.createObjectURL(file))
    setResult(null)
    setError(null)
    setLoading(true)

    try {
      const res = await uploadImage(file)
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

  const violationColors: Record<string, string> = {
    NO_HELMET: 'text-red-400 border-red-500/30 bg-red-500/10',
    TRIPLE_RIDING: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
    SEATBELT_VIOLATION: 'text-orange-400 border-orange-500/30 bg-orange-500/10',
    WRONG_SIDE_DRIVING: 'text-purple-400 border-purple-500/30 bg-purple-500/10',
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-2">Traffic Image Analysis</h1>
      <p className="text-trinetra-muted mb-8">Upload a traffic image for AI-powered violation detection</p>

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
            <h3 className="text-sm font-medium text-trinetra-muted mb-3">Original Image</h3>
            <img src={preview} alt="Uploaded" className="w-full rounded-lg object-cover max-h-96" />
          </div>

          {result?.evidence_path && (
            <div className="glass rounded-xl p-4">
              <h3 className="text-sm font-medium text-trinetra-muted mb-3">Analyzed Result</h3>
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
          {result.detections.length > 0 && (
            <div className="glass rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Detected Objects</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {result.detections.map((d, i) => (
                  <div key={i} className="bg-[#1a2040] rounded-lg p-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-trinetra-muted font-mono">{d.instance_id}</span>
                      <span className="text-white capitalize">{d.label}</span>
                    </div>
                    <span className="text-sm text-trinetra-muted">{(d.confidence * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.motorcycle_riders?.length > 0 && (
            <div className="glass rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Motorcycle Rider Breakdown</h3>
              <div className="space-y-3">
                {result.motorcycle_riders.map((mr, i) => (
                  <div key={i} className="bg-[#1a2040] rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Users className="w-4 h-4 text-amber-400 shrink-0" />
                      <span className="font-mono text-sm text-amber-400">{mr.motorcycle_id}</span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-bold text-white">{mr.rider_count}</span>
                      <span className="text-sm text-trinetra-muted">
                        {mr.rider_count === 1 ? 'rider' : 'riders'}
                        {mr.rider_count > 2 ? ' ⚠️ Triple riding violation' : ''}
                      </span>
                    </div>
                    {mr.riders.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {mr.riders.map((r, j) => (
                          <span key={j} className="text-xs bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full font-mono">{r}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="glass rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Violation Report</h3>
            {result.violations.length > 0 ? (
              <div className="space-y-3">
                {result.violations.map((v, i) => (
                  <div key={i} className={`rounded-lg p-4 border ${violationColors[v.type] || 'border-trinetra-border'}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-semibold">{v.type.replace('_', ' ')}</span>
                        <p className="text-sm opacity-80 mt-1">{v.description}</p>
                        {v.involved_objects?.length > 0 && (
                          <div className="flex flex-wrap gap-2 mt-2">
                            {v.involved_objects.map((obj, j) => (
                              <span key={j} className="text-xs bg-white/5 text-trinetra-muted px-2 py-0.5 rounded-full font-mono">{obj}</span>
                            ))}
                          </div>
                        )}
                      </div>
                      <span className="text-sm font-mono">{(v.confidence * 100).toFixed(0)}%</span>
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
                  <div className="text-sm text-trinetra-muted">
                    OCR Confidence: {(result.license_plate.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
