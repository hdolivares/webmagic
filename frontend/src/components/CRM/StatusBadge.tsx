/**
 * CRM Status Badge Component
 * 
 * Displays color-coded badges for contact statuses.
 * Uses semantic CSS variables for theming and consistency.
 * 
 * @author WebMagic Team
 * @date January 22, 2026
 */
import React from 'react'
import './StatusBadge.css'

export type ContactStatus =
  | 'pending'
  | 'emailed'
  | 'sms_sent'
  | 'opened'
  | 'clicked'
  | 'replied'
  | 'purchased'
  | 'bounced'
  | 'unsubscribed'
  | 'opted_out'
  | 'delivered'
  | 'failed'

export interface StatusBadgeProps {
  status: ContactStatus | string
  label?: string
  className?: string
}

/**
 * Maps backend status values to display labels
 */
const STATUS_LABELS: Record<string, string> = {
  pending: 'New Lead',
  emailed: 'Contacted (Email)',
  sms_sent: 'Contacted (SMS)',
  delivered: 'Delivered',
  opened: 'Opened Email',
  clicked: 'Clicked Link',
  replied: 'Replied',
  purchased: 'Customer',
  bounced: 'Bounced',
  unsubscribed: 'Unsubscribed',
  opted_out: 'Opted Out',
  failed: 'Failed',
}

/**
 * Maps status to CSS class for styling
 */
const STATUS_STYLES: Record<string, string> = {
  pending: 'crm-badge-pending',
  emailed: 'crm-badge-emailed',
  sms_sent: 'crm-badge-sms',
  delivered: 'crm-badge-sms',
  opened: 'crm-badge-opened',
  clicked: 'crm-badge-clicked',
  replied: 'crm-badge-replied',
  purchased: 'crm-badge-customer',
  bounced: 'crm-badge-bounced',
  unsubscribed: 'crm-badge-unsubscribed',
  opted_out: 'crm-badge-unsubscribed',
  failed: 'crm-badge-bounced',
}

/**
 * StatusBadge Component
 * 
 * Usage:
 * ```tsx
 * <StatusBadge status="emailed" />
 * <StatusBadge status="purchased" label="Paying Customer" />
 * ```
 */
export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  className = '',
}) => {
  const displayLabel = label || STATUS_LABELS[status] || status
  const styleClass = STATUS_STYLES[status] || 'crm-badge-pending'

  return (
    <span className={`crm-status-badge ${styleClass} ${className}`}>
      {displayLabel}
    </span>
  )
}

/**
 * StatusIndicator - Compact dot indicator
 * 
 * Usage:
 * ```tsx
 * <StatusIndicator status="replied" />
 * ```
 */
export interface StatusIndicatorProps {
  status: ContactStatus | string
  showLabel?: boolean
  className?: string
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  showLabel = false,
  className = '',
}) => {
  const displayLabel = STATUS_LABELS[status] || status
  const styleClass = STATUS_STYLES[status] || 'crm-badge-pending'

  return (
    <span className={`crm-status-indicator ${styleClass} ${className}`}>
      <span className="crm-status-dot" />
      {showLabel && <span className="crm-status-label">{displayLabel}</span>}
    </span>
  )
}

