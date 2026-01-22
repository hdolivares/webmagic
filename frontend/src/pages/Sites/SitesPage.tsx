/**
 * Deployed Sites page - Shows purchased/deployed customer sites
 */
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge, Button } from '@/components/ui'
import { Globe, ExternalLink, Wand2 } from 'lucide-react'

export const SitesPage = () => {
  const navigate = useNavigate()
  
  const { data, isLoading } = useQuery({
    queryKey: ['deployed-sites'],
    queryFn: () => api.getSites({ limit: 50 }),
  })

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      active: 'success',
      pending: 'info',
      inactive: 'error',
      published: 'primary',
    }
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>
  }
  
  const getSubscriptionBadge = (status: string | null) => {
    if (!status) return null
    const variants: Record<string, any> = {
      active: 'success',
      cancelled: 'error',
      past_due: 'warning',
      trialing: 'info',
    }
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>
  }

  return (
    <div className="p-xl">
      <div className="flex items-center justify-between mb-xl">
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">Deployed Sites</h1>
          <p className="text-text-secondary">View all customer websites</p>
        </div>
        
        <Button
          onClick={() => navigate('/sites/image-generator')}
          variant="primary"
          className="flex items-center gap-2"
        >
          <Wand2 className="w-4 h-4" />
          Test Image Generator
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-xl">
          <div className="spinner-lg" />
        </div>
      ) : data?.sites.length === 0 ? (
        <Card>
          <CardBody className="text-center py-xl">
            <Globe className="w-12 h-12 text-text-tertiary mx-auto mb-md" />
            <h3 className="text-xl font-semibold text-text-primary mb-sm">No sites yet</h3>
            <p className="text-text-secondary">
              Deployed sites will appear here once customers purchase them.
            </p>
          </CardBody>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-md">
          {data?.sites.map((site: any) => (
            <Card key={site.id} hover>
              <CardHeader className="flex items-center gap-md">
                <Globe className="w-5 h-5 text-primary-600" />
                <div className="flex-1">
                  <CardTitle>{site.site_title || site.slug}</CardTitle>
                </div>
                {getStatusBadge(site.status || 'active')}
              </CardHeader>
              <CardBody>
                <div className="space-y-sm text-sm">
                  <div>
                    <span className="text-text-secondary">URL:</span>
                    <p className="font-mono text-xs text-primary-600 truncate">
                      {site.site_url}
                    </p>
                  </div>
                  
                  {site.subscription_status && (
                    <div>
                      <span className="text-text-secondary">Subscription:</span>
                      <div className="mt-1">
                        {getSubscriptionBadge(site.subscription_status)}
                      </div>
                    </div>
                  )}
                  
                  {site.business_id && (
                    <div>
                      <span className="text-text-secondary">Business ID:</span>
                      <p className="font-mono text-xs text-text-primary truncate">
                        {site.business_id}
                      </p>
                    </div>
                  )}
                  
                  <div className="flex items-center justify-between text-text-tertiary text-xs pt-sm border-t border-border">
                    <span>
                      {site.purchased_at 
                        ? `Purchased ${new Date(site.purchased_at).toLocaleDateString()}`
                        : `Created ${new Date(site.created_at).toLocaleDateString()}`
                      }
                    </span>
                    {site.site_url && (
                      <a
                        href={site.site_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-primary-600 hover:underline"
                      >
                        <ExternalLink className="w-3 h-3" />
                        View
                      </a>
                    )}
                  </div>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
