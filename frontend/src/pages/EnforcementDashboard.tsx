import { useState, useEffect } from 'react'
import {
  AlertTriangle, TrendingUp, MapPin, Users, FileText,
  BarChart3, Clock, ShieldAlert, GitCompare,
} from 'lucide-react'
import {
  getEnforcementDashboard, getForecasts, getHotspotAnalysis,
  getRepeatOffenders, generateReport, getReports,
  type EnforcementDashboard, type Forecast, type HotspotAnalysis,
  type RepeatOffender, type Report,
} from '../api/client'

const statusColor = (s: string) =>
  s === 'CRITICAL' ? 'text-red-300 bg-red-500/20' :
  s === 'HIGH' ? 'text-orange-300 bg-orange-500/20' :
  s === 'MEDIUM' ? 'text-yellow-300 bg-yellow-500/20' :
  'text-green-300 bg-green-500/20'

export default function EnforcementDashboard() {
  const [dashboard, setDashboard] = useState<EnforcementDashboard | null>(null)
  const [forecasts, setForecasts] = useState<Forecast[]>([])
  const [hotspots, setHotspots] = useState<HotspotAnalysis | null>(null)
  const [offenders, setOffenders] = useState<RepeatOffender[]>([])
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'overview' | 'hotspots' | 'offenders' | 'forecasts' | 'reports'>('overview')
  const [reportLoading, setReportLoading] = useState(false)

  useEffect(() => {
    Promise.all([
      getEnforcementDashboard(),
      getForecasts(),
      getHotspotAnalysis(),
      getRepeatOffenders(20),
      getReports(),
    ]).then(([d, f, h, o, r]) => {
      setDashboard(d)
      setForecasts(f.forecasts)
      setHotspots(h)
      setOffenders(o.offenders)
      setReports(r.reports)
    }).finally(() => setLoading(false))
  }, [])

  const handleGenerateReport = async (type: 'daily' | 'weekly' | 'monthly') => {
    setReportLoading(true)
    try {
      await generateReport(type)
      const res = await getReports()
      setReports(res.reports)
    } finally {
      setReportLoading(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center py-20">
      <div className="w-8 h-8 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  const stats = dashboard?.stats

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <ShieldAlert className="w-6 h-6 text-red-400" />
        <h1 className="text-2xl font-bold text-white">Enforcement Intelligence</h1>
      </div>
      <p className="text-trinetra-muted text-sm -mt-3">
        Operational intelligence for traffic enforcement planning and decision support.
      </p>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass rounded-xl p-4">
          <div className="flex items-center gap-2 text-trinetra-muted text-xs mb-2">
            <AlertTriangle className="w-3.5 h-3.5" /> Total Violations
          </div>
          <div className="text-2xl font-bold text-white">{stats?.total || 0}</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="flex items-center gap-2 text-trinetra-muted text-xs mb-2">
            <Users className="w-3.5 h-3.5" /> Unique Vehicles
          </div>
          <div className="text-2xl font-bold text-white">{stats?.unique_vehicles || 0}</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="flex items-center gap-2 text-trinetra-muted text-xs mb-2">
            <ShieldAlert className="w-3.5 h-3.5" /> High-Risk Offenders
          </div>
          <div className="text-2xl font-bold text-red-400">{stats?.high_risk_offenders || 0}</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="flex items-center gap-2 text-trinetra-muted text-xs mb-2">
            <TrendingUp className="w-3.5 h-3.5" /> Today's Forecast
          </div>
          <div className="text-2xl font-bold text-amber-400">
            {forecasts.filter(f => f.forecast_date === new Date().toISOString().slice(0, 10)).length || forecasts.length}
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 border-b border-trinetra-border pb-2">
        {(['overview', 'hotspots', 'offenders', 'forecasts', 'reports'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm transition-all capitalize ${
              tab === t ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'text-trinetra-muted hover:text-white'
            }`}
          >
            {t === 'overview' && <BarChart3 className="w-4 h-4 inline mr-1.5" />}
            {t === 'hotspots' && <MapPin className="w-4 h-4 inline mr-1.5" />}
            {t === 'offenders' && <Users className="w-4 h-4 inline mr-1.5" />}
            {t === 'forecasts' && <TrendingUp className="w-4 h-4 inline mr-1.5" />}
            {t === 'reports' && <FileText className="w-4 h-4 inline mr-1.5" />}
            {t}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Most Common Violations */}
          <div className="glass rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Violation Breakdown</h3>
            <div className="space-y-3">
              {[
                { label: 'No Helmet', count: stats?.no_helmet || 0, color: 'bg-red-500' },
                { label: 'Triple Riding', count: stats?.triple_riding || 0, color: 'bg-amber-500' },
                { label: 'Overloading', count: (stats?.motorcycle_overloading || 0) + (stats?.motorcycle_extreme_overloading || 0), color: 'bg-rose-500' },
                { label: 'Wrong Side', count: stats?.wrong_side || 0, color: 'bg-purple-500' },
              ].map(item => {
                const pct = stats?.total ? ((item.count / stats.total) * 100).toFixed(1) : '0'
                return (
                  <div key={item.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-trinetra-text">{item.label}</span>
                      <span className="text-white font-mono">{item.count} ({pct}%)</span>
                    </div>
                    <div className="h-2 bg-[#1a2040] rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${item.color}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Top Offenders Preview */}
          <div className="glass rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Top Repeat Offenders</h3>
            {offenders.length === 0 ? (
              <p className="text-trinetra-muted text-sm">No repeat offenders recorded.</p>
            ) : (
              <div className="space-y-2">
                {offenders.slice(0, 5).map((o, i) => (
                  <div key={i} className="flex items-center justify-between bg-[#1a2040] rounded-lg p-3">
                    <div className="flex items-center gap-3">
                      <span className="text-trinetra-muted text-xs font-mono">#{i + 1}</span>
                      <span className="text-white font-mono text-sm">{o.vehicle_number}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-trinetra-muted">{o.total_violations} violations</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(o.risk_status)}`}>
                        {o.risk_score}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Active Hotspots */}
          <div className="glass rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Active Hotspots</h3>
            {!hotspots?.hotspots?.length ? (
              <p className="text-trinetra-muted text-sm">No hotspots recorded.</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {hotspots.hotspots.slice(0, 8).map((h, i) => (
                  <div key={i} className="flex items-center justify-between bg-[#1a2040] rounded-lg p-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <MapPin className="w-3.5 h-3.5 text-trinetra-muted shrink-0" />
                      <span className="text-white text-sm truncate">{h.location_name}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs bg-white/5 text-trinetra-muted px-2 py-0.5 rounded-full">{h.violation_type.replace('_', ' ')}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(h.risk_level)}`}>
                        {h.count}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Forecast Preview */}
          <div className="glass rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Violation Forecast</h3>
            {forecasts.length === 0 ? (
              <p className="text-trinetra-muted text-sm">No forecasts available.</p>
            ) : (
              <div className="space-y-3">
                {forecasts.slice(0, 5).map((f, i) => (
                  <div key={i} className="bg-[#1a2040] rounded-lg p-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-white text-sm capitalize">{f.violation_type.replace('_', ' ').toLowerCase()}</span>
                        <p className="text-xs text-trinetra-muted mt-0.5">{f.forecast_date} — Peak: {f.peak_hours}</p>
                      </div>
                      <div className="text-right">
                        <span className="text-lg font-bold text-amber-400">{f.predicted_count}</span>
                        <p className="text-xs text-trinetra-muted">predicted</p>
                      </div>
                    </div>
                    {f.recommendation && (
                      <p className="text-xs text-trinetra-muted mt-2 italic">{f.recommendation}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Enforcement Recommendations */}
          <div className="glass rounded-xl p-6 lg:col-span-2">
            <h3 className="text-lg font-semibold text-white mb-4">Enforcement Recommendations</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
                <div className="flex items-center gap-2 text-red-400 text-sm font-semibold mb-2">
                  <AlertTriangle className="w-4 h-4" /> Immediate Actions
                </div>
                <ul className="space-y-1 text-xs text-trinetra-text">
                  <li>• Deploy officers to top hotspot zones</li>
                  <li>• Flag high-risk repeat offenders</li>
                  <li>• Increase patrols during peak hours</li>
                </ul>
              </div>
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                <div className="flex items-center gap-2 text-amber-400 text-sm font-semibold mb-2">
                  <TrendingUp className="w-4 h-4" /> Short-Term Planning
                </div>
                <ul className="space-y-1 text-xs text-trinetra-text">
                  <li>• Schedule enforcement drives for tomorrow's forecasted hotspots</li>
                  <li>• Prioritize repeat offenders for officer follow-up</li>
                  <li>• Conduct targeted helmet compliance drives</li>
                </ul>
              </div>
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
                <div className="flex items-center gap-2 text-blue-400 text-sm font-semibold mb-2">
                  <BarChart3 className="w-4 h-4" /> Strategic
                </div>
                <ul className="space-y-1 text-xs text-trinetra-text">
                  <li>• Analyze monthly trends for resource allocation</li>
                  <li>• Identify emerging violation patterns</li>
                  <li>• Deploy predictive enforcement units</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Hotspots Tab */}
      {tab === 'hotspots' && (
        <div className="space-y-6">
          {/* By Location */}
          <div className="glass rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Violations by Location</h3>
            {!hotspots?.by_location?.length ? (
              <p className="text-trinetra-muted">No location data available.</p>
            ) : (
              <div className="space-y-2">
                {hotspots.by_location.map((loc, i) => (
                  <div key={i} className="flex items-center justify-between bg-[#1a2040] rounded-lg p-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <MapPin className="w-4 h-4 text-red-400 shrink-0" />
                      <span className="text-white text-sm">{loc.location}</span>
                      {loc.types && (
                        <span className="text-xs text-trinetra-muted truncate">{loc.types.replace(/,/g, ', ')}</span>
                      )}
                    </div>
                    <span className="text-white font-bold">{loc.count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* By Hour */}
          <div className="glass rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Violations by Hour</h3>
            {!hotspots?.by_hour?.length ? (
              <p className="text-trinetra-muted">No hourly data available.</p>
            ) : (
              <div className="grid grid-cols-6 sm:grid-cols-12 gap-2">
                {hotspots.by_hour.map(h => {
                  const maxCount = Math.max(...hotspots.by_hour.map(x => x.count))
                  const height = maxCount > 0 ? (h.count / maxCount) * 100 : 0
                  return (
                    <div key={h.hour} className="flex flex-col items-center gap-1">
                      <div className="w-full bg-[#1a2040] rounded-full overflow-hidden" style={{ height: 48 }}>
                        <div
                          className="bg-gradient-to-t from-red-500 to-red-400 w-full rounded-full transition-all"
                          style={{ height: `${height}%`, marginTop: `${100 - height}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-trinetra-muted">{h.hour}:00</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* High Risk Zones */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="glass rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-3">Top Helmet Violation Zones</h3>
              {!hotspots?.top_helmet_zones?.length ? (
                <p className="text-trinetra-muted text-xs">No data</p>
              ) : (
                <div className="space-y-2">
                  {hotspots.top_helmet_zones.slice(0, 5).map((z, i) => (
                    <div key={i} className="flex justify-between text-sm">
                      <span className="text-trinetra-text">{z.location_name}</span>
                      <span className="text-white font-mono">{z.total}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="glass rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-3">Top Overloading Zones</h3>
              {!hotspots?.top_overloading_zones?.length ? (
                <p className="text-trinetra-muted text-xs">No data</p>
              ) : (
                <div className="space-y-2">
                  {hotspots.top_overloading_zones.slice(0, 5).map((z, i) => (
                    <div key={i} className="flex justify-between text-sm">
                      <span className="text-trinetra-text">{z.location_name}</span>
                      <span className="text-white font-mono">{z.total}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Offenders Tab */}
      {tab === 'offenders' && (
        <div className="glass rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Repeat Offender Intelligence</h3>
          {offenders.length === 0 ? (
            <p className="text-trinetra-muted">No repeat offenders recorded.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-trinetra-muted border-b border-trinetra-border">
                    <th className="text-left py-3 px-2">Vehicle</th>
                    <th className="text-center py-3 px-2">Total</th>
                    <th className="text-center py-3 px-2">Helmet</th>
                    <th className="text-center py-3 px-2">Overload</th>
                    <th className="text-center py-3 px-2">Wrong Side</th>
                    <th className="text-center py-3 px-2">Risk Score</th>
                    <th className="text-center py-3 px-2">Status</th>
                    <th className="text-right py-3 px-2">Last Seen</th>
                  </tr>
                </thead>
                <tbody>
                  {offenders.map((o, i) => (
                    <tr key={i} className="border-b border-trinetra-border/50 hover:bg-[#1a2040]/50">
                      <td className="py-3 px-2 text-white font-mono">{o.vehicle_number}</td>
                      <td className="py-3 px-2 text-center text-white">{o.total_violations}</td>
                      <td className="py-3 px-2 text-center text-trinetra-text">{o.helmet_violations}</td>
                      <td className="py-3 px-2 text-center text-trinetra-text">{o.overloading_violations}</td>
                      <td className="py-3 px-2 text-center text-trinetra-text">{o.wrong_side_violations}</td>
                      <td className="py-3 px-2 text-center font-bold text-white">{o.risk_score}</td>
                      <td className="py-3 px-2 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(o.risk_status)}`}>
                          {o.risk_status}
                        </span>
                      </td>
                      <td className="py-3 px-2 text-right text-trinetra-muted text-xs">{o.last_violation_date?.slice(0, 10)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Forecasts Tab */}
      {tab === 'forecasts' && (
        <div className="space-y-6">
          <div className="glass rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Predicted Violations</h3>
            {forecasts.length === 0 ? (
              <p className="text-trinetra-muted">No forecasts available. Generate by uploading violations.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {forecasts.map((f, i) => (
                  <div key={i} className="bg-[#1a2040] rounded-xl p-4 border border-trinetra-border">
                    <div className="flex justify-between items-start mb-3">
                      <span className="text-xs text-trinetra-muted">{f.forecast_date}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${f.confidence >= 0.7 ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'}`}>
                        {(f.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                    <div className="text-lg font-bold text-white capitalize mb-1">
                      {f.violation_type.replace('_', ' ').toLowerCase()}
                    </div>
                    <div className="text-3xl font-bold text-amber-400 mb-2">{f.predicted_count}</div>
                    <div className="flex items-center gap-1 text-xs text-trinetra-muted mb-2">
                      <Clock className="w-3 h-3" /> Peak: {f.peak_hours}
                    </div>
                    <div className="text-xs text-trinetra-muted bg-[#0d1225] rounded-lg p-2">
                      {f.recommendation}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Reports Tab */}
      {tab === 'reports' && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-3">
            <button onClick={() => handleGenerateReport('daily')} disabled={reportLoading}
              className="px-5 py-2.5 bg-red-500 hover:bg-red-600 disabled:opacity-50 rounded-lg text-white text-sm font-medium transition-colors flex items-center gap-2"
            >
              <FileText className="w-4 h-4" /> Generate Daily Report
            </button>
            <button onClick={() => handleGenerateReport('weekly')} disabled={reportLoading}
              className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 rounded-lg text-white text-sm font-medium transition-colors flex items-center gap-2"
            >
              <FileText className="w-4 h-4" /> Generate Weekly Report
            </button>
            <button onClick={() => handleGenerateReport('monthly')} disabled={reportLoading}
              className="px-5 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 rounded-lg text-white text-sm font-medium transition-colors flex items-center gap-2"
            >
              <FileText className="w-4 h-4" /> Generate Monthly Report
            </button>
          </div>

          <div className="glass rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Generated Reports</h3>
            {reports.length === 0 ? (
              <p className="text-trinetra-muted">No reports generated yet.</p>
            ) : (
              <div className="space-y-2">
                {reports.map((r, i) => (
                  <div key={i} className="flex items-center justify-between bg-[#1a2040] rounded-lg p-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-trinetra-muted shrink-0" />
                        <span className="text-white text-sm truncate">{r.title}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${
                          r.report_type === 'daily' ? 'bg-red-500/10 text-red-300' :
                          r.report_type === 'weekly' ? 'bg-amber-500/10 text-amber-300' :
                          'bg-blue-500/10 text-blue-300'
                        }`}>{r.report_type}</span>
                      </div>
                      <p className="text-xs text-trinetra-muted mt-1 truncate">{r.summary}</p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs text-trinetra-muted">{r.generated_at?.slice(0, 10)}</span>
                      {r.file_path && (
                        <a href={`/api/evidence/../${r.file_path}`} target="_blank" rel="noopener noreferrer"
                          className="px-3 py-1.5 bg-[#243050] hover:bg-[#2f4060] rounded-lg text-xs text-white transition-colors"
                        >
                          Download
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}


    </div>
  )
}
