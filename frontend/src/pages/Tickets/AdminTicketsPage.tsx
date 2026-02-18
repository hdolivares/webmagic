/**
 * Admin Support Tickets — List View
 *
 * Uses the project's semantic design system throughout:
 *   - Colors: bg-primary-*, bg-surface, bg-background-secondary, text-text-*
 *   - Badges: .badge-* component classes from global.css
 *   - Buttons: .btn-* component classes from global.css
 *   - Cards: Card / CardHeader / CardBody UI components
 *   - Spacing: p-md, p-xl, gap-md etc. (CSS variable–backed Tailwind tokens)
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  HeadphonesIcon,
  Search,
  ChevronRight,
  RefreshCw,
  AlertCircle,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardBody, Badge } from '@/components/ui'
import { api } from '@/services/api'

// ── Status → badge variant mapping ────────────────────────────────────────────
const STATUS_VARIANT: Record<string, 'info' | 'warning' | 'primary' | 'success' | 'secondary'> = {
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

// ── Priority → badge variant mapping ──────────────────────────────────────────
const PRIORITY_VARIANT: Record<string, 'error' | 'warning' | 'primary' | 'secondary'> = {
  urgent: 'error',
  high: 'warning',
  medium: 'primary',
  low: 'secondary',
}

// ── Category display labels ────────────────────────────────────────────────────
const CATEGORY_LABELS: Record<string, string> = {
  billing: 'Billing',
  technical_support: 'Technical',
  site_edit: 'Site Edit',
  question: 'Question',
  other: 'Other',
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

// ── Component ──────────────────────────────────────────────────────────────────
export default function AdminTicketsPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [offset, setOffset] = useState(0)
  const LIMIT = 30

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin-tickets', statusFilter, categoryFilter, priorityFilter, search, offset],
    queryFn: () =>
      api.getAdminTickets({
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        priority: priorityFilter || undefined,
        search: search || undefined,
        limit: LIMIT,
        offset,
      }),
  })

  const tickets = data?.tickets ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / LIMIT)
  const currentPage = Math.floor(offset / LIMIT) + 1
  const hasFilters = !!(statusFilter || categoryFilter || priorityFilter || search)

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setSearch(searchInput)
    setOffset(0)
  }

  function clearFilters() {
    setStatusFilter('')
    setCategoryFilter('')
    setPriorityFilter('')
    setSearch('')
    setSearchInput('')
    setOffset(0)
  }

  return (
    <div className="p-xl space-y-lg max-w-7xl mx-auto">

      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-md">
          <HeadphonesIcon className="w-7 h-7 text-primary-600" />
          <div>
            <h1 className="text-4xl font-bold text-text-primary">Support</h1>
            <p className="text-text-secondary text-sm">{total} ticket{total !== 1 ? 's' : ''} total</p>
          </div>
        </div>
        <button onClick={() => refetch()} className="btn-outline btn-sm flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <Card>
        <CardBody className="flex flex-wrap gap-md items-end">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex gap-sm flex-1 min-w-56">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
              <input
                type="text"
                placeholder="Search ticket # or subject…"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="form-input pl-9 w-full"
              />
            </div>
            <button type="submit" className="btn-primary btn-sm">Search</button>
          </form>

          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setOffset(0) }}
            className="form-select"
          >
            <option value="">All Statuses</option>
            {Object.entries(STATUS_LABEL).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>

          <select
            value={categoryFilter}
            onChange={(e) => { setCategoryFilter(e.target.value); setOffset(0) }}
            className="form-select"
          >
            <option value="">All Categories</option>
            {Object.entries(CATEGORY_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => { setPriorityFilter(e.target.value); setOffset(0) }}
            className="form-select"
          >
            <option value="">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {hasFilters && (
            <button onClick={clearFilters} className="btn-ghost btn-sm">
              Clear filters
            </button>
          )}
        </CardBody>
      </Card>

      {/* Tickets table */}
      <Card>
        <CardHeader>
          <CardTitle>Tickets</CardTitle>
        </CardHeader>
        <CardBody className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-xl gap-sm text-text-secondary">
              <RefreshCw className="w-5 h-5 animate-spin" />
              Loading tickets…
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-xl gap-sm text-error">
              <AlertCircle className="w-5 h-5" />
              Failed to load tickets
            </div>
          ) : tickets.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-xl text-text-tertiary">
              <HeadphonesIcon className="w-10 h-10 mb-md opacity-30" />
              <p className="text-sm">No tickets found{hasFilters ? ' matching your filters' : ''}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table w-full">
                <thead>
                  <tr>
                    <th className="table-th">Ticket</th>
                    <th className="table-th">Customer</th>
                    <th className="table-th">Category</th>
                    <th className="table-th">Priority</th>
                    <th className="table-th">Status</th>
                    <th className="table-th">Created</th>
                    <th className="table-th w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((ticket: any) => (
                    <tr key={ticket.id} className="table-row">
                      <td className="table-td">
                        <Link to={`/tickets/${ticket.id}`} className="block hover:underline">
                          <span className="font-medium text-text-primary">{ticket.ticket_number}</span>
                          <span className="block text-text-secondary text-sm truncate max-w-xs">
                            {ticket.subject}
                          </span>
                          {ticket.site_title && (
                            <span className="block text-primary-600 text-xs mt-0.5">
                              {ticket.site_title}
                            </span>
                          )}
                        </Link>
                      </td>
                      <td className="table-td">
                        <span className="text-text-primary">{ticket.customer_name || '—'}</span>
                        {ticket.customer_email && (
                          <span className="block text-text-secondary text-xs">{ticket.customer_email}</span>
                        )}
                      </td>
                      <td className="table-td text-text-secondary">
                        {CATEGORY_LABELS[ticket.category] ?? ticket.category}
                      </td>
                      <td className="table-td">
                        <Badge variant={PRIORITY_VARIANT[ticket.priority] ?? 'secondary'}>
                          {ticket.priority}
                        </Badge>
                      </td>
                      <td className="table-td">
                        <Badge variant={STATUS_VARIANT[ticket.status] ?? 'secondary'}>
                          {STATUS_LABEL[ticket.status] ?? ticket.status}
                        </Badge>
                      </td>
                      <td className="table-td text-text-tertiary text-sm whitespace-nowrap">
                        {timeAgo(ticket.created_at)}
                      </td>
                      <td className="table-td">
                        <Link to={`/tickets/${ticket.id}`}>
                          <ChevronRight className="w-4 h-4 text-text-tertiary" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {total > LIMIT && (
            <div className="flex items-center justify-between px-md py-sm border-t border-border">
              <span className="text-sm text-text-secondary">
                Page {currentPage} of {totalPages} ({total} total)
              </span>
              <div className="flex gap-sm">
                <button
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                  className="btn-outline btn-sm"
                >
                  Previous
                </button>
                <button
                  disabled={offset + LIMIT >= total}
                  onClick={() => setOffset(offset + LIMIT)}
                  className="btn-outline btn-sm"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
