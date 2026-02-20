/**
 * Messaging Settings - Configure SMS message templates for campaigns.
 * Templates support variables for personalization (Friendly, Professional, Urgent).
 */
import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Card } from '@/components/ui'
import './MessagingSettings.css'

const SUPPORTED_COUNTRIES = [
  { code: 'US', flag: '🇺🇸', label: 'United States (+1)' },
  { code: 'MX', flag: '🇲🇽', label: 'Mexico (+52)' },
]

const TEMPLATE_KEYS = {
  friendly: 'messaging_sms_template_friendly',
  professional: 'messaging_sms_template_professional',
  urgent: 'messaging_sms_template_urgent',
} as const

const VARIABLES = [
  { name: '{{business_name}}', description: 'Business name' },
  { name: '{{rating}}', description: 'Google rating with star (e.g. 4.8⭐)' },
  { name: '{{review_count}}', description: 'Number of Google reviews (e.g. 47)' },
  { name: '{{site_url}}', description: 'Generated site preview URL' },
  { name: '{{category}}', description: 'Business category (e.g. Plumber)' },
  { name: '{{city}}', description: 'Business city' },
  { name: '{{state}}', description: 'Business state or region' },
]

type ToneKey = 'friendly' | 'professional' | 'urgent'

export const MessagingSettings: React.FC = () => {
  const queryClient = useQueryClient()
  const [local, setLocal] = useState<Record<ToneKey, string>>({
    friendly: '',
    professional: '',
    urgent: '',
  })
  const [testPhone, setTestPhone] = useState('')
  const [testMessage, setTestMessage] = useState('')
  const [testResult, setTestResult] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [isSendingTest, setIsSendingTest] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['messaging-templates'],
    queryFn: () => api.getMessagingTemplates(),
  })

  useEffect(() => {
    if (data) {
      setLocal({
        friendly: data.friendly || data.defaults?.friendly || '',
        professional: data.professional || data.defaults?.professional || '',
        urgent: data.urgent || data.defaults?.urgent || '',
      })
    }
  }, [data])

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      api.updateSystemSetting(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['messaging-templates'] })
    },
  })

  const handleSave = (tone: ToneKey) => {
    const key = TEMPLATE_KEYS[tone]
    const value = local[tone] || ''
    updateMutation.mutate({ key, value })
  }

  const handleChange = (tone: ToneKey, value: string) => {
    setLocal(prev => ({ ...prev, [tone]: value }))
  }

  const handleSendTest = async () => {
    if (!testPhone.trim()) return
    setIsSendingTest(true)
    setTestResult(null)
    try {
      const result = await api.sendTestSms(testPhone.trim(), testMessage.trim() || undefined)
      setTestResult({
        type: 'success',
        text: `Sent! Message ID: ${result.message_id}. From ${result.from} → ${result.to}`,
      })
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Unknown error'
      setTestResult({ type: 'error', text: typeof detail === 'string' ? detail : JSON.stringify(detail) })
    } finally {
      setIsSendingTest(false)
    }
  }

  if (isLoading) {
    return (
      <Card>
        <div className="messaging-settings-loading">Loading templates…</div>
      </Card>
    )
  }

  return (
    <div className="messaging-settings">
      <Card>
        <div className="messaging-settings__intro">
          <h2 className="messaging-settings__title">SMS message templates</h2>
          <p className="messaging-settings__description">
            Configure the message text for each tone used in campaigns. Leave a template empty to use
            AI-generated messages. Use the variables below to personalize each message.
          </p>
        </div>

        <div className="messaging-settings__variables">
          <h3 className="messaging-settings__variables-title">Template variables</h3>
          <p className="messaging-settings__variables-desc">
            Use these placeholders in your templates; they will be replaced with real data when sending.
          </p>
          <ul className="messaging-settings__variables-list">
            {VARIABLES.map(v => (
              <li key={v.name}>
                <code>{v.name}</code>
                <span>{v.description}</span>
              </li>
            ))}
          </ul>
        </div>

        {(['friendly', 'professional', 'urgent'] as ToneKey[]).map(tone => (
          <div key={tone} className="messaging-settings__template">
            <label className="messaging-settings__label">
              {tone.charAt(0).toUpperCase() + tone.slice(1)} template
            </label>
            <textarea
              className="messaging-settings__textarea"
              value={local[tone]}
              onChange={e => handleChange(tone, e.target.value)}
              placeholder={data?.defaults?.[tone] || `e.g. {{business_name}} - We built you a {{category}} website! Preview: {{site_url}} Reply STOP to opt out.`}
              rows={4}
            />
            <div className="messaging-settings__actions">
              <button
                type="button"
                className="messaging-settings__btn messaging-settings__btn--primary"
                onClick={() => handleSave(tone)}
                disabled={updateMutation.isPending}
              >
                {updateMutation.isPending ? 'Saving…' : 'Save template'}
              </button>
            </div>
          </div>
        ))}
      </Card>

      <Card>
        <div className="messaging-settings__intro">
          <h2 className="messaging-settings__title">Send a test SMS</h2>
          <p className="messaging-settings__description">
            Verify that Telnyx is correctly configured and messages are delivered before running campaigns.
          </p>
        </div>

        <div className="messaging-settings__test-info">
          <div className="messaging-settings__test-info-row">
            <span className="messaging-settings__test-info-label">Sending from</span>
            <code className="messaging-settings__test-info-value">+1 (415) 863-7488</code>
          </div>
          <div className="messaging-settings__test-info-row">
            <span className="messaging-settings__test-info-label">Supported countries</span>
            <span className="messaging-settings__test-info-countries">
              {SUPPORTED_COUNTRIES.map(c => (
                <span key={c.code} className="messaging-settings__country-badge">
                  {c.flag} {c.label}
                </span>
              ))}
            </span>
          </div>
        </div>

        <div className="messaging-settings__test-form">
          <div className="messaging-settings__test-field">
            <label className="messaging-settings__label">
              Recipient phone number <span className="messaging-settings__required">*</span>
            </label>
            <input
              type="tel"
              className="messaging-settings__input"
              value={testPhone}
              onChange={e => setTestPhone(e.target.value)}
              placeholder="+1 (555) 123-4567  or  +52 55 1234 5678"
            />
          </div>

          <div className="messaging-settings__test-field">
            <label className="messaging-settings__label">
              Custom message <span className="messaging-settings__optional">(optional)</span>
            </label>
            <textarea
              className="messaging-settings__textarea"
              value={testMessage}
              onChange={e => setTestMessage(e.target.value)}
              placeholder="Leave blank to use the default test message"
              rows={3}
            />
          </div>

          {testResult && (
            <div className={`messaging-settings__test-result messaging-settings__test-result--${testResult.type}`}>
              {testResult.type === 'success' ? '✓ ' : '✗ '}
              {testResult.text}
            </div>
          )}

          <div className="messaging-settings__actions">
            <button
              type="button"
              className="messaging-settings__btn messaging-settings__btn--send-test"
              onClick={handleSendTest}
              disabled={isSendingTest || !testPhone.trim()}
            >
              {isSendingTest ? 'Sending…' : 'Send test message'}
            </button>
          </div>
        </div>
      </Card>
    </div>
  )
}
