/**
 * Ticket Detail Page
 * 
 * View and interact with a specific ticket
 */
import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../../services/api'
import { TicketDetail } from '../../components/Tickets'
import './TicketDetailPage.css'

const TicketDetailPage: React.FC = () => {
  const { ticketId } = useParams<{ ticketId: string }>()
  const navigate = useNavigate()
  const [ticket, setTicket] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (ticketId) {
      loadTicket()
    }
  }, [ticketId])

  const loadTicket = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await api.getTicket(ticketId!)
      setTicket(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load ticket')
    } finally {
      setLoading(false)
    }
  }

  const handleBack = () => {
    navigate('/customer/tickets')
  }

  if (loading) {
    return (
      <div className="ticket-detail-page">
        <button className="btn-back" onClick={handleBack}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="19" y1="12" x2="5" y2="12"/>
            <polyline points="12 19 5 12 12 5"/>
          </svg>
          Back to Tickets
        </button>

        <div className="loading-state">
          <div className="spinner-large"></div>
          <p>Loading ticket...</p>
        </div>
      </div>
    )
  }

  if (error || !ticket) {
    return (
      <div className="ticket-detail-page">
        <button className="btn-back" onClick={handleBack}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="19" y1="12" x2="5" y2="12"/>
            <polyline points="12 19 5 12 12 5"/>
          </svg>
          Back to Tickets
        </button>

        <div className="error-state">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <h2>Ticket Not Found</h2>
          <p>{error || 'The ticket you are looking for could not be found.'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="ticket-detail-page">
      <button className="btn-back" onClick={handleBack}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="19" y1="12" x2="5" y2="12"/>
          <polyline points="12 19 5 12 12 5"/>
        </svg>
        Back to Tickets
      </button>

      <TicketDetail ticket={ticket} onUpdate={loadTicket} />
    </div>
  )
}

export default TicketDetailPage

