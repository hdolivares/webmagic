/**
 * Campaigns dashboard page
 */
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge } from '@/components/ui'
import { Mail, Eye, MousePointer } from 'lucide-react'

export const CampaignsPage = () => {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => api.getCampaigns({ limit: 50 }),
    retry: false, // Don't retry on this page
    refetchOnMount: false, // Don't refetch automatically
  })

  const { data: stats, isError: isStatsError } = useQuery({
    queryKey: ['campaign-stats'],
    queryFn: () => api.getCampaignStats(),
    retry: false, // Don't retry on this page
    refetchOnMount: false, // Don't refetch automatically
  })

  // Show error state
  if (isError || isStatsError) {
    return (
      <div className="p-xl">
        <div className="mb-xl">
          <h1 className="text-4xl font-bold text-text-primary mb-2">Email Campaigns</h1>
          <p className="text-text-secondary">Track your email outreach performance</p>
        </div>
        <Card>
          <CardBody>
            <div className="text-center py-xl">
              <p className="text-error text-lg mb-4">Unable to load campaigns data</p>
              <p className="text-text-secondary mb-4">
                {error instanceof Error ? error.message : 'An error occurred'}
              </p>
              <p className="text-sm text-text-secondary">
                This page will be available once you start creating campaigns.
              </p>
            </div>
          </CardBody>
        </Card>
      </div>
    )
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      sent: 'success',
      opened: 'info',
      clicked: 'primary',
      failed: 'error',
      draft: 'secondary',
    }
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>
  }

  return (
    <div className="p-xl">
      <div className="mb-xl">
        <h1 className="text-4xl font-bold text-text-primary mb-2">Email Campaigns</h1>
        <p className="text-text-secondary">Track your email outreach performance</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-md mb-md">
        <Card>
          <CardBody className="flex items-center gap-md">
            <Mail className="w-6 h-6 text-primary-600" />
            <div>
              <p className="text-2xl font-bold">{stats?.sent || 0}</p>
              <p className="text-sm text-text-secondary">Sent</p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-md">
            <Eye className="w-6 h-6 text-info" />
            <div>
              <p className="text-2xl font-bold">
                {((stats?.open_rate || 0) * 100).toFixed(1)}%
              </p>
              <p className="text-sm text-text-secondary">Open Rate</p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-md">
            <MousePointer className="w-6 h-6 text-success" />
            <div>
              <p className="text-2xl font-bold">
                {((stats?.click_rate || 0) * 100).toFixed(1)}%
              </p>
              <p className="text-sm text-text-secondary">Click Rate</p>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Campaigns list */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Campaigns ({data?.total || 0})</CardTitle>
        </CardHeader>
        <CardBody>
          {isLoading ? (
            <div className="flex items-center justify-center py-xl">
              <div className="spinner-lg" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table">
                <thead className="table-header">
                  <tr>
                    <th className="table-header-cell">Recipient</th>
                    <th className="table-header-cell">Subject</th>
                    <th className="table-header-cell">Status</th>
                    <th className="table-header-cell">Sent</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.campaigns.map((campaign) => (
                    <tr key={campaign.id} className="table-row">
                      <td className="table-cell">
                        <div>
                          <p className="font-medium">{campaign.recipient_name || 'Unknown'}</p>
                          <p className="text-xs text-text-secondary">{campaign.recipient_email}</p>
                        </div>
                      </td>
                      <td className="table-cell">{campaign.subject_line}</td>
                      <td className="table-cell">{getStatusBadge(campaign.status)}</td>
                      <td className="table-cell text-text-secondary">
                        {campaign.sent_at
                          ? new Date(campaign.sent_at).toLocaleDateString()
                          : 'Not sent'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
