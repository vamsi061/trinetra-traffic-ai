import { NavLink } from 'react-router-dom'
import {
  Home, Upload, FileText, BarChart3, Bot, TrafficCone,
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/records', label: 'Records', icon: FileText },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/copilot', label: 'AI Copilot', icon: Bot },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="w-64 bg-[#0d1225] border-r border-trinetra-border flex flex-col shrink-0">
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
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition-all ${
                  isActive
                    ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                    : 'text-trinetra-muted hover:text-white hover:bg-[#1a2040]'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
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

      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
