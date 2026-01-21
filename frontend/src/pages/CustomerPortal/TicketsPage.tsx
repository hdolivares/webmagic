/**
 * Customer Tickets Page
 * 
 * Main page for viewing and managing support tickets
 */
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../services/api'
import { CreateTicketForm, TicketList } from '../../components/Tickets'
import './TicketsPage.css'

const TicketsPage: React.FC = () => {
  const navigate = useNavigate()
  const [tickets, setTickets] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [categoryFilter, setCategoryFilter] = useState<string>('')

  useEffect(() => {
    loadData()
  }, [statusFilter, categoryFilter])

  const loadData = async () => {
    setLoading(true)
    try {
      const [ticketsData, statsData] = await Promise.all([
        api.listTickets({
          status: statusFilter || undefined,
          category: categoryFilter || undefined,
          limit: 50
        }),
        api.getTicketStats()
      ])

      setTickets(ticketsData.tickets)
      setStats(statsData)
    } catch (error) {
      console.error('Failed to load tickets:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleTicketCreated = (ticket: any) => {
    setShowCreateForm(false)
    loadData()
    navigate(`/customer/tickets/${ticket.id}`)
  }

  return (
    <div className="tickets-page">
      <div className="tickets-page-header">
        <div>
          <h1>My Support Tickets</h1>
          <p className="page-description">
            Get help with your website, billing, or any questions you have
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          {showCreateForm ? (
            <>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
              <span>Cancel</span>
            </>
          ) : (
            <>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              <span>New Ticket</span>
            </>
          )}
        </button>
      </div>

      {stats && (
        <div className="tickets-stats">
          <div className="stat-card">
            <div className="stat-value">{stats.total}</div>
            <div className="stat-label">Total Tickets</div>
          </div>
          <div className="stat-card stat-open">
            <div className="stat-value">{stats.open}</div>
            <div className="stat-label">Open</div>
          </div>
          <div className="stat-card stat-waiting">
            <div className="stat-value">{stats.waiting}</div>
            <div className="stat-label">Waiting Response</div>
          </div>
          <div className="stat-card stat-resolved">
            <div className="stat-value">{stats.resolved}</div>
            <div className="stat-label">Resolved</div>
          </div>
        </div>
      )}

      {showCreateForm && (
        <div className="create-ticket-section">
          <h2>Create New Ticket</h2>
          <CreateTicketForm
            onSuccess={handleTicketCreated}
            onCancel={() => setShowCreateForm(false)}
          />
        </div>
      )}

      <div className="tickets-list-section">
        <div className="tickets-filters">
          <div className="filter-group">
            <label htmlFor="status-filter">Status:</label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All</option>
              <option value="new">New</option>
              <option value="in_progress">In Progress</option>
              <option value="waiting_customer">Waiting for Response</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="category-filter">Category:</label>
            <select
              id="category-filter"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">All</option>
              <option value="billing">Billing</option>
              <option value="technical_support">Technical Support</option>
              <option value="site_edit">Site Edit</option>
              <option value="question">Question</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        <TicketList
          tickets={tickets}
          loading={loading}
          emptyMessage={
            statusFilter || categoryFilter
              ? 'No tickets match your filters'
              : 'No tickets yet. Create your first ticket to get help!'
          }
        />
      </div>
    </div>
  )
}

export default TicketsPage

