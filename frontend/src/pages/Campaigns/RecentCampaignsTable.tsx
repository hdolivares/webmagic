/**
 * RecentCampaignsTable - Presentational table for campaigns list
 *
 * Displays campaigns with optional Send action for draft/pending campaigns.
 * Separation of concerns: receives data and callbacks; no data fetching.
 */
import React from 'react'
import { Badge } from '@/components/ui'
import type { Campaign } from '@/types'
import './Campaigns.css'

/** Status values that allow sending (backend accepts pending | scheduled) */
const SENDABLE_STATUSES = ['pending', 'scheduled']

const STATUS_BADGE_VARIANTS: Record<string, 'success' | 'info' | 'primary' | 'error' | 'warning' | 'secondary'> = {
  sent: 'success',
  delivered: 'success',
  opened: 'info',
  clicked: 'primary',
  failed: 'error',
  pending: 'warning',
  scheduled: 'warning',
  draft: 'secondary',
}

function getStatusBadge(status: string) {
  return <Badge variant={STATUS_BADGE_VARIANTS[status] ?? 'secondary'}>{status}</Badge>
}

function formatRecipient(campaign: Campaign): string {
  return campaign.channel === 'sms'
    ? (campaign.recipient_phone ?? '—')
    : (campaign.recipient_email ?? '—')
}

export interface RecentCampaignsTableProps {
  campaigns: Campaign[]
  isLoading: boolean
  /** Called when user clicks Send for a draft/pending campaign */
  onSendCampaign?: (campaignId: string) => void
  /** ID of campaign currently being sent (disables that row's button and shows loading) */
  sendingCampaignId?: string | null
}

/**
 * Renders the recent campaigns table with optional Send action for sendable campaigns.
 */
export const RecentCampaignsTable: React.FC<RecentCampaignsTableProps> = ({
  campaigns,
  isLoading,
  onSendCampaign,
  sendingCampaignId = null,
}) => {
  const canSend = (status: string) => SENDABLE_STATUSES.includes(status)

  if (isLoading) {
    return (
      <div className="campaigns-loading">
        <div className="spinner" />
      </div>
    )
  }

  if (!campaigns.length) {
    return (
      <div className="campaigns-empty">
        <div className="campaigns-empty__icon">📭</div>
        <h4 className="campaigns-empty__title">No Campaigns Yet</h4>
        <p className="campaigns-empty__description">
          Create your first campaign by selecting businesses above
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="table campaigns-table">
        <thead className="table-header">
          <tr>
            <th className="table-header-cell">Recipient</th>
            <th className="table-header-cell">Channel</th>
            <th className="table-header-cell">Subject/Message</th>
            <th className="table-header-cell">Status</th>
            <th className="table-header-cell">Sent</th>
            {(onSendCampaign != null) && (
              <th className="table-header-cell campaigns-table__actions-header">Actions</th>
            )}
          </tr>
        </thead>
        <tbody>
          {campaigns.map((campaign) => {
            const isSending = sendingCampaignId === campaign.id
            const showSend = canSend(campaign.status)

            return (
              <tr key={campaign.id} className="table-row">
                <td className="table-cell">
                  <div>
                    <p className="font-medium">
                      {campaign.business_name ?? campaign.recipient_name ?? 'Unknown'}
                    </p>
                    <p className="text-xs text-text-secondary">{formatRecipient(campaign)}</p>
                  </div>
                </td>
                <td className="table-cell">
                  <Badge variant="info">
                    {campaign.channel === 'sms' ? '💬 SMS' : '📧 Email'}
                  </Badge>
                </td>
                <td
                  className="table-cell"
                  style={{
                    maxWidth: 280,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {campaign.channel === 'sms'
                    ? (campaign.sms_body ?? 'SMS Campaign')
                    : (campaign.subject_line ?? '—')}
                </td>
                <td className="table-cell">
                  <div className="campaigns-table__status-cell">
                    {getStatusBadge(campaign.status)}
                    {campaign.status === 'failed' && campaign.error_message && (
                      <p className="campaigns-table__error-message" title={campaign.error_message}>
                        {campaign.error_message}
                      </p>
                    )}
                  </div>
                </td>
                <td className="table-cell text-text-secondary">
                  {campaign.sent_at
                    ? new Date(campaign.sent_at).toLocaleDateString()
                    : 'Not sent'}
                </td>
                {(onSendCampaign != null) && (
                  <td className="table-cell campaigns-table__actions-cell">
                    {showSend && (
                      <button
                        type="button"
                        className="campaigns-button campaigns-button--primary campaigns-button--small"
                        onClick={() => onSendCampaign(campaign.id)}
                        disabled={isSending}
                        aria-busy={isSending}
                        aria-label={`Send campaign to ${campaign.business_name ?? campaign.recipient_name ?? 'recipient'}`}
                      >
                        {isSending ? (
                          <>
                            <span className="campaigns-table__spinner" aria-hidden />
                            Sending…
                          </>
                        ) : (
                          'Send'
                        )}
                      </button>
                    )}
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default RecentCampaignsTable
