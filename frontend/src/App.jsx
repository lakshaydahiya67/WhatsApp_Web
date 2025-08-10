import { useEffect, useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function StatusTicks({ status }) {
  if (!status) return null
  if (status === 'sent') return <span title="sent" className="text-[var(--wa-tick-grey)]">✓</span>
  if (status === 'delivered') return <span title="delivered" className="text-[var(--wa-tick-grey)]">✓✓</span>
  if (status === 'read') return <span title="read" style={{color:'var(--wa-blue)'}}>✓✓</span>
  return null
}

function formatTime(epochSec) {
  if (!epochSec) return ''
  const d = new Date(epochSec * 1000)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function App() {
  const [conversations, setConversations] = useState([])
  const [activeWaId, setActiveWaId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showList, setShowList] = useState(true)
  const [ws, setWs] = useState(null)

  async function fetchConversations() {
    try {
      const res = await fetch(`${API_BASE}/conversations`)
      if (!res.ok) throw new Error('failed')
      const data = await res.json()
      const list = Array.isArray(data) ? data : []
      setConversations(list)
      if (!activeWaId && list.length > 0) {
        setActiveWaId(list[0].waId)
      }
    } catch (e) {
      setConversations([])
    }
  }

  async function fetchMessages(waId) {
    if (!waId) return
    try {
      const res = await fetch(`${API_BASE}/messages?wa_id=${encodeURIComponent(waId)}`)
      if (!res.ok) throw new Error('failed')
      const data = await res.json()
      setMessages(Array.isArray(data) ? data : [])
    } catch (e) {
      setMessages([])
    }
  }

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    fetchMessages(activeWaId)
  }, [activeWaId])

  // Polling for updates every 5s
  useEffect(() => {
    const interval = setInterval(() => {
      fetchConversations()
      if (activeWaId) {
        fetchMessages(activeWaId)
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [activeWaId])

  // Connect WebSocket for realtime updates (if available)
  useEffect(() => {
    const url = (API_BASE.replace('http', 'ws') + '/ws')
    try {
      const socket = new WebSocket(url)
      socket.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data)
          if (data?.type === 'insert') {
            fetchConversations()
            if (data.message?.waId === activeWaId) {
              fetchMessages(activeWaId)
            }
          }
        } catch {}
      }
      setWs(socket)
      return () => socket.close()
    } catch {
      // ignore if ws fails
    }
  }, [activeWaId])

  useEffect(() => {
    // On small screens, auto-hide list when a chat is selected
    if (window.innerWidth < 768) {
      setShowList(!activeWaId ? true : false)
    }
  }, [activeWaId])

  async function sendMessage() {
    if (!input.trim() || !activeWaId) return
    const optimistic = {
      _id: `local-${Math.random().toString(36).slice(2)}`,
      waId: activeWaId,
      direction: 'outbound',
      text: input,
      type: 'text',
      status: 'sent',
      timestamps: { whatsapp: Math.floor(Date.now() / 1000), sent: Math.floor(Date.now() / 1000), delivered: null, read: null },
    }
    setMessages((prev) => [...prev, optimistic])
    setInput('')
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ waId: activeWaId, text: optimistic.text }),
      })
      const saved = await res.json()
      setMessages((prev) => prev.map((m) => (m._id === optimistic._id ? saved : m)))
      fetchConversations()
    } catch (e) {
      // rollback on error
      setMessages((prev) => prev.filter((m) => m._id !== optimistic._id))
    } finally {
      setLoading(false)
    }
  }

  const activeConversation = useMemo(() => (
    Array.isArray(conversations) ? (conversations.find((c) => c.waId === activeWaId) || null) : null
  ), [conversations, activeWaId])

  return (
    <div className="h-screen p-0 md:p-6" style={{background:'var(--wa-bg)'}}>
      <div className="mx-auto max-w-6xl h-full bg-[var(--wa-panel)] shadow rounded-lg grid grid-cols-1 md:grid-cols-3 md:overflow-hidden">
        {/* Sidebar */}
        <div className={`md:col-span-1 flex flex-col border-r ${showList ? '' : 'hidden md:flex'}`}>
          <div className="h-14 px-4 flex items-center justify-between bg-[var(--wa-panel)] border-b">
            <div className="font-semibold">Chats</div>
          </div>
          <div className="flex-1 overflow-auto chat-scroll">
            {Array.isArray(conversations) && conversations.map((c) => (
              <button
                key={c.waId}
                onClick={() => {
                  setActiveWaId(c.waId)
                  if (window.innerWidth < 768) setShowList(false)
                }}
                className={`w-full text-left px-4 py-3 flex gap-3 items-center chat-row ${activeWaId===c.waId ? 'bg-gray-100' : ''}`}
              >
                <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 text-sm">
                  {(c.name?.[0] || c.waId?.[0] || '?')}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center">
                    <div className="font-medium truncate">{c.name || c.waId}</div>
                    <div className="text-[11px] text-gray-500 ml-2 shrink-0">{formatTime(c.lastMessageAt)}</div>
                  </div>
                  <div className="flex items-center gap-1 text-[13px] text-gray-600 truncate">
                    {c.lastMessageDirection === 'outbound' && <StatusTicks status={c.lastMessageStatus} />}
                    <span className="truncate">{c.lastMessageText}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Chat area */}
        <div className={`md:col-span-2 flex flex-col ${showList ? 'hidden md:flex' : ''}`}>
          <div className="h-14 px-4 flex items-center justify-between bg-[var(--wa-panel)] border-b">
            <div>
              <div className="font-medium">{activeConversation?.name || activeWaId || 'Select a chat'}</div>
              {activeWaId && <div className="text-[11px] text-gray-500">{activeWaId}</div>}
            </div>
            <button className="md:hidden text-[var(--wa-accent)]" onClick={()=>setShowList(true)}>Back</button>
          </div>
          <div className="flex-1 overflow-auto p-4 space-y-2 chat-scroll chat-bg">
            {Array.isArray(messages) && messages.map((m) => (
              <div key={m._id} className={`max-w-[70%] px-3 py-2 rounded-lg text-[14px] ${m.direction==='outbound' ? 'ml-auto' : 'mr-auto'} ${m.direction==='outbound' ? 'bg-[var(--wa-bubble-out)]' : 'bg-white'}`}>
                <div className="whitespace-pre-wrap break-words">{m.text}</div>
                <div className="flex justify-end items-center gap-1 text-[10px] text-gray-500 mt-1">
                  <span>{formatTime(m.timestamps?.whatsapp)}</span>
                  {m.direction==='outbound' && <StatusTicks status={m.status} />}
                </div>
              </div>
            ))}
          </div>
          <div className="p-2 sm:p-3 border-t flex gap-2 bg-[var(--wa-panel)] shrink-0" style={{paddingBottom:'max(env(safe-area-inset-bottom), 0px)'}}>
            <input value={input} onChange={(e)=>setInput(e.target.value)} placeholder="Type a message" className="flex-1 border rounded-full px-3 sm:px-4 py-2 focus:outline-none bg-white" onKeyDown={(e)=>{ if(e.key==='Enter'){ e.preventDefault(); sendMessage(); } }} />
            <button onClick={sendMessage} disabled={loading || !activeWaId} className="bg-[var(--wa-accent)] text-white px-3 sm:px-4 py-2 rounded-full disabled:opacity-50 whitespace-nowrap">Send</button>
          </div>
        </div>
      </div>
    </div>
  )
}

