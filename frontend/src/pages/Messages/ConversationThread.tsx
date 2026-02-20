/**
 * ConversationThread
 *
 * Right-panel of the two-panel messages inbox.
 * Shows all messages for a selected contact phone in chat-bubble style,
 * oldest at top, newest at bottom.
 */
import { RefreshCw, MessageSquare, CheckCircle, XCircle, Clock } from 'lucide-react'
import type { SMSMessageItem } from '@/services/api'
import './MessagesPage.css'

interface ConversationThreadProps {
  contactPhone: string
  messages: SMSMessageItem[]
  isLoading: boolean
  onRefresh: () => void
}

function formatPhone(phone: string): string {
  if (!phone) return 'Unknown'
  if (phone.startsWith('+1') && phone.length === 12) {
    return `(${phone.slice(2, 5)}) ${phone.slice(5, 8)}-${phone.slice(8)}`
  }
  return phone
}

function formatTimestamp(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'delivered') return <CheckCircle className="w-3 h-3 text-success" />
  if (status === 'failed') return <XCircle className="w-3 h-3 text-error" />
  return <Clock className="w-3 h-3 text-text-secondary" />
}

export function ConversationThread({
  contactPhone,
  messages,
  isLoading,
  onRefresh,
}: ConversationThreadProps) {
  const businessName = messages.find((m) => m.business_name)?.business_name
  const city = messages.find((m) => m.business_city)?.business_city
  const state = messages.find((m) => m.business_state)?.business_state

  return (
    <section className="convo-thread">
      {/* Thread header */}
      <div className="convo-thread__header">
        <div className="convo-thread__contact-info">
          <span className="convo-thread__contact-name">
            {businessName ?? formatPhone(contactPhone)}
          </span>
          {businessName && (
            <span className="convo-thread__contact-sub">
              {formatPhone(contactPhone)}
              {city && ` • ${city}${state ? `, ${state}` : ''}`}
            </span>
          )}
        </div>
        <button
          className="convo-list__refresh-btn"
          onClick={onRefresh}
          aria-label="Refresh thread"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'spinning' : ''}`} />
        </button>
      </div>

      {/* Bubbles */}
      <div className="convo-thread__messages">
        {isLoading ? (
          <div className="convo-thread__empty">
            <div className="spinner" />
          </div>
        ) : messages.length === 0 ? (
          <div className="convo-thread__empty">
            <MessageSquare className="w-8 h-8 opacity-30" />
            <p>No messages in this thread</p>
          </div>
        ) : (
          messages.map((msg) => {
            const isOutbound = msg.direction === 'outbound'
            return (
              <div
                key={msg.id}
                className={`convo-bubble ${isOutbound ? 'convo-bubble--out' : 'convo-bubble--in'}`}
              >
                <div className="convo-bubble__content">
                  <p className="convo-bubble__body">{msg.body}</p>
                  <div className="convo-bubble__meta">
                    <span>{formatTimestamp(msg.created_at)}</span>
                    {isOutbound && <StatusIcon status={msg.status} />}
                    {msg.cost != null && (
                      <span className="convo-bubble__cost">${msg.cost.toFixed(4)}</span>
                    )}
                  </div>
                  {msg.error_message && (
                    <div className="convo-bubble__error">
                      <XCircle className="w-3.5 h-3.5" />
                      {msg.error_message}
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </section>
  )
}
