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
  PhoneOff,
  ImagePlus,
  Calendar,
  RefreshCw,
  Monitor,
  Maximize2,
  Minimize2,
  XCircle,
  Download,
  Shuffle,
  History,
  ChevronDown,
  ChevronUp,
  Check,
} from 'lucide-react'
import { api } from '@/services/api'
import { Badge, Button, Card, CardBody, ConfirmModal } from '@/components/ui'
import type { ConfirmAction } from '@/components/ui'
import type { ManualGenerationRequest } from '@/types'

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

function EditPromptsModal({
  manualInput,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  manualInput: ManualGenerationRequest
  onClose: () => void
  onSubmit: (payload: ManualGenerationRequest) => void
  isSubmitting: boolean
}) {
  const [description, setDescription] = useState(manualInput.description || '')
  const [websiteType, setWebsiteType] = useState<'informational' | 'ecommerce'>((manualInput.website_type as any) || 'informational')
  const [language, setLanguage] = useState(manualInput.language || 'en')
  const [websiteCurrency, setWebsiteCurrency] = useState(manualInput.website_currency || '$')
  const [name, setName] = useState(manualInput.name || '')
  const [phone, setPhone] = useState(manualInput.phone || '')
  const [email, setEmail] = useState(manualInput.email || '')
  const [address, setAddress] = useState(manualInput.address || '')
  const [city, setCity] = useState(manualInput.city || '')
  const [state, setState] = useState(manualInput.state || '')
  const [currencySymbol, setCurrencySymbol] = useState(manualInput.currency_symbol || '$')
  const [oneTimePrice, setOneTimePrice] = useState(String(manualInput.one_time_price ?? ''))
  const [monthlyPrice, setMonthlyPrice] = useState(String(manualInput.monthly_price ?? ''))
  const [brandingNotes, setBrandingNotes] = useState(manualInput.branding_notes || '')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload: ManualGenerationRequest = {
      description: description.trim(),
      website_type: websiteType,
      ...(language && language !== 'en' && { language }),
      ...(websiteType === 'ecommerce' && websiteCurrency.trim() && { website_currency: websiteCurrency.trim() }),
      ...(name.trim() && { name: name.trim() }),
      ...(phone.trim() && { phone: phone.trim() }),
      ...(email.trim() && { email: email.trim() }),
      ...(address.trim() && { address: address.trim() }),
      ...(city.trim() && { city: city.trim() }),
      ...(state.trim() && { state: state.trim() }),
      ...(brandingNotes.trim() && { branding_notes: brandingNotes.trim() }),
      ...(manualInput.branding_images?.length && { branding_images: manualInput.branding_images }),
      ...(oneTimePrice !== '' && !isNaN(parseFloat(oneTimePrice)) && { one_time_price: parseFloat(oneTimePrice) }),
      ...(monthlyPrice !== '' && !isNaN(parseFloat(monthlyPrice)) && { monthly_price: parseFloat(monthlyPrice) }),
      ...(currencySymbol.trim() && { currency_symbol: currencySymbol.trim() }),
    }
    onSubmit(payload)
  }

  return (
    <div className="fixed inset-0 z-modal flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="p-4 border-b border-border flex justify-between items-center">
          <h3 className="font-semibold text-text-primary">Edit Prompts & Regenerate</h3>
          <button type="button" onClick={onClose} className="text-text-secondary hover:text-text-primary text-xl">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-3">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Description *</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} required rows={4} className="w-full px-3 py-2 text-sm border border-border rounded-md" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Website type</label>
              <select value={websiteType} onChange={e => setWebsiteType(e.target.value as any)} className="w-full px-3 py-2 text-sm border border-border rounded-md">
                <option value="informational">Informational</option>
                <option value="ecommerce">E-commerce</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Language</label>
              <select value={language} onChange={e => setLanguage(e.target.value)} className="w-full px-3 py-2 text-sm border border-border rounded-md">
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="pt">Portuguese</option>
                <option value="it">Italian</option>
              </select>
            </div>
          </div>
          {websiteType === 'ecommerce' && (
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Product currency</label>
              <input type="text" value={websiteCurrency} onChange={e => setWebsiteCurrency(e.target.value)} maxLength={8} className="w-full px-3 py-2 text-sm border border-border rounded-md max-w-[6rem]" placeholder="$" />
            </div>
          )}
          <div className="grid grid-cols-3 gap-2">
            <div><label className="block text-xs font-medium text-text-secondary mb-1">Name</label><input type="text" value={name} onChange={e => setName(e.target.value)} className="w-full px-3 py-2 text-sm border border-border rounded-md" /></div>
            <div><label className="block text-xs font-medium text-text-secondary mb-1">Phone</label><input type="text" value={phone} onChange={e => setPhone(e.target.value)} className="w-full px-3 py-2 text-sm border border-border rounded-md" /></div>
            <div><label className="block text-xs font-medium text-text-secondary mb-1">Email</label><input type="email" value={email} onChange={e => setEmail(e.target.value)} className="w-full px-3 py-2 text-sm border border-border rounded-md" /></div>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="col-span-2"><label className="block text-xs font-medium text-text-secondary mb-1">Address</label><input type="text" value={address} onChange={e => setAddress(e.target.value)} className="w-full px-3 py-2 text-sm border border-border rounded-md" /></div>
            <div><label className="block text-xs font-medium text-text-secondary mb-1">City</label><input type="text" value={city} onChange={e => setCity(e.target.value)} className="w-full px-3 py-2 text-sm border border-border rounded-md" /></div>
            <div><label className="block text-xs font-medium text-text-secondary mb-1">State</label><input type="text" value={state} onChange={e => setState(e.target.value)} className="w-full px-3 py-2 text-sm border border-border rounded-md" /></div>
          </div>
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Branding notes</label>
            <textarea value={brandingNotes} onChange={e => setBrandingNotes(e.target.value)} rows={2} className="w-full px-3 py-2 text-sm border border-border rounded-md" />
          </div>
          <div className="grid grid-cols-4 gap-2">
            <div><label className="block text-xs font-medium text-text-secondary mb-1">Claim bar currency</label><input type="text" value={currencySymbol} onChange={e => setCurrencySymbol(e.target.value)} maxLength={8} className="w-full px-3 py-2 text-sm border border-border rounded-md" placeholder="$" /></div>
            <div><label className="block text-xs font-medium text-text-secondary mb-1">One-time price</label><input type="number" value={oneTimePrice} onChange={e => setOneTimePrice(e.target.value)} min={0} className="w-full px-3 py-2 text-sm border border-border rounded-md" placeholder="497" /></div>
            <div><label className="block text-xs font-medium text-text-secondary mb-1">Monthly price</label><input type="number" value={monthlyPrice} onChange={e => setMonthlyPrice(e.target.value)} min={0} className="w-full px-3 py-2 text-sm border border-border rounded-md" placeholder="97" /></div>
          </div>
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={isSubmitting || !description.trim()}>
              {isSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Regenerate with These Prompts'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
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
  const [exportError, setExportError] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<ConfirmAction | null>(null)
  const [showVersionBrowser, setShowVersionBrowser] = useState(false)
  const [showEditPromptsModal, setShowEditPromptsModal] = useState(false)
  const [showRegenHeroModal, setShowRegenHeroModal] = useState(false)
  const [heroGuidanceInput, setHeroGuidanceInput] = useState('')

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['generated-site-detail', siteId] })
    queryClient.invalidateQueries({ queryKey: ['generated-sites'] })
  }

  const exportMutation = useMutation({
    mutationFn: () => api.exportSiteFiles(siteId!),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${site?.subdomain ?? siteId}.zip`
      a.click()
      URL.revokeObjectURL(url)
      setExportError(null)
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail ?? err?.message ?? 'Export failed'
      setExportError(msg)
    },
  })

  const regenerateMutation = useMutation({
    mutationFn: () => api.regenerateSite(siteId!),
    onSuccess: () => {
      invalidate()
      setPendingAction(null)
      setShowEditPromptsModal(false)
    },
    onError: (err: any) => {
      setPendingAction(null)
      alert(`❌ Regeneration failed: ${err?.response?.data?.detail ?? err?.message}`)
    },
  })

  const regenImagesMutation = useMutation({
    mutationFn: () => api.regenerateSiteImages(siteId!),
    onSuccess: (data) => {
      invalidate()
      setPendingAction(null)
      if (data.failed_slots?.length) {
        alert(`⚠️ Images regenerated with some failures. Failed slots: ${data.failed_slots.join(', ')}`)
      }
    },
    onError: (err: any) => {
      setPendingAction(null)
      alert(`❌ Image regeneration failed: ${err?.response?.data?.detail ?? err?.message}`)
    },
  })

  const markHasWebsiteMutation = useMutation({
    mutationFn: () => api.markSiteHasWebsite(siteId!),
    onSuccess: () => {
      invalidate()
      setPendingAction(null)
    },
    onError: (err: any) => {
      setPendingAction(null)
      alert(`❌ Failed: ${err?.response?.data?.detail ?? err?.message}`)
    },
  })

  const markUnreachableMutation = useMutation({
    mutationFn: () => api.markSiteUnreachable(siteId!),
    onSuccess: () => {
      invalidate()
      setPendingAction(null)
    },
    onError: (err: any) => {
      setPendingAction(null)
      alert(`❌ Failed: ${err?.response?.data?.detail ?? err?.message}`)
    },
  })

  const regenHeroMutation = useMutation({
    mutationFn: (payload?: { hero_guidance?: string }) => api.regenerateHeroImage(siteId!, payload),
    onSuccess: (data) => {
      invalidate()
      queryClient.invalidateQueries({ queryKey: ['image-versions', siteId] })
      setShowRegenHeroModal(false)
      setHeroGuidanceInput('')
      if (data.saved) {
        alert(`✅ ${data.message}`)
      } else {
        alert(`⚠️ ${data.message}`)
      }
    },
    onError: (err: any) => {
      alert(`❌ Hero image regeneration failed: ${err?.response?.data?.detail ?? err?.message}`)
    },
  })

  const remapImagesMutation = useMutation({
    mutationFn: () => api.remapProductImages(siteId!),
    onSuccess: (data) => {
      invalidate()
      setPendingAction(null)
      if (data.success) {
        alert(`✅ ${data.message}`)
      } else {
        alert(`ℹ️ ${data.message}`)
      }
    },
    onError: (err: any) => {
      setPendingAction(null)
      alert(`❌ Remap failed: ${err?.response?.data?.detail ?? err?.message}`)
    },
  })

  const regenerateWithPromptsMutation = useMutation({
    mutationFn: (payload: ManualGenerationRequest) => api.regenerateSiteWithPrompts(siteId!, payload),
    onSuccess: () => {
      invalidate()
      setShowEditPromptsModal(false)
    },
    onError: (err: any) => {
      alert(`Regeneration failed: ${err?.response?.data?.detail ?? err?.message}`)
    },
  })

  const activateVersionMutation = useMutation({
    mutationFn: ({ slot, versionFilename }: { slot: string; versionFilename: string }) =>
      api.activateImageVersion(siteId!, slot, versionFilename),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['image-versions', siteId] })
      invalidate()
      alert(`✅ ${data.message}`)
    },
    onError: (err: any) => {
      alert(`❌ Failed: ${err?.response?.data?.detail ?? err?.message}`)
    },
  })

  const imageVersionsQuery = useQuery({
    queryKey: ['image-versions', siteId],
    queryFn: () => api.getImageVersions(siteId!),
    enabled: showVersionBrowser && !!siteId,
  })

  const isAnyMutationPending =
    regenerateMutation.isPending ||
    regenImagesMutation.isPending ||
    regenHeroMutation.isPending ||
    regenerateWithPromptsMutation.isPending ||
    markHasWebsiteMutation.isPending ||
    markUnreachableMutation.isPending ||
    remapImagesMutation.isPending ||
    activateVersionMutation.isPending

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

            {/* Generation Prompts (manual sites only) */}
            {site.manual_input && (
              <Card>
                <CardBody className="p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-sm uppercase tracking-wide text-text-secondary">
                      Generation Prompts
                    </h3>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowEditPromptsModal(true)}
                      disabled={regenerateWithPromptsMutation.isPending || site.status === 'generating'}
                    >
                      {regenerateWithPromptsMutation.isPending ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        'Edit & Regenerate'
                      )}
                    </Button>
                  </div>
                  <div className="text-xs space-y-1 max-h-32 overflow-y-auto">
                    <p><span className="text-text-secondary">Description:</span> {site.manual_input.description?.slice(0, 150)}{site.manual_input.description && site.manual_input.description.length > 150 ? '…' : ''}</p>
                    <p><span className="text-text-secondary">Type:</span> {site.manual_input.website_type}</p>
                    {site.manual_input.language && <p><span className="text-text-secondary">Language:</span> {site.manual_input.language}</p>}
                    {site.manual_input.website_currency && <p><span className="text-text-secondary">Product currency:</span> {site.manual_input.website_currency}</p>}
                    {(site.manual_input.name || site.manual_input.currency_symbol) && (
                      <p><span className="text-text-secondary">Details:</span> {[site.manual_input.name, site.manual_input.currency_symbol && `Claim bar: ${site.manual_input.currency_symbol}`].filter(Boolean).join(' · ')}</p>
                    )}
                  </div>
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
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full flex items-center justify-center gap-2"
                  onClick={() => exportMutation.mutate()}
                  disabled={exportMutation.isPending || !site?.html_content}
                  title={!site?.html_content ? 'Site has no content yet' : 'Download HTML, CSS, JS and images as a ZIP'}
                >
                  {exportMutation.isPending
                    ? <RefreshCw className="w-4 h-4 animate-spin" />
                    : <Download className="w-4 h-4" />
                  }
                  {exportMutation.isPending ? 'Preparing…' : 'Download Site Files'}
                </Button>
                {exportError && (
                  <p className="text-xs text-error px-1">{exportError}</p>
                )}

                {/* ── Divider */}
                {(site.status === 'completed' || site.status === 'published' || site.status === 'failed') && (
                  <div className="border-t border-border pt-2 mt-1 space-y-2">
                    <p className="text-xs text-text-secondary font-medium uppercase tracking-wide">
                      Site Management
                    </p>

                    {/* Regenerate site — any status */}
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full flex items-center justify-center gap-2 text-warning-700 border-warning-300 hover:bg-warning-50"
                      onClick={() =>
                        setPendingAction({
                          title: 'Regenerate Site?',
                          message:
                            'This will clear the existing HTML, CSS and JS and re-run the full AI pipeline from scratch. The process takes 1–3 minutes.',
                          confirmLabel: 'Yes, Regenerate',
                          variant: 'warning',
                          onConfirm: () => regenerateMutation.mutate(),
                        })
                      }
                      disabled={regenerateMutation.isPending}
                    >
                      <RefreshCw className={`w-4 h-4 ${regenerateMutation.isPending ? 'animate-spin' : ''}`} />
                      {regenerateMutation.isPending ? 'Queueing…' : 'Regenerate Site'}
                    </Button>

                    {/* Regen images — completed / published only */}
                    {(site.status === 'completed' || site.status === 'published') && (
                      <Button
                        variant="secondary"
                        size="sm"
                        className="w-full flex items-center justify-center gap-2 text-purple-700 hover:bg-purple-50"
                        onClick={() =>
                          setPendingAction({
                            title: 'Regenerate Images?',
                            message:
                              'This will regenerate the AI images (hero, about, services) using the original brand context. The existing HTML structure is kept — only the image files are overwritten.',
                            confirmLabel: 'Yes, Regenerate Images',
                            variant: 'default',
                            onConfirm: () => regenImagesMutation.mutate(),
                          })
                        }
                        disabled={regenImagesMutation.isPending}
                      >
                        <ImagePlus className={`w-4 h-4 ${regenImagesMutation.isPending ? 'animate-spin' : ''}`} />
                        {regenImagesMutation.isPending ? 'Generating…' : 'Regenerate Images'}
                      </Button>
                    )}

                    {/* Regenerate hero only — with optional guidance */}
                    {(site.status === 'completed' || site.status === 'published') && (
                      <Button
                        variant="secondary"
                        size="sm"
                        className="w-full flex items-center justify-center gap-2 text-teal-700 hover:bg-teal-50"
                        onClick={() => setShowRegenHeroModal(true)}
                        disabled={regenHeroMutation.isPending}
                      >
                        <ImagePlus className={`w-4 h-4 ${regenHeroMutation.isPending ? 'animate-spin' : ''}`} />
                        {regenHeroMutation.isPending ? 'Generating…' : 'Regenerate Hero Image'}
                      </Button>
                    )}

                    {/* Remap product images — fix mismatch without regenerating */}
                    {(site.status === 'completed' || site.status === 'published') && (
                      <Button
                        variant="secondary"
                        size="sm"
                        className="w-full flex items-center justify-center gap-2 text-indigo-700 hover:bg-indigo-50"
                        onClick={() =>
                          setPendingAction({
                            title: 'Remap Product Images?',
                            message:
                              'This uses AI to match each product image to the correct product card based on what each image depicts. It fixes mismatches without regenerating the whole site.',
                            confirmLabel: 'Yes, Remap Images',
                            variant: 'default',
                            onConfirm: () => remapImagesMutation.mutate(),
                          })
                        }
                        disabled={remapImagesMutation.isPending}
                      >
                        <Shuffle className={`w-4 h-4 ${remapImagesMutation.isPending ? 'animate-spin' : ''}`} />
                        {remapImagesMutation.isPending ? 'Remapping…' : 'Remap Product Images'}
                      </Button>
                    )}

                    {/* Image version browser */}
                    {(site.status === 'completed' || site.status === 'published') && (
                      <div>
                        <button
                          className="w-full flex items-center justify-between px-3 py-2 rounded-md border border-border text-xs text-text-secondary hover:bg-surface-elevated transition-colors"
                          onClick={() => setShowVersionBrowser(v => !v)}
                        >
                          <span className="flex items-center gap-1.5">
                            <History className="w-3.5 h-3.5" />
                            Image Version History
                          </span>
                          {showVersionBrowser ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>

                        {showVersionBrowser && (
                          <div className="mt-2 border border-border rounded-md overflow-hidden">
                            {imageVersionsQuery.isLoading && (
                              <p className="p-3 text-xs text-text-secondary">Loading versions…</p>
                            )}
                            {imageVersionsQuery.data && Object.keys(imageVersionsQuery.data.slots).length === 0 && (
                              <p className="p-3 text-xs text-text-secondary">No version history yet. Versions are saved each time images are generated.</p>
                            )}
                            {imageVersionsQuery.data && Object.entries(imageVersionsQuery.data.slots).map(([slot, info]) => (
                              <div key={slot} className="border-b border-border last:border-0 p-2">
                                <p className="text-xs font-semibold text-text-primary mb-0.5">{slot}</p>
                                {info.subject && (
                                  <p className="text-xs text-text-secondary mb-1 line-clamp-2">{info.subject.split('.')[0]}</p>
                                )}
                                <div className="space-y-1">
                                  {info.versions.map((v) => (
                                    <div key={v.filename} className="flex items-center justify-between gap-2">
                                      <span className="text-xs text-text-secondary font-mono truncate">
                                        {new Date(v.timestamp * 1000).toLocaleString()}
                                      </span>
                                      <button
                                        className="flex-shrink-0 flex items-center gap-1 px-2 py-0.5 text-xs rounded bg-primary-50 text-primary-700 hover:bg-primary-100 transition-colors disabled:opacity-50"
                                        onClick={() => activateVersionMutation.mutate({ slot, versionFilename: v.filename })}
                                        disabled={activateVersionMutation.isPending}
                                      >
                                        <Check className="w-3 h-3" />
                                        Use
                                      </button>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* ── Status actions */}
                {site.status !== 'superseded' && (
                  <div className="border-t border-border pt-2 mt-1 space-y-2">
                    <p className="text-xs text-text-secondary font-medium uppercase tracking-wide">
                      Flag Business
                    </p>

                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full flex items-center justify-center gap-2 text-warning-700 hover:bg-warning-50"
                      onClick={() =>
                        setPendingAction({
                          title: 'Mark as Has Website?',
                          message:
                            'This flags the business as already having their own website. The generated site will be marked as superseded and removed from campaigns.',
                          confirmLabel: 'Yes, Mark as Has Website',
                          variant: 'warning',
                          onConfirm: () => markHasWebsiteMutation.mutate(),
                        })
                      }
                      disabled={markHasWebsiteMutation.isPending}
                    >
                      <Globe className="w-4 h-4" />
                      Has Website
                    </Button>

                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full flex items-center justify-center gap-2 text-error-600 hover:bg-error-50"
                      onClick={() =>
                        setPendingAction({
                          title: 'Mark as Unreachable?',
                          message:
                            'This flags the business as unreachable (no valid phone or email found). The generated site will be marked as superseded.',
                          confirmLabel: 'Yes, Mark as Unreachable',
                          variant: 'danger',
                          onConfirm: () => markUnreachableMutation.mutate(),
                        })
                      }
                      disabled={markUnreachableMutation.isPending}
                    >
                      <PhoneOff className="w-4 h-4" />
                      Unreachable
                    </Button>
                  </div>
                )}
              </CardBody>
            </Card>
          </div>
        )}
      </div>

      {/* Confirmation modal */}
      {pendingAction && (
        <ConfirmModal
          {...pendingAction}
          isLoading={isAnyMutationPending}
          onCancel={() => setPendingAction(null)}
        />
      )}

      {/* Regenerate hero image modal */}
      {showRegenHeroModal && (
        <div className="fixed inset-0 z-modal flex items-center justify-center bg-black/50 p-4" onClick={() => setShowRegenHeroModal(false)}>
          <div className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b border-border">
              <h3 className="text-lg font-semibold text-text-primary">Regenerate Hero Image</h3>
            </div>
            <form
              className="p-4 space-y-4"
              onSubmit={e => {
                e.preventDefault()
                regenHeroMutation.mutate(heroGuidanceInput.trim() ? { hero_guidance: heroGuidanceInput.trim() } : undefined)
              }}
            >
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1">
                  Describe the hero image you&apos;d like (optional)
                </label>
                <textarea
                  value={heroGuidanceInput}
                  onChange={e => setHeroGuidanceInput(e.target.value)}
                  placeholder="e.g. A cozy interior with warm lighting and plants"
                  className="w-full h-24 px-3 py-2 rounded-md border border-border bg-surface text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={regenHeroMutation.isPending}
                />
                <p className="mt-1 text-xs text-text-secondary">
                  Leave blank to use the default. Your description will be combined with the site&apos;s branding for a cohesive look.
                </p>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="secondary" onClick={() => setShowRegenHeroModal(false)} disabled={regenHeroMutation.isPending}>
                  Cancel
                </Button>
                <Button type="submit" disabled={regenHeroMutation.isPending}>
                  {regenHeroMutation.isPending ? 'Generating…' : 'Regenerate Hero Image'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit prompts modal (manual sites) */}
      {showEditPromptsModal && site?.manual_input && (
        <EditPromptsModal
          manualInput={site.manual_input}
          onClose={() => setShowEditPromptsModal(false)}
          onSubmit={(payload) => regenerateWithPromptsMutation.mutate(payload)}
          isSubmitting={regenerateWithPromptsMutation.isPending}
        />
      )}
    </div>
  )
}

export default GeneratedSiteDetailPage
