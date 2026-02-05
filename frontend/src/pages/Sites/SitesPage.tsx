/**
 * Deployed Sites page - Shows customer-purchased sites from sites table
 * These are sites that customers have bought and are actively managing
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge, Button } from '@/components/ui'
import { Globe, ExternalLink, Search, DollarSign, Users } from 'lucide-react'

export const SitesPage = () => {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  
  const { data, isLoading } = useQuery({
    queryKey: ['deployed-sites'],
    queryFn: () => api.getSites({ limit: 50 }),
  })
  
  // Filter sites based on search term
  const filteredSites = data?.sites.filter((site: any) => {
    const search = searchTerm.toLowerCase()
    return (
      site.site_title?.toLowerCase().includes(search) ||
      site.slug?.toLowerCase().includes(search) ||
      site.business_id?.toLowerCase().includes(search)
    )
  }) || []

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      active: 'success',
      owned: 'success',
      preview: 'info',
      suspended: 'warning',
      cancelled: 'error',
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
      {/* Header */}
      <div className="flex items-center justify-between mb-xl">
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2 flex items-center gap-3">
            <Globe className="w-8 h-8 text-success-500" />
            Deployed Customer Sites
          </h1>
          <p className="text-text-secondary">
            Customer-purchased and managed websites ({data?.total || 0} total)
          </p>
        </div>
      </div>
      
      {/* Search Bar */}
      {data && data.sites.length > 0 && (
        <div className="mb-lg">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-text-tertiary" />
            <input
              type="text"
              placeholder="Search sites by name, slug, or business ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-bg-secondary text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          {searchTerm && (
            <p className="text-sm text-text-secondary mt-2">
              Found {filteredSites.length} of {data.sites.length} sites
            </p>
          )}
        </div>
      )}

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
      ) : filteredSites.length === 0 ? (
        <Card>
          <CardBody className="text-center py-xl">
            <Search className="w-12 h-12 text-text-tertiary mx-auto mb-md" />
            <h3 className="text-xl font-semibold text-text-primary mb-sm">No sites found</h3>
            <p className="text-text-secondary">
              No sites match your search. Try a different search term.
            </p>
          </CardBody>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-md">
          {filteredSites.map((site: any) => (
            <Card 
              key={site.id} 
              hover
              onClick={() => window.open(site.site_url, '_blank')}
              className="cursor-pointer transition-all hover:shadow-lg"
            >
              <CardHeader className="flex items-center gap-md">
                <Globe className="w-5 h-5 text-primary-600" />
                <div className="flex-1 min-w-0">
                  <CardTitle className="truncate" title={site.site_title || site.slug}>
                    {site.site_title?.split('|')[0].trim() || site.slug}
                  </CardTitle>
                </div>
                {getStatusBadge(site.status || 'active')}
              </CardHeader>
              <CardBody>
                <div className="space-y-sm text-sm">
                  <div>
                    <span className="text-text-secondary">URL:</span>
                    <p className="font-mono text-xs text-primary-600 truncate" title={site.site_url}>
                      {site.site_url?.replace('https://', '').replace('http://', '')}
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
                      <p className="font-mono text-xs text-text-primary truncate" title={site.business_id}>
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
                    <span className="flex items-center gap-1 text-primary-600">
                      <ExternalLink className="w-3 h-3" />
                      View
                    </span>
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
