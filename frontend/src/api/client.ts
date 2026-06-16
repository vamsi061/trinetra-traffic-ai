import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

export interface Detection {
  label: string
  confidence: number
  bbox: number[]
}

export interface Violation {
  type: string
  confidence: number
  description: string
}

export interface LicensePlate {
  number: string
  confidence: number
}

export interface DetectResponse {
  success: boolean
  detections: Detection[]
  violations: Violation[]
  license_plate: LicensePlate | null
  evidence_path: string | null
}

export interface ViolationRecord {
  id: number
  vehicle_number: string
  vehicle_type: string
  violation_type: string
  confidence: number
  image_path: string
  evidence_path: string
  timestamp: string
}

export interface ViolationStats {
  total: number
  no_helmet: number
  triple_riding: number
  seatbelt_offence: number
  wrong_side: number
  unique_vehicles: number
}

export interface AnalyticsData {
  by_type: { type: string; count: number }[]
  by_day: { day: string; count: number }[]
  repeat_offenders: { vehicle: string; count: number; types: string }[]
  monthly_trend: { month: string; count: number }[]
}

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

export default api
