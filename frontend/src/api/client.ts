import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

export interface Detection {
  instance_id: string
  label: string
  confidence: number
  bbox: number[]
}

export interface MotorcycleRider {
  motorcycle_id: string
  motorcycle_bbox: number[]
  rider_count: number
  occupancy_estimate: string
  confirmed_count: number
  possible_count: number
  riders: string[]
  assignment_scores: Record<string, number>
}

export interface ReliabilityBadge {
  label: string
  reason: string
  color: string
}

export interface HelmetCompliance {
  status: string
  confidence_band: string
  needs_review: boolean
}

export interface Violation {
  type: string
  confidence: number
  confidence_band: string
  confidence_label: string
  description: string
  occupancy_estimate: string
  explainable_reason?: string
  human_review_status: string
  enforcement_recommendation: string
  escalation?: string
  reliability_badge: ReliabilityBadge
  helmet_compliance?: HelmetCompliance | null
  involved_objects: string[]
  severity_score?: number
  needs_review?: boolean
}

export interface OperationalIntelligence {
  mode: string
  note: string
}

export interface DetectResponse {
  success: boolean
  detections: Detection[]
  violations: Violation[]
  motorcycle_riders: MotorcycleRider[]
  risk_score?: number
  risk_status?: string
  crowded_scene?: boolean
  ai_review_recommended?: boolean
  operational_intelligence?: OperationalIntelligence
  license_plate: LicensePlate | null
  evidence_path: string | null
}

export interface LicensePlate {
  number: string
  confidence: number
}

export interface ViolationRecord {
  id: number
  vehicle_number: string
  vehicle_type: string
  violation_type: string
  confidence: number
  image_path: string
  evidence_path: string
  location?: string
  timestamp: string
}

export interface ViolationStats {
  total: number
  no_helmet: number
  triple_riding: number
  seatbelt_offence: number
  wrong_side: number
  motorcycle_overloading: number
  motorcycle_extreme_overloading: number
  unique_vehicles: number
  high_risk_offenders?: number
}

export interface AnalyticsData {
  by_type: { type: string; count: number }[]
  by_day: { day: string; count: number }[]
  by_hour: { hour: number; count: number }[]
  by_location: { location: string; count: number; types: string }[]
  repeat_offenders: { vehicle: string; count: number; types: string }[]
  monthly_trend: { month: string; count: number }[]
}

// Repeat Offender types
export interface RepeatOffender {
  vehicle_number: string
  total_violations: number
  helmet_violations: number
  overloading_violations: number
  seatbelt_violations: number
  wrong_side_violations: number
  risk_score: number
  risk_status: string
  last_violation_date: string
  first_seen_date: string
}

// Hotspot types
export interface HotspotAnalysis {
  hotspots: { location_name: string; violation_type: string; count: number; risk_level: string; last_updated: string }[]
  top_helmet_zones: { location_name: string; total: number; types: string }[]
  top_overloading_zones: { location_name: string; total: number; types: string }[]
  top_high_risk_areas: { location_name: string; total: number; types: string }[]
  by_location: { location: string; count: number; types: string }[]
  by_hour: { hour: number; count: number }[]
}

// Forecast types
export interface Forecast {
  forecast_date: string
  violation_type: string
  predicted_count: number
  confidence: number
  peak_hours: string
  recommendation: string
}

// Report types
export interface Report {
  id: number
  report_type: string
  title: string
  summary: string
  generated_at: string
  file_path: string
}

// Dashboard types
export interface EnforcementDashboard {
  stats: ViolationStats
  hotspots: HotspotAnalysis
  forecasts: Forecast[]
  top_offenders: RepeatOffender[]
}

// API functions
export async function uploadImage(file: File): Promise<DetectResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<DetectResponse>('/detect', form)
  return data
}

export async function getViolations(params?: {
  vehicle_number?: string
  violation_type?: string
  date_from?: string
  date_to?: string
  location?: string
  limit?: number
}): Promise<{ total: number; violations: ViolationRecord[] }> {
  const { data } = await api.get('/violations', { params })
  return data
}

export async function getRecentViolations(limit = 10): Promise<{ violations: ViolationRecord[] }> {
  const { data } = await api.get('/violations/recent', { params: { limit } })
  return data
}

export async function getStats(): Promise<ViolationStats> {
  const { data } = await api.get('/violations/stats')
  return data
}

export async function getAnalytics(): Promise<AnalyticsData> {
  const { data } = await api.get('/violations/analytics')
  return data
}

export function getEvidenceUrl(filename: string): string {
  return `/api/evidence/${filename}`
}

// — Intelligence API —

export async function getRepeatOffenders(limit = 20, riskStatus?: string): Promise<{ offenders: RepeatOffender[]; total: number }> {
  const { data } = await api.get('/intelligence/repeat-offenders', { params: { limit, risk_status: riskStatus } })
  return data
}

export async function searchRepeatOffender(vehicle: string): Promise<{ offenders: RepeatOffender[] }> {
  const { data } = await api.get('/intelligence/repeat-offenders/search', { params: { vehicle } })
  return data
}

export async function getHotspotAnalysis(): Promise<HotspotAnalysis> {
  const { data } = await api.get('/intelligence/hotspots')
  return data
}

export async function getForecasts(): Promise<{ forecasts: Forecast[]; total: number }> {
  const { data } = await api.get('/intelligence/forecasts')
  return data
}

export async function getTomorrowForecast(): Promise<{ forecasts: Forecast[] }> {
  const { data } = await api.get('/intelligence/forecasts/tomorrow')
  return data
}

export async function generateReport(reportType = 'daily'): Promise<{ success: boolean; report: Report }> {
  const { data } = await api.post('/intelligence/reports/generate', null, { params: { report_type: reportType } })
  return data
}

export async function getReports(): Promise<{ reports: Report[] }> {
  const { data } = await api.get('/intelligence/reports')
  return data
}

export async function getEnforcementDashboard(): Promise<EnforcementDashboard> {
  const { data } = await api.get('/intelligence/dashboard')
  return data
}

export async function copilotQuery(q: string): Promise<{ query: string; answer: string }> {
  const { data } = await api.get('/copilot/query', { params: { q } })
  return data
}

// — Executive Summary —
export interface ExecutiveSummary {
  total_violations: number
  unique_vehicles: number
  high_risk_offenders: number
  today_violations: number
  active_hotspots: number
  active_forecasts: number
  top_violation_type: string | null
  top_violation_count: number
  top_offender: string | null
  top_offender_count: number
  average_risk_score: number
  top_location: string
}

export async function getExecutiveSummary(): Promise<ExecutiveSummary> {
  const { data } = await api.get('/intelligence/executive-summary')
  return data
}

export default api
