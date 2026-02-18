/**
 * Notification Settings
 *
 * Lets admins configure which email address receives:
 *  - New ticket alerts
 *  - Customer reply alerts
 *
 * Value is stored in system_settings (DB), falling back to the
 * server's SUPPORT_ADMIN_EMAIL env var when no DB value is set.
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Mail, CheckCircle2, AlertCircle, Info } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardBody } from '@/components/ui'
import { api } from '@/services/api'

export const NotificationSettings = () => {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [saved, setSaved] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['notification-settings'],
    queryFn: () => api.getNotificationSettings(),
  })

  // Sync local state when data loads
  useEffect(() => {
    if (data) {
      setEmail(data.support_admin_email)
      setSaved(false)
    }
  }, [data])

  const mutation = useMutation({
    mutationFn: (value: string) => api.updateNotificationSettings(value),
    onSuccess: () => {
      setSaved(true)
      queryClient.invalidateQueries({ queryKey: ['notification-settings'] })
      setTimeout(() => setSaved(false), 3000)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim()) return
    mutation.mutate(email.trim())
  }

  const isDirty = data && email !== data.support_admin_email
  const isDefault = data && email === data.config_default

  return (
    <div className="space-y-lg max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-sm">
            <Mail className="w-5 h-5 text-primary-600" />
            Support Notification Email
          </CardTitle>
        </CardHeader>
        <CardBody className="space-y-lg">

          {/* Info banner */}
          <div className="flex gap-sm p-sm rounded-md bg-info-light dark:bg-info-dark/20 border border-info text-sm text-info-dark dark:text-info-light">
            <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>
              This address receives an email every time a customer opens a new support ticket
              or replies to an existing one. It can be a single address or a shared inbox.
            </span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-md">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-xs">
                Notification Email Address
              </label>
              {isLoading ? (
                <div className="form-input w-full animate-pulse bg-background-secondary" style={{ height: '2.5rem' }} />
              ) : (
                <input
                  type="email"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); setSaved(false) }}
                  placeholder={data?.config_default ?? 'admin@yourdomain.com'}
                  className="form-input w-full"
                  required
                />
              )}
              <div className="mt-xs flex items-center justify-between">
                <p className="text-xs text-text-tertiary">
                  {isDefault
                    ? 'Using server default — override it by saving a different address.'
                    : `Server default: ${data?.config_default}`}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-md">
              <button
                type="submit"
                disabled={!isDirty || mutation.isPending || isLoading}
                className="btn-primary"
              >
                {mutation.isPending ? 'Saving…' : 'Save'}
              </button>

              {saved && (
                <span className="flex items-center gap-xs text-sm text-success">
                  <CheckCircle2 className="w-4 h-4" />
                  Saved — new tickets will notify this address.
                </span>
              )}

              {mutation.isError && (
                <span className="flex items-center gap-xs text-sm text-error">
                  <AlertCircle className="w-4 h-4" />
                  Failed to save. Please try again.
                </span>
              )}
            </div>
          </form>
        </CardBody>
      </Card>

      {/* How it works */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">When will you receive emails?</CardTitle>
        </CardHeader>
        <CardBody>
          <ul className="space-y-sm text-sm text-text-secondary">
            <li className="flex items-start gap-sm">
              <span className="badge-info mt-0.5 flex-shrink-0">New</span>
              <span>A customer submits a new support ticket — you get an email with a direct link to the ticket in the admin panel.</span>
            </li>
            <li className="flex items-start gap-sm">
              <span className="badge-warning mt-0.5 flex-shrink-0">Reply</span>
              <span>A customer replies to an existing ticket — you get an email with their message and a link to respond.</span>
            </li>
          </ul>
          <p className="text-xs text-text-tertiary mt-md">
            Customers receive emails when you (or the AI) reply to their ticket, using a separate template.
          </p>
        </CardBody>
      </Card>
    </div>
  )
}
