/**
 * Account Settings Page - Customer Portal
 * 
 * Allows customers to view their account information and change their password.
 * 
 * Author: WebMagic Team
 * Date: January 24, 2026
 */
import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuth } from '../../hooks/useAuth'
import { api } from '../../services/api'
import PasswordInput from '../../components/PasswordInput/PasswordInput'
import PasswordStrengthIndicator from '../../components/PasswordStrengthIndicator/PasswordStrengthIndicator'
import { usePasswordValidation, validatePasswordMatch } from '../../hooks/usePasswordValidation'
import './AccountSettingsPage.css'

const AccountSettingsPage: React.FC = () => {
  const { user } = useAuth()
  
  // Password change state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [confirmPasswordError, setConfirmPasswordError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const passwordValidation = usePasswordValidation(newPassword)

  // Password change mutation
  const changePasswordMutation = useMutation({
    mutationFn: async () => {
      // Validate passwords match
      const matchError = validatePasswordMatch(newPassword, confirmPassword)
      if (matchError) {
        throw new Error(matchError)
      }

      // Validate password requirements
      if (!passwordValidation.isValid) {
        throw new Error(passwordValidation.errorMessage || 'Password does not meet requirements')
      }

      return api.customerChangePassword(currentPassword, newPassword)
    },
    onSuccess: () => {
      // Show success message
      setSuccessMessage('Password changed successfully!')
      
      // Clear form
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setConfirmPasswordError(null)

      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000)
    },
    onError: (error: any) => {
      console.error('Password change failed:', error)
    },
  })

  // Validate password match when confirmPassword changes
  React.useEffect(() => {
    if (confirmPassword) {
      const matchError = validatePasswordMatch(newPassword, confirmPassword)
      setConfirmPasswordError(matchError)
    } else {
      setConfirmPasswordError(null)
    }
  }, [newPassword, confirmPassword])

  const handlePasswordChange = (e: React.FormEvent) => {
    e.preventDefault()
    setSuccessMessage(null)
    changePasswordMutation.mutate()
  }

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  return (
    <div className="account-settings-page">
      <div className="page-header">
        <h1 className="page-title">Account Settings</h1>
        <p className="page-subtitle">Manage your account information and security settings</p>
      </div>

      <div className="settings-container">
        {/* Account Information Section */}
        <section className="settings-section">
          <div className="section-header">
            <h2 className="section-title">Account Information</h2>
            <p className="section-description">Your personal account details</p>
          </div>

          <div className="info-card">
            <div className="info-row">
              <span className="info-label">Email Address</span>
              <span className="info-value">{user?.email || 'N/A'}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Account Created</span>
              <span className="info-value">{formatDate(user?.created_at)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Last Login</span>
              <span className="info-value">{formatDate(user?.last_login) || 'Never'}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Email Verified</span>
              <span className={`info-badge ${user?.email_verified ? 'badge-success' : 'badge-warning'}`}>
                {user?.email_verified ? '✓ Verified' : '⚠ Not Verified'}
              </span>
            </div>
          </div>
        </section>

        {/* Change Password Section */}
        <section className="settings-section">
          <div className="section-header">
            <h2 className="section-title">Change Password</h2>
            <p className="section-description">Update your password to keep your account secure</p>
          </div>

          {/* Success Message */}
          {successMessage && (
            <div className="alert alert-success" role="alert">
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
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              <span>{successMessage}</span>
            </div>
          )}

          {/* Error Message */}
          {changePasswordMutation.isError && (
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
              <span>
                {(changePasswordMutation.error as any)?.response?.data?.detail ||
                  (changePasswordMutation.error as any)?.message ||
                  'Failed to change password'}
              </span>
            </div>
          )}

          <form onSubmit={handlePasswordChange} className="password-change-form">
            {/* Current Password */}
            <PasswordInput
              id="current-password"
              label="Current Password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Enter your current password"
              autoComplete="current-password"
              required
              disabled={changePasswordMutation.isPending}
            />

            {/* New Password */}
            <PasswordInput
              id="new-password"
              label="New Password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Enter your new password"
              autoComplete="new-password"
              required
              disabled={changePasswordMutation.isPending}
              hint="At least 8 characters with letters and numbers"
            />

            {/* Password Strength Indicator */}
            {newPassword && (
              <PasswordStrengthIndicator password={newPassword} showRequirements={true} />
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
              disabled={changePasswordMutation.isPending}
              error={confirmPasswordError || undefined}
            />

            <button
              type="submit"
              className="btn-primary"
              disabled={
                changePasswordMutation.isPending ||
                !currentPassword ||
                !passwordValidation.isValid ||
                !!confirmPasswordError
              }
            >
              {changePasswordMutation.isPending ? (
                <>
                  <span className="spinner" aria-hidden="true"></span>
                  Changing Password...
                </>
              ) : (
                'Change Password'
              )}
            </button>
          </form>
        </section>
      </div>
    </div>
  )
}

export default AccountSettingsPage
