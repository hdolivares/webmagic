/**
 * SMS Messages Inbox Page
 * 
 * Displays all SMS messages (inbound and outbound) with filtering and search.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge } from '@/components/ui'
import { 
  MessageSquare, 
  ArrowDownLeft, 
  ArrowUpRight, 
  Send, 
  CheckCircle, 
  XCircle,
  Ban,
  Search,
  RefreshCw,
  DollarSign,
  Clock
} from 'lucide-react'
import './MessagesPage.css'

export const MessagesPage = () => {
  const [page, setPage] = useState(1)
  const [direction, setDirection] = useState<'inbound' | 'outbound' | ''>('')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  // Debounce search
  const handleSearchChange = (value: string) => {
    setSearch(value)
    setTimeout(() => setDebouncedSearch(value), 500)
  }

  // Fetch messages
  const { data: messagesData, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['messages', page, direction, debouncedSearch],
    queryFn: () => api.getMessages({
      page,
      page_size: 25,
      direction: direction || undefined,
      search: debouncedSearch || undefined,
    }),
  })

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['message-stats'],
    queryFn: () => api.getMessageStats(),
  })

  // Status badge helper
  const getStatusBadge = (status: string, direction: string) => {
    if (direction === 'inbound') {
      return <Badge variant="info">Received</Badge>
    }
    
    const variants: Record<string, 'success' | 'warning' | 'error' | 'secondary' | 'info'> = {
      delivered: 'success',
      sent: 'info',
      pending: 'warning',
      failed: 'error',
      received: 'info',
    }
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>
  }

  // Direction icon helper
  const DirectionIcon = ({ dir }: { dir: string }) => {
    if (dir === 'inbound') {
      return <ArrowDownLeft className="w-4 h-4 text-info" />
    }
    return <ArrowUpRight className="w-4 h-4 text-success" />
  }

  // Format phone number
  const formatPhone = (phone: string) => {
    if (!phone) return 'Unknown'
    // Format E.164 to readable
    if (phone.startsWith('+1') && phone.length === 12) {
      return `(${phone.slice(2, 5)}) ${phone.slice(5, 8)}-${phone.slice(8)}`
    }
    return phone
  }

  // Format timestamp
  const formatTime = (dateStr: string) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  // Error state
  if (isError) {
    return (
      <div className="p-xl">
        <div className="mb-xl">
          <h1 className="text-4xl font-bold text-text-primary mb-2">📱 SMS Messages</h1>
          <p className="text-text-secondary">View and manage all SMS communications</p>
        </div>
        <Card>
          <CardBody>
            <div className="text-center py-xl">
              <p className="text-error text-lg mb-4">Unable to load messages</p>
              <p className="text-text-secondary mb-4">
                {error instanceof Error ? error.message : 'An error occurred'}
              </p>
              <button onClick={() => refetch()} className="btn btn-primary">
                <RefreshCw className="w-4 h-4 mr-2" />
                Retry
              </button>
            </div>
          </CardBody>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-xl messages-page">
      {/* Header */}
      <div className="mb-xl flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">📱 SMS Messages</h1>
          <p className="text-text-secondary">View and manage all SMS communications</p>
        </div>
        <button onClick={() => refetch()} className="btn btn-secondary">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-md mb-lg">
        <Card className="stat-card">
          <CardBody className="flex items-center gap-md p-md">
            <div className="stat-icon bg-primary/10">
              <MessageSquare className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.total_messages || 0}</p>
              <p className="text-xs text-text-secondary">Total</p>
            </div>
          </CardBody>
        </Card>

        <Card className="stat-card">
          <CardBody className="flex items-center gap-md p-md">
            <div className="stat-icon bg-info/10">
              <ArrowDownLeft className="w-5 h-5 text-info" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.inbound_count || 0}</p>
              <p className="text-xs text-text-secondary">Received</p>
            </div>
          </CardBody>
        </Card>

        <Card className="stat-card">
          <CardBody className="flex items-center gap-md p-md">
            <div className="stat-icon bg-success/10">
              <Send className="w-5 h-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.outbound_count || 0}</p>
              <p className="text-xs text-text-secondary">Sent</p>
            </div>
          </CardBody>
        </Card>

        <Card className="stat-card">
          <CardBody className="flex items-center gap-md p-md">
            <div className="stat-icon bg-success/10">
              <CheckCircle className="w-5 h-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.delivered_count || 0}</p>
              <p className="text-xs text-text-secondary">Delivered</p>
            </div>
          </CardBody>
        </Card>

        <Card className="stat-card">
          <CardBody className="flex items-center gap-md p-md">
            <div className="stat-icon bg-warning/10">
              <Ban className="w-5 h-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.opt_out_count || 0}</p>
              <p className="text-xs text-text-secondary">Opt-outs</p>
            </div>
          </CardBody>
        </Card>

        <Card className="stat-card">
          <CardBody className="flex items-center gap-md p-md">
            <div className="stat-icon bg-accent/10">
              <DollarSign className="w-5 h-5 text-accent" />
            </div>
            <div>
              <p className="text-2xl font-bold">${(stats?.total_cost || 0).toFixed(2)}</p>
              <p className="text-xs text-text-secondary">Total Cost</p>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Today's Activity */}
      {stats && (stats.messages_today > 0 || stats.inbound_today > 0) && (
        <Card className="mb-lg activity-card">
          <CardBody className="flex items-center gap-lg p-md">
            <Clock className="w-5 h-5 text-primary" />
            <span className="text-text-secondary">Today:</span>
            <span className="font-medium">{stats.messages_today} messages</span>
            {stats.inbound_today > 0 && (
              <Badge variant="info">{stats.inbound_today} new replies</Badge>
            )}
          </CardBody>
        </Card>
      )}

      {/* Filters */}
      <Card className="mb-lg">
        <CardBody className="flex flex-wrap items-center gap-md p-md">
          {/* Search */}
          <div className="search-input flex-1 min-w-[200px]">
            <Search className="w-4 h-4 text-text-secondary" />
            <input
              type="text"
              placeholder="Search messages, phone numbers..."
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="input-field"
            />
          </div>

          {/* Direction Filter */}
          <select
            value={direction}
            onChange={(e) => {
              setDirection(e.target.value as 'inbound' | 'outbound' | '')
              setPage(1)
            }}
            className="select-field"
          >
            <option value="">All Messages</option>
            <option value="inbound">📥 Received</option>
            <option value="outbound">📤 Sent</option>
          </select>
        </CardBody>
      </Card>

      {/* Messages List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            Messages
            {messagesData && (
              <span className="text-text-secondary font-normal text-sm">
                ({messagesData.total} total)
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardBody>
          {isLoading ? (
            <div className="flex items-center justify-center py-xl">
              <div className="spinner-lg" />
            </div>
          ) : !messagesData?.messages?.length ? (
            <div className="text-center py-xl">
              <MessageSquare className="w-12 h-12 text-text-secondary mx-auto mb-4 opacity-50" />
              <p className="text-text-secondary">No messages found</p>
              <p className="text-sm text-text-secondary mt-2">
                Messages will appear here when you send SMS campaigns or receive replies.
              </p>
            </div>
          ) : (
            <>
              <div className="messages-list">
                {messagesData.messages.map((message: any) => (
                  <div 
                    key={message.id} 
                    className={`message-item ${message.direction === 'inbound' ? 'inbound' : 'outbound'}`}
                  >
                    <div className="message-header">
                      <div className="message-direction">
                        <DirectionIcon dir={message.direction} />
                        <span className="font-medium">
                          {message.direction === 'inbound' 
                            ? formatPhone(message.from_phone)
                            : formatPhone(message.to_phone)
                          }
                        </span>
                      </div>
                      <div className="message-meta">
                        {getStatusBadge(message.status, message.direction)}
                        <span className="text-xs text-text-secondary">
                          {formatTime(message.created_at)}
                        </span>
                      </div>
                    </div>

                    {message.business_name && (
                      <div className="message-business">
                        <span className="text-sm text-text-secondary">
                          {message.business_name}
                          {message.business_city && ` • ${message.business_city}, ${message.business_state}`}
                        </span>
                      </div>
                    )}

                    <div className="message-body">
                      <p>{message.body}</p>
                    </div>

                    {message.error_message && (
                      <div className="message-error">
                        <XCircle className="w-4 h-4 text-error" />
                        <span className="text-sm text-error">{message.error_message}</span>
                      </div>
                    )}

                    {message.cost && (
                      <div className="message-cost">
                        <span className="text-xs text-text-secondary">
                          Cost: ${message.cost.toFixed(4)} • {message.segments || 1} segment(s)
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {messagesData.pages > 1 && (
                <div className="pagination mt-lg">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="btn btn-secondary btn-sm"
                  >
                    Previous
                  </button>
                  <span className="text-text-secondary">
                    Page {page} of {messagesData.pages}
                  </span>
                  <button
                    onClick={() => setPage(p => Math.min(messagesData.pages, p + 1))}
                    disabled={page === messagesData.pages}
                    className="btn btn-secondary btn-sm"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

