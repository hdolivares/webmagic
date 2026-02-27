/**
 * Human Verification Queue
 *
 * Presents borderline validation cases to an admin for a quick yes/no decision.
 * Each card shows:
 *   - Google Business info (name, address, phone, category, rating)
 *   - The candidate URL the LLM found but couldn't confirm
 *   - What was scraped from that URL (title, phones, content preview)
 *   - The LLM's reasoning for the rejection
 *   - Three action buttons: Has Website | No Website | Re-run Discovery
 */
import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ShieldCheck,
  XCircle,
  RefreshCw,
  ExternalLink,
  Search,
  Phone,
  MapPin,
  Star,
  AlertTriangle,
  Globe,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Wand2,
  CheckCircle,
} from 'lucide-react'
import { api } from '@/services/api'
import type { VerificationQueueItem, VerificationDecisionRequest } from '@/services/api'

// ─── Constants ───────────────────────────────────────────────────────────────

const PAGE_SIZE = 50

const REASON_LABELS: Record<string, { label: string; description: string }> = {
  wrong_business: {
    label: 'Wrong Business',
    description: 'A real website was found but the LLM determined it belongs to a different company.',
  },
  no_contact: {
    label: 'No Contact Match',
    description: 'A real website was found but the phone/address on the page did not match.',
  },
}

// ─── Sub-components ──────────────────────────────────────────────────────────

/** Pill badge for the rejection reason */
function ReasonBadge({ reason }: { reason: string | null }) {
  if (!reason) return null
  const info = REASON_LABELS[reason] ?? { label: reason, description: '' }
  const isWrongBusiness = reason === 'wrong_business'
  return (
    <span
      className={`inline-flex items-center gap-1 px-sm py-xs rounded-full text-xs font-medium ${
        isWrongBusiness
          ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
          : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
      }`}
      title={info.description}
    >
      <AlertTriangle className="w-3 h-3" />
      {info.label}
    </span>
  )
}

/** Small confidence meter */
function ConfidenceMeter({ value }: { value: number | null }) {
  if (value === null) return null
  const pct = Math.round(value * 100)
  const color =
    pct >= 80 ? 'bg-red-500' : pct >= 60 ? 'bg-orange-400' : 'bg-yellow-400'
  return (
    <div className="flex items-center gap-sm text-xs text-text-secondary">
      <span>LLM confidence:</span>
      <div className="flex-1 h-1.5 bg-background-secondary rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-medium text-text-primary">{pct}%</span>
    </div>
  )
}

/** Match signals row (phone / address / name) */
function MatchSignalsRow({ signals }: { signals: VerificationQueueItem['match_signals'] }) {
  if (!signals) return null
  const items = [
    { key: 'name_match', label: 'Name' },
    { key: 'phone_match', label: 'Phone' },
    { key: 'address_match', label: 'Address' },
  ] as const
  return (
    <div className="flex items-center gap-md text-xs">
      <span className="text-text-secondary">Matched:</span>
      {items.map(({ key, label }) => (
        <span
          key={key}
          className={`inline-flex items-center gap-0.5 font-medium ${
            signals[key] ? 'text-success' : 'text-error'
          }`}
        >
          {signals[key] ? (
            <CheckCircle className="w-3 h-3" />
          ) : (
            <XCircle className="w-3 h-3" />
          )}
          {label}
        </span>
      ))}
    </div>
  )
}

/** Decision modal overlay for the "Has Website" path (needs URL confirmation) */
function HasWebsiteModal({
  item,
  onConfirm,
  onCancel,
  isPending,
}: {
  item: VerificationQueueItem
  onConfirm: (url: string, notes: string) => void
  onCancel: () => void
  isPending: boolean
}) {
  const [url, setUrl] = useState(item.candidate_url ?? '')
  const [notes, setNotes] = useState('')

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center bg-black/50 p-md"
      onClick={onCancel}
    >
      <div
        className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg p-lg space-y-md"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-text-primary flex items-center gap-sm">
          <Globe className="w-5 h-5 text-primary-500" />
          Confirm Website URL
        </h3>

        <p className="text-sm text-text-secondary">
          Marking <strong className="text-text-primary">{item.name}</strong> as having a valid
          website. Confirm or correct the URL below.
        </p>

        <div className="space-y-xs">
          <label className="text-xs font-medium text-text-secondary uppercase tracking-wide">
            Website URL
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full px-md py-sm border border-border rounded-md bg-background text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500"
            placeholder="https://example.com"
          />
        </div>

        <div className="space-y-xs">
          <label className="text-xs font-medium text-text-secondary uppercase tracking-wide">
            Notes (optional)
          </label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full px-md py-sm border border-border rounded-md bg-background text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500"
            placeholder="e.g. confirmed via Google Maps"
          />
        </div>

        <div className="flex gap-sm justify-end pt-xs">
          <button
            onClick={onCancel}
            disabled={isPending}
            className="px-md py-sm text-sm rounded-md border border-border text-text-secondary hover:bg-background-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(url.trim(), notes.trim())}
            disabled={isPending || !url.trim()}
            className="px-md py-sm text-sm rounded-md bg-success text-white font-medium hover:bg-success/90 disabled:opacity-50 transition-colors flex items-center gap-sm"
          >
            {isPending ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <ShieldCheck className="w-4 h-4" />
            )}
            Confirm — Has Website
          </button>
        </div>
      </div>
    </div>
  )
}

/** A single verification card */
function VerificationCard({
  item,
  onDecide,
  isProcessing,
}: {
  item: VerificationQueueItem
  onDecide: (id: string, req: VerificationDecisionRequest) => void
  isProcessing: boolean
}) {
  const [showHasWebsiteModal, setShowHasWebsiteModal] = useState(false)

  const googleMapsUrl = `https://www.google.com/maps/search/${encodeURIComponent(
    `${item.name} ${item.city ?? ''} ${item.state ?? ''}`
  )}`
  const googleSearchUrl = `https://www.google.com/search?q=${encodeURIComponent(
    `${item.name} ${item.city ?? ''} ${item.state ?? ''} website`
  )}`

  return (
    <>
      <div
        className={`border rounded-xl overflow-hidden transition-shadow hover:shadow-md ${
          item.has_generated_site
            ? 'border-amber-400/60 bg-amber-50/30 dark:bg-amber-900/10'
            : 'border-border bg-surface'
        }`}
      >
        {/* Generated site banner */}
        {item.has_generated_site && (
          <div className="flex items-center gap-sm px-lg py-xs bg-amber-100/80 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-xs font-medium border-b border-amber-200 dark:border-amber-800">
            <Wand2 className="w-3.5 h-3.5" />
            We already generated a site for this business —
            {item.generated_site_url && (
              <a
                href={item.generated_site_url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:no-underline"
              >
                view it
              </a>
            )}
          </div>
        )}

        <div className="p-lg grid grid-cols-1 lg:grid-cols-2 gap-lg">
          {/* ── Left: Google Business info ──────────────────────────────── */}
          <div className="space-y-sm">
            <div className="flex items-start justify-between gap-sm">
              <div>
                <h3 className="font-semibold text-text-primary text-base leading-tight">
                  {item.name}
                </h3>
                {item.category && (
                  <p className="text-xs text-text-secondary mt-0.5">{item.category}</p>
                )}
              </div>
              <ReasonBadge reason={item.invalid_reason} />
            </div>

            <div className="space-y-xs text-sm text-text-secondary">
              {item.address && (
                <div className="flex items-start gap-xs">
                  <MapPin className="w-4 h-4 mt-0.5 shrink-0 text-text-tertiary" />
                  <span>
                    {item.address}
                    {item.city && `, ${item.city}`}
                    {item.state && `, ${item.state}`}
                  </span>
                </div>
              )}
              {item.phone && (
                <div className="flex items-center gap-xs">
                  <Phone className="w-4 h-4 shrink-0 text-text-tertiary" />
                  <span className="font-medium text-text-primary">{item.phone}</span>
                </div>
              )}
              {item.rating != null && (
                <div className="flex items-center gap-xs">
                  <Star className="w-4 h-4 shrink-0 text-yellow-500" />
                  <span>
                    {item.rating.toFixed(1)} · {item.review_count} reviews
                  </span>
                </div>
              )}
              {item.outscraper_website && (
                <div className="flex items-center gap-xs">
                  <Globe className="w-4 h-4 shrink-0 text-text-tertiary" />
                  <span className="text-xs italic">
                    Outscraper raw: {item.outscraper_website}
                  </span>
                </div>
              )}
            </div>

            <div className="flex flex-wrap gap-sm pt-xs">
              <a
                href={googleMapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-xs text-xs text-primary-600 dark:text-primary-400 hover:underline"
              >
                <MapPin className="w-3.5 h-3.5" />
                Google Maps
                <ExternalLink className="w-3 h-3" />
              </a>
              <a
                href={googleSearchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-xs text-xs text-primary-600 dark:text-primary-400 hover:underline"
              >
                <Search className="w-3.5 h-3.5" />
                Google Search
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          {/* ── Right: Candidate URL and scraped content ────────────────── */}
          <div className="space-y-sm">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
                Candidate Website Found
              </h4>
              {item.candidate_quality_score != null && (
                <span className="text-xs text-text-tertiary">
                  Quality: {item.candidate_quality_score}/100
                </span>
              )}
            </div>

            {item.candidate_url ? (
              <a
                href={item.candidate_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-xs text-sm font-medium text-primary-600 dark:text-primary-400 hover:underline break-all"
              >
                <Globe className="w-4 h-4 shrink-0" />
                {item.candidate_url}
                <ExternalLink className="w-3.5 h-3.5 shrink-0" />
              </a>
            ) : (
              <p className="text-sm text-text-tertiary italic">No URL recorded</p>
            )}

            {item.candidate_title && (
              <p className="text-sm text-text-primary font-medium">
                "{item.candidate_title}"
              </p>
            )}

            {item.candidate_phones.length > 0 && (
              <div className="flex items-center gap-xs text-sm">
                <Phone className="w-3.5 h-3.5 text-text-tertiary" />
                <span className="text-text-secondary">
                  Phones on site:{' '}
                  <span className="text-text-primary font-medium">
                    {item.candidate_phones.slice(0, 3).join(', ')}
                  </span>
                </span>
              </div>
            )}

            {item.candidate_content_preview && (
              <p className="text-xs text-text-secondary bg-background-secondary rounded-md px-sm py-xs leading-relaxed line-clamp-3">
                {item.candidate_content_preview}
              </p>
            )}

            {/* LLM reasoning */}
            {item.llm_reasoning && (
              <div className="border border-border rounded-md p-sm space-y-xs">
                <p className="text-xs font-medium text-text-secondary uppercase tracking-wide">
                  LLM Reasoning
                </p>
                <p className="text-xs text-text-secondary leading-relaxed">
                  {item.llm_reasoning}
                </p>
              </div>
            )}

            <div className="space-y-xs">
              <ConfidenceMeter value={item.llm_confidence} />
              <MatchSignalsRow signals={item.match_signals} />
            </div>
          </div>
        </div>

        {/* ── Action bar ───────────────────────────────────────────────────── */}
        <div className="px-lg py-md border-t border-border bg-background-secondary/50 flex flex-wrap items-center gap-sm">
          <button
            onClick={() => setShowHasWebsiteModal(true)}
            disabled={isProcessing}
            className="inline-flex items-center gap-sm px-md py-sm text-sm font-medium rounded-md bg-success/10 text-success border border-success/30 hover:bg-success/20 disabled:opacity-50 transition-colors"
          >
            <ShieldCheck className="w-4 h-4" />
            Has Website
          </button>

          <button
            onClick={() => onDecide(item.id, { decision: 'no_website' })}
            disabled={isProcessing}
            className="inline-flex items-center gap-sm px-md py-sm text-sm font-medium rounded-md bg-error/10 text-error border border-error/30 hover:bg-error/20 disabled:opacity-50 transition-colors"
          >
            {isProcessing ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <XCircle className="w-4 h-4" />
            )}
            No Website
          </button>

          <button
            onClick={() => onDecide(item.id, { decision: 're_run' })}
            disabled={isProcessing}
            className="inline-flex items-center gap-sm px-md py-sm text-sm font-medium rounded-md bg-background border border-border text-text-secondary hover:bg-background-secondary disabled:opacity-50 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Re-run Discovery
          </button>

          <span className="ml-auto text-xs text-text-tertiary">
            {item.website_validated_at
              ? `Flagged ${new Date(item.website_validated_at).toLocaleDateString()}`
              : ''}
          </span>
        </div>
      </div>

      {showHasWebsiteModal && (
        <HasWebsiteModal
          item={item}
          isPending={isProcessing}
          onCancel={() => setShowHasWebsiteModal(false)}
          onConfirm={(url, notes) => {
            setShowHasWebsiteModal(false)
            onDecide(item.id, { decision: 'valid_website', website_url: url, notes })
          }}
        />
      )}
    </>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function VerificationPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [filterGeneratedOnly, setFilterGeneratedOnly] = useState(false)
  const [processingId, setProcessingId] = useState<string | null>(null)
  const [toasts, setToasts] = useState<{ id: string; message: string; type: 'success' | 'error' }[]>([])

  const showToast = useCallback(
    (message: string, type: 'success' | 'error' = 'success') => {
      const id = Math.random().toString(36).slice(2)
      setToasts((prev) => [...prev, { id, message, type }])
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000)
    },
    []
  )

  const { data, isLoading, isError } = useQuery({
    queryKey: ['verification-queue', page, filterGeneratedOnly],
    queryFn: () =>
      api.getVerificationQueue({
        page,
        page_size: PAGE_SIZE,
        has_generated_site: filterGeneratedOnly ? true : undefined,
      }),
    placeholderData: (prev) => prev,
  })

  const decideMutation = useMutation({
    mutationFn: ({ id, req }: { id: string; req: VerificationDecisionRequest }) =>
      api.submitVerificationDecision(id, req),
    onMutate: ({ id }) => setProcessingId(id),
    onSuccess: (_, { req }) => {
      const labels: Record<VerificationDecisionRequest['decision'], string> = {
        valid_website: 'Marked as having a website',
        no_website: 'Confirmed — no website',
        re_run: 'Re-queued for discovery',
      }
      showToast(labels[req.decision], 'success')
      queryClient.invalidateQueries({ queryKey: ['verification-queue'] })
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail ?? err?.message ?? 'Something went wrong'
      showToast(msg, 'error')
    },
    onSettled: () => setProcessingId(null),
  })

  const handleDecide = useCallback(
    (id: string, req: VerificationDecisionRequest) => {
      decideMutation.mutate({ id, req })
    },
    [decideMutation]
  )

  const total = data?.total ?? 0
  const pages = data?.pages ?? 1
  const withGeneratedSite = data?.items.filter((i) => i.has_generated_site).length ?? 0

  return (
    <div className="p-xl space-y-xl">
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-md">
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-sm">
            <ClipboardCheck className="w-7 h-7 text-primary-500" />
            Verification Queue
          </h1>
          <p className="text-text-secondary mt-1 text-sm">
            Businesses where a real site was found but couldn't be auto-confirmed. A quick look
            is all it takes.
          </p>
        </div>

        {/* Stats pills */}
        <div className="flex flex-wrap gap-sm text-sm">
          <div className="px-md py-sm rounded-lg bg-surface border border-border text-center min-w-[90px]">
            <div className="text-2xl font-bold text-text-primary">{total}</div>
            <div className="text-xs text-text-secondary">Pending</div>
          </div>
          <div className="px-md py-sm rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-center min-w-[90px]">
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {data?.items.filter((i) => i.has_generated_site).length ?? 0}
            </div>
            <div className="text-xs text-text-secondary">Have Generated Site</div>
          </div>
        </div>
      </div>

      {/* ── Filters ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-sm">
        <button
          onClick={() => { setFilterGeneratedOnly(false); setPage(1) }}
          className={`px-md py-xs text-sm rounded-full border transition-colors ${
            !filterGeneratedOnly
              ? 'bg-primary-500 text-white border-primary-500'
              : 'border-border text-text-secondary hover:bg-background-secondary'
          }`}
        >
          All ({total})
        </button>
        <button
          onClick={() => { setFilterGeneratedOnly(true); setPage(1) }}
          className={`px-md py-xs text-sm rounded-full border transition-colors ${
            filterGeneratedOnly
              ? 'bg-amber-500 text-white border-amber-500'
              : 'border-border text-text-secondary hover:bg-background-secondary'
          }`}
        >
          Has Generated Site
        </button>
      </div>

      {/* ── Content ──────────────────────────────────────────────────────── */}
      {isLoading && (
        <div className="flex items-center justify-center py-2xl text-text-secondary">
          <RefreshCw className="w-6 h-6 animate-spin mr-sm" />
          Loading verification queue…
        </div>
      )}

      {isError && (
        <div className="flex items-center gap-sm p-lg rounded-xl border border-error/30 bg-error/5 text-error">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          Failed to load verification queue. Please refresh.
        </div>
      )}

      {!isLoading && !isError && data?.items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-2xl text-center">
          <ShieldCheck className="w-12 h-12 text-success mb-md" />
          <h3 className="text-lg font-semibold text-text-primary">Queue is empty</h3>
          <p className="text-text-secondary text-sm mt-xs">
            No businesses waiting for human verification. Great job!
          </p>
        </div>
      )}

      {!isLoading && data && data.items.length > 0 && (
        <div className="space-y-md">
          {data.items.map((item) => (
            <VerificationCard
              key={item.id}
              item={item}
              onDecide={handleDecide}
              isProcessing={processingId === item.id}
            />
          ))}
        </div>
      )}

      {/* ── Pagination ───────────────────────────────────────────────────── */}
      {pages > 1 && (
        <div className="flex items-center justify-between pt-md">
          <p className="text-sm text-text-secondary">
            Page {page} of {pages} · {total} total
          </p>
          <div className="flex gap-sm">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="inline-flex items-center gap-xs px-md py-sm text-sm rounded-md border border-border text-text-secondary hover:bg-background-secondary disabled:opacity-40 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(pages, p + 1))}
              disabled={page === pages}
              className="inline-flex items-center gap-xs px-md py-sm text-sm rounded-md border border-border text-text-secondary hover:bg-background-secondary disabled:opacity-40 transition-colors"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ── Toast notifications ──────────────────────────────────────────── */}
      <div className="fixed bottom-xl right-xl z-toast space-y-sm pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-center gap-sm px-lg py-md rounded-xl shadow-lg text-sm font-medium text-white transition-all ${
              toast.type === 'success' ? 'bg-success' : 'bg-error'
            }`}
          >
            {toast.type === 'success' ? (
              <CheckCircle className="w-4 h-4 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            )}
            {toast.message}
          </div>
        ))}
      </div>
    </div>
  )
}
