import { useState } from 'react'
import { Bot, Send, User, Trash2 } from 'lucide-react'
import { getViolations, getAnalytics, getStats } from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const HELPER_TEXT = `I can answer questions like:
• Show helmet violations
• Show triple riding cases
• Show repeat offenders
• Show violation statistics
• Show violations today
• Show monthly trend
• Show records for vehicle [number]
• Show highest confidence violations`

async function processQuery(query: string): Promise<string> {
  const q = query.toLowerCase().trim()

  if (!q) return 'Please ask a question about traffic violations.'
  if (['hi', 'hello', 'hey'].includes(q)) {
    const stats = await getStats()
    return `Hello! I am TRINETRA AI Copilot. There are **${stats.total}** violations recorded. Try asking about helmet violations, repeat offenders, or statistics.`
  }
  if (q.includes('help')) return HELPER_TEXT

  if (q.includes('statistics') || q.includes('stats') || q.includes('summary')) {
    const stats = await getStats()
    return [
      `**Total Violations:** ${stats.total}`,
      `**No Helmet:** ${stats.no_helmet}`,
      `**Triple Riding:** ${stats.triple_riding}`,
      `**Unique Vehicles:** ${stats.unique_vehicles}`,
    ].join('\n')
  }

  if (q.includes('helmet') || q.includes('no helmet')) {
    const res = await getViolations({ violation_type: 'NO_HELMET', limit: 100 })
    if (q.includes('today')) {
      const today = new Date().toISOString().slice(0, 10)
      const todayV = res.violations.filter(v => v.timestamp.startsWith(today))
      return todayV.length ? `**${todayV.length}** helmet violations recorded today.` : `No helmet violations today. Total: **${res.total}**.`
    }
    return res.total > 0
      ? `Found **${res.total}** helmet violations.\n` + res.violations.slice(0, 5).map(v => `• ${v.vehicle_number || 'Unknown'} (${v.timestamp.slice(0, 10)})`).join('\n')
      : 'No helmet violations found.'
  }

  if (q.includes('triple') || q.includes('triple riding')) {
    const res = await getViolations({ violation_type: 'TRIPLE_RIDING', limit: 100 })
    return `Found **${res.total}** triple riding violations.`
  }

  if (q.includes('repeat') || q.includes('top') || q.includes('offender')) {
    const analytics = await getAnalytics()
    const offenders = analytics.repeat_offenders.filter(o => o.vehicle).slice(0, 5)
    return offenders.length
      ? '**Top Repeat Offenders:**\n' + offenders.map((o, i) => `${i + 1}. **${o.vehicle}** - ${o.count} violations`).join('\n')
      : 'No repeat offender data available.'
  }

  if (q.includes('today')) {
    const today = new Date().toISOString().slice(0, 10)
    const res = await getViolations({ date_from: today, date_to: today + 'T23:59:59' })
    return res.total > 0
      ? `**${res.total}** violation(s) today.\n` + res.violations.slice(0, 5).map(v => `• ${v.violation_type.replace('_', ' ')} - ${v.vehicle_number || 'Unknown'}`).join('\n')
      : `No violations recorded today.`
  }

  if (q.includes('monthly') || q.includes('trend')) {
    const analytics = await getAnalytics()
    return analytics.monthly_trend.length
      ? '**Monthly Trend:**\n' + analytics.monthly_trend.map(m => `• ${m.month}: ${m.count} violations`).join('\n')
      : 'No monthly trend data available.'
  }

  if (q.includes('highest') || q.includes('most confident')) {
    const res = await getViolations({ limit: 200 })
    const sorted = res.violations.sort((a, b) => b.confidence - a.confidence).slice(0, 5)
    return sorted.length
      ? '**Highest Confidence Violations:**\n' + sorted.map((v, i) => `${i + 1}. ${v.violation_type.replace('_', ' ')} - ${v.vehicle_number || 'Unknown'} (${(v.confidence * 100).toFixed(0)}%)`).join('\n')
      : 'No violations found.'
  }

  if (q.includes('vehicle') || q.includes('number') || q.includes('plate')) {
    const words = query.split(/\s+/)
    const plate = words.find(w => w.length >= 4 && /[A-Za-z0-9-]+/.test(w))
    if (plate) {
      const res = await getViolations({ vehicle_number: plate })
      return res.total > 0
        ? `**${res.total}** violation(s) for ${plate.toUpperCase()}:\n` + res.violations.map(v => `• ${v.violation_type.replace('_', ' ')} on ${v.timestamp.slice(0, 10)}`).join('\n')
        : `No violations found for **${plate.toUpperCase()}**.`
    }
    const res = await getViolations({ limit: 200 })
    const vehicles = [...new Set(res.violations.filter(v => v.vehicle_number).map(v => v.vehicle_number))].slice(0, 10)
    return vehicles.length ? `**Vehicles with violations:**\n${vehicles.map(v => `• ${v}`).join('\n')}` : 'No vehicle data available.'
  }

  return `I'm not sure how to answer that. Try:\n${HELPER_TEXT}`
}

export default function Copilot() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hello! I am TRINETRA AI Copilot. Ask me about traffic violations in the database.' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  async function sendMessage() {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)
    try {
      const response = await processQuery(userMsg)
      setMessages(prev => [...prev, { role: 'assistant', content: response }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error querying database. Is the backend running?' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] sm:h-[calc(100vh-8rem)]">
      <h1 className="text-xl sm:text-2xl font-bold text-white mb-2">AI Copilot</h1>
      <p className="text-trinetra-muted mb-4 sm:mb-6 text-sm sm:text-base">Ask questions about traffic violations in natural language</p>

      <div className="flex-1 glass rounded-xl p-4 mb-4 overflow-y-auto space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-white" />
              </div>
            )}
            <div className={`max-w-[80%] rounded-xl p-4 ${
              msg.role === 'user'
                ? 'bg-red-500/10 border border-red-500/20 text-white'
                : 'bg-[#1a2040] text-trinetra-text'
            }`}>
              <div className="text-xs font-medium mb-1 opacity-60">
                {msg.role === 'user' ? 'You' : 'TRINETRA AI'}
              </div>
              <div className="text-sm whitespace-pre-line leading-relaxed">{msg.content}</div>
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
                <User className="w-4 h-4 text-blue-400" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-[#1a2040] rounded-xl p-4">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="glass rounded-xl p-3 flex gap-3">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          placeholder="Ask about traffic violations..."
          className="flex-1 bg-[#1a2040] border border-trinetra-border rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-red-500/50"
        />
        <button onClick={sendMessage} disabled={loading} className="px-4 py-2.5 bg-red-500 hover:bg-red-600 disabled:opacity-50 rounded-lg text-white transition-colors">
          <Send className="w-4 h-4" />
        </button>
        <button onClick={() => setMessages([{ role: 'assistant', content: 'Chat cleared. Ask me about traffic violations.' }])} className="px-3 py-2.5 bg-[#1a2040] hover:bg-[#243050] rounded-lg text-trinetra-muted transition-colors">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
