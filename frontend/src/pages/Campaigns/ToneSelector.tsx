/**
 * ToneSelector Component
 * 
 * Allows selection of SMS message tone (Friendly, Professional, Urgent)
 * Following best practices: Single responsibility, type safety, accessibility
 */
import React from 'react'
import './Campaigns.css'

type ToneVariant = 'friendly' | 'professional' | 'urgent'

interface ToneSelectorProps {
  value: ToneVariant
  onChange: (tone: ToneVariant) => void
  disabled?: boolean
}

interface ToneOption {
  id: ToneVariant
  label: string
  icon: string
  description: string
  recommended?: boolean
}

const TONE_OPTIONS: ToneOption[] = [
  {
    id: 'friendly',
    label: 'Friendly',
    icon: '😊',
    description: 'Warm, conversational (Best for cold outreach)',
    recommended: true,
  },
  {
    id: 'professional',
    label: 'Professional',
    icon: '💼',
    description: 'Formal, business-appropriate',
  },
  {
    id: 'urgent',
    label: 'Urgent',
    icon: '⚡',
    description: 'Direct, action-oriented',
  },
]

/**
 * ToneSelector - Select message tone for SMS campaigns
 */
export const ToneSelector: React.FC<ToneSelectorProps> = ({
  value,
  onChange,
  disabled = false,
}) => {
  return (
    <div className="selector-group">
      <label className="selector-label">
        Message Tone
        {TONE_OPTIONS.find(t => t.id === value)?.recommended && (
          <span style={{ marginLeft: '0.5rem', color: 'var(--campaigns-tone-friendly)' }}>
            (Recommended)
          </span>
        )}
      </label>

      <div className="selector-options">
        {TONE_OPTIONS.map((tone) => (
          <button
            key={tone.id}
            type="button"
            className={`selector-option ${
              value === tone.id ? 'selector-option--selected' : ''
            }`}
            onClick={() => onChange(tone.id)}
            disabled={disabled}
            title={tone.description}
          >
            <span className="selector-option__icon">{tone.icon}</span>
            <div>{tone.label}</div>
            <div style={{ fontSize: '0.75rem', opacity: 0.8, marginTop: '0.25rem' }}>
              {tone.description}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

export default ToneSelector
