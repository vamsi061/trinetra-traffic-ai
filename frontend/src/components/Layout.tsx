import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  Home, Upload, FileText, BarChart3, Bot, TrafficCone, Menu, X,
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/records', label: 'Records', icon: FileText },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/copilot', label: 'AI Copilot', icon: Bot },
]

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
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'} className={navLinkClass}>
              <item.icon className="w-4 h-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-trinetra-border">
          <div className="flex items-center gap-2 text-xs text-trinetra-muted">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            System Online
          </div>
          <p className="text-xs text-trinetra-muted mt-1">v2.0.0</p>
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
        <div className="w-9" /> {/* spacer */}
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
            <nav className="flex-1 p-4 space-y-1">
              {navItems.map(item => (
                <NavLink key={item.to} to={item.to} end={item.to === '/'} className={navLinkClass}>
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </NavLink>
              ))}
            </nav>
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
