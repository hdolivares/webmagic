/**
 * Account Settings Component
 * 
 * Handles password changes and account management
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Card, CardHeader, CardBody, CardTitle, Button } from '@/components/ui'
import { Lock, CheckCircle2, AlertCircle, Eye, EyeOff } from 'lucide-react'
import { api } from '@/services/api'
import { useAuth } from '@/hooks/useAuth'

export const AccountSettings = () => {
  const { user } = useAuth()
  
  // Form state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  
  // UI state
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  // Password change mutation
  const changePasswordMutation = useMutation({
    mutationFn: ({ currentPassword, newPassword }: { currentPassword: string; newPassword: string }) =>
      api.changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setSuccessMessage('Password changed successfully!')
      setErrorMessage('')
      
      // Clear form
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      
      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(''), 5000)
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to change password'
      setErrorMessage(message)
      setSuccessMessage('')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Clear previous messages
    setSuccessMessage('')
    setErrorMessage('')

    // Validation
    if (!currentPassword || !newPassword || !confirmPassword) {
      setErrorMessage('All fields are required')
      return
    }

    if (newPassword.length < 8) {
      setErrorMessage('New password must be at least 8 characters long')
      return
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage('New passwords do not match')
      return
    }

    if (currentPassword === newPassword) {
      setErrorMessage('New password must be different from current password')
      return
    }

    // Submit
    changePasswordMutation.mutate({ currentPassword, newPassword })
  }

  return (
    <div className="max-w-2xl">
      {/* Profile Information */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="space-y-4">
            <div>
              <label className="form-label">Email</label>
              <input
                type="email"
                value={user?.email || ''}
                disabled
                className="input bg-background-secondary cursor-not-allowed"
              />
              <p className="text-xs text-text-secondary mt-1">
                Email cannot be changed
              </p>
            </div>

            <div>
              <label className="form-label">Full Name</label>
              <input
                type="text"
                value={user?.full_name || ''}
                disabled
                className="input bg-background-secondary cursor-not-allowed"
              />
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Change Password */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Lock className="w-5 h-5 text-primary-600" />
            <CardTitle>Change Password</CardTitle>
          </div>
        </CardHeader>
        <CardBody>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Success Message */}
            {successMessage && (
              <div className="alert alert-success">
                <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                <span>{successMessage}</span>
              </div>
            )}

            {/* Error Message */}
            {errorMessage && (
              <div className="alert alert-error">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Current Password */}
            <div>
              <label className="form-label" htmlFor="current-password">
                Current Password
              </label>
              <div className="relative">
                <input
                  id="current-password"
                  type={showCurrentPassword ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="input pr-10"
                  placeholder="Enter your current password"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                >
                  {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* New Password */}
            <div>
              <label className="form-label" htmlFor="new-password">
                New Password
              </label>
              <div className="relative">
                <input
                  id="new-password"
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="input pr-10"
                  placeholder="Enter new password (min 8 characters)"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                >
                  {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-text-secondary mt-1">
                Must be at least 8 characters long
              </p>
            </div>

            {/* Confirm New Password */}
            <div>
              <label className="form-label" htmlFor="confirm-password">
                Confirm New Password
              </label>
              <div className="relative">
                <input
                  id="confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="input pr-10"
                  placeholder="Confirm your new password"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <div className="flex justify-end pt-2">
              <Button
                type="submit"
                disabled={changePasswordMutation.isPending}
                variant="primary"
              >
                {changePasswordMutation.isPending ? 'Changing Password...' : 'Change Password'}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
