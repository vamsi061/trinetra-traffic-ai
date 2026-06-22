import React, { useState, useEffect } from 'react'
import { Upload as UploadIcon, Activity, Search, AlertTriangle, FileText, Eye, Shield, Download, BarChart3, Zap, Server, ChevronRight, Cpu, Loader2 } from 'lucide-react'
import { getRuntimeMetrics } from '../api/client'
import type { RuntimeMetrics } from '../api/client'

const pipelineSteps = [
  { icon: UploadIcon, label: 'Upload', desc: 'Image ingestion and validation' },
  { icon: Activity, label: 'Enhancement', desc: 'CLAHE + denoise + dehaze' },
  { icon: Search, label: 'Detection', desc: 'YOLOv8s / OwlViT' },
  { icon: AlertTriangle, label: 'Violations', desc: '8 violation detectors' },
  { icon: FileText, label: 'OCR', desc: 'PaddleOCR + EasyOCR' },
  { icon: Eye, label: 'Reasoning', desc: 'Florence-2 scene analysis' },
  { icon: Shield, label: 'Verification', desc: 'Cross-validation engine' },
  { icon: Download, label: 'Report', desc: 'PDF evidence generation' },
]

const pipelineDetails = [
  { title: '1. Image Enhancement', desc: 'CLAHE normalization, denoising, dehazing, adaptive contrast adjustment, super-resolution for low-quality inputs' },
  { title: '2. Object Detection', desc: 'YOLOv8s (COCO) primary detector + OwlViT zero-shot fallback for vehicles, persons, traffic lights, and stop lines' },
  { title: '3. Violation Detection', desc: '8 violation types with violation-specific confidence thresholds, environment-aware adjustment, and Florence context boost' },
  { title: '4. License Plate OCR', desc: 'PaddleOCR primary → EasyOCR fallback → OpenCV contour detection, 6 preprocessing variants, India-format regex validation' },
  { title: '5. Scene Reasoning', desc: 'Florence-2 vision-language model generates natural-language scene narrative and structured scene breakdown' },
  { title: '6. AI Verification', desc: 'Cross-validates each violation against the scene narrative, adjusts confidence based on contextual evidence' },
  { title: '7. Evidence Generation', desc: 'Annotated images with bounding boxes + 8-section PDF evidence report with primary finding and enforcement recommendations' },
  { title: '8. Intelligence Report', desc: 'Risk scoring, compliance assessment, database storage, hotspot registration, repeat offender tracking' },
]

export default function Architecture() {
  const [metrics, setMetrics] = useState<RuntimeMetrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getRuntimeMetrics()
      .then(setMetrics)
      .catch(() => setMetrics(null))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">TRINETRA AI System Architecture</h1>
        <p className="text-trinetra-muted text-sm">Live Runtime Intelligence</p>
      </div>

      {/* Pipeline Flow */}
      <div className="glass rounded-xl p-6 mb-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4" /> Detection Pipeline
        </h3>
        <div className="flex flex-wrap items-center justify-center gap-1 sm:gap-2">
          {pipelineSteps.map((step, i) => (
            <React.Fragment key={i}>
              <div className="flex flex-col items-center p-2 sm:p-3 rounded-lg bg-[#1a2040] border border-trinetra-border min-w-[60px] sm:min-w-[80px]">
                <step.icon className="w-4 h-4 text-red-400 mb-1" />
                <span className="text-[10px] font-medium text-white">{step.label}</span>
                <span className="text-[8px] text-trinetra-muted text-center leading-tight mt-0.5">{step.desc}</span>
              </div>
              {i < pipelineSteps.length - 1 && (
                <ChevronRight className="w-4 h-4 text-trinetra-muted shrink-0 hidden sm:block" />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Runtime Metrics */}
      <div className="glass rounded-xl p-6 mb-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <BarChart3 className="w-4 h-4" /> Runtime Metrics
        </h3>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-trinetra-muted">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading metrics...
          </div>
        ) : metrics ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-[#1a2040] rounded-lg p-4 text-center">
              <BarChart3 className="w-5 h-5 text-blue-400 mx-auto mb-2" />
              <div className="text-2xl font-bold text-white">{metrics.total_images_processed}</div>
              <div className="text-xs text-trinetra-muted">Images Processed</div>
            </div>
            <div className="bg-[#1a2040] rounded-lg p-4 text-center">
              <AlertTriangle className="w-5 h-5 text-red-400 mx-auto mb-2" />
              <div className="text-2xl font-bold text-white">{metrics.total_violations_detected}</div>
              <div className="text-xs text-trinetra-muted">Violations Detected</div>
            </div>
            <div className="bg-[#1a2040] rounded-lg p-4 text-center">
              <FileText className="w-5 h-5 text-green-400 mx-auto mb-2" />
              <div className="text-2xl font-bold text-white">{metrics.total_reports_generated}</div>
              <div className="text-xs text-trinetra-muted">Reports Generated</div>
            </div>
            <div className="bg-[#1a2040] rounded-lg p-4 text-center">
              <Zap className="w-5 h-5 text-yellow-400 mx-auto mb-2" />
              <div className="text-2xl font-bold text-white">{metrics.false_positives_logged}</div>
              <div className="text-xs text-trinetra-muted">FP Candidates</div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-trinetra-muted">Unable to load metrics. Ensure the backend is running.</p>
        )}
      </div>

      {/* Active Models */}
      <div className="glass rounded-xl p-6 mb-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Server className="w-4 h-4" /> Active Models
        </h3>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-trinetra-muted">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading model status...
          </div>
        ) : metrics?.active_models ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-trinetra-muted text-xs border-b border-trinetra-border">
                  <th className="text-left py-2 pr-4">Model</th>
                  <th className="text-left py-2 pr-4">Status</th>
                  <th className="text-left py-2">Purpose</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(metrics.active_models).map(([name, info], i) => (
                  <tr key={i} className="border-b border-trinetra-border/50">
                    <td className="py-2 pr-4 text-white font-mono text-xs">{name.replace(/_/g, ' ')}</td>
                    <td className="py-2 pr-4">
                      <span className={`flex items-center gap-1.5 text-xs ${
                        info.status === 'loaded' ? 'text-green-400' : 'text-yellow-400'
                      }`}>
                        <span className={`w-2 h-2 rounded-full ${
                          info.status === 'loaded' ? 'bg-green-400' : 'bg-yellow-400'
                        }`} />
                        {info.status === 'loaded' ? 'Loaded' : info.status}
                      </span>
                    </td>
                    <td className="py-2 text-trinetra-muted text-xs">{info.purpose}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-trinetra-muted">Unable to load model status.</p>
        )}
      </div>

      {/* Pipeline Details */}
      <div className="glass rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Cpu className="w-4 h-4" /> Pipeline Stages
        </h3>
        <div className="space-y-3">
          {pipelineDetails.map((stage, i) => (
            <div key={i} className="bg-[#1a2040] rounded-lg p-3 border border-trinetra-border">
              <h4 className="text-sm font-medium text-white mb-1">{stage.title}</h4>
              <p className="text-xs text-trinetra-muted">{stage.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
