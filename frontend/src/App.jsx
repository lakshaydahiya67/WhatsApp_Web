import { useEffect, useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function StatusTicks({ status }) {
  if (!status) return null
  if (status === 'sent') return (
    <svg width="16" height="12" viewBox="0 0 18 14" aria-label="sent">
      <path d="M5 8l-3-3  -2 2 5 5 10-10 -2-2z" fill="currentColor" />
    </svg>
  )
  if (status === 'delivered') return (
    <svg width="20" height="14" viewBox="0 0 24 14" aria-label="delivered" className="text-[var(--wa-tick-grey)]">
      <path d="M6 8l-3-3 -2 2 5 5 7-7 -2-2z" fill="currentColor" />
      <path d="M13 8l-3-3 -2 2 5 5 7-7 -2-2z" fill="currentColor" />
    </svg>
  )
  if (status === 'read') return (
    <svg width="20" height="14" viewBox="0 0 24 14" aria-label="read" style={{color:'var(--wa-blue)'}}>
      <path d="M6 8l-3-3 -2 2 5 5 7-7 -2-2z" fill="currentColor" />
      <path d="M13 8l-3-3 -2 2 5 5 7-7 -2-2z" fill="currentColor" />
    </svg>
  )
  return null
}

const IST_TZ = 'Asia/Kolkata'

function formatTime(epochSec) {
  if (!epochSec) return ''
  const d = new Date(epochSec * 1000)
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: IST_TZ })
}

function dayKeyIST(epochSec) {
  const d = new Date(epochSec * 1000)
  // en-CA yields YYYY-MM-DD stable sortable key
  return d.toLocaleDateString('en-CA', { timeZone: IST_TZ })
}

function formatDateChip(epochSec) {
  const d = new Date(epochSec * 1000)
  const keyMsg = dayKeyIST(epochSec)
  const keyToday = new Date().toLocaleDateString('en-CA', { timeZone: IST_TZ })
  const parseKey = (k) => {
    const [y, m, dd] = k.split('-').map(Number)
    return Date.UTC(y, m - 1, dd)
  }
  const oneDay = 24 * 60 * 60 * 1000
  const diffDays = Math.round((parseKey(keyToday) - parseKey(keyMsg)) / oneDay)
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return d.toLocaleDateString('en-IN', { weekday: 'long', timeZone: IST_TZ })
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: IST_TZ })
}

export default function App() {
  const [conversations, setConversations] = useState([])
  const [activeWaId, setActiveWaId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationsLoading, setConversationsLoading] = useState(true)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [showList, setShowList] = useState(true)
  const [ws, setWs] = useState(null)
  const [showColdStartInfo, setShowColdStartInfo] = useState(true)

  async function fetchConversations(silent = false) {
    try {
      if (!silent) setConversationsLoading(true)
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
    } finally {
      if (!silent) setConversationsLoading(false)
    }
  }

  async function fetchMessages(waId, silent = false) {
    if (!waId) return
    try {
      if (!silent) setMessagesLoading(true)
      const res = await fetch(`${API_BASE}/messages?wa_id=${encodeURIComponent(waId)}`)
      if (!res.ok) throw new Error('failed')
      const data = await res.json()
      setMessages(Array.isArray(data) ? data : [])
    } catch (e) {
      setMessages([])
    } finally {
      if (!silent) setMessagesLoading(false)
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
      fetchConversations(true)
      if (activeWaId) {
        fetchMessages(activeWaId, true)
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
            fetchConversations(true)
            if (data.message?.waId === activeWaId) {
              fetchMessages(activeWaId, true)
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
    <div className="min-h-screen flex flex-col p-0 md:px-4 md:py-3" style={{background:'var(--wa-bg)'}}>
      {showColdStartInfo && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs sm:text-sm text-center py-1.5 px-3 mx-2 mt-2 rounded">
          Note: backend is deployed on Render free tier and may take ~30–60 seconds to cold-start. If chats are empty, please wait and refresh.
          <button onClick={() => setShowColdStartInfo(false)} className="ml-2 underline">Dismiss</button>
        </div>
      )}
      <div className="mx-auto w-full md:max-w-6xl flex-1 bg-[var(--wa-panel)] shadow rounded-lg grid grid-cols-1 md:grid-cols-3 md:overflow-hidden mt-2 min-h-0">
        {/* Sidebar */}
        <div className={`md:col-span-1 flex flex-col border-r w-full ${showList ? '' : 'hidden md:flex'}`}>
          <div className="h-14 px-4 flex items-center justify-between bg-[var(--wa-panel)] border-b">
            <div className="font-semibold">Chats</div>
          </div>
          <div className="flex-1 overflow-auto chat-scroll">
            {conversationsLoading && (
              <div className="p-3 space-y-2">
                {[...Array(4)].map((_,i)=> (
                  <div key={i} className="flex items-center gap-3">
                    <div className="avatar-circle animate-pulse bg-gray-300" />
                    <div className="flex-1">
                      <div className="h-3 w-1/3 bg-gray-200 animate-pulse rounded mb-2"></div>
                      <div className="h-2 w-1/2 bg-gray-100 animate-pulse rounded"></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {!conversationsLoading && Array.isArray(conversations) && conversations.map((c) => (
              <button
                key={c.waId}
                onClick={() => {
                  setActiveWaId(c.waId)
                  if (window.innerWidth < 768) setShowList(false)
                }}
                className={`w-full text-left px-4 py-3 flex gap-3 items-center chat-row ${activeWaId===c.waId ? 'bg-gray-100' : ''}`}
              >
                <div className="avatar-circle">
                  {(c.name?.[0] || c.waId?.[0] || '?')}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center">
                    <div className="font-medium truncate">{c.name || c.waId}</div>
                    <div className="text-[11px] text-[var(--wa-text-secondary)] ml-2 shrink-0">{formatTime(c.lastMessageAt)}</div>
                  </div>
                  <div className="flex items-center gap-1 text-[13px] text-[var(--wa-text-secondary)] truncate">
                    {c.lastMessageDirection === 'outbound' && <StatusTicks status={c.lastMessageStatus} />}
                    <span className="truncate">{c.lastMessageText}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Chat area */}
        <div className={`md:col-span-2 flex flex-col w-full ${showList ? 'hidden md:flex' : ''}`}>
          <div className="h-14 px-4 flex items-center justify-between bg-[var(--wa-panel)] border-b">
            <div>
              <div className="font-medium">{activeConversation?.name || activeWaId || 'Select a chat'}</div>
              {activeWaId && <div className="text-[11px] text-gray-500">{activeWaId}</div>}
            </div>
            <button className="md:hidden text-[var(--wa-accent)]" onClick={()=>setShowList(true)}>Back</button>
          </div>
          <div className="flex-1 overflow-auto p-4 space-y-1 chat-scroll chat-bg">
            {messagesLoading && (
              <div className="space-y-1">
                {[...Array(5)].map((_,i)=> (
                  <div key={i} className={`max-w-[70%] px-3 py-3 ${i%2? 'ml-auto':'mr-auto'} rounded-lg bg-gray-100 animate-pulse`}></div>
                ))}
              </div>
            )}
            {!messagesLoading && Array.isArray(messages) && messages.length > 0 && (
              (() => {
                const blocks = []
                let lastDayKey = ''
                for (const m of messages) {
                  const ts = m?.timestamps?.whatsapp
                  const dayKey = ts ? dayKeyIST(ts) : ''
                  if (dayKey && dayKey !== lastDayKey) {
                    lastDayKey = dayKey
                    blocks.push(
                      <div key={`date-${dayKey}`} className="w-full flex justify-center">
                        <span className="date-chip">{formatDateChip(ts)}</span>
                      </div>
                    )
                  }
                  blocks.push(
                    <div key={m._id} className={`max-w-[70%] px-3 py-1.5 text-[14px] ${m.direction==='outbound' ? 'ml-auto bubble-out' : 'mr-auto bubble-in'}`}>
                      <div className="whitespace-pre-wrap break-words">{m.text}</div>
                      <div className="time-ticks mt-0.5">
                        <span className="text-[10px]">{formatTime(m.timestamps?.whatsapp)}</span>
                        {m.direction==='outbound' && <StatusTicks status={m.status} />}
                      </div>
                    </div>
                  )
                }
                return blocks
              })()
            )}
          </div>
          <div className="p-2 sm:p-3 border-t flex items-center gap-2 bg-[var(--wa-panel)] shrink-0" style={{paddingBottom:'max(env(safe-area-inset-bottom), 0px)'}}>
            <input value={input} onChange={(e)=>setInput(e.target.value)} placeholder="Type a message" className="flex-1 border rounded-full px-3 sm:px-4 h-10 focus:outline-none bg-white" onKeyDown={(e)=>{ if(e.key==='Enter'){ e.preventDefault(); sendMessage(); } }} />
            <button onClick={sendMessage} disabled={loading || !activeWaId} className="bg-[var(--wa-accent)] text-white px-4 h-10 rounded-full disabled:opacity-50 whitespace-nowrap inline-flex items-center justify-center">Send</button>
          </div>
        </div>
      </div>
    </div>
  )
}

