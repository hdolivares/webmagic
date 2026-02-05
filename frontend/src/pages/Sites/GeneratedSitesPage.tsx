/**
 * Generated Sites Inventory - Shows AI-generated sites from generated_sites table
 * These are sites created by the system but not yet purchased by customers
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge, Button } from '@/components/ui'
import { Wand2, Search, ExternalLink, Eye, Calendar, TrendingUp, ChevronDown, ChevronUp, ExternalLink as LinkIcon } from 'lucide-react'

export const GeneratedSitesPage = () => {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [expandedSites, setExpandedSites] = useState<Set<string>>(new Set())
  
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['generated-sites', statusFilter],
    queryFn: () => api.getGeneratedSites({ 
      limit: 100,
      status: statusFilter === 'all' ? undefined : statusFilter 
    }),
    refetchInterval: 10000, // Refresh every 10 seconds to see generation progress
  })
  
  // Sort sites by created_at descending (most recent first) and filter
  const filteredAndSortedSites = [...(data?.sites || [])]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .filter((site: any) => {
      const search = searchTerm.toLowerCase()
      return (
        site.subdomain?.toLowerCase().includes(search) ||
        site.business?.name?.toLowerCase().includes(search) ||
        site.id?.toLowerCase().includes(search)
      )
    })
  
  const toggleExpanded = (siteId: string) => {
    setExpandedSites(prev => {
      const newSet = new Set(prev)
      if (newSet.has(siteId)) {
        newSet.delete(siteId)
      } else {
        newSet.add(siteId)
      }
      return newSet
    })
  }

  const getStatusBadge = (status: string) => {
    const config: Record<string, { variant: any; label: string }> = {
      generating: { variant: 'info', label: 'Generating...' },
      completed: { variant: 'success', label: 'Ready' },
      published: { variant: 'primary', label: 'Published' },
      failed: { variant: 'error', label: 'Failed' },
      draft: { variant: 'secondary', label: 'Draft' },
    }
    const { variant, label } = config[status] || { variant: 'secondary', label: status }
    return <Badge variant={variant}>{label}</Badge>
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // Stats calculations
  const stats = {
    total: data?.total || 0,
    generating: data?.sites.filter((s: any) => s.status === 'generating').length || 0,
    completed: data?.sites.filter((s: any) => s.status === 'completed').length || 0,
    published: data?.sites.filter((s: any) => s.status === 'published').length || 0,
    failed: data?.sites.filter((s: any) => s.status === 'failed').length || 0,
  }

  return (
    <div className="p-xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-lg">
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2 flex items-center gap-3">
            <Wand2 className="w-8 h-8 text-primary-500" />
            Generated Sites Inventory
          </h1>
          <p className="text-text-secondary">
            AI-generated websites ready for deployment ({data?.total || 0} total)
          </p>
        </div>
        
        <Button
          onClick={() => refetch()}
          variant="secondary"
          className="flex items-center gap-2"
        >
          Refresh Status
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-lg">
        <Card>
          <CardBody className="p-4">
            <div className="text-sm text-text-secondary mb-1">Total Sites</div>
            <div className="text-2xl font-bold text-text-primary">{stats.total}</div>
          </CardBody>
        </Card>
        
        <Card>
          <CardBody className="p-4">
            <div className="text-sm text-text-secondary mb-1 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              Generating
            </div>
            <div className="text-2xl font-bold text-info-500">{stats.generating}</div>
          </CardBody>
        </Card>
        
        <Card>
          <CardBody className="p-4">
            <div className="text-sm text-text-secondary mb-1">Ready</div>
            <div className="text-2xl font-bold text-success-500">{stats.completed}</div>
          </CardBody>
        </Card>
        
        <Card>
          <CardBody className="p-4">
            <div className="text-sm text-text-secondary mb-1">Published</div>
            <div className="text-2xl font-bold text-primary-500">{stats.published}</div>
          </CardBody>
        </Card>
        
        <Card>
          <CardBody className="p-4">
            <div className="text-sm text-text-secondary mb-1">Failed</div>
            <div className="text-2xl font-bold text-error-500">{stats.failed}</div>
          </CardBody>
        </Card>
      </div>
      
      {/* Filters */}
      <div className="flex gap-4 mb-lg">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-text-tertiary" />
          <input
            type="text"
            placeholder="Search by subdomain, business name, or ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-bg-secondary text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border border-border rounded-lg bg-bg-secondary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="all">All Status</option>
          <option value="generating">Generating</option>
          <option value="completed">Ready</option>
          <option value="published">Published</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {searchTerm && (
        <p className="text-sm text-text-secondary mb-4">
          Found {filteredAndSortedSites.length} of {data?.sites.length || 0} sites
        </p>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="flex items-center justify-center py-xl">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
            <p className="text-text-secondary">Loading generated sites...</p>
          </div>
        </div>
      ) : filteredAndSortedSites.length === 0 ? (
        <Card>
          <CardBody className="text-center py-xl">
            <Wand2 className="w-16 h-16 text-text-tertiary mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-text-primary mb-2">
              {searchTerm ? 'No sites found' : 'No generated sites yet'}
            </h3>
            <p className="text-text-secondary mb-6">
              {searchTerm
                ? 'Try adjusting your search or filters'
                : 'AI-generated sites will appear here as they are created'}
            </p>
          </CardBody>
        </Card>
      ) : (
        /* Sites Grid - 3 Columns */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAndSortedSites.map((site: any, index: number) => {
            const isExpanded = expandedSites.has(site.id)
            const business = site.business
            const rawData = business?.raw_data
            const googleMapsUrl = rawData?.link || rawData?.google_maps_url
            
            return (
              <Card key={site.id} className="hover:shadow-lg transition-shadow flex flex-col">
                <CardBody className="p-4 flex flex-col h-full">
                  {/* Header with number and status */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-100 text-primary-700 font-bold text-sm">
                        {index + 1}
                      </div>
                      {getStatusBadge(site.status)}
                    </div>
                    
                    {site.status === 'generating' && (
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-info-500"></div>
                    )}
                  </div>
                  
                  {/* Site info */}
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold text-text-primary mb-1 line-clamp-2">
                      {business?.name || site.subdomain}
                    </h3>
                    
                    <p className="text-xs text-text-secondary mb-2 line-clamp-1">
                      {site.subdomain}
                    </p>
                    
                    <div className="flex items-center gap-1 text-xs text-text-secondary mb-3">
                      <Calendar className="w-3 h-3" />
                      {formatDate(site.created_at)}
                    </div>
                    
                    {site.error_message && (
                      <div className="mb-3 p-2 bg-error-50 border border-error-200 rounded text-xs text-error-700 line-clamp-2">
                        Error: {site.error_message}
                      </div>
                    )}
                  </div>
                  
                  {/* Actions */}
                  <div className="flex flex-col gap-2 mt-3">
                    {(site.status === 'completed' || site.status === 'published') && site.subdomain && (
                      <div className="flex gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          className="flex-1 flex items-center justify-center gap-1 text-xs"
                          onClick={() => navigate(`/sites/generated/${site.id}`)}
                        >
                          <Eye className="w-3 h-3" />
                          View
                        </Button>
                        
                        <Button
                          variant="primary"
                          size="sm"
                          className="flex-1 flex items-center justify-center gap-1 text-xs"
                          onClick={() => window.open(`https://sites.lavish.solutions/${site.subdomain}`, '_blank')}
                        >
                          <ExternalLink className="w-3 h-3" />
                          Preview
                        </Button>
                      </div>
                    )}
                    
                    {/* Expandable data button */}
                    {business && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full flex items-center justify-between text-xs"
                        onClick={() => toggleExpanded(site.id)}
                      >
                        <span>Business Data</span>
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </Button>
                    )}
                  </div>
                  
                  {/* Expanded business data */}
                  {isExpanded && business && (
                    <div className="mt-3 pt-3 border-t border-border text-xs space-y-2">
                      {business.name && (
                        <div>
                          <span className="font-semibold">Name:</span> {business.name}
                        </div>
                      )}
                      {business.category && (
                        <div>
                          <span className="font-semibold">Category:</span> {business.category}
                        </div>
                      )}
                      {business.phone && (
                        <div>
                          <span className="font-semibold">Phone:</span> {business.phone}
                        </div>
                      )}
                      {business.address && (
                        <div>
                          <span className="font-semibold">Address:</span> {business.address}
                        </div>
                      )}
                      {business.rating && (
                        <div>
                          <span className="font-semibold">Rating:</span> {business.rating} ⭐ ({business.review_count || 0} reviews)
                        </div>
                      )}
                      {business.website_url && (
                        <div>
                          <span className="font-semibold">Website:</span>{' '}
                          <a 
                            href={business.website_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-primary-500 hover:underline"
                          >
                            {business.website_url}
                          </a>
                        </div>
                      )}
                      {googleMapsUrl && (
                        <div className="pt-2">
                          <a
                            href={googleMapsUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-primary-500 hover:underline font-semibold"
                          >
                            <LinkIcon className="w-3 h-3" />
                            View on Google Maps
                          </a>
                        </div>
                      )}
                    </div>
                  )}
                </CardBody>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}

