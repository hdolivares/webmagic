/**
 * EditRequestForm Component
 * 
 * Form for customers to submit AI-powered edit requests.
 * Uses semantic CSS variables for consistent styling.
 * 
 * Author: WebMagic Team
 * Date: January 21, 2026
 */
import { useState } from 'react'
import { api } from '@/services/api'
import './EditRequestForm.css'

interface EditRequestFormProps {
  siteId: string
  onSuccess?: (editRequest: any) => void
  onCancel?: () => void
}

const EDIT_TYPES = [
  { value: 'text', label: 'Text Content', description: 'Change headings, paragraphs, or any text' },
  { value: 'style', label: 'Styling', description: 'Colors, fonts, spacing, or layout' },
  { value: 'layout', label: 'Layout', description: 'Rearrange or restructure sections' },
  { value: 'content', label: 'Content', description: 'Add or remove sections' },
]

const EXAMPLE_REQUESTS = [
  'Change the hero button color to blue',
  'Make the heading font size larger',
  'Add a testimonials section after the services',
  'Update the contact email to hello@example.com',
  'Change the background to a gradient from purple to blue',
]

export function EditRequestForm({ siteId, onSuccess, onCancel }: EditRequestFormProps) {
  const [requestText, setRequestText] = useState('')
  const [requestType, setRequestType] = useState<string>('')
  const [targetSection, setTargetSection] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!requestText.trim()) {
      setError('Please describe what you want to change')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const data = {
        request_text: requestText.trim(),
        ...(requestType && { request_type: requestType }),
        ...(targetSection && { target_section: targetSection }),
      }

      const result = await api.createEditRequest(siteId, data)
      
      // Reset form
      setRequestText('')
      setRequestType('')
      setTargetSection('')
      
      onSuccess?.(result)
    } catch (err: any) {
      console.error('Failed to create edit request:', err)
      setError(err.response?.data?.detail || 'Failed to submit request. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const insertExample = (example: string) => {
    setRequestText(example)
  }

  return (
    <div className="edit-request-form-container">
      <form onSubmit={handleSubmit} className="edit-request-form">
        {/* Header */}
        <div className="form-header">
          <h2 className="form-title">Request Site Changes</h2>
          <p className="form-description">
            Describe what you'd like to change in plain English. Our AI will understand and generate a preview for you to approve.
          </p>
        </div>

        {/* Main Request Input */}
        <div className="form-group">
          <label htmlFor="request-text" className="form-label">
            What would you like to change?
            <span className="required">*</span>
          </label>
          <textarea
            id="request-text"
            className="form-textarea"
            rows={4}
            value={requestText}
            onChange={(e) => setRequestText(e.target.value)}
            placeholder="Example: Change the hero button color to blue and make it larger"
            disabled={isSubmitting}
            required
            maxLength={1000}
          />
          <div className="form-hint">
            {requestText.length}/1000 characters
          </div>
        </div>

        {/* Edit Type Selection */}
        <div className="form-group">
          <label className="form-label">
            Type of change (optional)
          </label>
          <div className="edit-types-grid">
            {EDIT_TYPES.map((type) => (
              <label
                key={type.value}
                className={`edit-type-card ${requestType === type.value ? 'selected' : ''}`}
              >
                <input
                  type="radio"
                  name="edit-type"
                  value={type.value}
                  checked={requestType === type.value}
                  onChange={(e) => setRequestType(e.target.value)}
                  disabled={isSubmitting}
                  className="edit-type-radio"
                />
                <div className="edit-type-content">
                  <div className="edit-type-label">{type.label}</div>
                  <div className="edit-type-description">{type.description}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Target Section (optional) */}
        <div className="form-group">
          <label htmlFor="target-section" className="form-label">
            Specific section (optional)
          </label>
          <input
            id="target-section"
            type="text"
            className="form-input"
            value={targetSection}
            onChange={(e) => setTargetSection(e.target.value)}
            placeholder="e.g., hero, about, services, contact"
            disabled={isSubmitting}
          />
          <div className="form-hint">
            Leave blank to apply changes site-wide
          </div>
        </div>

        {/* Example Requests */}
        <div className="examples-section">
          <div className="examples-header">Need inspiration? Try these:</div>
          <div className="examples-list">
            {EXAMPLE_REQUESTS.map((example, index) => (
              <button
                key={index}
                type="button"
                className="example-chip"
                onClick={() => insertExample(example)}
                disabled={isSubmitting}
              >
                {example}
              </button>
            ))}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <svg className="error-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {error}
          </div>
        )}

        {/* Info Box */}
        <div className="info-box">
          <svg className="info-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="info-text">
            <strong>What happens next:</strong>
            <ol>
              <li>Our AI will process your request (usually 2-5 minutes)</li>
              <li>You'll receive an email when the preview is ready</li>
              <li>Review the changes side-by-side with your current site</li>
              <li>Approve to make it live, or reject with feedback</li>
            </ol>
          </div>
        </div>

        {/* Form Actions */}
        <div className="form-actions">
          {onCancel && (
            <button
              type="button"
              className="btn-cancel"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            className="btn-submit"
            disabled={isSubmitting || !requestText.trim()}
          >
            {isSubmitting ? (
              <>
                <svg className="spinner" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Processing...
              </>
            ) : (
              'Submit Request'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

