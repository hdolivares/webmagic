/**
 * CRM Contact Indicator Component
 * 
 * Displays visual indicators for email/phone availability.
 * Shows ✓📧 if email exists, ✓📱 if phone exists.
 * 
 * @author WebMagic Team
 * @date January 22, 2026
 */
import React from 'react'
import { Mail, Phone, X } from 'lucide-react'
import './ContactIndicator.css'

export interface ContactIndicatorProps {
  hasEmail?: boolean
  hasPhone?: boolean
  email?: string | null
  phone?: string | null
  showLabels?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

/**
 * ContactIndicator Component
 * 
 * Shows at-a-glance contact information availability.
 * 
 * Usage:
 * ```tsx
 * <ContactIndicator hasEmail={true} hasPhone={false} />
 * <ContactIndicator hasEmail={true} hasPhone={true} showLabels />
 * <ContactIndicator email="test@test.com" phone="(310) 555-1234" />
 * ```
 */
export const ContactIndicator: React.FC<ContactIndicatorProps> = ({
  hasEmail,
  hasPhone,
  email,
  phone,
  showLabels = false,
  size = 'md',
  className = '',
}) => {
  // Auto-detect if email/phone props are provided
  const emailAvailable = hasEmail ?? (email != null && email.length > 0)
  const phoneAvailable = hasPhone ?? (phone != null && phone.length > 0)

  const sizeClass = `crm-contact-indicator-${size}`

  return (
    <div className={`crm-contact-indicator ${sizeClass} ${className}`}>
      {/* Email indicator */}
      <div
        className={`crm-contact-item ${emailAvailable ? 'has-contact' : 'missing-contact'}`}
        title={emailAvailable ? (email || 'Email available') : 'No email'}
      >
        {emailAvailable ? (
          <Mail className="icon" />
        ) : (
          <X className="icon" />
        )}
        {showLabels && (
          <span className="label">
            {emailAvailable ? (email || 'Email') : 'No email'}
          </span>
        )}
      </div>

      {/* Phone indicator */}
      <div
        className={`crm-contact-item ${phoneAvailable ? 'has-contact' : 'missing-contact'}`}
        title={phoneAvailable ? (phone || 'Phone available') : 'No phone'}
      >
        {phoneAvailable ? (
          <Phone className="icon" />
        ) : (
          <X className="icon" />
        )}
        {showLabels && (
          <span className="label">
            {phoneAvailable ? (phone || 'Phone') : 'No phone'}
          </span>
        )}
      </div>
    </div>
  )
}

/**
 * ContactInfoRow - Expanded view with full details
 * 
 * Usage:
 * ```tsx
 * <ContactInfoRow email="test@test.com" phone="(310) 555-1234" />
 * ```
 */
export interface ContactInfoRowProps {
  email?: string | null
  phone?: string | null
  className?: string
}

export const ContactInfoRow: React.FC<ContactInfoRowProps> = ({
  email,
  phone,
  className = '',
}) => {
  return (
    <div className={`crm-contact-info-row ${className}`}>
      {/* Email */}
      <div className="crm-contact-detail">
        <Mail className="icon" />
        <span className="value">
          {email || <span className="empty">No email</span>}
        </span>
      </div>

      {/* Phone */}
      <div className="crm-contact-detail">
        <Phone className="icon" />
        <span className="value">
          {phone || <span className="empty">No phone</span>}
        </span>
      </div>
    </div>
  )
}

/**
 * DataCompleteness - Shows data quality percentage
 * 
 * Usage:
 * ```tsx
 * <DataCompleteness score={85} />
 * ```
 */
export interface DataCompletenessProps {
  score: number // 0-100
  showLabel?: boolean
  className?: string
}

export const DataCompleteness: React.FC<DataCompletenessProps> = ({
  score,
  showLabel = true,
  className = '',
}) => {
  // Determine quality level
  const getQualityLevel = (score: number): string => {
    if (score >= 80) return 'excellent'
    if (score >= 60) return 'good'
    if (score >= 40) return 'fair'
    return 'poor'
  }

  const qualityLevel = getQualityLevel(score)

  return (
    <div className={`crm-data-completeness ${className}`}>
      <div className="completeness-bar">
        <div
          className={`completeness-fill quality-${qualityLevel}`}
          style={{ width: `${score}%` }}
        />
      </div>
      {showLabel && (
        <span className={`completeness-label quality-${qualityLevel}`}>
          {score}%
        </span>
      )}
    </div>
  )
}

