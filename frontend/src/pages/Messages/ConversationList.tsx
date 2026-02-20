/**
 * ConversationList
 *
 * Left-panel of the two-panel messages inbox.
 * Shows one row per unique contact phone, sorted by most-recent message.
 */
import { ArrowDownLeft, ArrowUpRight, Search, RefreshCw, MessageSquare } from 'lucide-react'
import type { ConversationSummary } from '@/services/api'
import './MessagesPage.css'

interface ConversationListProps {
  conversations: ConversationSummary[]
  selectedPhone: string | null
  isLoading: boolean
  search: string
  onSearchChange: (value: string) => void
  onSelect: (phone: string) => void
  onRefresh: () => void
}

function formatPhone(phone: string): string {
  if (!phone) return 'Unknown'
  if (phone.startsWith('+1') && phone.length === 12) {
    return `(${phone.slice(2, 5)}) ${phone.slice(5, 8)}-${phone.slice(8)}`
  }
  return phone
}

function formatRelativeTime(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const diffMs = Date.now() - date.getTime()
  const mins = Math.floor(diffMs / 60_000)
  const hours = Math.floor(diffMs / 3_600_000)
  const days = Math.floor(diffMs / 86_400_000)

  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`
  return date.toLocaleDateString()
}

function truncateBody(body: string, max = 55): string {
  return body.length > max ? `${body.slice(0, max)}…` : body
}

export function ConversationList({
  conversations,
  selectedPhone,
  isLoading,
  search,
  onSearchChange,
  onSelect,
  onRefresh,
}: ConversationListProps) {
  return (
    <aside className="convo-list">
      {/* Header */}
      <div className="convo-list__header">
        <span className="convo-list__title">Conversations</span>
        <button
          className="convo-list__refresh-btn"
          onClick={onRefresh}
          aria-label="Refresh conversations"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'spinning' : ''}`} />
        </button>
      </div>

      {/* Search */}
      <div className="convo-list__search">
        <Search className="w-4 h-4 text-text-secondary" />
        <input
          type="text"
          placeholder="Search name or phone…"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="convo-list__search-input"
        />
      </div>

      {/* List */}
      <div className="convo-list__items">
        {isLoading ? (
          <div className="convo-list__empty">
            <div className="spinner" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="convo-list__empty">
            <MessageSquare className="w-8 h-8 opacity-30" />
            <p>No conversations yet</p>
          </div>
        ) : (
          conversations.map((c) => (
            <button
              key={c.contact_phone}
              className={`convo-list__item ${selectedPhone === c.contact_phone ? 'convo-list__item--active' : ''} ${c.inbound_count > 0 ? 'convo-list__item--has-reply' : ''}`}
              onClick={() => onSelect(c.contact_phone)}
            >
              {/* Direction indicator */}
              <span className="convo-list__direction-icon">
                {c.last_message_direction === 'inbound' ? (
                  <ArrowDownLeft className="w-3.5 h-3.5 text-info" />
                ) : (
                  <ArrowUpRight className="w-3.5 h-3.5 text-success" />
                )}
              </span>

              <div className="convo-list__item-body">
                <div className="convo-list__item-top">
                  <span className="convo-list__contact-name">
                    {c.business_name ?? formatPhone(c.contact_phone)}
                  </span>
                  <span className="convo-list__timestamp">
                    {formatRelativeTime(c.last_message_at)}
                  </span>
                </div>

                {c.business_name && (
                  <div className="convo-list__phone-sub">{formatPhone(c.contact_phone)}</div>
                )}

                <div className="convo-list__preview">
                  {truncateBody(c.last_message_body)}
                </div>

                {c.inbound_count > 0 && (
                  <div className="convo-list__badge">
                    {c.inbound_count} {c.inbound_count === 1 ? 'reply' : 'replies'}
                  </div>
                )}
              </div>
            </button>
          ))
        )}
      </div>
    </aside>
  )
}
