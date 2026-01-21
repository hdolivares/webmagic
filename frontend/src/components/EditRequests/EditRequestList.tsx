/**
 * EditRequestList Component
 * 
 * Displays list of edit requests with status badges and actions.
 * 
 * Author: WebMagic Team
 * Date: January 21, 2026
 */
import { useState, useEffect } from 'react'
import { api } from '@/services/api'
import './EditRequestList.css'

interface EditRequest {
  id: string
  site_id: string
  request_text: string
  request_type?: string
  status: string
  preview_url?: string
  created_at: string
  ai_confidence?: number
}

interface EditRequestListProps {
  siteId: string
  refreshTrigger?: number
  onViewPreview?: (request: EditRequest) => void
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  processing: 'Processing',
  ready_for_review: 'Ready for Review',
  approved: 'Approved',
  rejected: 'Rejected',
  deployed: 'Live',
  failed: 'Failed',
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'status-pending',
  processing: 'status-processing',
  ready_for_review: 'status-ready',
  approved: 'status-approved',
  rejected: 'status-rejected',
  deployed: 'status-deployed',
  failed: 'status-failed',
}

export function EditRequestList({ siteId, refreshTrigger, onViewPreview }: EditRequestListProps) {
  const [requests, setRequests] = useState<EditRequest[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedStatus, setSelectedStatus] = useState<string>('')

  useEffect(() => {
    fetchRequests()
  }, [siteId, refreshTrigger, selectedStatus])

  const fetchRequests = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const params = selectedStatus ? { status: selectedStatus } : {}
      const data = await api.listEditRequests(siteId, params)
      setRequests(data.items || [])
    } catch (err: any) {
      console.error('Failed to fetch edit requests:', err)
      setError('Failed to load edit requests')
    } finally {
      setIsLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString()
  }

  const getTypeIcon = (type?: string) => {
    switch (type) {
      case 'text':
        return '📝'
      case 'style':
        return '🎨'
      case 'layout':
        return '📐'
      case 'content':
        return '📄'
      case 'image':
        return '🖼️'
      default:
        return '✏️'
    }
  }

  if (isLoading) {
    return (
      <div className="edit-request-list">
        <div className="loading-skeleton">
          <div className="skeleton-item" />
          <div className="skeleton-item" />
          <div className="skeleton-item" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="edit-request-list">
        <div className="error-state">
          <svg className="error-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>{error}</p>
          <button className="btn-retry" onClick={fetchRequests}>
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (requests.length === 0) {
    return (
      <div className="edit-request-list">
        <div className="empty-state">
          <svg className="empty-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3>No edit requests yet</h3>
          <p>Submit your first request to get started</p>
        </div>
      </div>
    )
  }

  return (
    <div className="edit-request-list">
      {/* Filter Bar */}
      <div className="filter-bar">
        <button
          className={`filter-btn ${!selectedStatus ? 'active' : ''}`}
          onClick={() => setSelectedStatus('')}
        >
          All
        </button>
        {Object.entries(STATUS_LABELS).map(([value, label]) => (
          <button
            key={value}
            className={`filter-btn ${selectedStatus === value ? 'active' : ''}`}
            onClick={() => setSelectedStatus(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Requests List */}
      <div className="requests-container">
        {requests.map((request) => (
          <div key={request.id} className="request-card">
            <div className="request-header">
              <div className="request-meta">
                <span className="request-type-icon">{getTypeIcon(request.request_type)}</span>
                <span className={`status-badge ${STATUS_COLORS[request.status]}`}>
                  {STATUS_LABELS[request.status] || request.status}
                </span>
                <span className="request-time">{formatDate(request.created_at)}</span>
              </div>
              
              {request.ai_confidence && (
                <div className="confidence-badge">
                  {Math.round(request.ai_confidence * 100)}% confident
                </div>
              )}
            </div>

            <div className="request-body">
              <p className="request-text">{request.request_text}</p>
            </div>

            {request.status === 'ready_for_review' && request.preview_url && (
              <div className="request-actions">
                <button
                  className="btn-preview"
                  onClick={() => onViewPreview?.(request)}
                >
                  <svg className="btn-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  View Preview
                </button>
              </div>
            )}

            {request.status === 'processing' && (
              <div className="processing-indicator">
                <div className="processing-spinner" />
                <span>AI is generating preview...</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

