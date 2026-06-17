import { useState, useRef, useEffect } from 'react'
import { Bot, Send, Loader2, Sparkles, TrendingUp, Users, MapPin, FileText, ArrowLeft } from 'lucide-react'
import { copilotQuery } from '../api/client'

const suggestedQueries = [
  { icon: Users, text: 'Show repeat offenders' },
  { icon: MapPin, text: 'Which location has highest violations?' },
  { icon: TrendingUp, text: 'What should enforcement teams prioritize?' },
  { icon: FileText, text: 'Generate daily report' },
  { icon: TrendingUp, text: 'Violation forecast for tomorrow' },
  { icon: TrendingUp, text: 'Why did violations increase this week?' },
]

export default function Copilot() {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([{
    role: 'assistant',
    text: '**TRINETRA AI Copilot**\n\nI\'m your Traffic Enforcement Intelligence assistant. I can help you with:\n- Repeat offender intelligence\n- Violation hotspot analysis\n- Predictive enforcement forecasts\n- Automated report generation\n- Enforcement prioritization\n- Violation trend analysis\n\n*Try one of the suggestions below or type your own question.*',
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  async function handleSend(q?: string) {
    const query = (q || input).trim()
    if (!query || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: query }])
    setLoading(true)
    try {
      const res = await copilotQuery(query)
      setMessages(prev => [...prev, { role: 'assistant', text: res.answer }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', text: 'Sorry, I encountered an error. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  function formatMessage(text: string) {
    return text.split('\n').map((line, i) => {
      if (line.startsWith('**') && line.endsWith('**')) {
        return <p key={i} className="font-bold text-white text-base mt-2 mb-1">{line.slice(2, -2)}</p>
      }
      if (line.startsWith('- ')) {
        return <p key={i} className="text-trinetra-text text-sm ml-3">{line}</p>
      }
      if (line.startsWith('*') && line.endsWith('*')) {
        return <p key={i} className="text-trinetra-muted text-xs italic mt-1">{line.slice(1, -1)}</p>
      }
      return <p key={i} className="text-trinetra-text text-sm">{line}</p>
    })
  }

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)] max-h-[800px]">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center">
          <Bot className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">AI Copilot</h1>
          <p className="text-xs text-trinetra-muted">Traffic Enforcement Intelligence Assistant</p>
        </div>
      </div>

      {/* Chat */}
      <div ref={listRef} className="flex-1 overflow-y-auto space-y-4 mb-4 px-1">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-xl p-4 ${
              m.role === 'user'
                ? 'bg-red-500/10 border border-red-500/20'
                : 'bg-[#1a2040] border border-trinetra-border'
            }`}>
              {m.role === 'assistant' && (
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                  <span className="text-xs text-purple-400 font-semibold">TRINETRA AI</span>
                </div>
              )}
              <div className="text-sm space-y-1">{formatMessage(m.text)}</div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#1a2040] border border-trinetra-border rounded-xl p-4">
              <Loader2 className="w-5 h-5 animate-spin text-purple-400" />
            </div>
          </div>
        )}
      </div>

      {/* Suggestions */}
      {messages.length <= 1 && (
        <div className="mb-4">
          <p className="text-xs text-trinetra-muted mb-2">Suggested queries:</p>
          <div className="flex flex-wrap gap-2">
            {suggestedQueries.map((sq, i) => (
              <button key={i} onClick={() => handleSend(sq.text)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1a2040] hover:bg-[#243050] rounded-full text-xs text-trinetra-text transition-colors"
              >
                <sq.icon className="w-3 h-3" /> {sq.text}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Ask about violations, offenders, hotspots..."
          className="flex-1 bg-[#1a2040] border border-trinetra-border rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-purple-500/50 placeholder:text-trinetra-muted"
        />
        <button onClick={() => handleSend()} disabled={loading || !input.trim()}
          className="px-4 py-3 bg-purple-500 hover:bg-purple-600 disabled:opacity-50 rounded-xl text-white transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
