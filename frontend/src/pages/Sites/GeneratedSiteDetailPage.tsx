/**
 * Generated Site Detail Page
 * Internal admin view: iframe preview + business data + management actions
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  ExternalLink,
  Building2,
  Star,
  Phone,
  MapPin,
  Globe,
  Calendar,
  RefreshCw,
  Monitor,
  Maximize2,
  Minimize2,
  XCircle,
} from 'lucide-react'
import { api } from '@/services/api'
import { Badge, Button, Card, CardBody } from '@/components/ui'

// Detect closed/temporarily-closed status from the business record.
// Falls back to raw_data for records where the model column isn't yet populated.
function getClosedStatus(business: any): 'temporarily_closed' | 'permanently_closed' | null {
  const status = (
    business?.business_status ||
    business?.raw_data?.business_status ||
    ''
  ).toUpperCase()
  if (status === 'CLOSED_TEMPORARILY') return 'temporarily_closed'
  if (status === 'CLOSED_PERMANENTLY') return 'permanently_closed'
  return null
}

function ClosedBadge({ business }: { business: any }) {
  const closed = getClosedStatus(business)
  if (!closed) return null
  const isPermanent = closed === 'permanently_closed'
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border ${
      isPermanent
        ? 'bg-gray-900 text-white border-gray-700'
        : 'bg-amber-100 text-amber-900 border-amber-400'
    }`}>
      <XCircle className="w-3.5 h-3.5 flex-shrink-0" />
      {isPermanent ? 'Permanently Closed' : 'Temporarily Closed'}
    </span>
  )
}

export const GeneratedSiteDetailPage = () => {
  const { siteId } = useParams<{ siteId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [iframeFullscreen, setIframeFullscreen] = useState(false)

  const { data: site, isLoading, error } = useQuery({
    queryKey: ['generated-site-detail', siteId],
    queryFn: () => api.getSite(siteId!),
    enabled: !!siteId,
  })
  const business = site?.business
  const liveUrl = site?.subdomain
    ? `https://sites.lavish.solutions/${site.subdomain}`
    : null

  const getStatusBadge = (status: string) => {
    const config: Record<string, { variant: any; label: string }> = {
      generating: { variant: 'info',      label: 'Generating…' },
      completed:  { variant: 'success',   label: 'Ready' },
      published:  { variant: 'primary',   label: 'Published' },
      failed:     { variant: 'error',     label: 'Failed' },
      draft:      { variant: 'secondary', label: 'Draft' },
    }
    const { variant, label } = config[status] || { variant: 'secondary', label: status }
    return <Badge variant={variant}>{label}</Badge>
  }

  const formatDate = (d: string | null) =>
    d ? new Date(d).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    }) : 'N/A'

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500" />
      </div>
    )
  }

  if (error || !site) {
    return (
      <div className="p-xl">
        <Button variant="secondary" onClick={() => navigate('/sites/generated')} className="mb-4 flex items-center gap-2">
          <ArrowLeft className="w-4 h-4" /> Back to Sites
        </Button>
        <Card><CardBody className="text-center py-xl">
          <p className="text-error-500 font-semibold">Site not found.</p>
        </CardBody></Card>
      </div>
    )
  }

  return (
    <div className="p-xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-lg">
        <div className="flex items-center gap-3">
          <Button variant="secondary" size="sm" onClick={() => navigate('/sites/generated')} className="flex items-center gap-2">
            <ArrowLeft className="w-4 h-4" /> Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3 flex-wrap">
              {business?.name || site.subdomain}
              {getStatusBadge(site.status)}
              <ClosedBadge business={business} />
            </h1>
            <p className="text-sm text-text-secondary mt-1">{site.subdomain}</p>
          </div>
        </div>

        {liveUrl && (
          <Button
            variant="primary"
            className="flex items-center gap-2"
            onClick={() => window.open(liveUrl, '_blank')}
          >
            <ExternalLink className="w-4 h-4" />
            Open Live Site
          </Button>
        )}
      </div>

      <div className={`grid gap-6 ${iframeFullscreen ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-3'}`}>

        {/* ── Iframe preview ─────────────────────────────────────────────── */}
        <div className={iframeFullscreen ? 'col-span-1' : 'lg:col-span-2'}>
          <Card className="overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-bg-secondary">
              <div className="flex items-center gap-2 text-sm text-text-secondary">
                <Monitor className="w-4 h-4" />
                <span className="font-mono truncate max-w-xs">{liveUrl}</span>
              </div>
              <div className="flex items-center gap-2">
                {liveUrl && (
                  <Button variant="ghost" size="sm" onClick={() => window.open(liveUrl, '_blank')} title="Open in new tab">
                    <ExternalLink className="w-4 h-4" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIframeFullscreen(f => !f)}
                  title={iframeFullscreen ? 'Collapse' : 'Expand'}
                >
                  {iframeFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                </Button>
              </div>
            </div>

            {liveUrl ? (
              <iframe
                key={liveUrl}
                src={liveUrl}
                title={business?.name || site.subdomain}
                className="w-full border-0"
                style={{ height: iframeFullscreen ? '85vh' : '600px' }}
                sandbox="allow-scripts allow-same-origin allow-forms"
              />
            ) : (
              <div className="flex items-center justify-center bg-bg-secondary" style={{ height: '600px' }}>
                <div className="text-center">
                  <Monitor className="w-12 h-12 text-text-tertiary mx-auto mb-3" />
                  <p className="text-text-secondary">
                    {site.status === 'generating' ? 'Site is still generating…' :
                     site.status === 'failed'     ? 'Generation failed — no preview available.' :
                     'No preview available'}
                  </p>
                  {site.status === 'generating' && (
                    <div className="mt-3 animate-spin rounded-full h-6 w-6 border-b-2 border-info-500 mx-auto" />
                  )}
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* ── Sidebar: business data + actions ───────────────────────────── */}
        {!iframeFullscreen && (
          <div className="space-y-4">

            {/* Site metadata */}
            <Card>
              <CardBody className="p-4 space-y-3">
                <h3 className="font-semibold text-text-primary text-sm uppercase tracking-wide text-text-secondary mb-2">
                  Site Info
                </h3>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-text-secondary w-20 shrink-0">Status</span>
                  {getStatusBadge(site.status)}
                </div>
                <div className="flex items-start gap-2 text-sm">
                  <Calendar className="w-4 h-4 text-text-tertiary mt-0.5 shrink-0" />
                  <div>
                    <div className="text-text-secondary text-xs">Created</div>
                    <div className="text-text-primary">{formatDate(site.created_at)}</div>
                  </div>
                </div>
                {site.short_url && (
                  <div className="flex items-start gap-2 text-sm">
                    <Globe className="w-4 h-4 text-text-tertiary mt-0.5 shrink-0" />
                    <div className="break-all">
                      <div className="text-text-secondary text-xs">Short URL</div>
                      <a href={site.short_url} target="_blank" rel="noopener noreferrer"
                        className="text-primary-500 hover:underline text-xs">{site.short_url}</a>
                    </div>
                  </div>
                )}
              </CardBody>
            </Card>

            {/* Business data */}
            {business && (
              <Card>
                <CardBody className="p-4 space-y-3">
                  <h3 className="font-semibold text-sm uppercase tracking-wide text-text-secondary mb-2">
                    Business
                  </h3>
                  {getClosedStatus(business) && (
                    <div className="mb-3">
                      <ClosedBadge business={business} />
                    </div>
                  )}
                  <div className="flex items-start gap-2 text-sm">
                    <Building2 className="w-4 h-4 text-text-tertiary mt-0.5 shrink-0" />
                    <div>
                      <div className="font-medium text-text-primary">{business.name}</div>
                      {business.category && (
                        <div className="text-text-secondary text-xs">{business.category}</div>
                      )}
                    </div>
                  </div>
                  {(business.city || business.state) && (
                    <div className="flex items-center gap-2 text-sm">
                      <MapPin className="w-4 h-4 text-text-tertiary shrink-0" />
                      <span className="text-text-primary">
                        {[business.city, business.state].filter(Boolean).join(', ')}
                      </span>
                    </div>
                  )}
                  {business.phone && (
                    <div className="flex items-center gap-2 text-sm">
                      <Phone className="w-4 h-4 text-text-tertiary shrink-0" />
                      <a href={`tel:${business.phone}`} className="text-text-primary hover:text-primary-500">
                        {business.phone}
                      </a>
                    </div>
                  )}
                  {business.rating && (
                    <div className="flex items-center gap-2 text-sm">
                      <Star className="w-4 h-4 text-warning-500 shrink-0" />
                      <span className="text-text-primary font-medium">{business.rating}</span>
                      <span className="text-text-secondary text-xs">
                        ({business.review_count || 0} reviews)
                      </span>
                    </div>
                  )}
                  {business.gmb_place_id && (
                    <a
                      href={`https://www.google.com/maps/place/?q=place_id:${business.gmb_place_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-xs text-primary-600 font-medium hover:text-primary-700 mt-1"
                    >
                      <ExternalLink className="w-3 h-3" />
                      Google Business Profile
                    </a>
                  )}
                </CardBody>
              </Card>
            )}

            {/* Actions */}
            <Card>
              <CardBody className="p-4 space-y-2">
                <h3 className="font-semibold text-sm uppercase tracking-wide text-text-secondary mb-2">
                  Actions
                </h3>
                {liveUrl && (
                  <Button
                    variant="primary"
                    size="sm"
                    className="w-full flex items-center justify-center gap-2"
                    onClick={() => window.open(liveUrl, '_blank')}
                  >
                    <ExternalLink className="w-4 h-4" />
                    Open in New Tab
                  </Button>
                )}
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full flex items-center justify-center gap-2"
                  onClick={() => navigate('/campaigns')}
                >
                  Add to Campaign
                </Button>
              </CardBody>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}

export default GeneratedSiteDetailPage
