/**
 * CampaignCreator Component
 * 
 * Main form for creating SMS/Email campaigns
 * Orchestrates ToneSelector, MessagePreview, and bulk actions
 * Following best practices: Single responsibility, controlled components, error handling
 */
import React, { useState, useEffect, useMemo } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/services/api'
import type { ReadyBusiness, SMSPreviewResponse, BulkCampaignCreateRequest } from '@/types'
import ToneSelector from './ToneSelector'
import MessagePreview from './MessagePreview'
import './Campaigns.css'

interface CampaignCreatorProps {
  selectedBusinesses: ReadyBusiness[]
  onSuccess?: () => void
  onClear?: () => void
}

/**
 * CampaignCreator - Create and preview campaigns for selected businesses
 */
export const CampaignCreator: React.FC<CampaignCreatorProps> = ({
  selectedBusinesses,
  onSuccess,
  onClear,
}) => {
  // State management
  const [channel, setChannel] = useState<'auto' | 'email' | 'sms'>('auto')
  const [tone, setTone] = useState<'friendly' | 'professional' | 'urgent'>('friendly')
  const [preview, setPreview] = useState<SMSPreviewResponse | null>(null)
  const [previewBusinessId, setPreviewBusinessId] = useState<string | null>(null)

  // Preview mutation
  const previewMutation = useMutation({
    mutationFn: (businessId: string) =>
      api.previewSMSMessage({
        business_id: businessId,
        variant: tone,
      }),
    onSuccess: (data) => {
      setPreview(data)
    },
  })

  // Bulk campaign creation mutation
  const createMutation = useMutation({
    mutationFn: (sendNow: boolean) => {
      const request: BulkCampaignCreateRequest = {
        business_ids: selectedBusinesses.map(b => b.id),
        channel,
        variant: tone,
        send_immediately: sendNow,
      }
      return api.createBulkCampaigns(request)
    },
    onSuccess: (data) => {
      // Show success message
      alert(
        `✅ ${data.message}\n\n` +
        `📧 Email: ${data.by_channel.email || 0}\n` +
        `💬 SMS: ${data.by_channel.sms || 0}\n` +
        `💰 SMS Cost: $${data.estimated_sms_cost.toFixed(4)}`
      )
      onSuccess?.()
    },
    onError: (error: any) => {
      alert(`❌ Failed to create campaigns: ${error.message}`)
    },
  })

  // Auto-preview first selected business when tone changes
  useEffect(() => {
    if (selectedBusinesses.length > 0 && selectedBusinesses[0].phone) {
      const firstBiz = selectedBusinesses[0]
      if (previewBusinessId !== firstBiz.id || !preview) {
        setPreviewBusinessId(firstBiz.id)
        previewMutation.mutate(firstBiz.id)
      }
    }
  }, [tone, selectedBusinesses])

  // Calculate stats
  const totalCost = useMemo(() => {
    const smsCount = selectedBusinesses.filter(b => {
      if (channel === 'email') return false
      if (channel === 'sms') return b.phone
      // auto: SMS only if no email
      return b.phone && !b.email
    }).length

    return smsCount * 0.0079 // Average cost per SMS
  }, [selectedBusinesses, channel])

  const channelBreakdown = useMemo(() => {
    let email = 0
    let sms = 0

    selectedBusinesses.forEach(b => {
      if (channel === 'auto') {
        if (b.email) email++
        else if (b.phone) sms++
      } else if (channel === 'email' && b.email) {
        email++
      } else if (channel === 'sms' && b.phone) {
        sms++
      }
    })

    return { email, sms }
  }, [selectedBusinesses, channel])

  // Empty state
  if (selectedBusinesses.length === 0) {
    return (
      <div className="campaigns-card">
        <div className="campaigns-card__header">
          <h3 className="campaigns-card__title">Create Campaign</h3>
        </div>
        <div className="campaigns-card__body">
          <div className="campaigns-empty">
            <div className="campaigns-empty__icon">✉️</div>
            <h4 className="campaigns-empty__title">No Businesses Selected</h4>
            <p className="campaigns-empty__description">
              Select one or more businesses from the list to create campaigns
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="campaigns-card">
      <div className="campaigns-card__header">
        <h3 className="campaigns-card__title">
          Create Campaign ({selectedBusinesses.length} selected)
        </h3>
        {onClear && (
          <button
            type="button"
            className="campaigns-button campaigns-button--secondary"
            onClick={onClear}
            style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
          >
            Clear Selection
          </button>
        )}
      </div>

      <div className="campaigns-card__body">
        {/* Channel Selector */}
        <div className="selector-group" style={{ marginBottom: 'var(--campaigns-spacing-lg)' }}>
          <label className="selector-label">Campaign Channel</label>
          <div className="selector-options">
            <button
              type="button"
              className={`selector-option ${channel === 'auto' ? 'selector-option--selected' : ''}`}
              onClick={() => setChannel('auto')}
            >
              <span className="selector-option__icon">🤖</span>
              <div>Auto</div>
              <div style={{ fontSize: '0.7rem', opacity: 0.8 }}>Email first, SMS if no email</div>
            </button>
            <button
              type="button"
              className={`selector-option ${channel === 'email' ? 'selector-option--selected' : ''}`}
              onClick={() => setChannel('email')}
            >
              <span className="selector-option__icon">📧</span>
              <div>Email Only</div>
              <div style={{ fontSize: '0.7rem', opacity: 0.8 }}>Free (requires email)</div>
            </button>
            <button
              type="button"
              className={`selector-option ${channel === 'sms' ? 'selector-option--selected' : ''}`}
              onClick={() => setChannel('sms')}
            >
              <span className="selector-option__icon">💬</span>
              <div>SMS Only</div>
              <div style={{ fontSize: '0.7rem', opacity: 0.8 }}>~$0.01 each</div>
            </button>
          </div>
        </div>

        {/* Tone Selector (for SMS) */}
        <div style={{ marginBottom: 'var(--campaigns-spacing-lg)' }}>
          <ToneSelector value={tone} onChange={setTone} />
        </div>

        {/* Message Preview */}
        <MessagePreview
          preview={preview}
          isLoading={previewMutation.isPending}
          error={previewMutation.isError ? 'Failed to generate preview' : null}
        />

        {/* Campaign Stats */}
        <div
          style={{
            marginTop: 'var(--campaigns-spacing-lg)',
            padding: 'var(--campaigns-spacing-md)',
            background: 'var(--color-bg-secondary)',
            borderRadius: 'var(--campaigns-radius-md)',
            fontSize: '0.875rem',
          }}
        >
          <div style={{ fontWeight: 'var(--campaigns-font-weight-medium)', marginBottom: 'var(--campaigns-spacing-sm)' }}>
            Campaign Summary
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', color: 'var(--color-text-secondary)' }}>
            <div>📧 Email: {channelBreakdown.email} (Free)</div>
            <div>💬 SMS: {channelBreakdown.sms} (~${totalCost.toFixed(4)})</div>
            <div style={{ paddingTop: '0.375rem', borderTop: '1px solid var(--color-border-primary)', fontWeight: 'var(--campaigns-font-weight-semibold)', color: 'var(--color-text-primary)' }}>
              💰 Total Cost: ${totalCost.toFixed(4)}
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="campaigns-card__footer">
        <div style={{ display: 'flex', gap: 'var(--campaigns-spacing-sm)', justifyContent: 'flex-end' }}>
          <button
            type="button"
            className="campaigns-button campaigns-button--secondary"
            onClick={() => createMutation.mutate(false)}
            disabled={createMutation.isPending}
          >
            Create Drafts
          </button>
          <button
            type="button"
            className="campaigns-button campaigns-button--primary"
            onClick={() => {
              if (window.confirm(
                `Send campaigns to ${selectedBusinesses.length} businesses now?\n\n` +
                `Email: ${channelBreakdown.email}\n` +
                `SMS: ${channelBreakdown.sms} (~$${totalCost.toFixed(4)})\n\n` +
                `This action cannot be undone.`
              )) {
                createMutation.mutate(true)
              }
            }}
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? 'Creating...' : `Create & Send Now`}
          </button>
        </div>
      </div>
    </div>
  )
}

export default CampaignCreator
