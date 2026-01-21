/**
 * Ticket Detail Component
 * 
 * Displays full ticket conversation with messages
 */
import React, { useState } from 'react'
import { api } from '../../services/api'
import './TicketDetail.css'

interface Message {
  id: string
  message: string
  message_type: string
  ai_generated: boolean
  created_at: string
  customer_user_id?: string
  admin_user_id?: string
}

interface Ticket {
  id: string
  ticket_number: string
  subject: string
  description: string
  category: string
  priority: string
  status: string
  created_at: string
  messages: Message[]
  ai_suggested_response?: string
}

interface TicketDetailProps {
  ticket: Ticket
  onUpdate?: () => void
}

const TicketDetail: React.FC<TicketDetailProps> = ({ ticket, onUpdate }) => {
  const [replyMessage, setReplyMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleReply = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!replyMessage.trim()) return

    setError(null)
    setLoading(true)

    try {
      await api.addTicketMessage(ticket.id, replyMessage)
      setReplyMessage('')
      if (onUpdate) onUpdate()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send message')
    } finally {
      setLoading(false)
    }
  }

  const handleCloseTicket = async () => {
    if (!confirm('Are you sure you want to close this ticket?')) return

    try {
      await api.updateTicketStatus(ticket.id, 'closed')
      if (onUpdate) onUpdate()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to close ticket')
    }
  }

  const handleResolveTicket = async () => {
    try {
      await api.updateTicketStatus(ticket.id, 'resolved')
      if (onUpdate) onUpdate()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resolve ticket')
    }
  }

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString)
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatCategory = (category: string): string => {
    return category.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatStatus = (status: string): string => {
    return status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const getStatusColor = (status: string): string => {
    const statusColors: Record<string, string> = {
      new: 'status-new',
      in_progress: 'status-progress',
      waiting_customer: 'status-waiting',
      waiting_ai: 'status-waiting',
      resolved: 'status-resolved',
      closed: 'status-closed'
    }
    return statusColors[status] || 'status-default'
  }

  // Combine description with messages
  const allMessages = [
    {
      id: 'initial',
      message: ticket.description,
      message_type: 'customer',
      ai_generated: false,
      created_at: ticket.created_at,
      customer_user_id: 'customer'
    },
    ...ticket.messages
  ]

  return (
    <div className="ticket-detail">
      <div className="ticket-detail-header">
        <div>
          <div className="ticket-detail-number">#{ticket.ticket_number}</div>
          <h2 className="ticket-detail-subject">{ticket.subject}</h2>
          <div className="ticket-detail-meta">
            <span className="ticket-category-badge">{formatCategory(ticket.category)}</span>
            <span className={`ticket-status-badge ${getStatusColor(ticket.status)}`}>
              {formatStatus(ticket.status)}
            </span>
            <span className="ticket-priority-badge priority-{ticket.priority}">
              {ticket.priority} priority
            </span>
          </div>
        </div>

        {ticket.status !== 'closed' && (
          <div className="ticket-actions">
            {ticket.status !== 'resolved' && (
              <button
                className="btn btn-success"
                onClick={handleResolveTicket}
              >
                Mark as Resolved
              </button>
            )}
            <button
              className="btn btn-secondary"
              onClick={handleCloseTicket}
            >
              Close Ticket
            </button>
          </div>
        )}
      </div>

      <div className="ticket-conversation">
        {allMessages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.message_type === 'customer' ? 'message-customer' : 'message-staff'} ${message.ai_generated ? 'message-ai' : ''}`}
          >
            <div className="message-header">
              <div className="message-author">
                {message.message_type === 'customer' ? (
                  <>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                      <circle cx="12" cy="7" r="4"/>
                    </svg>
                    <span>You</span>
                  </>
                ) : (
                  <>
                    {message.ai_generated ? (
                      <>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                        </svg>
                        <span>AI Assistant</span>
                      </>
                    ) : (
                      <>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                          <circle cx="9" cy="7" r="4"/>
                          <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                          <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                        </svg>
                        <span>Support Staff</span>
                      </>
                    )}
                  </>
                )}
              </div>
              <div className="message-time">{formatDate(message.created_at)}</div>
            </div>
            <div className="message-content">
              {message.message}
            </div>
          </div>
        ))}
      </div>

      {ticket.status !== 'closed' && (
        <div className="ticket-reply-form">
          <form onSubmit={handleReply}>
            <div className="form-group">
              <label htmlFor="reply">Reply to ticket</label>
              <textarea
                id="reply"
                value={replyMessage}
                onChange={(e) => setReplyMessage(e.target.value)}
                placeholder="Type your message here..."
                rows={4}
                disabled={loading}
                required
              />
            </div>

            {error && (
              <div className="form-error">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="12"/>
                  <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !replyMessage.trim()}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  <span>Sending...</span>
                </>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="22" y1="2" x2="11" y2="13"/>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                  </svg>
                  <span>Send Message</span>
                </>
              )}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}

export default TicketDetail

