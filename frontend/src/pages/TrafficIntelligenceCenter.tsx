import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Shield, ShieldAlert, TrendingUp, MapPin, Users, FileText,
  Bot, AlertTriangle, Camera, BarChart3, Radio, Activity,
  Clock, Map, ChevronRight, BrainCircuit, Target,
} from 'lucide-react'
import {
  getStats, getEnforcementDashboard, getExecutiveSummary,
  type ViolationStats, type EnforcementDashboard, type ExecutiveSummary,
} from '../api/client'

export default function TrafficIntelligenceCenter() {
  const [exec, setExec] = useState<ExecutiveSummary | null>(null)
  const [dash, setDash] = useState<EnforcementDashboard | null>(null)

  useEffect(() => {
    getExecutiveSummary().then(setExec)
    getEnforcementDashboard().then(setDash)
  }, [])

  const hasData = exec && exec.total_violations > 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center">
          <Radio className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Command Center</h1>
          <p className="text-trinetra-muted text-sm">Traffic Enforcement Intelligence — Live Overview</p>
        </div>
      </div>

      {/* Status Bar */}
      <div className="glass rounded-xl p-4 flex flex-wrap items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-trinetra-text">System: <strong className="text-white">Active</strong></span>
        </div>
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-trinetra-muted" />
          <span className="text-trinetra-text">Total Cases: <strong className="text-white">{exec?.total_violations || 0}</strong></span>
        </div>
        <div className="flex items-center gap-2">
          <Users className="w-3.5 h-3.5 text-trinetra-muted" />
          <span className="text-trinetra-text">Vehicles Tracked: <strong className="text-white">{exec?.unique_vehicles || 0}</strong></span>
        </div>
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-3.5 h-3.5 text-trinetra-muted" />
          <span className="text-trinetra-text">High-Risk: <strong className="text-red-400">{exec?.high_risk_offenders || 0}</strong></span>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="glass rounded-xl p-6 border-l-4 border-l-blue-500">
        <h2 className="text-sm font-semibold text-blue-400 mb-4 flex items-center gap-2">
          <BarChart3 className="w-4 h-4" /> Executive Summary
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { label: 'Total Violations', value: exec?.total_violations || 0, color: 'text-white' },
            { label: 'Today\'s Cases', value: exec?.today_violations || 0, color: 'text-amber-400' },
            { label: 'Active Hotspots', value: exec?.active_hotspots || 0, color: 'text-red-400' },
            { label: 'High-Risk Persons', value: exec?.high_risk_offenders || 0, color: 'text-red-300' },
            { label: 'Vehicles Monitored', value: exec?.unique_vehicles || 0, color: 'text-blue-400' },
            { label: 'Forecasts Active', value: exec?.active_forecasts || 0, color: 'text-purple-400' },
          ].map(item => (
            <div key={item.label} className="bg-[#1a2040] rounded-xl p-4 text-center">
              <div className="text-xs text-trinetra-muted mb-1">{item.label}</div>
              <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
            </div>
          ))}
        </div>
        {hasData && (
          <div className="mt-4 pt-4 border-t border-trinetra-border grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
            <div className="text-trinetra-text">
              <span className="text-trinetra-muted">Most Common:</span>{' '}
              <strong className="text-white">{exec?.top_violation_type?.replace(/_/g, ' ') || 'N/A'}</strong>
              <span className="text-trinetra-muted ml-1">({exec?.top_violation_count || 0} cases)</span>
            </div>
            <div className="text-trinetra-text">
              <span className="text-trinetra-muted">Top Location:</span>{' '}
              <strong className="text-white">{exec?.top_location || 'N/A'}</strong>
            </div>
            <div className="text-trinetra-text">
              <span className="text-trinetra-muted">Top Offender:</span>{' '}
              <strong className="text-white">{exec?.top_offender || 'None recorded'}</strong>
              {exec?.top_offender && <span className="text-trinetra-muted ml-1">({exec?.top_offender_count} violations)</span>}
            </div>
          </div>
        )}
      </div>

      {/* Command Center Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Violations by Type */}
        <div className="glass rounded-xl p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-blue-400" /> Violation Intelligence
            </h2>
          </div>
          {hasData ? (
            <div className="space-y-3">
              {[
                { label: 'No Helmet', count: dash?.stats?.no_helmet || 0, color: 'bg-red-500', text: 'text-red-400' },
                { label: 'Triple Riding', count: dash?.stats?.triple_riding || 0, color: 'bg-amber-500', text: 'text-amber-400' },
                { label: 'Overloading', count: (dash?.stats?.motorcycle_overloading || 0) + (dash?.stats?.motorcycle_extreme_overloading || 0), color: 'bg-rose-500', text: 'text-rose-300' },
                { label: 'Wrong-Side Driving', count: dash?.stats?.wrong_side || 0, color: 'bg-purple-500', text: 'text-purple-400' },
              ].map(item => {
                const pct = exec!.total_violations > 0 ? ((item.count / exec!.total_violations) * 100).toFixed(1) : '0'
                return (
                  <div key={item.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className={item.text}>{item.label}</span>
                      <span className="text-white font-mono">{item.count} ({pct}%)</span>
                    </div>
                    <div className="h-2.5 bg-[#1a2040] rounded-full overflow-hidden">
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
              <Link to="/upload" className="text-blue-400 text-sm mt-2 inline-block hover:text-blue-300">Upload an image →</Link>
            </div>
          )}
        </div>

        {/* Recommendations */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-red-400" /> Enforcement Guidance
          </h2>
          <div className="space-y-3 text-sm">
            <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-3">
              <div className="text-green-400 text-xs font-semibold mb-1">HIGH CONFIDENCE</div>
              <p className="text-trinetra-text text-xs">Automated processing. Evidence captured. Ready for enforcement workflow.</p>
            </div>
            <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-lg p-3">
              <div className="text-yellow-400 text-xs font-semibold mb-1">MEDIUM CONFIDENCE</div>
              <p className="text-trinetra-text text-xs">Officer review recommended. Consider on-site verification.</p>
            </div>
            <div className="bg-orange-500/5 border border-orange-500/20 rounded-lg p-3">
              <div className="text-orange-400 text-xs font-semibold mb-1">LOW CONFIDENCE</div>
              <p className="text-trinetra-text text-xs">Manual officer review required. Do not proceed without human verification.</p>
            </div>
            <div className="mt-4 pt-4 border-t border-trinetra-border">
              <div className="text-trinetra-muted text-xs mb-2">Reliability Guide</div>
              <ul className="text-xs text-trinetra-text space-y-1">
                <li><strong className="text-green-300">High</strong> — Clear detection, strong AI confidence</li>
                <li><strong className="text-yellow-300">Medium</strong> — Moderate confidence, some uncertainty</li>
                <li><strong className="text-orange-300">Limited</strong> — Crowded scene, overlapping occupants</li>
                <li><strong className="text-red-300">Low</strong> — Low confidence, mandatory human review</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Hotspots & Offenders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Hotspots */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-red-400" /> Violation Hotspots
          </h2>
          {dash?.hotspots?.by_location && dash.hotspots.by_location.length > 0 ? (
            <div className="space-y-2">
              {dash.hotspots.by_location.slice(0, 5).map((loc, i) => (
                <div key={i} className="flex items-center justify-between bg-[#1a2040] rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5 text-red-400" />
                    <span className="text-sm text-white">{loc.location}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-trinetra-muted">{loc.types || 'Multiple'}</span>
                    <span className="text-sm font-bold text-white">{loc.count}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-trinetra-muted text-sm py-4 text-center">No hotspot data yet.</p>
          )}
          <Link to="/enforcement" className="text-xs text-blue-400 mt-3 inline-block hover:text-blue-300">
            View full hotspot analysis →
          </Link>
        </div>

        {/* Repeat Offenders */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-amber-400" /> Repeat Offenders
          </h2>
          {dash?.top_offenders && dash.top_offenders.length > 0 ? (
            <div className="space-y-2">
              {dash.top_offenders.slice(0, 5).map((o, i) => (
                <div key={i} className="flex items-center justify-between bg-[#1a2040] rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      o.risk_status === 'CRITICAL' ? 'bg-red-500' :
                      o.risk_status === 'HIGH' ? 'bg-orange-500' : 'bg-yellow-500'
                    }`} />
                    <span className="text-sm text-white">{o.vehicle_number}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-trinetra-muted">{o.total_violations} cases</span>
                    <span className={`text-xs font-semibold ${
                      o.risk_status === 'CRITICAL' ? 'text-red-400' :
                      o.risk_status === 'HIGH' ? 'text-orange-400' : 'text-yellow-400'
                    }`}>{o.risk_status}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-trinetra-muted text-sm py-4 text-center">No repeat offenders flagged.</p>
          )}
          <Link to="/enforcement" className="text-xs text-blue-400 mt-3 inline-block hover:text-blue-300">
            View all offenders →
          </Link>
        </div>
      </div>

      {/* Intelligence Pipeline */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-purple-400" /> Enforcement Intelligence Pipeline
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 text-center">
          {[
            { icon: '📷', label: 'CCTV Feed' },
            { icon: '🧠', label: 'AI Detection' },
            { icon: '⚡', label: 'Violation Engine' },
            { icon: '📊', label: 'Intel Dashboard' },
            { icon: '📱', label: 'Officer Dispatch' },
            { icon: '📄', label: 'Evidence Log' },
            { icon: '🔍', label: 'Review Queue' },
            { icon: '📋', label: 'Case Closed' },
          ].map((item, i) => (
            <div key={i} className="bg-[#1a2040] rounded-xl p-3 border border-trinetra-border">
              <div className="text-xl mb-1">{item.icon}</div>
              <div className="text-white text-xs font-semibold">{item.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Access */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { to: '/upload', icon: Camera, label: 'Analyze Image', color: 'from-red-500 to-red-700', desc: 'Upload & detect violations' },
          { to: '/enforcement', icon: Shield, label: 'Enforcement Intel', color: 'from-blue-500 to-blue-700', desc: 'Hotspots, offenders, forecasts' },
          { to: '/analytics', icon: BarChart3, label: 'Analytics', color: 'from-amber-500 to-amber-700', desc: 'Trends & breakdowns' },
          { to: '/copilot', icon: Bot, label: 'AI Copilot', color: 'from-purple-500 to-purple-700', desc: 'Ask questions in plain English' },
        ].map(item => (
          <Link key={item.to} to={item.to} className="glass rounded-xl p-4 hover:bg-[#1a2040]/80 transition-all group text-center">
            <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${item.color} flex items-center justify-center mx-auto mb-2`}>
              <item.icon className="w-4 h-4 text-white" />
            </div>
            <h3 className="font-semibold text-white text-sm group-hover:text-red-400 transition-colors">{item.label}</h3>
            <p className="text-xs text-trinetra-muted mt-0.5">{item.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
