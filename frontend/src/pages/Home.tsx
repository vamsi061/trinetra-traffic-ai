import { useEffect, useState } from 'react'
import { TrafficCone, Shield, Car, AlertTriangle } from 'lucide-react'
import MetricCard from '../components/MetricCard'
import { getStats, getRecentViolations, ViolationStats, ViolationRecord } from '../api/client'

export default function Home() {
  const [stats, setStats] = useState<ViolationStats | null>(null)
  const [recent, setRecent] = useState<ViolationRecord[]>([])

  useEffect(() => {
    getStats().then(setStats)
    getRecentViolations(5).then(r => setRecent(r.violations))
  }, [])

  return (
    <div>
      <div className="text-center mb-6 sm:mb-12 p-6 sm:p-10 rounded-2xl relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #0d1225 0%, #1a2040 50%, #0f1a3a 100%)' }}>
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 w-40 h-40 rounded-full bg-red-500 blur-3xl" />
          <div className="absolute bottom-10 right-10 w-60 h-60 rounded-full bg-blue-500 blur-3xl" />
        </div>
        <div className="relative">
          <div className="inline-flex items-center justify-center w-12 h-12 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-red-500 to-red-700 mb-3 sm:mb-4">
            <TrafficCone className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
          </div>
          <h1 className="text-2xl sm:text-4xl font-bold text-white mb-2">TRINETRA AI</h1>
          <p className="text-trinetra-muted text-sm sm:text-lg max-w-xl mx-auto">
            AI-Powered Traffic Violation Detection &amp; Enforcement Intelligence Platform
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
        <MetricCard label="Total Violations" value={stats?.total ?? '—'} icon={<AlertTriangle className="w-4 h-4" />} color="red" />
        <MetricCard label="Helmet Violations" value={stats?.no_helmet ?? '—'} icon={<Shield className="w-4 h-4" />} color="red" />
        <MetricCard label="Triple Riding" value={stats?.triple_riding ?? '—'} icon={<Car className="w-4 h-4" />} color="green" />
        <MetricCard label="Unique Vehicles" value={stats?.unique_vehicles ?? '—'} icon={<Car className="w-4 h-4" />} color="blue" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Supported Violations</h2>
          <div className="space-y-3">
            {[
              { name: 'No Helmet', desc: 'Detects motorcycle riders without helmets using YOLO-based head region analysis', color: 'border-l-red-500' },
              { name: 'Triple Riding', desc: 'Identifies motorcycles carrying more than 2 persons via IoU analysis', color: 'border-l-amber-500' },
              { name: 'License Plate OCR', desc: 'Extracts vehicle numbers using EasyOCR with contour-based plate detection', color: 'border-l-green-500' },
            ].map(v => (
              <div key={v.name} className={`bg-[#1a2040] rounded-lg p-4 border-l-4 ${v.color}`}>
                <h3 className="font-medium text-white">{v.name}</h3>
                <p className="text-sm text-trinetra-muted mt-1">{v.desc}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Recent Detections</h2>
          {recent.length > 0 ? (
            <div className="space-y-3">
              {recent.map(v => (
                <div key={v.id} className="bg-[#1a2040] rounded-lg p-4 border-l-4 border-l-green-500">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-medium text-white">{v.violation_type.replace('_', ' ')}</span>
                      <span className="text-trinetra-muted ml-2">— {v.vehicle_number || 'Unknown'}</span>
                    </div>
                    <span className="text-xs text-trinetra-muted">{v.timestamp.slice(0, 19)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-trinetra-muted">
              <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No violations recorded yet. Upload an image to get started.</p>
            </div>
          )}
        </div>
      </div>

      <div className="glass rounded-xl p-4 sm:p-6 mt-6 sm:mt-8">
        <h2 className="text-lg font-semibold text-white mb-4">System Workflow</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4">
          {[
            { step: '1', label: 'Upload Image' },
            { step: '2', label: 'Image Enhancement' },
            { step: '3', label: 'YOLO Detection' },
            { step: '4', label: 'Violation Check' },
            { step: '5', label: 'License Plate OCR' },
            { step: '6', label: 'Evidence Generation' },
            { step: '7', label: 'Database Storage' },
            { step: '8', label: 'Analytics' },
          ].map(s => (
            <div key={s.step} className="flex items-center gap-3 bg-[#1a2040] rounded-lg p-3">
              <span className="w-8 h-8 rounded-full bg-red-500/10 text-red-400 flex items-center justify-center text-sm font-bold shrink-0">
                {s.step}
              </span>
              <span className="text-sm text-trinetra-text">{s.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
