/**
 * Login page
 */
import { useState, FormEvent, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui'

export const LoginPage = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { unifiedLogin, isLoading, error, clearError } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Check for password reset success message
  useEffect(() => {
    if (searchParams.get('reset') === 'success') {
      setSuccessMessage('Password reset successful! You can now log in with your new password.')
      // Clear the query param
      setTimeout(() => {
        const newUrl = window.location.pathname
        window.history.replaceState({}, '', newUrl)
      }, 100)
    }
  }, [searchParams])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    clearError()
    setSuccessMessage(null)

    try {
      const userType = await unifiedLogin({ email, password })
      
      // Redirect based on user type
      if (userType === 'admin') {
        navigate('/dashboard')
      } else if (userType === 'customer') {
        navigate('/customer/sites')
      }
    } catch (err) {
      // Error handled by useAuth
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-secondary">
      <div className="card w-full max-w-md p-xl">
        {/* Logo */}
        <div className="text-center mb-xl">
          <h1 className="text-4xl font-bold text-gradient mb-2">WebMagic</h1>
          <p className="text-text-secondary">Sign in to your account</p>
        </div>

        {/* Login form */}
        <form onSubmit={handleSubmit} className="space-y-md">
          {successMessage && (
            <div className="bg-success/10 border border-success/30 text-success px-md py-sm rounded-md">
              <p className="text-sm">
                {successMessage}
              </p>
            </div>
          )}

          {error && (
            <div className="alert-error">
              <p className="text-sm">
                {typeof error === 'string' ? error : 'An error occurred. Please try again.'}
              </p>
            </div>
          )}

          <div>
            <label htmlFor="email" className="label label-required">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input"
              placeholder="admin@webmagic.com"
              required
            />
          </div>

          <div>
            <label htmlFor="password" className="label label-required">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input"
              placeholder="••••••••"
              required
            />
            <div style={{ textAlign: 'right', marginTop: '0.5rem' }}>
              <a
                href="/forgot-password"
                className="text-sm text-primary hover:text-primary-hover"
                style={{ textDecoration: 'none', transition: 'color 0.2s ease' }}
              >
                Forgot your password?
              </a>
            </div>
          </div>

          <Button type="submit" className="w-full" isLoading={isLoading}>
            Sign In
          </Button>
        </form>

        {/* Footer */}
        <p className="text-center text-sm text-text-tertiary mt-lg">
          WebMagic Admin Panel v1.0
        </p>
      </div>
    </div>
  )
}
