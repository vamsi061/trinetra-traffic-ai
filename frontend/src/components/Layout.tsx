import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  Home, Upload, FileText, BarChart3, Bot, TrafficCone, Menu, X, ShieldAlert, Radio, CheckSquare, Cpu, TrendingUp,
  Settings, Key, HardDrive, Loader2, Activity, CheckCircle, Download,
} from 'lucide-react'
import { getDetectStatus, checkOwlvitCompat, downloadOwlvitModel, setHfToken } from '../api/client'
import type { DetectStatus, OwlVitCompat, OwlVitDownloadResult } from '../api/client'

const navItems = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/validation', label: 'Validation', icon: CheckSquare },
  { to: '/records', label: 'Records', icon: FileText },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/enforcement', label: 'Enforcement', icon: ShieldAlert },
  { to: '/intel-center', label: 'Intel Center', icon: Radio },
  { to: '/copilot', label: 'AI Copilot', icon: Bot },
  { to: '/architecture', label: 'Architecture', icon: Cpu },
  { to: '/impact', label: 'Impact', icon: TrendingUp },
]

function SidebarConfig() {
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState<DetectStatus | null>(null)
  const [compat, setCompat] = useState<OwlVitCompat | null>(null)
  const [hfTokenInput, setHfTokenInput] = useState('')
  const [downloading, setDownloading] = useState(false)
  const [downloadResult, setDownloadResult] = useState<OwlVitDownloadResult | null>(null)
  const [savingToken, setSavingToken] = useState(false)
  const [tokenSaved, setTokenSaved] = useState(false)

  const refresh = () => {
    getDetectStatus().then(setStatus).catch(() => {})
    checkOwlvitCompat().then(setCompat).catch(() => {})
  }

  useEffect(() => {
    if (open) refresh()
  }, [open])

  const handleSaveToken = async () => {
    if (!hfTokenInput.trim()) return
    setSavingToken(true)
    try {
      await setHfToken(hfTokenInput.trim())
      setTokenSaved(true)
      setTimeout(() => setTokenSaved(false), 3000)
      refresh()
    } catch {
      setTokenSaved(false)
    } finally {
      setSavingToken(false)
    }
  }

  const handleDownload = async () => {
    setDownloading(true)
    setDownloadResult(null)
    try {
      const res = await downloadOwlvitModel()
      setDownloadResult(res)
      refresh()
    } catch {
      setDownloadResult({ success: false, message: 'Download failed', model_path: '', model_size_mb: 0 })
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="border-t border-trinetra-border">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full px-4 py-3 text-sm text-trinetra-muted hover:text-white transition-colors"
      >
        <span className="flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Configuration
        </span>
        <span className={`text-xs transition-transform ${open ? 'rotate-90' : ''}`}>›</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4 text-xs">
          {/* ─── HF Token ─── */}
          <div>
            <label className="flex items-center gap-1.5 text-trinetra-muted mb-1.5">
              <Key className="w-3 h-3" />
              HuggingFace Token
              {status?.hf_token_set && (
                <span className="text-green-500 flex items-center gap-0.5">
                  <CheckCircle className="w-2.5 h-2.5" /> Saved
                </span>
              )}
            </label>
            <div className="flex gap-1">
              <input
                type="password"
                value={hfTokenInput}
                onChange={e => setHfTokenInput(e.target.value)}
                placeholder={status?.hf_token_set ? 'Token set (enter to replace)' : 'hf_...'}
                className="flex-1 px-2 py-1.5 rounded bg-[#1a2040] border border-trinetra-border text-white text-xs placeholder-trinetra-muted/50 focus:outline-none focus:border-red-500/50"
              />
              <button
                onClick={handleSaveToken}
                disabled={savingToken || !hfTokenInput.trim()}
                className="px-2 py-1.5 rounded bg-red-500/10 text-red-300 border border-red-500/30 hover:bg-red-500/20 disabled:opacity-50"
              >
                {savingToken ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Save'}
              </button>
            </div>
            {tokenSaved && <p className="text-green-500 mt-1">Token saved!</p>}
          </div>

          {/* ─── OwlViT Local Model ─── */}
          <div>
            <label className="flex items-center gap-1.5 text-trinetra-muted mb-1.5">
              <HardDrive className="w-3 h-3" />
              Local OwlViT Model
              {status?.owlvit_ready ? (
                <span className="text-green-500 flex items-center gap-0.5">
                  <CheckCircle className="w-2.5 h-2.5" /> Ready
                </span>
              ) : compat?.can_run ? (
                <span className="text-yellow-500">Not downloaded</span>
              ) : (
                <span className="text-red-500">Cannot run</span>
              )}
            </label>
            {compat && (
              <div className="space-y-1 text-trinetra-muted mb-2">
                <p>PyTorch: {compat.torch_installed ? '✓' : '✗'} | GPU: {compat.cuda_available ? compat.gpu_name : 'CPU'}</p>
                <p>RAM: {(compat.estimated_ram_mb / 1024).toFixed(1)}GB | Size: ~{compat.download_size_mb}MB</p>
              </div>
            )}
            {compat?.can_run && !status?.owlvit_ready && (
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="flex items-center gap-1.5 px-2 py-1.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/30 hover:bg-blue-500/20 w-full justify-center disabled:opacity-50"
              >
                {downloading ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Download className="w-3 h-3" />
                )}
                {downloading ? 'Downloading...' : `Download Model (${compat.download_size_mb}MB)`}
              </button>
            )}
            {downloadResult && (
              <p className={`mt-1 ${downloadResult.success ? 'text-green-500' : 'text-red-500'}`}>
                {downloadResult.message}
              </p>
            )}
          </div>

          {/* ─── Engine Status ─── */}
          <div>
            <label className="flex items-center gap-1.5 text-trinetra-muted mb-1.5">
              <Activity className="w-3 h-3" />
              Engine Status
            </label>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full ${status?.yolo_available ? 'bg-green-400' : 'bg-red-400'}`} />
                <span>YOLOv8: {status?.yolo_available ? 'Ready' : 'Unavailable'}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full ${status?.hf_token_set ? 'bg-green-400' : 'bg-yellow-400'}`} />
                <span>LocateAnything (HF API): {status?.hf_token_set ? 'Token set' : 'No token'}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full ${status?.owlvit_ready ? 'bg-green-400' : status?.owlvit_can_run ? 'bg-yellow-400' : 'bg-red-400'}`} />
                <span>OwlViT Local: {status?.owlvit_ready ? 'Ready' : status?.owlvit_can_run ? 'Not downloaded' : 'Cannot run'}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full ${status?.gradio_available ? 'bg-green-400' : 'bg-red-400'}`} />
                <span>LocateAnything (Gradio): {status?.gradio_available ? 'Available' : 'Unavailable'}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  useEffect(() => { setSidebarOpen(false) }, [location.pathname])

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition-all ${
      isActive
        ? 'bg-red-500/10 text-red-400 border border-red-500/20'
        : 'text-trinetra-muted hover:text-white hover:bg-[#1a2040]'
    }`

  return (
    <div className="min-h-screen bg-[#0a0e17]">
      {/* ─── Desktop Sidebar ─── */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:fixed lg:inset-y-0 bg-[#0d1225] border-r border-trinetra-border z-30">
        <div className="p-6 border-b border-trinetra-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center">
              <TrafficCone className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">TRINETRA</h1>
              <p className="text-xs text-trinetra-muted">AI Enforcement</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'} className={navLinkClass}>
              <item.icon className="w-4 h-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        {/* Configuration section at bottom */}
        <SidebarConfig />
        <div className="p-4 border-t border-trinetra-border">
          <div className="flex items-center gap-2 text-xs text-trinetra-muted">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            System Online
          </div>
          <p className="text-xs text-trinetra-muted mt-1">v3.0.0</p>
        </div>
      </aside>

      {/* ─── Mobile Header ─── */}
      <header className="lg:hidden flex items-center justify-between px-4 py-3 bg-[#0d1225] border-b border-trinetra-border sticky top-0 z-30">
        <button onClick={() => setSidebarOpen(true)} className="p-2 text-trinetra-muted hover:text-white">
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center">
            <TrafficCone className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-bold text-white">TRINETRA</span>
        </div>
        <div className="w-9" />
      </header>

      {/* ─── Mobile Drawer ─── */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSidebarOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-72 bg-[#0d1225] border-r border-trinetra-border flex flex-col">
            <div className="p-4 border-b border-trinetra-border flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center">
                  <TrafficCone className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-base font-bold text-white">TRINETRA</h1>
                  <p className="text-xs text-trinetra-muted">AI Enforcement</p>
                </div>
              </div>
              <button onClick={() => setSidebarOpen(false)} className="p-2 text-trinetra-muted hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
              {navItems.map(item => (
                <NavLink key={item.to} to={item.to} end={item.to === '/'} className={navLinkClass}>
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <SidebarConfig />
            <div className="p-4 border-t border-trinetra-border">
              <div className="flex items-center gap-2 text-xs text-trinetra-muted">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                System Online
              </div>
            </div>
          </aside>
        </div>
      )}

      {/* ─── Main Content ─── */}
      <main className="lg:pl-64">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-8">
          {children}
        </div>
      </main>

      {/* ─── Mobile Bottom Nav ─── */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-[#0d1225] border-t border-trinetra-border z-30">
        <div className="flex items-center justify-around py-1">
          {navItems.map(item => {
            const isActive = location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to))
            return (
              <NavLink key={item.to} to={item.to} end={item.to === '/'}
                className={`flex flex-col items-center gap-0.5 px-2 py-1.5 text-xs transition-colors ${
                  isActive ? 'text-red-400' : 'text-trinetra-muted'
                }`}
              >
                <item.icon className="w-4 h-4" />
                <span className="text-[10px]">{item.label}</span>
              </NavLink>
            )
          })}
        </div>
      </nav>

      {/* Spacer for mobile bottom nav */}
      <div className="lg:hidden h-14" />
    </div>
  )
}
