/**
 * MessagePreview Component
 * 
 * Displays SMS message preview with character count, segments, and cost
 * Following best practices: Pure component, clear data display, loading states
 */
import React from 'react'
import type { SMSPreviewResponse } from '@/types'
import './Campaigns.css'

interface MessagePreviewProps {
  preview: SMSPreviewResponse | null
  isLoading: boolean
  error?: string | null
}

/**
 * MessagePreview - Show SMS message preview with metadata
 */
export const MessagePreview: React.FC<MessagePreviewProps> = ({
  preview,
  isLoading,
  error,
}) => {
  // Loading state
  if (isLoading) {
    return (
      <div className="message-preview">
        <div className="message-preview__label">Message Preview</div>
        <div className="campaigns-loading">
          <div className="spinner" />
          <span style={{ marginLeft: '0.5rem' }}>Generating preview...</span>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="message-preview">
        <div className="message-preview__label">Message Preview</div>
        <div style={{ color: 'var(--color-error)', fontSize: '0.875rem', padding: '1rem' }}>
          {error}
        </div>
      </div>
    )
  }

  // Empty state
  if (!preview) {
    return (
      <div className="message-preview">
        <div className="message-preview__label">Message Preview</div>
        <div className="campaigns-empty" style={{ padding: '2rem 1rem' }}>
          <div className="campaigns-empty__icon">💬</div>
          <p className="campaigns-empty__description">
            Select a business to preview the SMS message
          </p>
        </div>
      </div>
    )
  }

  // Determine if message is optimal (1 segment)
  const isOptimal = preview.segment_count === 1
  const segmentColor = isOptimal ? 'var(--campaigns-tone-friendly)' : 'var(--campaigns-status-pending)'

  return (
    <div className="message-preview">
      <div className="message-preview__label">
        Message Preview for {preview.business_name}
      </div>

      {/* SMS Message Content */}
      <div className="message-preview__content">
        {preview.sms_body}
      </div>

      {/* Metadata */}
      <div className="message-preview__meta">
        <div className="message-preview__meta-item">
          <span className="message-preview__meta-label">Characters</span>
          <span className="message-preview__meta-value">
            {preview.character_count} / 160
          </span>
        </div>

        <div className="message-preview__meta-item">
          <span className="message-preview__meta-label">Segments</span>
          <span className="message-preview__meta-value" style={{ color: segmentColor }}>
            {preview.segment_count}
            {isOptimal && ' ✓'}
          </span>
        </div>

        <div className="message-preview__meta-item">
          <span className="message-preview__meta-label">Cost</span>
          <span className="message-preview__meta-value">
            ${preview.estimated_cost.toFixed(4)}
          </span>
        </div>

        <div className="message-preview__meta-item">
          <span className="message-preview__meta-label">Tone</span>
          <span className="message-preview__meta-value" style={{ textTransform: 'capitalize' }}>
            {preview.variant}
          </span>
        </div>
      </div>

      {/* Optimization Tip */}
      {!isOptimal && (
        <div
          style={{
            marginTop: 'var(--campaigns-spacing-md)',
            padding: 'var(--campaigns-spacing-sm)',
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            borderRadius: 'var(--campaigns-radius-sm)',
            fontSize: '0.75rem',
            color: 'var(--campaigns-status-pending)',
          }}
        >
          ⚠️ This message uses {preview.segment_count} SMS segments, which costs {preview.segment_count}x more.
          Consider using a shorter message.
        </div>
      )}
    </div>
  )
}

export default MessagePreview
