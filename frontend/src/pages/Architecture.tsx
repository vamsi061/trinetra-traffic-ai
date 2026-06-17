import { Shield, Camera, Brain, FileText, BarChart3, AlertTriangle, Users, Search, Download, Eye, Radio } from 'lucide-react'

export default function Architecture() {
  const steps = [
    { icon: Camera, label: 'Traffic Camera', desc: 'Image capture from traffic cameras, patrol feeds, or manual upload.' },
    { icon: Brain, label: 'Image Quality Assessment', desc: 'Evaluate brightness, blur, fog, glare, contrast, and shadow before processing.' },
    { icon: Brain, label: 'TRINETRA Vision Engine', desc: 'YOLOv8s-based detection for vehicles, motorcycles, persons. Rider association and occupancy estimation.' },
    { icon: AlertTriangle, label: 'Violation Detection', desc: 'Helmet compliance check, triple riding, overloading, illegal parking heuristics.' },
    { icon: Search, label: 'OCR Engine', desc: 'License plate recognition with confidence scoring and visibility assessment.' },
    { icon: FileText, label: 'Evidence Generator', desc: 'Annotated images with bounding boxes, violation labels, and confidence scores.' },
    { icon: BarChart3, label: 'Risk Assessment', desc: 'Severity scoring, crowding analysis, reliability calculation, and risk level classification.' },
    { icon: Eye, label: 'Human Review', desc: 'Confidence-based review workflow: auto-confirmed, human review recommended, or manual verification required.' },
    { icon: Radio, label: 'Traffic Intelligence Center', desc: 'Executive summary, violation analytics, hotspot mapping, repeat offender tracking, and forecasts.' },
    { icon: Shield, label: 'Enforcement Recommendations', desc: 'Officer review recommendations — never automated enforcement. AI as decision support tool.' },
  ]

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
          <Brain className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">System Architecture</h1>
          <p className="text-trinetra-muted text-sm">TRINETRA AI — End-to-end processing pipeline</p>
        </div>
      </div>

      <div className="relative">
        {/* Vertical connecting line */}
        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-red-500/50 via-blue-500/50 to-emerald-500/50 hidden sm:block" />

        <div className="space-y-6">
          {steps.map((s, i) => (
            <div key={i} className="relative flex items-start gap-5 glass rounded-xl p-5">
              <div className="w-14 h-14 rounded-xl bg-[#1a2040] flex items-center justify-center shrink-0 border border-trinetra-border z-10">
                <s.icon className="w-6 h-6 text-red-400" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-trinetra-muted font-mono">{(i + 1).toString().padStart(2, '0')}</span>
                  <h3 className="font-semibold text-white">{s.label}</h3>
                </div>
                <p className="text-sm text-trinetra-muted">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-8 glass rounded-xl p-6 border-l-4 border-l-emerald-500">
        <h3 className="text-sm font-semibold text-emerald-400 mb-2">Design Principles</h3>
        <ul className="space-y-1 text-sm text-trinetra-text">
          <li>• All detections include <strong className="text-white">confidence scoring</strong> — no binary decisions</li>
          <li>• <strong className="text-white">Explainable AI</strong> — every violation includes a natural-language reason</li>
          <li>• <strong className="text-white">Human-in-the-loop</strong> — enforcement recommendations require officer review</li>
          <li>• <strong className="text-white">Single-image analysis</strong> — no motion-based violations (wrong-side, red-light, stop-line disabled)</li>
          <li>• <strong className="text-white">Occupancy ranges</strong> — never implies exact certainty for crowded scenes</li>
        </ul>
      </div>
    </div>
  )
}
