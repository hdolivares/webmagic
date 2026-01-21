/**
 * Channel Selector Component
 * 
 * Allows selection of campaign channel (Email, SMS, Auto)
 * with intelligent tooltips explaining each option.
 * 
 * Author: WebMagic Team
 * Date: January 21, 2026
 */
import React from 'react'
import './ChannelSelector.css'

export interface ChannelSelectorProps {
    /** Currently selected channel */
    value: 'auto' | 'email' | 'sms'
    
    /** Callback when channel changes */
    onChange: (channel: 'auto' | 'email' | 'sms') => void
    
    /** Optional: Disable selector */
    disabled?: boolean
    
    /** Optional: Show cost estimates */
    showCost?: boolean
}

const ChannelSelector: React.FC<ChannelSelectorProps> = ({
    value,
    onChange,
    disabled = false,
    showCost = true,
}) => {
    const channels = [
        {
            id: 'auto' as const,
            label: 'Auto',
            icon: '🤖',
            description: 'Smart channel selection (Email first, SMS if no email)',
            cost: 'Free (Email) or ~$0.01 (SMS)',
            recommended: true,
        },
        {
            id: 'email' as const,
            label: 'Email Only',
            icon: '📧',
            description: 'Send via email (free, requires email address)',
            cost: 'Free',
            recommended: false,
        },
        {
            id: 'sms' as const,
            label: 'SMS Only',
            icon: '💬',
            description: 'Send via SMS (paid, requires phone number)',
            cost: '~$0.01-0.03 per message',
            recommended: false,
        },
    ]

    return (
        <div className="channel-selector">
            <label className="channel-selector__label">
                Campaign Channel
                {showCost && (
                    <span className="channel-selector__info" title="Choose how to contact businesses">
                        ℹ️
                    </span>
                )}
            </label>

            <div className="channel-selector__options">
                {channels.map((channel) => (
                    <button
                        key={channel.id}
                        type="button"
                        className={`channel-option ${
                            value === channel.id ? 'channel-option--selected' : ''
                        } ${disabled ? 'channel-option--disabled' : ''}`}
                        onClick={() => !disabled && onChange(channel.id)}
                        disabled={disabled}
                        title={channel.description}
                    >
                        <div className="channel-option__icon">{channel.icon}</div>
                        <div className="channel-option__content">
                            <div className="channel-option__header">
                                <span className="channel-option__label">{channel.label}</span>
                                {channel.recommended && (
                                    <span className="channel-option__badge">Recommended</span>
                                )}
                            </div>
                            <p className="channel-option__description">{channel.description}</p>
                            {showCost && (
                                <p className="channel-option__cost">{channel.cost}</p>
                            )}
                        </div>
                        {value === channel.id && (
                            <div className="channel-option__checkmark">✓</div>
                        )}
                    </button>
                ))}
            </div>
        </div>
    )
}

export default ChannelSelector

