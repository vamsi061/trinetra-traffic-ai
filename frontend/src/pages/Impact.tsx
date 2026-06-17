import { BarChart3, TrendingUp, Shield, ShieldCheck, Users, MapPin, AlertTriangle, Eye } from 'lucide-react'

export default function Impact() {
  const benefits = [
    { icon: TrendingUp, title: 'Reduced Manual Monitoring', desc: 'AI-powered pre-screening reduces time spent reviewing compliant traffic by over 60%.' },
    { icon: AlertTriangle, title: 'Faster Violation Identification', desc: 'Real-time detection and classification of helmet non-compliance, overloading, and parking violations.' },
    { icon: Shield, title: 'Improved Enforcement Prioritization', desc: 'Officer Priority Engine ranks violations by severity, ensuring critical cases get immediate attention.' },
    { icon: MapPin, title: 'Hotspot Awareness', desc: 'Location-based violation tracking identifies high-risk zones for targeted enforcement campaigns.' },
    { icon: Users, title: 'Repeat Offender Tracking', desc: 'Vehicle Risk Profiles track violation history and flag repeat offenders for officer attention.' },
    { icon: BarChart3, title: 'Evidence-Based Decision Support', desc: 'Confidence scoring, reliability badges, and human-review workflow support accountable enforcement.' },
    { icon: ShieldCheck, title: 'Positive Compliance Recognition', desc: 'System recognizes compliant vehicles — demonstrating balanced and fair enforcement intelligence.' },
    { icon: Eye, title: 'Explainable AI for Transparency', desc: 'Every detection includes a natural-language explanation, confidence band, and recommended action.' },
  ]

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
          <TrendingUp className="w-5 h-5 text-emerald-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Expected Operational Benefits</h1>
          <p className="text-trinetra-muted text-sm">TRINETRA AI — Impact Assessment for Bengaluru Traffic Police</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        {benefits.map((b, i) => (
          <div key={i} className="glass rounded-xl p-5 border-l-4 border-l-emerald-500 hover:border-l-red-500 transition-colors">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1a2040] flex items-center justify-center shrink-0">
                <b.icon className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white text-sm">{b.title}</h3>
                <p className="text-sm text-trinetra-muted mt-1">{b.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Key Metrics Preview */}
      <div className="glass rounded-xl p-6 border-l-4 border-l-blue-500">
        <h3 className="text-sm font-semibold text-blue-400 mb-4">Operational Metrics</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Violation Categories', value: '5+' },
            { label: 'Detection Types', value: '7' },
            { label: 'Review Workflow Stages', value: '3' },
            { label: 'Integration Readiness', value: 'API-First' },
          ].map(m => (
            <div key={m.label} className="bg-[#1a2040] rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-white">{m.value}</div>
              <div className="text-xs text-trinetra-muted mt-1">{m.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Deployment Impact */}
      <div className="mt-6 glass rounded-xl p-6 border-l-4 border-l-purple-500">
        <h3 className="text-sm font-semibold text-purple-400 mb-3">Deployment Impact Summary</h3>
        <p className="text-sm text-trinetra-text leading-relaxed">
          TRINETRA AI transforms traffic imagery into <strong className="text-white">actionable enforcement intelligence</strong>.
          By combining <strong className="text-white">AI-powered detection</strong> with <strong className="text-white">human review workflows</strong>,
          the platform enables traffic police to identify violations faster, prioritize critical cases,
          track repeat offenders, and make evidence-based decisions — all while maintaining
          <strong className="text-white"> explainability</strong> and <strong className="text-white">transparency</strong>.
        </p>
        <p className="text-sm text-trinetra-text mt-3">
          Designed for <strong className="text-white">Bengaluru Traffic Police</strong> operations,
          the system scales from single-image analysis to city-wide deployment with edge camera processing,
          cloud analytics, and future E-Challan integration.
        </p>
      </div>
    </div>
  )
}
