/**
 * Forgot Password Page
 * 
 * Allows customers to request a password reset email.
 * Follows security best practices (doesn't reveal if email exists).
 * 
 * Author: WebMagic Team
 * Date: January 24, 2026
 */
import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import './ForgotPasswordPage.css'

const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validate email format
    if (!email) {
      setError('Email address is required')
      return
    }

    if (!validateEmail(email)) {
      setError('Please enter a valid email address')
      return
    }

    setIsLoading(true)

    try {
      await api.customerForgotPassword(email)
      setSubmitted(true)
    } catch (err: any) {
      // For security, we don't reveal if the email exists
      // Show a generic error message
      console.error('Password reset request failed:', err)
      setError('An error occurred. Please try again later.')
    } finally {
      setIsLoading(false)
    }
  }

  // Success state - show confirmation message
  if (submitted) {
    return (
      <div className="forgot-password-page">
        <div className="forgot-password-container">
          <div className="forgot-password-card">
            {/* Success Icon */}
            <div className="success-icon">
              <svg
                width="64"
                height="64"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>

            <h1 className="forgot-password-title">Check Your Email</h1>
            
            <p className="success-message">
              If an account exists for <strong>{email}</strong>, you will receive a password reset link shortly.
            </p>

            <div className="success-instructions">
              <h2>What's next?</h2>
              <ol>
                <li>Check your email inbox (and spam folder)</li>
                <li>Click the "Reset Password" link in the email</li>
                <li>Choose a new password</li>
                <li>Log in with your new password</li>
              </ol>
            </div>

            <p className="email-note">
              The reset link will expire in <strong>1 hour</strong> for security reasons.
            </p>

            <div className="form-footer">
              <Link to="/login" className="btn-secondary">
                Back to Login
              </Link>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Main form
  return (
    <div className="forgot-password-page">
      <div className="forgot-password-container">
        <div className="forgot-password-card">
          {/* Header */}
          <div className="forgot-password-header">
            <div className="lock-icon">
              <svg
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
            <h1 className="forgot-password-title">Forgot Password?</h1>
            <p className="forgot-password-subtitle">
              No worries! Enter your email address and we'll send you a link to reset your password.
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="forgot-password-form">
            <div className="form-group">
              <label htmlFor="email" className="form-label">
                Email Address
                <span className="required-indicator" aria-label="required">*</span>
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
                aria-required="true"
                aria-invalid={!!error}
                aria-describedby={error ? 'email-error' : undefined}
                className={`form-input ${error ? 'form-input-error' : ''}`}
                disabled={isLoading}
              />
              {error && (
                <div id="email-error" className="form-error" role="alert">
                  {error}
                </div>
              )}
            </div>

            <button
              type="submit"
              className="btn-primary btn-full-width"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="spinner" aria-hidden="true"></span>
                  Sending Reset Link...
                </>
              ) : (
                'Send Reset Link'
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="form-footer">
            <p className="footer-text">
              Remember your password?{' '}
              <Link to="/login" className="footer-link">
                Back to Login
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ForgotPasswordPage
