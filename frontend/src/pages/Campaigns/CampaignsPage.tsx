/**
 * Campaigns Page - Multi-Channel Outreach Management
 * 
 * Allows creating and managing email/SMS campaigns for businesses with generated sites.
 * Features: Bulk selection, live message preview, channel selection, cost tracking
 * 
 * Architecture: Smart component pattern with local state management
 * Following best practices: Separation of concerns, modular components, semantic styles
 */
import React, { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge } from '@/components/ui'
import { Mail, Eye, MousePointer, MessageSquare } from 'lucide-react'
import ReadyBusinessesPanel from './ReadyBusinessesPanel'
import CampaignCreator from './CampaignCreator'
import type { ReadyBusiness } from '@/types'
import './Campaigns.css'

/**
 * CampaignsPage - Main campaigns management interface
 */
export const CampaignsPage: React.FC = () => {
  const queryClient = useQueryClient()

  // Selected business IDs for campaign creation
  const [selectedBusinessIds, setSelectedBusinessIds] = useState<string[]>([])

  // Fetch ready businesses (with completed sites)
  const {
    data: readyData,
    isLoading: isLoadingReady,
    refetch: refetchReady,
  } = useQuery({
    queryKey: ['campaigns-ready-businesses'],
    queryFn: () => api.getReadyBusinesses(),
  })

  // Fetch existing campaigns
  const { data: campaignsData, isLoading: isLoadingCampaigns } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => api.getCampaigns({ limit: 50 }),
    retry: false,
  })

  // Fetch campaign stats
  const { data: stats } = useQuery({
    queryKey: ['campaign-stats'],
    queryFn: () => api.getCampaignStats(),
    retry: false,
  })

  // Get selected businesses from IDs
  const selectedBusinesses = React.useMemo(() => {
    if (!readyData) return []
    return readyData.businesses.filter(b => selectedBusinessIds.includes(b.id))
  }, [readyData, selectedBusinessIds])

  // Handle successful campaign creation
  const handleCampaignSuccess = () => {
    setSelectedBusinessIds([])
    queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    queryClient.invalidateQueries({ queryKey: ['campaign-stats'] })
    queryClient.invalidateQueries({ queryKey: ['campaigns-ready-businesses'] })
  }

  // Handle business click (for preview)
  const handleBusinessClick = (business: ReadyBusiness) => {
    // Auto-trigger preview for this business
    console.log('Preview business:', business.name)
  }

  // Get status badge styling
  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      sent: 'success',
      delivered: 'success',
      opened: 'info',
      clicked: 'primary',
      failed: 'error',
      pending: 'warning',
      draft: 'secondary',
    }
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>
  }

  return (
    <div className="campaigns-page">
      {/* Page Header */}
      <div style={{ marginBottom: 'var(--campaigns-spacing-xl)' }}>
        <h1
          style={{
            fontSize: '2.25rem',
            fontWeight: 'var(--campaigns-font-weight-bold)',
            color: 'var(--color-text-primary)',
            marginBottom: 'var(--campaigns-spacing-sm)',
          }}
        >
          Campaigns
        </h1>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: '1rem' }}>
          Multi-channel outreach for businesses with generated sites
        </p>
      </div>

      {/* Stats Overview */}
      <div className="campaigns-stats" style={{ marginBottom: 'var(--campaigns-spacing-xl)' }}>
        <div className="campaigns-stat">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--campaigns-spacing-sm)' }}>
            <Mail size={20} style={{ color: 'var(--campaigns-channel-email)' }} />
            <div>
              <div className="campaigns-stat__value">{stats?.sent || 0}</div>
              <div className="campaigns-stat__label">Campaigns Sent</div>
            </div>
          </div>
        </div>

        <div className="campaigns-stat">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--campaigns-spacing-sm)' }}>
            <Eye size={20} style={{ color: 'var(--color-info)' }} />
            <div>
              <div className="campaigns-stat__value">
                {stats?.open_rate ? `${(stats.open_rate).toFixed(1)}%` : '0%'}
              </div>
              <div className="campaigns-stat__label">Open Rate</div>
            </div>
          </div>
        </div>

        <div className="campaigns-stat">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--campaigns-spacing-sm)' }}>
            <MousePointer size={20} style={{ color: 'var(--color-success)' }} />
            <div>
              <div className="campaigns-stat__value">
                {stats?.click_rate ? `${(stats.click_rate).toFixed(1)}%` : '0%'}
              </div>
              <div className="campaigns-stat__label">Click Rate</div>
            </div>
          </div>
        </div>

        <div className="campaigns-stat">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--campaigns-spacing-sm)' }}>
            <MessageSquare size={20} style={{ color: 'var(--campaigns-channel-sms)' }} />
            <div>
              <div className="campaigns-stat__value">{stats?.clicked || 0}</div>
              <div className="campaigns-stat__label">Clicked</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content: Business Selection + Campaign Creator */}
      <div className="campaigns-grid">
        {/* Left: Ready Businesses */}
        <ReadyBusinessesPanel
          businesses={readyData?.businesses || []}
          selectedIds={selectedBusinessIds}
          onSelectionChange={setSelectedBusinessIds}
          onBusinessClick={handleBusinessClick}
          isLoading={isLoadingReady}
        />

        {/* Right: Campaign Creator */}
        <CampaignCreator
          selectedBusinesses={selectedBusinesses}
          onSuccess={handleCampaignSuccess}
          onClear={() => setSelectedBusinessIds([])}
        />
      </div>

      {/* Existing Campaigns Table */}
      <div style={{ marginTop: 'var(--campaigns-spacing-xl)' }}>
        <Card>
          <CardHeader>
            <CardTitle>Recent Campaigns ({campaignsData?.total || 0})</CardTitle>
          </CardHeader>
          <CardBody>
            {isLoadingCampaigns ? (
              <div className="campaigns-loading">
                <div className="spinner" />
              </div>
            ) : campaignsData && campaignsData.campaigns.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="table">
                  <thead className="table-header">
                    <tr>
                      <th className="table-header-cell">Recipient</th>
                      <th className="table-header-cell">Channel</th>
                      <th className="table-header-cell">Subject/Message</th>
                      <th className="table-header-cell">Status</th>
                      <th className="table-header-cell">Sent</th>
                    </tr>
                  </thead>
                  <tbody>
                    {campaignsData.campaigns.map((campaign) => (
                      <tr key={campaign.id} className="table-row">
                        <td className="table-cell">
                          <div>
                            <p className="font-medium">
                              {campaign.recipient_name || 'Unknown'}
                            </p>
                            <p className="text-xs text-text-secondary">
                              {campaign.recipient_email}
                            </p>
                          </div>
                        </td>
                        <td className="table-cell">
                          <Badge variant="info">
                            {campaign.subject_line ? '📧' : '💬'}
                          </Badge>
                        </td>
                        <td className="table-cell">
                          {campaign.subject_line || 'SMS Campaign'}
                        </td>
                        <td className="table-cell">{getStatusBadge(campaign.status)}</td>
                        <td className="table-cell text-text-secondary">
                          {campaign.sent_at
                            ? new Date(campaign.sent_at).toLocaleDateString()
                            : 'Not sent'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="campaigns-empty">
                <div className="campaigns-empty__icon">📭</div>
                <h4 className="campaigns-empty__title">No Campaigns Yet</h4>
                <p className="campaigns-empty__description">
                  Create your first campaign by selecting businesses above
                </p>
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  )
}

export default CampaignsPage
