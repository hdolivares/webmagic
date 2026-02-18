/**
 * Admin Ticket Detail Page
 *
 * Shows:
 *  - Full ticket metadata (status, priority, customer, site)
 *  - AI Analysis panel (confidence, suggested response, processing notes)
 *  - Message thread (customer / staff / AI messages)
 *  - Reply form
 *  - Site-edit apply/reject controls (for site_edit category tickets)
 *
 * Design system: semantic Tailwind classes backed by CSS variables.
 * No hardcoded colors — all colors reference the theme token layer.
 */
import { useState, useRef, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  RefreshCw,
  AlertCircle,
  User,
  Bot,
  ShieldCheck,
  Send,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Clipboard,
  Sparkles,
  Globe,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardBody, Badge, Button } from '@/components/ui'
import { api } from '@/services/api'

// ── Helpers ────────────────────────────────────────────────────────────────────

const STATUS_VARIANT: Record<string, any> = {
  new: 'info',
  in_progress: 'warning',
  waiting_customer: 'primary',
  waiting_ai: 'primary',
  resolved: 'success',
  closed: 'secondary',
}

const STATUS_LABEL: Record<string, string> = {
  new: 'New',
  in_progress: 'In Progress',
  waiting_customer: 'Waiting Customer',
  waiting_ai: 'Waiting AI',
  resolved: 'Resolved',
  closed: 'Closed',
}

const PRIORITY_VARIANT: Record<string, any> = {
  urgent: 'error',
  high: 'warning',
  medium: 'primary',
  low: 'secondary',
}

const CATEGORY_LABELS: Record<string, string> = {
  billing: 'Billing',
  technical_support: 'Technical Support',
  site_edit: 'Site Edit Request',
  question: 'Question',
  other: 'Other',
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

// ── Message bubble ─────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: any }) {
  const isCustomer = message.message_type === 'customer'
  const isAI = message.ai_generated || message.message_type === 'ai'
  const isStaff = message.message_type === 'staff' && !message.ai_generated

  return (
    <div className={`flex gap-md ${isCustomer ? 'flex-row' : 'flex-row-reverse'}`}>
      {/* Avatar */}
      <div
        className={`
          flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
          ${isCustomer
            ? 'bg-secondary-100 text-secondary-600 dark:bg-secondary-800 dark:text-secondary-300'
            : isAI
            ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300'
            : 'bg-success-light text-success-dark dark:bg-success-dark dark:text-success-light'
          }
        `}
      >
        {isCustomer ? <User className="w-4 h-4" /> : isAI ? <Bot className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
      </div>

      {/* Bubble */}
      <div className={`flex-1 max-w-2xl space-y-1 ${isCustomer ? '' : 'items-end flex flex-col'}`}>
        <div className="flex items-center gap-sm text-xs text-text-tertiary">
          <span className="font-medium text-text-secondary">
            {isCustomer ? 'Customer' : isAI ? 'AI Assistant' : 'Support Team'}
          </span>
          <span>·</span>
          <span>{formatDate(message.created_at)}</span>
          {message.internal_only && (
            <span className="badge-warning text-xs">Internal</span>
          )}
        </div>
        <div
          className={`
            px-md py-sm rounded-lg text-sm leading-relaxed whitespace-pre-wrap
            ${isCustomer
              ? 'bg-background-secondary text-text-primary border border-border rounded-tl-none'
              : isAI
              ? 'bg-primary-50 text-text-primary border border-primary-200 dark:bg-primary-900/20 dark:border-primary-800 rounded-tr-none'
              : 'bg-success-light text-success-dark dark:bg-success-dark/20 dark:text-success-light border border-success dark:border-success-dark rounded-tr-none'
            }
          `}
        >
          {message.message}
        </div>
      </div>
    </div>
  )
}

// ── Edit Operations list ───────────────────────────────────────────────────────

function EditOperationsList({ operations }: { operations: any[] }) {
  if (!operations?.length) return null
  return (
    <div className="space-y-sm">
      {operations.map((op: any, i: number) => (
        <div
          key={i}
          className="p-sm rounded-md bg-background-secondary border border-border text-sm"
        >
          <div className="flex items-center gap-sm mb-xs">
            <span className="badge-info">{op.type?.replace('_', ' ')}</span>
            {op.location && <span className="text-text-secondary">{op.location}</span>}
            {op.target_variable && (
              <code className="text-xs bg-background-tertiary px-xs py-0.5 rounded font-mono">
                {op.target_variable}
              </code>
            )}
          </div>
          {(op.current_value || op.new_value) && (
            <div className="grid grid-cols-2 gap-sm mt-xs">
              {op.current_value && (
                <div>
                  <p className="text-xs text-text-tertiary font-medium mb-xs">Before</p>
                  <code className="text-xs bg-error-light dark:bg-error-dark/20 text-error-dark dark:text-error-light px-xs py-0.5 rounded block truncate">
                    {op.current_value}
                  </code>
                </div>
              )}
              {op.new_value && (
                <div>
                  <p className="text-xs text-text-tertiary font-medium mb-xs">After</p>
                  <code className="text-xs bg-success-light dark:bg-success-dark/20 text-success-dark dark:text-success-light px-xs py-0.5 rounded block truncate">
                    {op.new_value}
                  </code>
                </div>
              )}
            </div>
          )}
          {op.reason && (
            <p className="text-xs text-text-tertiary mt-xs italic">{op.reason}</p>
          )}
        </div>
      ))}
    </div>
  )
}

// ── AI Analysis Panel ──────────────────────────────────────────────────────────

function AIAnalysisPanel({
  ticket,
  onUseResponse,
}: {
  ticket: any
  onUseResponse: (text: string) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const [opsExpanded, setOpsExpanded] = useState(false)

  const notes = ticket.ai_processing_notes || {}
  const confidence = ticket.ai_category_confidence || {}
  const requiresReview = notes.requires_human_review

  if (!ticket.ai_processed) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-sm">
            <Sparkles className="w-4 h-4 text-primary-600" />
            AI Analysis
          </CardTitle>
        </CardHeader>
        <CardBody>
          <p className="text-text-secondary text-sm">AI processing not yet completed.</p>
        </CardBody>
      </Card>
    )
  }

  return (
    <Card className="border-primary-200 dark:border-primary-800">
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between w-full">
          <CardTitle className="flex items-center gap-sm">
            <Sparkles className="w-4 h-4 text-primary-600" />
            AI Analysis
          </CardTitle>
          <div className="flex items-center gap-sm">
            {requiresReview && (
              <Badge variant="warning">Needs Human Review</Badge>
            )}
            {expanded ? <ChevronUp className="w-4 h-4 text-text-tertiary" /> : <ChevronDown className="w-4 h-4 text-text-tertiary" />}
          </div>
        </div>
      </CardHeader>

      {expanded && (
        <CardBody className="space-y-lg">
          {/* Priority reasoning */}
          {notes.priority_reasoning && (
            <div>
              <p className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-xs">
                Priority Reasoning
              </p>
              <p className="text-sm text-text-primary">{notes.priority_reasoning}</p>
            </div>
          )}

          {/* Category confidence */}
          {Object.keys(confidence).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-sm">
                Category Confidence
              </p>
              <div className="space-y-xs">
                {Object.entries(confidence)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .map(([cat, score]) => (
                    <div key={cat} className="flex items-center gap-sm">
                      <span className="text-xs text-text-secondary w-32 truncate">
                        {CATEGORY_LABELS[cat] ?? cat}
                      </span>
                      <div className="flex-1 h-1.5 bg-background-tertiary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary-500 rounded-full transition-all"
                          style={{ width: `${((score as number) * 100).toFixed(0)}%` }}
                        />
                      </div>
                      <span className="text-xs text-text-secondary w-10 text-right">
                        {((score as number) * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Site edit decomposition */}
          {ticket.category === 'site_edit' && notes.edit_summary && (
            <div>
              <p className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-sm">
                AI Understood the Request As
              </p>
              <p className="text-sm text-text-primary bg-background-secondary border border-border rounded-md p-sm">
                {notes.edit_summary}
              </p>
              {notes.edit_operations?.length > 0 && (
                <div className="mt-sm">
                  <button
                    onClick={() => setOpsExpanded(!opsExpanded)}
                    className="btn-ghost btn-sm flex items-center gap-xs text-xs"
                  >
                    {opsExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    {notes.edit_operations.length} edit operation{notes.edit_operations.length !== 1 ? 's' : ''}
                  </button>
                  {opsExpanded && (
                    <div className="mt-sm">
                      <EditOperationsList operations={notes.edit_operations} />
                    </div>
                  )}
                </div>
              )}
              {notes.preview_version_id && (
                <p className="text-xs text-success mt-sm flex items-center gap-xs">
                  <CheckCircle2 className="w-3 h-3" />
                  Preview version ready — use "Apply Change" below to deploy
                </p>
              )}
            </div>
          )}

          {/* Suggested response */}
          {ticket.ai_suggested_response && ticket.category !== 'site_edit' && (
            <div>
              <p className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-sm">
                Suggested Response
              </p>
              <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-md p-sm text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
                {ticket.ai_suggested_response}
              </div>
              <button
                onClick={() => onUseResponse(ticket.ai_suggested_response)}
                className="btn-outline btn-sm mt-sm flex items-center gap-xs"
              >
                <Clipboard className="w-3 h-3" />
                Use this response
              </button>
            </div>
          )}
        </CardBody>
      )}
    </Card>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function AdminTicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [replyText, setReplyText] = useState('')
  const [applyConfirm, setApplyConfirm] = useState(false)
  const threadEndRef = useRef<HTMLDivElement>(null)

  const { data: ticket, isLoading, error, refetch } = useQuery({
    queryKey: ['admin-ticket', ticketId],
    queryFn: () => api.getAdminTicket(ticketId!),
    enabled: !!ticketId,
  })

  // Scroll to bottom of thread when messages load
  useEffect(() => {
    if (ticket?.messages?.length) {
      threadEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [ticket?.messages?.length])

  const replyMutation = useMutation({
    mutationFn: (message: string) => api.replyToTicket(ticketId!, message),
    onSuccess: () => {
      setReplyText('')
      queryClient.invalidateQueries({ queryKey: ['admin-ticket', ticketId] })
      queryClient.invalidateQueries({ queryKey: ['admin-tickets'] })
    },
  })

  const statusMutation = useMutation({
    mutationFn: (status: string) => api.updateAdminTicketStatus(ticketId!, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-ticket', ticketId] })
      queryClient.invalidateQueries({ queryKey: ['admin-tickets'] })
    },
  })

  const applyEditMutation = useMutation({
    mutationFn: () => api.applyTicketSiteEdit(ticketId!),
    onSuccess: () => {
      setApplyConfirm(false)
      queryClient.invalidateQueries({ queryKey: ['admin-ticket', ticketId] })
      queryClient.invalidateQueries({ queryKey: ['admin-tickets'] })
    },
  })

  function handleReply(e: React.FormEvent) {
    e.preventDefault()
    if (!replyText.trim()) return
    replyMutation.mutate(replyText)
  }

  // ── Loading / Error states ─────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-xl gap-sm text-text-secondary">
        <RefreshCw className="w-5 h-5 animate-spin" />
        Loading ticket…
      </div>
    )
  }

  if (error || !ticket) {
    return (
      <div className="flex flex-col items-center justify-center py-xl gap-md text-error">
        <AlertCircle className="w-8 h-8" />
        <p>Failed to load ticket</p>
        <button onClick={() => refetch()} className="btn-outline btn-sm">Retry</button>
      </div>
    )
  }

  const notes = ticket.ai_processing_notes || {}
  const hasPreviewVersion = !!(ticket.category === 'site_edit' && notes.preview_version_id)
  const isResolved = ticket.status === 'resolved' || ticket.status === 'closed'

  return (
    <div className="p-xl max-w-7xl mx-auto space-y-lg">

      {/* Breadcrumb + actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-sm">
          <button onClick={() => navigate('/tickets')} className="btn-ghost btn-sm flex items-center gap-xs">
            <ArrowLeft className="w-4 h-4" />
            All Tickets
          </button>
          <span className="text-text-tertiary">/</span>
          <span className="font-medium text-text-primary">{ticket.ticket_number}</span>
        </div>

        {/* Quick status actions */}
        <div className="flex items-center gap-sm">
          {!isResolved && (
            <button
              onClick={() => statusMutation.mutate('resolved')}
              disabled={statusMutation.isPending}
              className="btn-success btn-sm flex items-center gap-xs"
            >
              <CheckCircle2 className="w-4 h-4" />
              Resolve
            </button>
          )}
          <button onClick={() => refetch()} className="btn-outline btn-sm">
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-lg">

        {/* ── Left column: thread + reply ─────────────────────────────────── */}
        <div className="xl:col-span-2 space-y-lg">

          {/* Message thread */}
          <Card>
            <CardHeader>
              <CardTitle>Conversation</CardTitle>
            </CardHeader>
            <CardBody className="space-y-lg max-h-[60vh] overflow-y-auto">
              {ticket.messages?.length === 0 ? (
                <p className="text-text-tertiary text-sm text-center py-md">No messages yet.</p>
              ) : (
                ticket.messages?.map((msg: any) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))
              )}
              <div ref={threadEndRef} />
            </CardBody>
          </Card>

          {/* Reply form */}
          <Card>
            <CardHeader>
              <CardTitle>Reply to Customer</CardTitle>
            </CardHeader>
            <CardBody>
              <form onSubmit={handleReply} className="space-y-md">
                <textarea
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder="Type your reply here…"
                  rows={5}
                  className="form-input w-full resize-none"
                />
                <div className="flex justify-end gap-sm">
                  {replyMutation.isError && (
                    <p className="text-error text-sm self-center">Failed to send. Try again.</p>
                  )}
                  <button
                    type="submit"
                    disabled={!replyText.trim() || replyMutation.isPending}
                    className="btn-primary flex items-center gap-sm"
                  >
                    <Send className="w-4 h-4" />
                    {replyMutation.isPending ? 'Sending…' : 'Send Reply'}
                  </button>
                </div>
              </form>
            </CardBody>
          </Card>

          {/* Site Edit controls */}
          {ticket.category === 'site_edit' && (
            <Card className="border-warning dark:border-warning-dark">
              <CardHeader>
                <CardTitle className="flex items-center gap-sm">
                  <Globe className="w-4 h-4 text-warning" />
                  Site Edit Controls
                </CardTitle>
              </CardHeader>
              <CardBody className="space-y-md">
                {hasPreviewVersion ? (
                  <>
                    <p className="text-sm text-text-secondary">
                      The AI has prepared a preview version with the requested changes.
                      Review the operations in the AI Analysis panel, then apply or reject.
                    </p>
                    {!applyConfirm ? (
                      <div className="flex gap-sm">
                        <button
                          onClick={() => setApplyConfirm(true)}
                          className="btn-success flex items-center gap-sm"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          Apply Change
                        </button>
                        <button
                          onClick={() => {
                            setReplyText(
                              "Thanks for the feedback! We've reviewed your request, but we need a bit more clarification before making the change. Could you provide more details about what you'd like updated?"
                            )
                          }}
                          className="btn-outline flex items-center gap-sm"
                        >
                          <XCircle className="w-4 h-4" />
                          Request Clarification
                        </button>
                      </div>
                    ) : (
                      <div className="bg-warning-light dark:bg-warning-dark/20 border border-warning rounded-md p-md space-y-sm">
                        <p className="text-sm font-medium text-warning-dark dark:text-warning-light">
                          This will deploy the changes to the live website. Are you sure?
                        </p>
                        <div className="flex gap-sm">
                          <button
                            onClick={() => applyEditMutation.mutate()}
                            disabled={applyEditMutation.isPending}
                            className="btn-success btn-sm"
                          >
                            {applyEditMutation.isPending ? 'Deploying…' : 'Yes, Deploy Now'}
                          </button>
                          <button
                            onClick={() => setApplyConfirm(false)}
                            className="btn-ghost btn-sm"
                          >
                            Cancel
                          </button>
                        </div>
                        {applyEditMutation.isError && (
                          <p className="text-error text-sm">Deployment failed. Check logs and retry.</p>
                        )}
                      </div>
                    )}
                    {applyEditMutation.isSuccess && (
                      <div className="flex items-center gap-sm text-success text-sm">
                        <CheckCircle2 className="w-4 h-4" />
                        Changes deployed and customer notified.
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-text-secondary">
                    {notes.error
                      ? `AI processing encountered an issue: ${notes.error}`
                      : 'AI is processing the edit request. The preview will appear here once ready.'}
                  </p>
                )}
              </CardBody>
            </Card>
          )}
        </div>

        {/* ── Right column: metadata + AI analysis ────────────────────────── */}
        <div className="space-y-lg">

          {/* Ticket metadata */}
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardBody className="space-y-md text-sm">
              <div className="flex items-center justify-between">
                <span className="text-text-tertiary">Status</span>
                <Badge variant={STATUS_VARIANT[ticket.status] ?? 'secondary'}>
                  {STATUS_LABEL[ticket.status] ?? ticket.status}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-tertiary">Priority</span>
                <Badge variant={PRIORITY_VARIANT[ticket.priority] ?? 'secondary'}>
                  {ticket.priority}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-tertiary">Category</span>
                <span className="text-text-primary">{CATEGORY_LABELS[ticket.category] ?? ticket.category}</span>
              </div>
              <div className="border-t border-border pt-md">
                <p className="text-text-tertiary mb-xs">Customer</p>
                <p className="text-text-primary font-medium">{ticket.customer_name || '—'}</p>
                {ticket.customer_email && (
                  <p className="text-text-secondary text-xs">{ticket.customer_email}</p>
                )}
              </div>
              {ticket.site_title && (
                <div className="border-t border-border pt-md">
                  <p className="text-text-tertiary mb-xs">Site</p>
                  <p className="text-text-primary font-medium">{ticket.site_title}</p>
                  {ticket.site_slug && (
                    <a
                      href={`https://sites.lavish.solutions/${ticket.site_slug}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary-600 hover:underline"
                    >
                      {ticket.site_slug} ↗
                    </a>
                  )}
                </div>
              )}
              <div className="border-t border-border pt-md space-y-xs text-xs text-text-tertiary">
                <div>Created: {formatDate(ticket.created_at)}</div>
                {ticket.first_response_at && (
                  <div>First response: {formatDate(ticket.first_response_at)}</div>
                )}
                {ticket.resolved_at && (
                  <div>Resolved: {formatDate(ticket.resolved_at)}</div>
                )}
              </div>
            </CardBody>
          </Card>

          {/* Subject + description */}
          <Card>
            <CardHeader>
              <CardTitle>Original Request</CardTitle>
            </CardHeader>
            <CardBody className="space-y-sm">
              <p className="font-medium text-text-primary">{ticket.subject}</p>
              <p className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">
                {ticket.description}
              </p>
            </CardBody>
          </Card>

          {/* AI Analysis panel */}
          <AIAnalysisPanel
            ticket={ticket}
            onUseResponse={(text) => setReplyText(text)}
          />

          {/* Status management */}
          <Card>
            <CardHeader>
              <CardTitle>Change Status</CardTitle>
            </CardHeader>
            <CardBody>
              <div className="grid grid-cols-2 gap-sm">
                {['new', 'in_progress', 'waiting_customer', 'resolved', 'closed'].map((s) => (
                  <button
                    key={s}
                    onClick={() => statusMutation.mutate(s)}
                    disabled={ticket.status === s || statusMutation.isPending}
                    className={`btn-sm ${ticket.status === s ? 'btn-primary' : 'btn-outline'} capitalize`}
                  >
                    {STATUS_LABEL[s] ?? s}
                  </button>
                ))}
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
