/**
 * Generated Sites Inventory - Shows AI-generated sites from generated_sites table
 * These are sites created by the system but not yet purchased by customers
 */
import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge, Button } from '@/components/ui'
import { Wand2, Search, ExternalLink, Eye, Calendar, TrendingUp, ChevronDown, ChevronUp, ExternalLink as LinkIcon, Play, AlertCircle, RefreshCw, ShieldCheck, Globe, PhoneOff, ImagePlus, CreditCard, Database, Clock, Zap, HelpCircle, XCircle } from 'lucide-react'

// Statuses that mean the business passed the full triple-check validation (no website found)
const TRIPLE_VERIFIED_STATUSES = new Set(['triple_verified', 'confirmed_no_website'])

// Statuses that mean the business DOES have a website (should not be in campaigns)
const HAS_WEBSITE_STATUSES = new Set(['valid_outscraper', 'valid_scrapingdog', 'valid_manual'])

type VerificationFilter = 'all' | 'verified' | 'has_website' | 'not_verified'

export const GeneratedSitesPage = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [verificationFilter, setVerificationFilter] = useState<VerificationFilter>('all')
  const [expandedSites, setExpandedSites] = useState<Set<string>>(new Set())
  const [showNeedingGeneration, setShowNeedingGeneration] = useState(false)
  
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['generated-sites', statusFilter],
    queryFn: () => api.getGeneratedSites({ 
      limit: 100,
      status: statusFilter === 'all' ? undefined : statusFilter 
    }),
    refetchInterval: 10000, // Refresh every 10 seconds to see generation progress
  })

  // Get businesses that need generation
  const { data: needingGeneration, isLoading: loadingNeeding, refetch: refetchNeeding } = useQuery({
    queryKey: ['businesses-needing-generation'],
    queryFn: () => api.getBusinessesNeedingGeneration(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Queue all businesses mutation
  const queueAllMutation = useMutation({
    mutationFn: () => api.queueBusinessesForGeneration({ queue_all: true }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['businesses-needing-generation'] })
      queryClient.invalidateQueries({ queryKey: ['generated-sites'] })
      alert(`✅ Queued ${result.queued} businesses for website generation!`)
    },
    onError: (error: any) => {
      alert(`❌ Failed to queue businesses: ${error.message}`)
    }
  })

  // Retry a single failed site
  const retryMutation = useMutation({
    mutationFn: (businessId: string) =>
      api.queueBusinessesForGeneration({ business_ids: [businessId] }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['generated-sites'] })
    },
    onError: (error: any) => {
      alert(`❌ Failed to retry: ${error.message}`)
    },
  })

  // Mark a site as superseded because the business already has a website
  const markHasWebsiteMutation = useMutation({
    mutationFn: (siteId: string) => api.markSiteHasWebsite(siteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['generated-sites'] })
    },
    onError: (error: any) => {
      alert(`❌ Failed to mark: ${error.message}`)
    },
  })

  // Mark a site as superseded because the business is unreachable (no contact info)
  const markUnreachableMutation = useMutation({
    mutationFn: (siteId: string) => api.markSiteUnreachable(siteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['generated-sites'] })
    },
    onError: (error: any) => {
      alert(`❌ Failed to mark: ${error.message}`)
    },
  })

  // Regenerate just the 3 AI images for an existing site (keeps HTML intact)
  const regenImagesMutation = useMutation({
    mutationFn: (siteId: string) => api.regenerateSiteImages(siteId),
    onSuccess: (data) => {
      alert(`✅ ${data.message}${data.failed_slots?.length ? `\n⚠️ Failed slots: ${data.failed_slots.join(', ')}` : ''}`)
      queryClient.invalidateQueries({ queryKey: ['generated-sites'] })
    },
    onError: (error: any) => {
      alert(`❌ Image regeneration failed: ${error.message}`)
    },
  })
  
  // Sort sites by created_at descending (most recent first) and filter
  const filteredAndSortedSites = useMemo(() => {
    return [...(data?.sites || [])]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .filter((site: any) => {
        // Text search
        const search = searchTerm.toLowerCase()
        const matchesSearch = (
          site.subdomain?.toLowerCase().includes(search) ||
          site.business?.name?.toLowerCase().includes(search) ||
          site.id?.toLowerCase().includes(search)
        )
        if (!matchesSearch) return false

        // Verification filter
        const validationStatus = site.business?.website_validation_status
        if (verificationFilter === 'verified') {
          return TRIPLE_VERIFIED_STATUSES.has(validationStatus)
        }
        if (verificationFilter === 'has_website') {
          return HAS_WEBSITE_STATUSES.has(validationStatus)
        }
        if (verificationFilter === 'not_verified') {
          return !TRIPLE_VERIFIED_STATUSES.has(validationStatus) && !HAS_WEBSITE_STATUSES.has(validationStatus)
        }
        return true
      })
  }, [data?.sites, searchTerm, verificationFilter])
  
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

  // Detect closed/temporarily-closed status from the business record.
  // Falls back to raw_data for records where the model column isn't yet populated.
  const getClosedStatus = (business: any): 'temporarily_closed' | 'permanently_closed' | null => {
    const status = (
      business?.business_status ||
      business?.raw_data?.business_status ||
      ''
    ).toUpperCase()
    if (status === 'CLOSED_TEMPORARILY') return 'temporarily_closed'
    if (status === 'CLOSED_PERMANENTLY') return 'permanently_closed'
    return null
  }

  const getClosedBadge = (business: any) => {
    const closed = getClosedStatus(business)
    if (!closed) return null
    const isPermanent = closed === 'permanently_closed'
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold border ${
        isPermanent
          ? 'bg-gray-900 text-white border-gray-700'
          : 'bg-amber-100 text-amber-900 border-amber-400'
      }`}>
        <XCircle className="w-3 h-3 flex-shrink-0" />
        {isPermanent ? 'Permanently Closed' : 'Temporarily Closed'}
      </span>
    )
  }

  const getStatusBadge = (status: string) => {
    const config: Record<string, { variant: any; label: string }> = {
      generating: { variant: 'info', label: 'Generating...' },
      completed: { variant: 'success', label: 'Ready' },
      published: { variant: 'primary', label: 'Published' },
      failed: { variant: 'error', label: 'Failed' },
      draft: { variant: 'secondary', label: 'Draft' },
      superseded: { variant: 'warning', label: 'Has Own Website' },
    }
    const { variant, label } = config[status] || { variant: 'secondary', label: status }
    return <Badge variant={variant}>{label}</Badge>
  }

  const getValidationBadge = (validationStatus: string | undefined) => {
    if (!validationStatus) return null
    if (TRIPLE_VERIFIED_STATUSES.has(validationStatus)) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-success-100 text-success-700 border border-success-200">
          ✅ No Website Confirmed
        </span>
      )
    }
    const pendingStates: Record<string, string> = {
      pending: '⏳ Pending',
      needs_discovery: '🔍 Needs Discovery',
      discovery_queued: '🔍 Queued',
      discovery_in_progress: '🔍 In Progress',
      invalid_technical: '❌ Invalid',
      invalid_type: '❌ Invalid Type',
      invalid_mismatch: '❌ Mismatch',
      valid_outscraper: '🌐 Has Website',
      valid_scrapingdog: '🌐 Has Website',
      valid_manual: '🌐 Has Website',
      geo_mismatch: '🌍 Geo Mismatch',
      error: '⚠️ Error',
    }
    const label = pendingStates[validationStatus] ?? `⚠️ ${validationStatus}`
    const isHasWebsite = validationStatus.startsWith('valid_')
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${
        isHasWebsite
          ? 'bg-error-50 text-error-700 border-error-200'
          : 'bg-warning-50 text-warning-700 border-warning-200'
      }`}>
        {label}
      </span>
    )
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
  const stats = useMemo(() => ({
    total: data?.total || 0,
    generating: data?.sites.filter((s: any) => s.status === 'generating').length || 0,
    completed: data?.sites.filter((s: any) => s.status === 'completed').length || 0,
    published: data?.sites.filter((s: any) => s.status === 'published').length || 0,
    failed: data?.sites.filter((s: any) => s.status === 'failed').length || 0,
    superseded: data?.sites.filter((s: any) => s.status === 'superseded').length || 0,
    tripleVerified: data?.sites.filter((s: any) =>
      TRIPLE_VERIFIED_STATUSES.has(s.business?.website_validation_status)
    ).length || 0,
    hasWebsite: data?.sites.filter((s: any) =>
      HAS_WEBSITE_STATUSES.has(s.business?.website_validation_status)
    ).length || 0,
    creditsExhausted: data?.sites.filter((s: any) =>
      s.error_category === 'credits_exhausted'
    ).length || 0,
  }), [data?.sites])

  /**
   * Returns display config for a given error_category value.
   * Used to render consistent, actionable error indicators on site cards.
   */
  const getErrorInfo = (category: string | null | undefined, message: string | null | undefined) => {
    switch (category) {
      case 'credits_exhausted':
        return {
          Icon: CreditCard,
          label: 'API Credits Exhausted',
          detail: 'Add Anthropic credits to resume.',
          link: 'https://console.anthropic.com/settings/billing',
          linkLabel: 'Top up →',
          bg: 'bg-red-50',
          border: 'border-red-300',
          text: 'text-red-700',
          iconColor: 'text-red-500',
        }
      case 'data_error':
        return {
          Icon: Database,
          label: 'Business Data Issue',
          detail: message || 'Missing or invalid field in business data.',
          bg: 'bg-orange-50',
          border: 'border-orange-300',
          text: 'text-orange-700',
          iconColor: 'text-orange-500',
        }
      case 'api_error':
        return {
          Icon: Zap,
          label: 'External API Error',
          detail: message || 'A third-party API call failed.',
          bg: 'bg-yellow-50',
          border: 'border-yellow-300',
          text: 'text-yellow-700',
          iconColor: 'text-yellow-600',
        }
      case 'timeout':
        return {
          Icon: Clock,
          label: 'Generation Timed Out',
          detail: message || 'The generation took too long and was stopped.',
          bg: 'bg-blue-50',
          border: 'border-blue-300',
          text: 'text-blue-700',
          iconColor: 'text-blue-500',
        }
      default:
        return {
          Icon: message ? XCircle : HelpCircle,
          label: 'Generation Failed',
          detail: message || 'An unexpected error occurred.',
          bg: 'bg-error-50',
          border: 'border-error-200',
          text: 'text-error-700',
          iconColor: 'text-error-500',
        }
    }
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
      <div className="grid grid-cols-2 md:grid-cols-7 gap-4 mb-lg">
        <Card>
          <CardBody className="p-4">
            <div className="text-sm text-text-secondary mb-1">Total Sites</div>
            <div className="text-2xl font-bold text-text-primary">{stats.total}</div>
          </CardBody>
        </Card>
        
        <Card
          className={`cursor-pointer transition-all ${verificationFilter === 'verified' ? 'ring-2 ring-success-500' : 'hover:shadow-md'}`}
          onClick={() => setVerificationFilter(v => v === 'verified' ? 'all' : 'verified')}
        >
          <CardBody className="p-4">
            <div className="text-sm text-text-secondary mb-1 flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-success-500" />
              No Website
            </div>
            <div className="text-2xl font-bold text-success-600">{stats.tripleVerified}</div>
            <div className="text-xs text-text-tertiary mt-1">Confirmed &amp; ready</div>
          </CardBody>
        </Card>

        <Card
          className={`cursor-pointer transition-all ${verificationFilter === 'has_website' ? 'ring-2 ring-warning-500' : 'hover:shadow-md'}`}
          onClick={() => setVerificationFilter(v => v === 'has_website' ? 'all' : 'has_website')}
        >
          <CardBody className="p-4">
            <div className="text-sm text-text-secondary mb-1 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 text-warning-500" />
              Has Website
            </div>
            <div className="text-2xl font-bold text-warning-600">{stats.hasWebsite}</div>
            <div className="text-xs text-text-tertiary mt-1">Already had one</div>
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

      {/* Anthropic Credits Exhausted Banner */}
      {stats.creditsExhausted > 0 && (
        <Card className="mb-lg border-l-4 border-l-red-500 bg-red-50">
          <CardBody className="p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <CreditCard className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-base font-semibold text-red-900 mb-1">
                    Anthropic API Credits Exhausted
                  </h3>
                  <p className="text-sm text-red-700 mb-2">
                    {stats.creditsExhausted} site{stats.creditsExhausted !== 1 ? 's are' : ' is'} stuck because
                    the Anthropic Claude API account has run out of credits. Generation will resume
                    automatically once credits are added.
                  </p>
                  <p className="text-xs text-red-600">
                    Affected sites show a <strong>Credits Exhausted</strong> badge below. Once you top up,
                    click <strong>Retry Generation</strong> on each card or wait for the next scheduled run.
                  </p>
                </div>
              </div>
              <a
                href="https://console.anthropic.com/settings/billing"
                target="_blank"
                rel="noopener noreferrer"
                className="flex-shrink-0 flex items-center gap-1.5 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                Add Credits
              </a>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Businesses Needing Generation Alert */}
      {needingGeneration && needingGeneration.total > 0 && (
        <Card className="mb-lg border-l-4 border-l-warning-500 bg-warning-50">
          <CardBody className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <AlertCircle className="w-6 h-6 text-warning-600 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="text-lg font-semibold text-warning-900 mb-2">
                    {needingGeneration.total} Business{needingGeneration.total !== 1 ? 'es' : ''} Need Website Generation
                  </h3>
                  <p className="text-sm text-warning-700 mb-3">
                    These businesses have been validated as having no existing website and are ready for AI generation.
                  </p>
                  
                  {showNeedingGeneration && (
                    <div className="mt-4 max-h-60 overflow-y-auto bg-white rounded-lg p-4 space-y-2">
                      {needingGeneration.businesses.slice(0, 20).map((biz) => (
                        <div key={biz.id} className="flex items-center justify-between py-2 px-3 hover:bg-gray-50 rounded">
                          <div className="flex-1">
                            <div className="font-medium text-gray-900">{biz.name}</div>
                            <div className="text-sm text-gray-600">
                              {biz.category} • {biz.city}, {biz.state}
                            </div>
                          </div>
                          <Badge variant="secondary" className="ml-2">
                            {biz.website_validation_status}
                          </Badge>
                        </div>
                      ))}
                      {needingGeneration.total > 20 && (
                        <div className="text-center text-sm text-gray-500 py-2">
                          ... and {needingGeneration.total - 20} more
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex flex-col gap-2 ml-4">
                <Button
                  onClick={() => queueAllMutation.mutate()}
                  disabled={queueAllMutation.isPending}
                  className="flex items-center gap-2 bg-warning-600 hover:bg-warning-700 text-white"
                >
                  <Play className="w-4 h-4" />
                  {queueAllMutation.isPending ? 'Queueing...' : `Queue All ${needingGeneration.total}`}
                </Button>
                
                <Button
                  onClick={() => setShowNeedingGeneration(!showNeedingGeneration)}
                  variant="secondary"
                  size="sm"
                >
                  {showNeedingGeneration ? 'Hide List' : 'Show List'}
                </Button>
              </div>
            </div>
          </CardBody>
        </Card>
      )}
      
      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-4">
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
          <option value="superseded">Has Own Website</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Verification Filter Tabs */}
      <div className="flex items-center gap-2 mb-lg flex-wrap">
        <span className="text-sm text-text-secondary font-medium mr-1">Validation:</span>
        {(
          [
            { value: 'all', label: 'All', count: data?.sites.length || 0, activeClass: 'bg-primary-100 border-primary-500 text-primary-700', activeBadge: 'bg-primary-500 text-white' },
            { value: 'verified', label: '✅ No Website Confirmed', count: stats.tripleVerified, activeClass: 'bg-success-100 border-success-500 text-success-700', activeBadge: 'bg-success-500 text-white' },
            { value: 'has_website', label: '🌐 Has Own Website', count: stats.hasWebsite, activeClass: 'bg-warning-100 border-warning-500 text-warning-700', activeBadge: 'bg-warning-500 text-white' },
            { value: 'not_verified', label: '⏳ Unconfirmed', count: (data?.sites.length || 0) - stats.tripleVerified - stats.hasWebsite, activeClass: 'bg-secondary-100 border-secondary-400 text-secondary-700', activeBadge: 'bg-secondary-500 text-white' },
          ] as { value: VerificationFilter; label: string; count: number; activeClass: string; activeBadge: string }[]
        ).map(({ value, label, count, activeClass, activeBadge }) => (
          <button
            key={value}
            onClick={() => setVerificationFilter(value)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
              verificationFilter === value
                ? activeClass
                : 'bg-bg-secondary border-border text-text-secondary hover:border-text-secondary'
            }`}
          >
            {label}
            <span className={`text-xs px-1.5 py-0.5 rounded-full ${
              verificationFilter === value ? activeBadge : 'bg-bg-tertiary text-text-tertiary'
            }`}>
              {count}
            </span>
          </button>
        ))}
        {(verificationFilter !== 'all' || statusFilter !== 'all' || searchTerm) && (
          <button
            onClick={() => { setVerificationFilter('all'); setStatusFilter('all'); setSearchTerm('') }}
            className="text-xs text-text-tertiary hover:text-text-secondary underline ml-2"
          >
            Clear filters
          </button>
        )}
      </div>

      {(searchTerm || verificationFilter !== 'all' || statusFilter !== 'all') && (
        <p className="text-sm text-text-secondary mb-4">
          Showing {filteredAndSortedSites.length} of {data?.sites.length || 0} sites
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
            // Construct Google Maps URL from place_id if available
            const googleMapsUrl = business?.gmb_place_id 
              ? `https://www.google.com/maps/place/?q=place_id:${business.gmb_place_id}`
              : (rawData?.link || rawData?.google_maps_url)
            
            const isSuperseded = site.status === 'superseded'
            const closedStatus = getClosedStatus(business)
            const isClosed = closedStatus !== null

            return (
              <Card key={site.id} className={`hover:shadow-lg transition-shadow flex flex-col ${
                isSuperseded ? 'border-warning-300 border-2' :
                isClosed ? 'border-gray-400 border-2 opacity-85' : ''
              }`}>
                <CardBody className="p-4 flex flex-col h-full">
                  {/* Header with number and status */}
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm ${isSuperseded ? 'bg-warning-100 text-warning-700' : 'bg-primary-100 text-primary-700'}`}>
                        {index + 1}
                      </div>
                      {getStatusBadge(site.status)}
                    </div>
                    
                    {site.status === 'generating' && (
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-info-500"></div>
                    )}
                  </div>

                  {/* Superseded: show comparison banner */}
                  {isSuperseded && business?.website_url && (
                    <div className="mb-3 p-2 bg-warning-50 border border-warning-200 rounded-lg">
                      <p className="text-xs font-semibold text-warning-800 mb-1.5">Website Comparison</p>
                      <div className="space-y-1">
                        <a
                          href={business.website_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-xs text-warning-700 hover:text-warning-900 hover:underline truncate"
                          title={business.website_url}
                        >
                          <ExternalLink className="w-3 h-3 flex-shrink-0" />
                          <span className="font-medium">Their site:</span>
                          <span className="truncate">{business.website_url.replace(/^https?:\/\/(www\.)?/, '')}</span>
                        </a>
                        <a
                          href={`https://sites.lavish.solutions/${site.subdomain}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-xs text-primary-600 hover:text-primary-800 hover:underline truncate"
                        >
                          <ExternalLink className="w-3 h-3 flex-shrink-0" />
                          <span className="font-medium">Our site:</span>
                          <span className="truncate">{site.subdomain}</span>
                        </a>
                      </div>
                    </div>
                  )}
                  
                  {/* Closed business badge — shown prominently for any closed business */}
                  {isClosed && (
                    <div className="mb-3">
                      {getClosedBadge(business)}
                    </div>
                  )}

                  {/* Validation status badge (non-superseded only) */}
                  {!isSuperseded && !isClosed && (
                    <div className="mb-3">
                      {getValidationBadge(business?.website_validation_status)}
                    </div>
                  )}
                  
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
                    
                    {(site.error_message || site.error_category) && (() => {
                      const err = getErrorInfo(site.error_category, site.error_message)
                      return (
                        <div className={`mb-3 p-2 ${err.bg} border ${err.border} rounded-lg`}>
                          <div className={`flex items-center gap-1.5 ${err.text} font-semibold text-xs mb-1`}>
                            <err.Icon className={`w-3.5 h-3.5 flex-shrink-0 ${err.iconColor}`} />
                            {err.label}
                          </div>
                          <p className={`text-xs ${err.text} opacity-80 line-clamp-2`}>
                            {err.detail}
                          </p>
                          {err.link && (
                            <a
                              href={err.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={`text-xs font-medium ${err.text} underline mt-1 inline-block`}
                            >
                              {err.linkLabel}
                            </a>
                          )}
                        </div>
                      )
                    })()}
                  </div>
                  
                  {/* Actions */}
                  <div className="flex flex-col gap-2 mt-3">
                    {(site.status === 'completed' || site.status === 'published' || isSuperseded) && site.subdomain && (
                      <div className="flex gap-2">
                        {/* View = in-app detail page with iframe + business data */}
                        <Button
                          variant="secondary"
                          size="sm"
                          className="flex-1 flex items-center justify-center gap-1 text-xs"
                          onClick={() => navigate(`/sites/generated/${site.id}`)}
                          title="View site details inside the admin panel"
                        >
                          <Eye className="w-3 h-3" />
                          View
                        </Button>

                        {/* Preview = open live site in a new browser tab */}
                        <Button
                          variant={isSuperseded ? 'secondary' : 'primary'}
                          size="sm"
                          className="flex-1 flex items-center justify-center gap-1 text-xs"
                          onClick={() => window.open(site.short_url || `https://sites.lavish.solutions/${site.subdomain}`, '_blank')}
                          title="Open our generated site in a new tab"
                        >
                          <ExternalLink className="w-3 h-3" />
                          {isSuperseded ? 'Our Site' : 'Preview'}
                        </Button>
                      </div>
                    )}

                    {/* Retry button for failed sites */}
                    {site.status === 'failed' && site.business?.id && (
                      <Button
                        variant="secondary"
                        size="sm"
                        className="w-full flex items-center justify-center gap-1 text-xs text-warning-700 border-warning-300 hover:bg-warning-50"
                        onClick={() => retryMutation.mutate(site.business.id)}
                        disabled={retryMutation.isPending}
                        title="Re-queue this site for generation"
                      >
                        <RefreshCw className={`w-3 h-3 ${retryMutation.isPending ? 'animate-spin' : ''}`} />
                        {retryMutation.isPending ? 'Retrying…' : 'Retry Generation'}
                      </Button>
                    )}

                    {/* Admin actions: mark as has-own-website or unreachable */}
                    {site.status !== 'superseded' && (
                      <div className="flex gap-1.5">
                        <button
                          className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-medium text-warning-700 bg-warning-50 border border-warning-200 hover:bg-warning-100 transition-colors disabled:opacity-50"
                          onClick={() => {
                            if (confirm('Mark this business as already having a website? The generated site will be flagged as superseded.')) {
                              markHasWebsiteMutation.mutate(site.id)
                            }
                          }}
                          disabled={markHasWebsiteMutation.isPending}
                          title="Business already has its own website"
                        >
                          <Globe className="w-3 h-3" />
                          Has Website
                        </button>
                        <button
                          className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-medium text-error-700 bg-error-50 border border-error-200 hover:bg-error-100 transition-colors disabled:opacity-50"
                          onClick={() => {
                            if (confirm('Mark this business as unreachable (no phone/email)? The generated site will be flagged as superseded.')) {
                              markUnreachableMutation.mutate(site.id)
                            }
                          }}
                          disabled={markUnreachableMutation.isPending}
                          title="Business has no phone or email — cannot be contacted"
                        >
                          <PhoneOff className="w-3 h-3" />
                          Unreachable
                        </button>
                      </div>
                    )}

                    {/* Regen images — available for any completed/published site */}
                    {(site.status === 'completed' || site.status === 'published') && (
                      <button
                        className="w-full flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-medium text-purple-700 bg-purple-50 border border-purple-200 hover:bg-purple-100 transition-colors disabled:opacity-50"
                        onClick={() => {
                          if (confirm('Regenerate the 3 AI images (hero, about, services) for this site? The existing HTML is kept — only the image files are overwritten.')) {
                            regenImagesMutation.mutate(site.id)
                          }
                        }}
                        disabled={regenImagesMutation.isPending}
                        title="Regenerate hero, about, and services images with correct brand context"
                      >
                        <ImagePlus className="w-3 h-3" />
                        {regenImagesMutation.isPending ? 'Generating…' : 'Regen Images'}
                      </button>
                    )}
                    
                    {/* Show short link if available */}
                    {site.short_url && (site.status === 'completed' || site.status === 'published') && (
                      <div className="text-xs text-text-secondary truncate" title={site.short_url}>
                        <LinkIcon className="w-3 h-3 inline mr-1" />
                        {site.short_url}
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
                        <div className="pt-2 mt-2 border-t border-border">
                          <a
                            href={googleMapsUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 px-3 py-2 mt-2 text-xs font-semibold text-primary-600 bg-primary-50 hover:bg-primary-100 rounded-lg transition-colors"
                          >
                            <ExternalLink className="w-4 h-4" />
                            View Google Business Profile
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

