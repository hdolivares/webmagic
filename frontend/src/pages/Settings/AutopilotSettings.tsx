/**
 * Autopilot Settings
 *
 * Controls whether the system runs automatically on schedule:
 *   Scrape → Validate → Generate sites → Create campaigns → Send SMS
 *
 * Also sets a target: how many businesses without websites should be in the
 * pipeline before scraping pauses (prevents over-spending on unused leads).
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Zap, ZapOff, CheckCircle2, AlertCircle, Info } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardBody } from '@/components/ui'
import { api } from '@/services/api'

export const AutopilotSettings = () => {
  const queryClient = useQueryClient()
  const [enabled, setEnabled] = useState(false)
  const [target, setTarget] = useState(30)
  const [saved, setSaved] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['autopilot-settings'],
    queryFn: () => api.getAutopilotSettings(),
  })

  useEffect(() => {
    if (data) {
      setEnabled(data.enabled)
      setTarget(data.target_businesses)
    }
  }, [data])

  const mutation = useMutation({
    mutationFn: () => api.updateAutopilotSettings(enabled, target),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['autopilot-settings'] })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
  })

  if (isLoading) {
    return (
      <Card>
        <CardBody>
          <div style={{ color: 'var(--color-text-secondary)', padding: '1rem' }}>
            Loading autopilot settings…
          </div>
        </CardBody>
      </Card>
    )
  }

  const pipelineSteps = [
    { icon: '🔍', label: 'Scrape territories', sub: 'Outscraper — every 6 hours' },
    { icon: '🔎', label: 'Validate & discover websites', sub: 'ScrapingDog + LLM' },
    { icon: '🏗️', label: 'Generate websites', sub: 'Creative pipeline — every hour' },
    { icon: '📣', label: 'Create campaigns', sub: 'Auto-create on publish — every 30 min' },
    { icon: '💬', label: 'Send SMS', sub: 'Scheduled with timezone guard — every 5 min' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Main toggle card */}
      <Card>
        <CardHeader>
          <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {enabled ? (
              <Zap size={20} style={{ color: 'var(--color-success)' }} />
            ) : (
              <ZapOff size={20} style={{ color: 'var(--color-text-tertiary)' }} />
            )}
            Autopilot Mode
          </CardTitle>
        </CardHeader>
        <CardBody>
          <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            When enabled, the system runs fully automatically on schedule — from scraping territories
            to sending outreach SMS. Turn this off while testing or making changes.
          </p>

          {/* Big toggle */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '1rem 1.25rem',
              background: enabled
                ? 'rgba(34, 197, 94, 0.08)'
                : 'var(--color-bg-secondary)',
              border: `1px solid ${enabled ? 'rgba(34, 197, 94, 0.3)' : 'var(--color-border-primary)'}`,
              borderRadius: '0.75rem',
              marginBottom: '1.5rem',
            }}
          >
            <div>
              <div style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--color-text-primary)' }}>
                {enabled ? 'Autopilot is ON' : 'Autopilot is OFF'}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: '0.2rem' }}>
                {enabled
                  ? 'System is running all pipeline stages automatically'
                  : 'All scheduled tasks are paused — manual mode active'}
              </div>
            </div>
            {/* Toggle switch */}
            <button
              type="button"
              onClick={() => setEnabled(v => !v)}
              style={{
                position: 'relative',
                width: '52px',
                height: '28px',
                borderRadius: '14px',
                border: 'none',
                cursor: 'pointer',
                background: enabled ? 'var(--color-success)' : 'var(--color-border-primary)',
                transition: 'background 0.2s',
                flexShrink: 0,
              }}
              aria-label="Toggle autopilot"
            >
              <span
                style={{
                  position: 'absolute',
                  top: '3px',
                  left: enabled ? '27px' : '3px',
                  width: '22px',
                  height: '22px',
                  borderRadius: '50%',
                  background: '#fff',
                  transition: 'left 0.2s',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                }}
              />
            </button>
          </div>

          {/* Target goal */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label
              htmlFor="target-businesses"
              style={{
                display: 'block',
                fontWeight: 600,
                marginBottom: '0.5rem',
                color: 'var(--color-text-primary)',
                fontSize: '0.9rem',
              }}
            >
              Target: businesses in generation queue
            </label>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
              Scraping will automatically pause once this many US businesses (confirmed
              without websites) are queued. Prevents over-spending on leads you haven't
              processed yet. Recommended: 30–50.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <input
                id="target-businesses"
                type="number"
                min={1}
                max={500}
                value={target}
                onChange={e => setTarget(Math.max(1, parseInt(e.target.value) || 1))}
                style={{
                  width: '100px',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid var(--color-border-primary)',
                  borderRadius: '0.5rem',
                  background: 'var(--color-bg-primary)',
                  color: 'var(--color-text-primary)',
                  fontSize: '1rem',
                  fontWeight: 600,
                }}
              />
              <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
                businesses
              </span>
              {/* Quick presets */}
              {[20, 30, 50].map(n => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setTarget(n)}
                  style={{
                    padding: '0.25rem 0.75rem',
                    borderRadius: '0.375rem',
                    border: `1px solid ${target === n ? 'var(--color-primary)' : 'var(--color-border-primary)'}`,
                    background: target === n ? 'var(--color-primary)' : 'transparent',
                    color: target === n ? '#fff' : 'var(--color-text-secondary)',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                  }}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          {/* Save button */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button
              type="button"
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              style={{
                padding: '0.625rem 1.5rem',
                borderRadius: '0.5rem',
                border: 'none',
                background: 'var(--color-primary)',
                color: '#fff',
                fontWeight: 600,
                fontSize: '0.9rem',
                cursor: mutation.isPending ? 'not-allowed' : 'pointer',
                opacity: mutation.isPending ? 0.7 : 1,
              }}
            >
              {mutation.isPending ? 'Saving…' : 'Save settings'}
            </button>

            {saved && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', color: 'var(--color-success)', fontSize: '0.875rem' }}>
                <CheckCircle2 size={16} /> Saved
              </span>
            )}
            {mutation.isError && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', color: 'var(--color-error)', fontSize: '0.875rem' }}>
                <AlertCircle size={16} /> Failed to save
              </span>
            )}
          </div>
        </CardBody>
      </Card>

      {/* Pipeline overview card */}
      <Card>
        <CardHeader>
          <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem' }}>
            <Info size={16} style={{ color: 'var(--color-text-secondary)' }} />
            Autopilot pipeline
          </CardTitle>
        </CardHeader>
        <CardBody>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            Each stage runs on a Celery Beat schedule. Every task checks the autopilot flag first —
            if it's OFF, the task skips without doing anything.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
            {pipelineSteps.map((step, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.875rem',
                  padding: '0.625rem 0.875rem',
                  background: 'var(--color-bg-secondary)',
                  borderRadius: '0.5rem',
                  opacity: enabled ? 1 : 0.5,
                  transition: 'opacity 0.2s',
                }}
              >
                <span style={{ fontSize: '1.25rem', flexShrink: 0 }}>{step.icon}</span>
                <div>
                  <div style={{ fontWeight: 500, color: 'var(--color-text-primary)', fontSize: '0.875rem' }}>
                    {step.label}
                  </div>
                  <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>
                    {step.sub}
                  </div>
                </div>
                <div style={{ marginLeft: 'auto', flexShrink: 0 }}>
                  {enabled ? (
                    <span style={{ fontSize: '0.7rem', color: 'var(--color-success)', fontWeight: 600, background: 'rgba(34,197,94,0.1)', padding: '0.15rem 0.5rem', borderRadius: '999px' }}>
                      ACTIVE
                    </span>
                  ) : (
                    <span style={{ fontSize: '0.7rem', color: 'var(--color-text-tertiary)', fontWeight: 600, background: 'var(--color-bg-tertiary)', padding: '0.15rem 0.5rem', borderRadius: '999px' }}>
                      PAUSED
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Warning box */}
          {!enabled && (
            <div
              style={{
                marginTop: '1rem',
                padding: '0.75rem 1rem',
                background: 'rgba(245, 158, 11, 0.08)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                borderRadius: '0.5rem',
                fontSize: '0.8rem',
                color: 'var(--color-text-secondary)',
                display: 'flex',
                gap: '0.5rem',
              }}
            >
              <span>⚠️</span>
              <span>
                Autopilot is off. You can still trigger each stage manually from the Hunter,
                Generated Sites, and Campaigns pages. Turn autopilot on when you're ready
                to run fully hands-free.
              </span>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

export default AutopilotSettings
