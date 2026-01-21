/**
 * Create Ticket Form Component
 * 
 * Form for customers to create new support tickets
 */
import React, { useState, useEffect } from 'react'
import { api } from '../../services/api'
import './CreateTicketForm.css'

interface CreateTicketFormProps {
  siteId?: string
  onSuccess?: (ticket: any) => void
  onCancel?: () => void
}

const CreateTicketForm: React.FC<CreateTicketFormProps> = ({
  siteId,
  onSuccess,
  onCancel
}) => {
  const [categories, setCategories] = useState<any>(null)
  const [formData, setFormData] = useState({
    subject: '',
    description: '',
    category: 'question',
    site_id: siteId || ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadCategories()
  }, [])

  const loadCategories = async () => {
    try {
      const data = await api.getTicketCategories()
      setCategories(data)
    } catch (err) {
      console.error('Failed to load categories:', err)
    }
  }

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const ticket = await api.createTicket(formData)
      
      // Reset form
      setFormData({
        subject: '',
        description: '',
        category: 'question',
        site_id: siteId || ''
      })

      if (onSuccess) {
        onSuccess(ticket)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create ticket')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="create-ticket-form">
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="category">Category *</label>
          <select
            id="category"
            name="category"
            value={formData.category}
            onChange={handleChange}
            required
            disabled={loading}
          >
            {categories?.categories?.map((cat: string) => (
              <option key={cat} value={cat}>
                {cat.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </option>
            ))}
          </select>
          {categories?.descriptions && (
            <p className="form-help">
              {categories.descriptions[formData.category]}
            </p>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="subject">Subject *</label>
          <input
            type="text"
            id="subject"
            name="subject"
            value={formData.subject}
            onChange={handleChange}
            placeholder="Brief summary of your issue"
            required
            minLength={5}
            maxLength={255}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="description">Description *</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Please provide detailed information about your issue or question..."
            required
            minLength={10}
            rows={6}
            disabled={loading}
          />
          <p className="form-help">
            Please be as detailed as possible to help us assist you better.
          </p>
        </div>

        {error && (
          <div className="form-error">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{error}</span>
          </div>
        )}

        <div className="form-actions">
          {onCancel && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onCancel}
              disabled={loading}
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                <span>Creating...</span>
              </>
            ) : (
              'Create Ticket'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

export default CreateTicketForm

