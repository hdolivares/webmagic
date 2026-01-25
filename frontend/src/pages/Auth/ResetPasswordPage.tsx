/**
 * Reset Password Page
 * 
 * Allows customers to set a new password using the token from their email.
 * Includes password strength indicator and validation.
 * 
 * Author: WebMagic Team
 * Date: January 24, 2026
 */
import React, { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../../services/api'
import PasswordInput from '../../components/PasswordInput/PasswordInput'
import PasswordStrengthIndicator from '../../components/PasswordStrengthIndicator/PasswordStrengthIndicator'
import { usePasswordValidation, validatePasswordMatch } from '../../hooks/usePasswordValidation'
import './ResetPasswordPage.css'

const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirmPasswordError, setConfirmPasswordError] = useState<string | null>(null)

  const passwordValidation = usePasswordValidation(newPassword)

  // Validate token exists on mount
  useEffect(() => {
    if (!token) {
      setError('Invalid or missing reset token. Please request a new password reset link.')
    }
  }, [token])

  // Validate password match when confirmPassword changes
  useEffect(() => {
    if (confirmPassword) {
      const matchError = validatePasswordMatch(newPassword, confirmPassword)
      setConfirmPasswordError(matchError)
    } else {
      setConfirmPasswordError(null)
    }
  }, [newPassword, confirmPassword])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setConfirmPasswordError(null)

    // Validate token
    if (!token) {
      setError('Invalid or missing reset token')
      return
    }

    // Validate password
    if (!passwordValidation.isValid) {
      setError(passwordValidation.errorMessage || 'Password does not meet requirements')
      return
    }

    // Validate passwords match
    const matchError = validatePasswordMatch(newPassword, confirmPassword)
    if (matchError) {
      setConfirmPasswordError(matchError)
      return
    }

    setIsLoading(true)

    try {
      await api.customerResetPassword(token, newPassword)
      
      // Success! Redirect to login with success message
      navigate('/login?reset=success', { replace: true })
    } catch (err: any) {
      console.error('Password reset failed:', err)
      
      // Handle specific error types
      if (err.response?.status === 400) {
        setError('Invalid or expired reset link. Please request a new one.')
      } else if (err.response?.status === 422) {
        setError('Password does not meet requirements.')
      } else {
        const message = err.response?.data?.detail || 'An error occurred. Please try again.'
        setError(message)
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="reset-password-page">
      <div className="reset-password-container">
        <div className="reset-password-card">
          {/* Header */}
          <div className="reset-password-header">
            <div className="key-icon">
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
                <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
              </svg>
            </div>
            <h1 className="reset-password-title">Reset Your Password</h1>
            <p className="reset-password-subtitle">
              Choose a strong password to secure your account.
            </p>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="alert alert-error" role="alert">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="reset-password-form">
            {/* New Password */}
            <PasswordInput
              id="new-password"
              label="New Password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Enter your new password"
              autoComplete="new-password"
              required
              disabled={isLoading || !token}
              hint="At least 8 characters with letters and numbers"
            />

            {/* Password Strength Indicator */}
            {newPassword && (
              <PasswordStrengthIndicator
                password={newPassword}
                showRequirements={true}
              />
            )}

            {/* Confirm Password */}
            <PasswordInput
              id="confirm-password"
              label="Confirm New Password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter your new password"
              autoComplete="new-password"
              required
              disabled={isLoading || !token}
              error={confirmPasswordError || undefined}
            />

            <button
              type="submit"
              className="btn-primary btn-full-width"
              disabled={isLoading || !token || !passwordValidation.isValid || !!confirmPasswordError}
            >
              {isLoading ? (
                <>
                  <span className="spinner" aria-hidden="true"></span>
                  Resetting Password...
                </>
              ) : (
                'Reset Password'
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

export default ResetPasswordPage
