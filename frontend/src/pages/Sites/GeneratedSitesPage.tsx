/**
 * Generated Sites Inventory - Shows AI-generated sites from generated_sites table
 * These are sites created by the system but not yet purchased by customers
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge, Button } from '@/components/ui'
import { Wand2, Search, ExternalLink, Eye, Calendar, TrendingUp } from 'lucide-react'

export const GeneratedSitesPage = () => {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['generated-sites', statusFilter],
    queryFn: () => api.getGeneratedSites({ 
      limit: 100,
      status: statusFilter === 'all' ? undefined : statusFilter 
    }),
    refetchInterval: 10000, // Refresh every 10 seconds to see generation progress
  })
  
  // Filter sites based on search term
  const filteredSites = data?.sites.filter((site: any) => {
    const search = searchTerm.toLowerCase()
    return (
      site.subdomain?.toLowerCase().includes(search) ||
      site.business_name?.toLowerCase().includes(search) ||
      site.id?.toLowerCase().includes(search)
    )
  }) || []

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
          Found {filteredSites.length} of {data?.sites.length || 0} sites
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
      ) : filteredSites.length === 0 ? (
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
        /* Sites Grid */
        <div className="grid grid-cols-1 gap-4">
          {filteredSites.map((site: any) => (
            <Card key={site.id} className="hover:shadow-lg transition-shadow">
              <CardBody className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-text-primary">
                        {site.subdomain}
                      </h3>
                      {getStatusBadge(site.status)}
                    </div>
                    
                    {site.business_name && (
                      <p className="text-text-secondary mb-2">
                        Business: <span className="font-medium text-text-primary">{site.business_name}</span>
                      </p>
                    )}
                    
                    <div className="flex items-center gap-6 text-sm text-text-secondary">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        Created: {formatDate(site.created_at)}
                      </div>
                      
                      {site.generation_completed_at && (
                        <div className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          Completed: {formatDate(site.generation_completed_at)}
                        </div>
                      )}
                      
                      {site.version && (
                        <div>Version: {site.version}</div>
                      )}
                    </div>
                    
                    {site.error_message && (
                      <div className="mt-2 p-2 bg-error-50 border border-error-200 rounded text-sm text-error-700">
                        Error: {site.error_message}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2 ml-4">
                    {(site.status === 'completed' || site.status === 'published') && (
                      <>
                        <Button
                          variant="secondary"
                          size="sm"
                          className="flex items-center gap-1"
                          onClick={() => navigate(`/sites/generated/${site.id}`)}
                        >
                          <Eye className="w-4 h-4" />
                          View
                        </Button>
                        
                        {site.subdomain && (
                          <Button
                            variant="primary"
                            size="sm"
                            className="flex items-center gap-1"
                            onClick={() => window.open(`https://sites.lavish.solutions/${site.subdomain}`, '_blank')}
                          >
                            <ExternalLink className="w-4 h-4" />
                            Preview
                          </Button>
                        )}
                      </>
                    )}
                    
                    {site.status === 'generating' && (
                      <div className="flex items-center gap-2 text-info-500">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-info-500"></div>
                        <span className="text-sm">In Progress...</span>
                      </div>
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

