import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  Home, Upload, FileText, BarChart3, Bot, TrafficCone, Menu, X, ShieldAlert, Radio, CheckSquare, Cpu, TrendingUp,
  Settings, Key, HardDrive, Loader2, Activity, CheckCircle, Download, XCircle, AlertTriangle,
  Eye, EyeOff, Wifi, WifiOff,
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

/* ─── Engine icons ─── */
const ENGINE_META: Record<string, { icon: React.ReactNode; short: string }> = {
  yolo: { icon: <Activity className="w-5 h-5" />, short: 'YOLOv8' },
  locateanything: { icon: <Wifi className="w-5 h-5" />, short: 'HF Inference' },
  owlvit_local: { icon: <HardDrive className="w-5 h-5" />, short: 'OwlViT Local' },
  locateanything_gradio: { icon: <WifiOff className="w-5 h-5" />, short: 'Gradio' },
}

/* ─── Configuration Modal ─── */
function ConfigModal({ close }: { close: () => void }) {
  const [status, setStatus] = useState<DetectStatus | null>(null)
  const [compat, setCompat] = useState<OwlVitCompat | null>(null)
  const [hfTokenInput, setHfTokenInput] = useState('')
  const [hfVisible, setHfVisible] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [downloadResult, setDownloadResult] = useState<OwlVitDownloadResult | null>(null)
  const [savingToken, setSavingToken] = useState(false)
  const [tokenSaved, setTokenSaved] = useState<'idle' | 'saved' | 'error'>('idle')

  const refresh = () => {
    getDetectStatus().then(setStatus).catch(() => {})
    checkOwlvitCompat().then(setCompat).catch(() => {})
  }

  useEffect(() => { refresh() }, [])

  const handleSaveToken = async () => {
    if (!hfTokenInput.trim()) return
    setSavingToken(true)
    setTokenSaved('idle')
    try {
      await setHfToken(hfTokenInput.trim())
      setTokenSaved('saved')
      setHfTokenInput('')
      refresh()
      setTimeout(() => setTokenSaved('idle'), 3000)
    } catch {
      setTokenSaved('error')
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
      setDownloadResult({ success: false, message: 'Download failed. Check server logs.', model_path: '', model_size_mb: 0 })
    } finally {
      setDownloading(false)
    }
  }

  /* ─── Engine card helper ─── */
  function EngineCard({
    id, label, description, ready, reason, action,
  }: {
    id: string; label: string; description: string
    ready: boolean; reason: string
    action?: React.ReactNode
  }) {
    const meta = ENGINE_META[id]
    return (
      <div className={`rounded-xl border p-4 ${
        ready ? 'border-green-500/30 bg-green-500/[0.03]' : 'border-yellow-500/30 bg-yellow-500/[0.03]'
      }`}>
        <div className="flex items-start gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
            ready ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'
          }`}>
            {meta?.icon || <Cpu className="w-5 h-5" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-0.5">
              <span className="text-sm font-semibold text-white">{label}</span>
              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                ready ? 'bg-green-500/10 text-green-300' : 'bg-yellow-500/10 text-yellow-300'
              }`}>
                {meta?.short || id}
              </span>
              {ready ? (
                <span className="flex items-center gap-1 text-[11px] text-green-400 ml-auto">
                  <CheckCircle className="w-3 h-3" /> Ready
                </span>
              ) : (
                <span className="flex items-center gap-1 text-[11px] text-yellow-400 ml-auto">
                  <AlertTriangle className="w-3 h-3" /> Not Ready
                </span>
              )}
            </div>
            <p className="text-[11px] text-trinetra-muted leading-relaxed mb-2">{description}</p>
            <div className="flex items-center gap-1.5 text-[11px]">
              {ready ? (
                <span className="text-green-500/80">No issues</span>
              ) : (
                <>
                  <XCircle className="w-3 h-3 text-yellow-400 shrink-0" />
                  <span className="text-yellow-400/90">{reason}</span>
                </>
              )}
            </div>
            {action && <div className="mt-3">{action}</div>}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={close}>
      <div className="absolute inset-0 bg-black/70" />
      <div
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-[#0d1225] border border-trinetra-border rounded-2xl shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-[#0d1225] z-10 flex items-center justify-between p-5 border-b border-trinetra-border rounded-t-2xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center">
              <Settings className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Detection Engine Configuration</h2>
              <p className="text-xs text-trinetra-muted">Manage detection engines, tokens &amp; models</p>
            </div>
          </div>
          <button onClick={close} className="p-2 text-trinetra-muted hover:text-white rounded-lg hover:bg-[#1a2040] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">

          {/* ─── Engine Cards ─── */}

          {/* 1. YOLOv8 */}
          <EngineCard
            id="yolo"
            label="YOLOv8 (COCO)"
            description="Fast, built-in object detection. Supports car, motorcycle, person, bus, truck. Limited to 80 COCO classes."
            ready={status?.yolo_available ?? false}
            reason="YOLO model file not found. Ensure yolov8s.pt is present in the backend directory."
          />

          {/* 2. LocateAnything (HF Inference API) */}
          <EngineCard
            id="locateanything"
            label="OwlViT via HF Inference API"
            description="Zero-shot detection. Can detect any object by name — no training needed. Requires HuggingFace API token. Fast and serverless."
            ready={status?.hf_token_set ?? false}
            reason={!status?.hf_token_set ? 'HF token not set. Enter your token below to enable.' : ''}
            action={
              <div>
                <label className="text-[11px] text-trinetra-muted block mb-1.5">
                  <Key className="w-3 h-3 inline mr-1" />
                  HuggingFace API Token
                  {status?.hf_token_set && (
                    <span className="text-green-500 ml-2">(currently set — enter new to replace)</span>
                  )}
                </label>
                <div className="flex gap-1.5">
                  <div className="relative flex-1">
                    <input
                      type={hfVisible ? 'text' : 'password'}
                      value={hfTokenInput}
                      onChange={e => setHfTokenInput(e.target.value)}
                      placeholder={status?.hf_token_set ? 'Enter new token to replace' : 'hf_...'}
                      className="w-full px-3 py-2 pr-8 rounded-lg bg-[#1a2040] border border-trinetra-border text-white text-xs placeholder-trinetra-muted/50 focus:outline-none focus:border-red-500/50"
                    />
                    <button
                      type="button"
                      onClick={() => setHfVisible(!hfVisible)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-trinetra-muted hover:text-white"
                    >
                      {hfVisible ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  <button
                    onClick={handleSaveToken}
                    disabled={savingToken || !hfTokenInput.trim()}
                    className="px-3 py-2 rounded-lg bg-red-500/10 text-red-300 border border-red-500/30 hover:bg-red-500/20 disabled:opacity-50 text-xs font-medium whitespace-nowrap"
                  >
                    {savingToken ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Save Token'}
                  </button>
                </div>
                {tokenSaved === 'saved' && <p className="text-[11px] text-green-500 mt-1.5">Token saved successfully!</p>}
                {tokenSaved === 'error' && <p className="text-[11px] text-red-500 mt-1.5">Failed to save token. Check server logs.</p>}
                <p className="text-[10px] text-trinetra-muted mt-2">
                  Get your free token at{' '}
                  <a href="https://huggingface.co/settings/tokens" target="_blank" rel="noopener noreferrer"
                     className="text-blue-400 underline">huggingface.co/settings/tokens</a>
                  . Token is stored in memory for the session only.
                </p>
              </div>
            }
          />

          {/* 3. OwlViT Local */}
          <EngineCard
            id="owlvit_local"
            label="OwlViT Local (Transformers)"
            description="Runs Google's OwlViT zero-shot model locally. No internet needed after download. Supports GPU acceleration if available."
            ready={status?.owlvit_ready ?? false}
            reason={
              !compat ? 'Checking compatibility...' :
              !compat.torch_installed ? 'PyTorch not installed. Run: pip install torch' :
              !compat.transformers_installed ? 'Transformers not installed. Run: pip install transformers' :
              !status?.owlvit_ready ? 'Model not downloaded. Download below (~380MB).' :
              ''
            }
            action={
              compat && (compat.torch_installed && compat.transformers_installed) && !status?.owlvit_ready ? (
                <div>
                  <div className="flex flex-wrap gap-3 mb-3 text-[11px] text-trinetra-muted">
                    <span className={`flex items-center gap-1 ${compat.torch_installed ? 'text-green-400' : 'text-red-400'}`}>
                      <CheckCircle className="w-3 h-3" /> PyTorch
                    </span>
                    <span className={`flex items-center gap-1 ${compat.transformers_installed ? 'text-green-400' : 'text-red-400'}`}>
                      <CheckCircle className="w-3 h-3" /> Transformers
                    </span>
                    <span className="flex items-center gap-1 text-blue-400">
                      <Cpu className="w-3 h-3" /> {compat.cuda_available ? compat.gpu_name : 'CPU mode'}
                    </span>
                    <span className="text-trinetra-muted">RAM: {(compat.estimated_ram_mb / 1024).toFixed(1)}GB</span>
                    <span className="text-trinetra-muted">Size: ~{compat.download_size_mb}MB</span>
                  </div>
                  <button
                    onClick={handleDownload}
                    disabled={downloading}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-500/10 text-blue-300 border border-blue-500/30 hover:bg-blue-500/20 disabled:opacity-50 text-xs font-medium"
                  >
                    {downloading ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Download className="w-3.5 h-3.5" />
                    )}
                    {downloading ? 'Downloading model...' : `Download OwlViT Model (${compat.download_size_mb}MB)`}
                  </button>
                  {downloadResult && (
                    <p className={`text-[11px] mt-1.5 ${downloadResult.success ? 'text-green-500' : 'text-red-500'}`}>
                      {downloadResult.message}
                    </p>
                  )}
                </div>
              ) : !compat ? (
                <div className="flex items-center gap-2 text-xs text-trinetra-muted">
                  <Loader2 className="w-3 h-3 animate-spin" /> Checking compatibility...
                </div>
              ) : (
                <div className="flex flex-wrap gap-2 text-[11px] text-trinetra-muted">
                  <span className={`flex items-center gap-1 ${compat.torch_installed ? 'text-green-400' : 'text-red-400'}`}>
                    {compat.torch_installed ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />} PyTorch
                  </span>
                  <span className={`flex items-center gap-1 ${compat.transformers_installed ? 'text-green-400' : 'text-red-400'}`}>
                    {compat.transformers_installed ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />} Transformers
                  </span>
                </div>
              )
            }
          />

          {/* 4. LocateAnything (Gradio) */}
          <EngineCard
            id="locateanything_gradio"
            label="LocateAnything (Gradio Spaces)"
            description="NVIDIA's zero-shot model hosted on HuggingFace Spaces. Uses GPU on HF infrastructure. Can be slow or fail if GPU quota is exceeded."
            ready={status?.gradio_available ?? false}
            reason={!status?.gradio_available
              ? 'Gradio spaces previously failed (likely GPU quota exceeded). Try again later. No action needed from your side.'
              : 'Gradio spaces are available but may be slow due to GPU contention.'}
          />

          {/* ─── Summary ─── */}
          <div className="rounded-xl border border-trinetra-border bg-[#0d1225] p-4">
            <div className="flex items-center gap-2 text-xs text-trinetra-muted mb-3">
              <Activity className="w-4 h-4" />
              <span className="font-semibold text-white">Engine Selection Priority</span>
            </div>
            <p className="text-[11px] text-trinetra-muted leading-relaxed">
              When set to <strong className="text-white">Auto</strong>, the system tries engines in this order:
              <strong className="text-green-400"> HF Inference API</strong> (fastest) →
              <strong className="text-white"> YOLOv8</strong> → <strong className="text-blue-400">OwlViT Local</strong> →
              <strong className="text-yellow-400"> Gradio</strong> (slowest).
              The first engine that returns results is used.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-[#0d1225] border-t border-trinetra-border p-4 flex justify-end rounded-b-2xl">
          <button
            onClick={close}
            className="px-5 py-2 bg-red-500/10 text-red-300 border border-red-500/30 rounded-lg hover:bg-red-500/20 transition-colors text-sm font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [configOpen, setConfigOpen] = useState(false)
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
      {/* ─── Config Modal ─── */}
      {configOpen && <ConfigModal close={() => setConfigOpen(false)} />}

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

        {/* Config button at bottom */}
        <div className="border-t border-trinetra-border">
          <button
            onClick={() => setConfigOpen(true)}
            className="flex items-center gap-3 w-full px-4 py-3 text-sm text-trinetra-muted hover:text-white hover:bg-[#1a2040] transition-colors"
          >
            <Settings className="w-4 h-4" />
            Engine Configuration
          </button>
        </div>

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
        <button
          onClick={() => setConfigOpen(true)}
          className="p-2 text-trinetra-muted hover:text-white"
        >
          <Settings className="w-5 h-5" />
        </button>
      </header>

      {/* ─── Mobile Drawer ─── */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSidebarOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-72 bg-[#0d1225] border-r border-trinetra-border flex flex-col">
            <div className="p-4 border-b border-trinetra-border flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center">
                  <TrafficCone className="w-4 h-4 text-white" />
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
            <div className="border-t border-trinetra-border">
              <button
                onClick={() => { setSidebarOpen(false); setConfigOpen(true) }}
                className="flex items-center gap-3 w-full px-4 py-3 text-sm text-trinetra-muted hover:text-white hover:bg-[#1a2040] transition-colors"
              >
                <Settings className="w-4 h-4" />
                Engine Configuration
              </button>
            </div>
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
          {navItems.concat({ to: '/config', label: 'Config', icon: Settings }).map(item => {
            const isActive = item.to === '/config' ? false : (location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to)))
            if (item.to === '/config') {
              return (
                <button key="config-btn" onClick={() => setConfigOpen(true)}
                  className="flex flex-col items-center gap-0.5 px-2 py-1.5 text-xs text-trinetra-muted transition-colors"
                >
                  <Settings className="w-4 h-4" />
                  <span className="text-[10px]">Config</span>
                </button>
              )
            }
            return (
              <NavLink key={item.to} to={item.to} end={item.to === '/'}
                className={`flex flex-col items-center gap-0.5 px-2 py-1.5 text-xs transition-colors ${
                  isActive ? 'text-red-400' : 'text-trinetra-muted'
                }`}
              >
                <item.icon className="w-4 h-4" />
                <span className="text-[10px]">{item.label === 'Intel Center' ? 'Intel' : item.label}</span>
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
