/**
 * Ticket List Component
 * 
 * Displays list of support tickets with filtering and status badges
 */
import React from 'react'
import { useNavigate } from 'react-router-dom'
import './TicketList.css'

interface Ticket {
  id: string
  ticket_number: string
  subject: string
  category: string
  priority: string
  status: string
  created_at: string
  last_customer_message_at?: string
  last_staff_message_at?: string
}

interface TicketListProps {
  tickets: Ticket[]
  loading?: boolean
  emptyMessage?: string
}

const TicketList: React.FC<TicketListProps> = ({
  tickets,
  loading = false,
  emptyMessage = 'No tickets found'
}) => {
  const navigate = useNavigate()

  const getStatusBadgeClass = (status: string): string => {
    const statusMap: Record<string, string> = {
      new: 'status-new',
      in_progress: 'status-progress',
      waiting_customer: 'status-waiting',
      waiting_ai: 'status-waiting',
      resolved: 'status-resolved',
      closed: 'status-closed'
    }
    return statusMap[status] || 'status-default'
  }

  const getPriorityBadgeClass = (priority: string): string => {
    const priorityMap: Record<string, string> = {
      low: 'priority-low',
      medium: 'priority-medium',
      high: 'priority-high',
      urgent: 'priority-urgent'
    }
    return priorityMap[priority] || 'priority-medium'
  }

  const formatCategory = (category: string): string => {
    return category
      .replace('_', ' ')
      .replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatStatus = (status: string): string => {
    return status
      .replace('_', ' ')
      .replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} min ago`
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    
    return date.toLocaleDateString()
  }

  const handleTicketClick = (ticketId: string) => {
    navigate(`/customer/tickets/${ticketId}`)
  }

  if (loading) {
    return (
      <div className="ticket-list-loading">
        <div className="spinner-large"></div>
        <p>Loading tickets...</p>
      </div>
    )
  }

  if (tickets.length === 0) {
    return (
      <div className="ticket-list-empty">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10 9 9 9 8 9"/>
        </svg>
        <p>{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="ticket-list">
      {tickets.map((ticket) => (
        <div
          key={ticket.id}
          className="ticket-item"
          onClick={() => handleTicketClick(ticket.id)}
        >
          <div className="ticket-header">
            <div className="ticket-number">#{ticket.ticket_number}</div>
            <div className="ticket-badges">
              <span className={`priority-badge ${getPriorityBadgeClass(ticket.priority)}`}>
                {ticket.priority}
              </span>
              <span className={`status-badge ${getStatusBadgeClass(ticket.status)}`}>
                {formatStatus(ticket.status)}
              </span>
            </div>
          </div>

          <h3 className="ticket-subject">{ticket.subject}</h3>

          <div className="ticket-meta">
            <span className="ticket-category">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
                <line x1="7" y1="7" x2="7.01" y2="7"/>
              </svg>
              {formatCategory(ticket.category)}
            </span>
            <span className="ticket-date">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              {formatDate(ticket.created_at)}
            </span>
          </div>

          {ticket.last_staff_message_at && (
            <div className="ticket-response-indicator">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <span>Staff responded {formatDate(ticket.last_staff_message_at)}</span>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default TicketList

