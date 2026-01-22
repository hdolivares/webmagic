/**
 * Draft Campaigns Panel
 * 
 * Displays and manages draft campaigns - businesses that have been scraped
 * but are awaiting manual review before outreach is sent.
 */
import { useState, useEffect } from 'react'
import { Card } from '@/components/ui'
import { api } from '@/services/api'
import {
  DraftCampaign,
  DraftCampaignStats,
  DraftCampaignBusiness
} from '@/types'
import './DraftCampaignsPanel.css'

interface DraftCampaignsPanelProps {
  onCampaignUpdate?: () => void
}

export function DraftCampaignsPanel({ onCampaignUpdate }: DraftCampaignsPanelProps) {
  const [campaigns, setCampaigns] = useState<DraftCampaign[]>([])
  const [stats, setStats] = useState<DraftCampaignStats | null>(null)
  const [selectedCampaign, setSelectedCampaign] = useState<string | null>(null)
  const [campaignDetails, setCampaignDetails] = useState<{
    campaign: DraftCampaign
    businesses: DraftCampaignBusiness[]
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadCampaigns()
    loadStats()
  }, [])

  const loadCampaigns = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.getDraftCampaigns()
      setCampaigns(response.campaigns || [])
    } catch (err: any) {
      setError('Failed to load draft campaigns')
      console.error('Error loading campaigns:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const statsData = await api.getDraftCampaignStats()
      setStats(statsData)
    } catch (err: any) {
      console.error('Error loading stats:', err)
    }
  }

  const loadCampaignDetails = async (campaignId: string) => {
    setDetailsLoading(true)
    setError(null)
    
    try {
      const details = await api.getDraftCampaignDetail(campaignId)
      setCampaignDetails(details)
      setSelectedCampaign(campaignId)
    } catch (err: any) {
      setError('Failed to load campaign details')
      console.error('Error loading details:', err)
    } finally {
      setDetailsLoading(false)
    }
  }

  const handleApprove = async (campaignId: string) => {
    const campaign = campaigns.find(c => c.id === campaignId)
    if (!campaign) return

    const confirmMsg = `Approve campaign for ${campaign.city}, ${campaign.state} - ${campaign.category}?\n\n` +
      `This will prepare ${campaign.qualified_leads_count} leads for outreach.`
    
    if (!confirm(confirmMsg)) return

    try {
      await api.approveDraftCampaign(campaignId)
      alert('✅ Campaign approved! Leads are ready for outreach.')
      
      // Refresh data
      await loadCampaigns()
      await loadStats()
      
      // Clear selected if it was the approved one
      if (selectedCampaign === campaignId) {
        setSelectedCampaign(null)
        setCampaignDetails(null)
      }
      
      // Notify parent
      if (onCampaignUpdate) {
        onCampaignUpdate()
      }
    } catch (err: any) {
      alert(`Failed to approve campaign: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleReject = async (campaignId: string) => {
    const campaign = campaigns.find(c => c.id === campaignId)
    if (!campaign) return

    const reason = prompt(`Reject campaign for ${campaign.city}, ${campaign.state} - ${campaign.category}?\n\nReason (optional):`)
    
    if (reason === null) return // User cancelled

    try {
      await api.rejectDraftCampaign(campaignId, reason || undefined)
      alert('Campaign rejected')
      
      // Refresh data
      await loadCampaigns()
      await loadStats()
      
      // Clear selected if it was the rejected one
      if (selectedCampaign === campaignId) {
        setSelectedCampaign(null)
        setCampaignDetails(null)
      }
      
      // Notify parent
      if (onCampaignUpdate) {
        onCampaignUpdate()
      }
    } catch (err: any) {
      alert(`Failed to reject campaign: ${err.response?.data?.detail || err.message}`)
    }
  }

  const getStatusBadgeClass = (status: string) => {
    const baseClass = 'status-badge'
    switch (status) {
      case 'pending_review':
        return `${baseClass} status-pending`
      case 'approved':
        return `${baseClass} status-approved`
      case 'rejected':
        return `${baseClass} status-rejected`
      case 'sent':
        return `${baseClass} status-sent`
      default:
        return baseClass
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'pending_review':
        return 'Pending Review'
      case 'approved':
        return 'Approved'
      case 'rejected':
        return 'Rejected'
      case 'sent':
        return 'Sent'
      default:
        return status
    }
  }

  return (
    <div className="draft-campaigns-panel">
      <Card className="panel-card">
        <div className="panel-header">
          <h2>📋 Draft Campaigns</h2>
          <p className="subtitle">
            Review and approve businesses found in draft mode before sending outreach
          </p>
        </div>

        {/* Statistics Summary */}
        {stats && (
          <div className="stats-summary">
            <div className="stat-item">
              <div className="stat-label">Pending Review</div>
              <div className="stat-value pending">{stats.pending_campaigns}</div>
              <div className="stat-sub">{stats.total_pending_leads} leads</div>
            </div>
            <div className="stat-item">
              <div className="stat-label">Approved</div>
              <div className="stat-value approved">{stats.approved_campaigns}</div>
              <div className="stat-sub">{stats.total_approved_leads} leads</div>
            </div>
            <div className="stat-item">
              <div className="stat-label">Sent</div>
              <div className="stat-value sent">{stats.sent_campaigns}</div>
              <div className="stat-sub">{stats.total_sent_messages} messages</div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading draft campaigns...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && campaigns.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h3>No Draft Campaigns</h3>
            <p>Run a campaign in draft mode to create reviews here</p>
          </div>
        )}

        {/* Campaigns List */}
        {!loading && campaigns.length > 0 && (
          <div className="campaigns-container">
            <div className="campaigns-list">
              {campaigns.map((campaign) => (
                <div
                  key={campaign.id}
                  className={`campaign-card ${selectedCampaign === campaign.id ? 'selected' : ''}`}
                  onClick={() => loadCampaignDetails(campaign.id)}
                >
                  <div className="campaign-header">
                    <div className="campaign-location">
                      <span className="location-icon">📍</span>
                      <span className="location-text">
                        {campaign.city}, {campaign.state}
                      </span>
                    </div>
                    <span className={getStatusBadgeClass(campaign.status)}>
                      {getStatusLabel(campaign.status)}
                    </span>
                  </div>
                  
                  <div className="campaign-category">
                    {campaign.category}
                  </div>
                  
                  <div className="campaign-metrics">
                    <div className="metric">
                      <span className="metric-value">{campaign.qualified_leads_count}</span>
                      <span className="metric-label">Qualified Leads</span>
                    </div>
                    <div className="metric">
                      <span className="metric-value">{campaign.total_businesses_found}</span>
                      <span className="metric-label">Total Found</span>
                    </div>
                    {campaign.qualification_rate && (
                      <div className="metric">
                        <span className="metric-value">{campaign.qualification_rate}%</span>
                        <span className="metric-label">Qual. Rate</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="campaign-footer">
                    <span className="campaign-zone">Zone: {campaign.zone_id}</span>
                    <span className="campaign-date">
                      {new Date(campaign.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  
                  {campaign.status === 'pending_review' && (
                    <div className="campaign-actions">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleApprove(campaign.id)
                        }}
                        className="btn btn-approve"
                      >
                        ✓ Approve
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleReject(campaign.id)
                        }}
                        className="btn btn-reject"
                      >
                        ✗ Reject
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Campaign Details Panel */}
            {selectedCampaign && campaignDetails && (
              <div className="campaign-details">
                {detailsLoading ? (
                  <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading details...</p>
                  </div>
                ) : (
                  <>
                    <div className="details-header">
                      <h3>Campaign Details</h3>
                      <button
                        onClick={() => {
                          setSelectedCampaign(null)
                          setCampaignDetails(null)
                        }}
                        className="btn-close"
                      >
                        ✕
                      </button>
                    </div>
                    
                    <div className="details-info">
                      <div className="info-row">
                        <span className="info-label">Location:</span>
                        <span className="info-value">
                          {campaignDetails.campaign.city}, {campaignDetails.campaign.state}
                        </span>
                      </div>
                      <div className="info-row">
                        <span className="info-label">Category:</span>
                        <span className="info-value">{campaignDetails.campaign.category}</span>
                      </div>
                      <div className="info-row">
                        <span className="info-label">Zone:</span>
                        <span className="info-value">{campaignDetails.campaign.zone_id}</span>
                      </div>
                    </div>
                    
                    <div className="businesses-section">
                      <h4>Businesses ({campaignDetails.businesses.length})</h4>
                      <div className="businesses-list">
                        {campaignDetails.businesses.map((business) => (
                          <div key={business.id} className="business-card">
                            <div className="business-name">{business.name}</div>
                            {business.phone && (
                              <div className="business-detail">📞 {business.phone}</div>
                            )}
                            {business.email && (
                              <div className="business-detail">✉️ {business.email}</div>
                            )}
                            {business.address && (
                              <div className="business-detail small">📍 {business.address}</div>
                            )}
                            {business.rating && (
                              <div className="business-detail">
                                ⭐ {business.rating} ({business.review_count} reviews)
                              </div>
                            )}
                            <div className="business-status">
                              Website: {business.website_status || 'Unknown'}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}

