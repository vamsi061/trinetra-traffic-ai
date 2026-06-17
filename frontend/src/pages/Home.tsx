import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Shield, ShieldAlert, TrendingUp, MapPin, Users, FileText,
  Bot, AlertTriangle, ArrowRight, Camera, BarChart3, Radio,
} from 'lucide-react'
import { getStats, getRecentViolations, getExecutiveSummary, type ViolationStats, type ViolationRecord, type ExecutiveSummary } from '../api/client'

export default function Home() {
  const [stats, setStats] = useState<ViolationStats | null>(null)
  const [exec, setExec] = useState<ExecutiveSummary | null>(null)
  const [recent, setRecent] = useState<ViolationRecord[]>([])

  useEffect(() => {
    getStats().then(setStats)
    getExecutiveSummary().then(setExec)
    getRecentViolations(5).then(r => setRecent(r.violations))
  }, [])

  const hasData = stats && stats.total > 0

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-2xl p-8"
        style={{ background: 'linear-gradient(135deg, #0d1225 0%, #1a2040 50%, #0f1a3a 100%)' }}
      >
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-5 left-10 w-48 h-48 rounded-full bg-red-500 blur-3xl" />
          <div className="absolute bottom-5 right-10 w-72 h-72 rounded-full bg-blue-500 blur-3xl" />
        </div>
        <div className="relative flex items-center gap-5">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center shadow-lg shadow-red-500/20">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">TRINETRA AI</h1>
            <p className="text-trinetra-muted text-lg">AI-Powered Traffic Enforcement Intelligence Platform</p>
          </div>
        </div>
      </div>

      {/* Mission Statement */}
      <div className="glass rounded-xl p-6 border-l-4 border-l-red-500">
        <p className="text-trinetra-text text-sm leading-relaxed">
          <strong className="text-white">TRINETRA AI</strong> is an AI-powered traffic enforcement intelligence platform.
          Core workflow: Traffic Image → Violation Detection → Risk Assessment → Explainable Analysis →
          Human Review → Recommended Response → Traffic Intelligence Dashboard.
        </p>
      </div>

      {/* Executive Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass rounded-xl p-4 border-l-4 border-l-green-500">
          <div className="flex items-center gap-2 text-trinetra-muted text-xs mb-2">
            <AlertTriangle className="w-3.5 h-3.5" /> Total Cases Processed
          </div>
          <div className="text-2xl font-bold text-white">{stats?.total || 0}</div>
        </div>
        <div className="glass rounded-xl p-4 border-l-4 border-l-amber-500">
          <div className="flex items-center gap-2 text-trinetra-muted text-xs mb-2">
            <Users className="w-3.5 h-3.5" /> Vehicles Monitored
          </div>
          <div className="text-2xl font-bold text-white">{stats?.unique_vehicles || 0}</div>
        </div>
        <div className="glass rounded-xl p-4 border-l-4 border-l-red-500">
          <div className="flex items-center gap-2 text-trinetra-muted text-xs mb-2">
            <ShieldAlert className="w-3.5 h-3.5" /> High-Risk Vehicles
          </div>
          <div className="text-2xl font-bold text-red-400">{stats?.high_risk_offenders || 0}</div>
        </div>
        <div className="glass rounded-xl p-4 border-l-4 border-l-blue-500">
          <div className="flex items-center gap-2 text-trinetra-muted text-xs mb-2">
            <BarChart3 className="w-3.5 h-3.5" /> Today's Cases
          </div>
          <div className="text-2xl font-bold text-blue-400">{exec?.today_violations || 0}</div>
        </div>
      </div>

      {/* Operations Center */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Operations Center</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { to: '/upload', icon: Camera, label: 'Analyze Image', desc: 'Upload traffic images for AI violation detection', color: 'from-red-500 to-red-700' },
            { to: '/enforcement', icon: Shield, label: 'Enforcement Intel', desc: 'Hotspots, offenders, forecasts, intelligence reports', color: 'from-blue-500 to-blue-700' },
            { to: '/intel-center', icon: Radio, label: 'Command Center', desc: 'Live executive summary and smart city overview', color: 'from-purple-500 to-purple-700' },
            { to: '/copilot', icon: Bot, label: 'AI Copilot', desc: 'Ask questions in plain English', color: 'from-cyan-500 to-cyan-700' },
          ].map(item => (
            <Link key={item.to} to={item.to}
              className="glass rounded-xl p-5 hover:bg-[#1a2040]/80 transition-all group"
            >
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${item.color} flex items-center justify-center mb-3`}>
                <item.icon className="w-5 h-5 text-white" />
              </div>
              <h3 className="font-semibold text-white group-hover:text-red-400 transition-colors">{item.label}</h3>
              <p className="text-xs text-trinetra-muted mt-1">{item.desc}</p>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent & Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Recent Cases</h2>
            <Link to="/records" className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {recent.length > 0 ? (
            <div className="space-y-2">
              {recent.map(v => (
                <div key={v.id} className="flex items-center justify-between bg-[#1a2040] rounded-lg px-4 py-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${
                      v.violation_type === 'NO_HELMET' ? 'bg-red-500' :
                      v.violation_type === 'TRIPLE_RIDING' ? 'bg-amber-500' :
                      v.violation_type === 'WRONG_SIDE_DRIVING' ? 'bg-purple-500' :
                      'bg-rose-500'
                    }`} />
                    <span className="text-white text-sm truncate">{v.violation_type.replace('_', ' ')}</span>
                    <span className="text-trinetra-muted text-xs truncate">{v.vehicle_number || 'Unknown'}</span>
                  </div>
                  <span className="text-xs text-trinetra-muted shrink-0">{v.timestamp.slice(0, 10)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-10 text-trinetra-muted">
              <Camera className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No cases recorded yet.</p>
              <Link to="/upload" className="text-red-400 text-sm mt-2 inline-block hover:text-red-300">
                Upload an image to begin →
              </Link>
            </div>
          )}
        </div>

        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Violation Breakdown</h2>
          {hasData ? (
            <div className="space-y-3">
              {[
                { label: 'No Helmet', count: stats!.no_helmet, color: 'bg-red-500', text: 'text-red-400' },
                { label: 'Triple Riding', count: stats!.triple_riding, color: 'bg-amber-500', text: 'text-amber-400' },
                { label: 'Overloading', count: (stats!.motorcycle_overloading || 0) + (stats!.motorcycle_extreme_overloading || 0), color: 'bg-rose-500', text: 'text-rose-300' },
              ].map(item => {
                const pct = ((item.count / stats!.total) * 100).toFixed(1)
                return (
                  <div key={item.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className={item.text}>{item.label}</span>
                      <span className="text-white font-mono">{item.count} ({pct}%)</span>
                    </div>
                    <div className="h-2 bg-[#1a2040] rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${item.color}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-10 text-trinetra-muted">
              <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No data yet. Upload traffic images to begin.</p>
            </div>
          )}
        </div>
      </div>

      {/* Confidence Guide */}
      <div className="glass rounded-xl p-6 border-t-2 border-trinetra-border">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-red-400" />
          <h2 className="text-lg font-semibold text-white">How to Interpret Results</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="bg-[#1a2040] rounded-xl p-4">
            <div className="text-xs font-semibold text-green-400 mb-2">HIGH CONFIDENCE (≥80%)</div>
            <p className="text-trinetra-text">Clear detection with strong AI confidence. Evidence is reliable for enforcement workflow. Automated processing recommended.</p>
          </div>
          <div className="bg-[#1a2040] rounded-xl p-4">
            <div className="text-xs font-semibold text-yellow-400 mb-2">MEDIUM CONFIDENCE (60-80%)</div>
            <p className="text-trinetra-text">Moderate confidence. Officer review recommended before taking action. Some uncertainty in the detection.</p>
          </div>
          <div className="bg-[#1a2040] rounded-xl p-4">
            <div className="text-xs font-semibold text-orange-400 mb-2">LOW CONFIDENCE (&lt;60%)</div>
            <p className="text-trinetra-text">Low confidence or crowded scene. Manual officer verification required. Do not proceed without human review.</p>
          </div>
        </div>
      </div>

      {/* Intelligence Pipeline */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Enforcement Intelligence Pipeline</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-center">
          {[
            { icon: '📷', label: 'Traffic Cameras' },
            { icon: '🧠', label: 'AI Analysis' },
            { icon: '⚡', label: 'Violation Engine' },
            { icon: '📊', label: 'Intel Dashboard' },
            { icon: '📱', label: 'Officer Dispatch' },
            { icon: '📋', label: 'Case Resolution' },
          ].map((item, i) => (
            <div key={i} className="bg-[#1a2040] rounded-xl p-4 border border-trinetra-border">
              <div className="text-2xl mb-2">{item.icon}</div>
              <div className="text-white text-sm font-semibold">{item.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
