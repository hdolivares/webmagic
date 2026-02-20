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
  // Business clicked for message preview (show SMS preview in right panel)
  const [previewBusiness, setPreviewBusiness] = useState<ReadyBusiness | null>(null)

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

  // Handle business click: show SMS preview in right panel
  const handleBusinessClick = (business: ReadyBusiness) => {
    setPreviewBusiness(business)
  }

  // Add previewed business to campaign selection (from "Add to campaign" button)
  const handleAddToCampaign = (business: ReadyBusiness) => {
    setSelectedBusinessIds(prev => (prev.includes(business.id) ? prev : [...prev, business.id]))
    setPreviewBusiness(null)
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

      {/* Best times and days — always visible */}
      <div style={{ marginBottom: 'var(--campaigns-spacing-xl)' }}>
        <Card>
          <CardHeader>
            <CardTitle style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              📊 Best times and days — the data
            </CardTitle>
          </CardHeader>
          <CardBody>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
              {/* Days table */}
              <div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--color-border-primary)' }}>
                      <th style={{ textAlign: 'left', padding: '0.4rem 0.5rem', color: 'var(--color-text-secondary)', fontWeight: 600 }}>Day</th>
                      <th style={{ textAlign: 'left', padding: '0.4rem 0.5rem', color: 'var(--color-text-secondary)', fontWeight: 600 }}>Performance</th>
                      <th style={{ textAlign: 'left', padding: '0.4rem 0.5rem', color: 'var(--color-text-secondary)', fontWeight: 600 }}>Why</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { day: 'Tuesday',   stars: 5, rank: 'Top 1', why: 'People are settled into the week, focused',    top: true },
                      { day: 'Wednesday', stars: 5, rank: 'Top 2', why: 'Mid-week peak engagement',                      top: true },
                      { day: 'Thursday',  stars: 4, rank: 'Top 3', why: 'Best single day by click-through data',         top: true },
                      { day: 'Monday',    stars: 2, rank: '',      why: 'Hectic, people clearing weekend backlog',       top: false },
                      { day: 'Friday',    stars: 2, rank: '',      why: 'Mentally checking out by afternoon',            top: false },
                      { day: 'Weekend',   stars: 1, rank: '',      why: 'Low business context, feels intrusive',         top: false },
                    ].map(row => (
                      <tr key={row.day} style={{ borderBottom: '1px solid var(--color-border-primary)' }}>
                        <td style={{ padding: '0.5rem', fontWeight: row.top ? 700 : 400, color: 'var(--color-text-primary)' }}>{row.day}</td>
                        <td style={{ padding: '0.5rem', whiteSpace: 'nowrap' }}>
                          <span style={{ color: '#f59e0b' }}>{'★'.repeat(row.stars)}{'☆'.repeat(5 - row.stars)}</span>
                          {row.rank && <span style={{ marginLeft: '0.4rem', fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-success)' }}>{row.rank}</span>}
                        </td>
                        <td style={{ padding: '0.5rem', color: 'var(--color-text-secondary)' }}>{row.why}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Windows table */}
              <div>
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>
                  Best time windows <em>(in recipient's local timezone)</em>:
                </p>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--color-border-primary)' }}>
                      <th style={{ textAlign: 'left', padding: '0.4rem 0.5rem', color: 'var(--color-text-secondary)', fontWeight: 600 }}>Window</th>
                      <th style={{ textAlign: 'left', padding: '0.4rem 0.5rem', color: 'var(--color-text-secondary)', fontWeight: 600 }}>Uplift</th>
                      <th style={{ textAlign: 'left', padding: '0.4rem 0.5rem', color: 'var(--color-text-secondary)', fontWeight: 600 }}>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { window: '1 PM – 5 PM',  uplift: '+33% engagement vs morning', notes: 'The single best window per Textla data',     highlight: true,  illegal: false },
                      { window: '7 PM – 9 PM',  uplift: 'Strong',                     notes: 'People are relaxed, scroll more',            highlight: false, illegal: false },
                      { window: '10 AM – 12 PM',uplift: 'Good',                       notes: 'Post-morning-rush settle-in spike',          highlight: false, illegal: false },
                      { window: 'Before 8 AM',  uplift: '🚫 ILLEGAL',                 notes: 'TCPA quiet hours — do not send',             highlight: false, illegal: true  },
                      { window: 'After 9 PM',   uplift: '🚫 ILLEGAL',                 notes: 'TCPA quiet hours — do not send',             highlight: false, illegal: true  },
                    ].map(row => (
                      <tr key={row.window} style={{ borderBottom: '1px solid var(--color-border-primary)', background: row.illegal ? 'rgba(239,68,68,0.05)' : undefined }}>
                        <td style={{ padding: '0.5rem', fontWeight: row.highlight ? 700 : 400, color: row.illegal ? 'var(--color-error)' : 'var(--color-text-primary)' }}>{row.window}</td>
                        <td style={{ padding: '0.5rem', fontWeight: row.highlight ? 700 : 400, color: row.illegal ? 'var(--color-error)' : row.highlight ? 'var(--color-success)' : 'var(--color-text-secondary)' }}>{row.uplift}</td>
                        <td style={{ padding: '0.5rem', color: row.illegal ? 'var(--color-error)' : 'var(--color-text-secondary)', fontSize: '0.8rem' }}>{row.notes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--color-text-tertiary)' }}>
                  Autopilot enforces these windows automatically. Manual "Send Now" respects TCPA quiet hours only.
                </p>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Main Content: Business Selection + Campaign Creator */}
      <div className="campaigns-grid">
        {/* Left: Ready Businesses */}
        <ReadyBusinessesPanel
          businesses={readyData?.businesses || []}
          selectedIds={selectedBusinessIds}
          previewBusinessId={previewBusiness?.id ?? null}
          onSelectionChange={setSelectedBusinessIds}
          onBusinessClick={handleBusinessClick}
          isLoading={isLoadingReady}
        />

        {/* Right: Campaign Creator + Message Preview (2/3 width) */}
        <CampaignCreator
          key={previewBusiness?.id ?? 'no-preview'}
          selectedBusinesses={selectedBusinesses}
          previewBusiness={previewBusiness}
          onPreviewClear={() => setPreviewBusiness(null)}
          onAddToCampaign={handleAddToCampaign}
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
