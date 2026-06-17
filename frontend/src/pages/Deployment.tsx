import { Shield, Camera, Server, Cloud, Monitor, Smartphone, Share2, GitBranch, Cpu, Wifi } from 'lucide-react'

export default function Deployment() {
  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center">
          <Server className="w-5 h-5 text-green-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Deployment Readiness</h1>
          <p className="text-trinetra-muted text-sm">Scalable architecture for city-wide traffic enforcement intelligence</p>
        </div>
      </div>

      {/* Architecture Layers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="glass rounded-xl p-5 border-l-4 border-l-blue-500">
          <Camera className="w-8 h-8 text-blue-400 mb-3" />
          <h3 className="font-semibold text-white mb-2">Edge Camera Processing</h3>
          <ul className="space-y-1.5 text-sm text-trinetra-muted">
            <li>• Real-time image capture from traffic cameras</li>
            <li>• On-device image quality assessment</li>
            <li>• Bandwidth-efficient upload (compressed frames)</li>
            <li>• Configurable capture intervals</li>
          </ul>
        </div>
        <div className="glass rounded-xl p-5 border-l-4 border-l-purple-500">
          <Cloud className="w-8 h-8 text-purple-400 mb-3" />
          <h3 className="font-semibold text-white mb-2">Cloud Analytics Layer</h3>
          <ul className="space-y-1.5 text-sm text-trinetra-muted">
            <li>• YOLOv8s detection on GPU-enabled servers</li>
            <li>• Violation detection and risk scoring engine</li>
            <li>• Database storage for all violations and evidence</li>
            <li>• REST API for frontend integration</li>
            <li>• Horizontal scaling via load balancer</li>
          </ul>
        </div>
        <div className="glass rounded-xl p-5 border-l-4 border-l-amber-500">
          <Monitor className="w-8 h-8 text-amber-400 mb-3" />
          <h3 className="font-semibold text-white mb-2">Traffic Police Dashboard</h3>
          <ul className="space-y-1.5 text-sm text-trinetra-muted">
            <li>• Real-time violation alerts and evidence</li>
            <li>• Executive summary with reliability scoring</li>
            <li>• Hotspot maps and repeat offender tracking</li>
            <li>• Filterable violation records and analytics</li>
          </ul>
        </div>
      </div>

      {/* Workflow */}
      <div className="glass rounded-xl p-6 mb-8">
        <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
          <GitBranch className="w-4 h-4" /> Officer Review Workflow
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { step: '1', title: 'Image Captured', desc: 'From traffic camera or patrol upload' },
            { step: '2', title: 'AI Analysis', desc: 'Detection, violation check, OCR, risk scoring' },
            { step: '3', title: 'Officer Review', desc: 'Review violations, confidence, evidence, recommendations' },
            { step: '4', title: 'Action Taken', desc: 'Advisory notice, follow-up, or further investigation' },
          ].map(w => (
            <div key={w.step} className="bg-[#1a2040] rounded-lg p-4 text-center">
              <div className="w-8 h-8 rounded-full bg-red-500/20 text-red-400 text-sm font-bold flex items-center justify-center mx-auto mb-2">{w.step}</div>
              <h4 className="font-semibold text-white text-sm">{w.title}</h4>
              <p className="text-xs text-trinetra-muted mt-1">{w.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Future Integrations */}
      <div className="glass rounded-xl p-6 mb-8 border-l-4 border-l-blue-500">
        <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
          <Share2 className="w-4 h-4" /> Future Integration Roadmap
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { icon: Cpu, title: 'E-Challan Integration', desc: 'Automated challan generation for confirmed violations after officer approval.' },
            { icon: Wifi, title: 'Traffic Control Rooms', desc: 'Real-time dashboard integration with city traffic management centers.' },
            { icon: Smartphone, title: 'Smart City Platform', desc: 'API-first design for integration with municipal smart city initiatives.' },
          ].map(f => (
            <div key={f.title} className="bg-[#1a2040] rounded-lg p-4">
              <f.icon className="w-5 h-5 text-blue-400 mb-2" />
              <h4 className="font-semibold text-white text-sm">{f.title}</h4>
              <p className="text-xs text-trinetra-muted mt-1">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Scalability */}
      <div className="glass rounded-xl p-6 border-l-4 border-l-green-500">
        <h3 className="text-sm font-semibold text-green-400 mb-3">Scalability &amp; Performance</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-white">&lt;5s</div>
            <div className="text-xs text-trinetra-muted">Per-image analysis time</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-white">10+</div>
            <div className="text-xs text-trinetra-muted">Concurrent camera feeds</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-white">99%</div>
            <div className="text-xs text-trinetra-muted">API uptime target</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-white">REST</div>
            <div className="text-xs text-trinetra-muted">API-first architecture</div>
          </div>
        </div>
      </div>
    </div>
  )
}
