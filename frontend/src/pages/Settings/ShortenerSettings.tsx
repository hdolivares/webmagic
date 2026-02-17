/**
 * URL Shortener Settings - Configure domain, slug length, expiration, and view stats.
 */
import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Card } from '@/components/ui'
import './ShortenerSettings.css'

interface ShortenerConfig {
  domain: string
  protocol: string
  slug_length: number
  default_expiry_days: number
  enabled: boolean
}

interface ShortenerStats {
  total_links: number
  active_links: number
  total_clicks: number
  links_by_type: Record<string, number>
}

export const ShortenerSettings: React.FC = () => {
  const queryClient = useQueryClient()

  const [local, setLocal] = useState<ShortenerConfig>({
    domain: '',
    protocol: 'https',
    slug_length: 6,
    default_expiry_days: 0,
    enabled: true,
  })
  const [dirty, setDirty] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')

  const { data: config, isLoading: configLoading } = useQuery<ShortenerConfig>({
    queryKey: ['shortener-config'],
    queryFn: () => api.getShortenerConfig(),
  })

  const { data: stats } = useQuery<ShortenerStats>({
    queryKey: ['shortener-stats'],
    queryFn: () => api.getShortenerStats(),
  })

  useEffect(() => {
    if (config) {
      setLocal({
        domain: config.domain || '',
        protocol: config.protocol || 'https',
        slug_length: config.slug_length || 6,
        default_expiry_days: config.default_expiry_days || 0,
        enabled: config.enabled ?? true,
      })
    }
  }, [config])

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      api.updateSystemSetting(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shortener-config'] })
      queryClient.invalidateQueries({ queryKey: ['shortener-stats'] })
    },
  })

  const handleSaveAll = async () => {
    setSaveStatus('saving')
    try {
      await Promise.all([
        updateMutation.mutateAsync({ key: 'shortener_domain', value: local.domain }),
        updateMutation.mutateAsync({ key: 'shortener_protocol', value: local.protocol }),
        updateMutation.mutateAsync({ key: 'shortener_slug_length', value: String(local.slug_length) }),
        updateMutation.mutateAsync({ key: 'shortener_default_expiry_days', value: String(local.default_expiry_days) }),
        updateMutation.mutateAsync({ key: 'shortener_enabled', value: String(local.enabled) }),
      ])
      setDirty(false)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch {
      setSaveStatus('idle')
    }
  }

  const handleChange = <K extends keyof ShortenerConfig>(key: K, value: ShortenerConfig[K]) => {
    setLocal(prev => ({ ...prev, [key]: value }))
    setDirty(true)
  }

  if (configLoading) {
    return (
      <Card>
        <div className="shortener-settings-loading">Loading shortener configuration...</div>
      </Card>
    )
  }

  const exampleSlug = 'a1B2c3'.slice(0, local.slug_length || 6)
  const exampleUrl = local.domain
    ? `${local.protocol}://${local.domain}/${exampleSlug}`
    : `https://your-domain.com/${exampleSlug}`

  return (
    <div className="shortener-settings">
      <Card>
        <div className="shortener-settings__intro">
          <h2 className="shortener-settings__title">URL Shortener</h2>
          <p className="shortener-settings__description">
            Shorten URLs for SMS campaigns to save characters and stay within the 160-character single-segment limit.
            Configure your short domain and settings below.
          </p>
        </div>

        {/* Stats summary */}
        {stats && (
          <div className="shortener-settings__stats">
            <div className="shortener-settings__stat">
              <span className="shortener-settings__stat-value">{stats.total_links}</span>
              <span className="shortener-settings__stat-label">Total Links</span>
            </div>
            <div className="shortener-settings__stat">
              <span className="shortener-settings__stat-value">{stats.active_links}</span>
              <span className="shortener-settings__stat-label">Active</span>
            </div>
            <div className="shortener-settings__stat">
              <span className="shortener-settings__stat-value">{stats.total_clicks}</span>
              <span className="shortener-settings__stat-label">Total Clicks</span>
            </div>
          </div>
        )}

        {/* Configuration fields */}
        <div className="shortener-settings__fields">

          {/* Enable / Disable */}
          <div className="shortener-settings__field">
            <label className="shortener-settings__label">Enabled</label>
            <div className="shortener-settings__toggle-row">
              <button
                type="button"
                className={`shortener-settings__toggle ${local.enabled ? 'shortener-settings__toggle--on' : ''}`}
                onClick={() => handleChange('enabled', !local.enabled)}
                role="switch"
                aria-checked={local.enabled}
              >
                <span className="shortener-settings__toggle-knob" />
              </button>
              <span className="shortener-settings__toggle-label">
                {local.enabled ? 'Shortener is active' : 'Shortener is disabled (original URLs will be used)'}
              </span>
            </div>
          </div>

          {/* Domain */}
          <div className="shortener-settings__field">
            <label className="shortener-settings__label">Short Domain</label>
            <input
              type="text"
              className="shortener-settings__input"
              value={local.domain}
              onChange={e => handleChange('domain', e.target.value.trim())}
              placeholder="e.g., wm.gt or go.lavish.solutions"
            />
            <p className="shortener-settings__hint">
              The domain that short URLs will use. Must be pointed to your server via DNS/Nginx.
            </p>
          </div>

          {/* Protocol */}
          <div className="shortener-settings__field">
            <label className="shortener-settings__label">Protocol</label>
            <select
              className="shortener-settings__select"
              value={local.protocol}
              onChange={e => handleChange('protocol', e.target.value)}
            >
              <option value="https">https (recommended)</option>
              <option value="http">http</option>
            </select>
          </div>

          {/* Slug Length */}
          <div className="shortener-settings__field">
            <label className="shortener-settings__label">Slug Length</label>
            <input
              type="number"
              className="shortener-settings__input shortener-settings__input--small"
              value={local.slug_length}
              onChange={e => handleChange('slug_length', Math.max(4, Math.min(12, parseInt(e.target.value) || 6)))}
              min={4}
              max={12}
            />
            <p className="shortener-settings__hint">
              Characters per slug. 6 = 56B combinations, 4 = 14M (minimum for production).
            </p>
          </div>

          {/* Default Expiry */}
          <div className="shortener-settings__field">
            <label className="shortener-settings__label">Default Expiry (days)</label>
            <input
              type="number"
              className="shortener-settings__input shortener-settings__input--small"
              value={local.default_expiry_days}
              onChange={e => handleChange('default_expiry_days', Math.max(0, parseInt(e.target.value) || 0))}
              min={0}
            />
            <p className="shortener-settings__hint">
              Default expiration for campaign and custom links. 0 = never expire.
              Site preview links always persist regardless of this setting.
            </p>
          </div>
        </div>

        {/* Example URL */}
        <div className="shortener-settings__example">
          <span className="shortener-settings__example-label">Example short URL:</span>
          <code className="shortener-settings__example-url">{exampleUrl}</code>
        </div>

        {/* Save button */}
        <div className="shortener-settings__actions">
          <button
            type="button"
            className="shortener-settings__btn shortener-settings__btn--primary"
            onClick={handleSaveAll}
            disabled={!dirty || saveStatus === 'saving'}
          >
            {saveStatus === 'saving' ? 'Saving...' : saveStatus === 'saved' ? 'Saved!' : 'Save configuration'}
          </button>
        </div>
      </Card>
    </div>
  )
}
