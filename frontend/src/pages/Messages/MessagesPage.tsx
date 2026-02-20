/**
 * SMS Messages Inbox Page
 *
 * Two-panel layout:
 *   Left  → ConversationList (one row per unique contact phone)
 *   Right → ConversationThread (chat bubbles for selected contact)
 *
 * Stats bar across the top provides quick counts/costs at a glance.
 */
import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Card, CardBody } from '@/components/ui'
import {
  MessageSquare,
  ArrowDownLeft,
  Send,
  CheckCircle,
  Ban,
  DollarSign,
  Clock,
} from 'lucide-react'
import { Badge } from '@/components/ui'
import { ConversationList } from './ConversationList'
import { ConversationThread } from './ConversationThread'
import './MessagesPage.css'

export const MessagesPage = () => {
  const [selectedPhone, setSelectedPhone] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value)
    const timer = setTimeout(() => setDebouncedSearch(value), 400)
    return () => clearTimeout(timer)
  }, [])

  // ─── Conversation list ──────────────────────────────────────────────────
  const {
    data: convData,
    isLoading: convLoading,
    refetch: refetchConvs,
  } = useQuery({
    queryKey: ['conversations', debouncedSearch],
    queryFn: () => api.getConversations({ search: debouncedSearch || undefined, limit: 200 }),
  })

  // ─── Thread for selected contact ────────────────────────────────────────
  const {
    data: threadData,
    isLoading: threadLoading,
    refetch: refetchThread,
  } = useQuery({
    queryKey: ['conversation-thread', selectedPhone],
    queryFn: () => api.getConversationThread(selectedPhone!),
    enabled: !!selectedPhone,
  })

  // ─── Stats bar ──────────────────────────────────────────────────────────
  const { data: stats } = useQuery({
    queryKey: ['message-stats'],
    queryFn: () => api.getMessageStats(),
  })

  return (
    <div className="p-xl messages-page">
      {/* Page header */}
      <div className="mb-lg">
        <h1 className="text-4xl font-bold text-text-primary mb-1">SMS Messages</h1>
        <p className="text-text-secondary">All SMS conversations with your leads</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-md mb-lg">
        <StatCard icon={<MessageSquare className="w-5 h-5 text-primary" />} bg="bg-primary/10" value={stats?.total_messages ?? 0} label="Total" />
        <StatCard icon={<ArrowDownLeft className="w-5 h-5 text-info" />} bg="bg-info/10" value={stats?.inbound_count ?? 0} label="Received" />
        <StatCard icon={<Send className="w-5 h-5 text-success" />} bg="bg-success/10" value={stats?.outbound_count ?? 0} label="Sent" />
        <StatCard icon={<CheckCircle className="w-5 h-5 text-success" />} bg="bg-success/10" value={stats?.delivered_count ?? 0} label="Delivered" />
        <StatCard icon={<Ban className="w-5 h-5 text-warning" />} bg="bg-warning/10" value={stats?.opt_out_count ?? 0} label="Opt-outs" />
        <StatCard icon={<DollarSign className="w-5 h-5 text-accent" />} bg="bg-accent/10" value={`$${(stats?.total_cost ?? 0).toFixed(2)}`} label="Total Cost" />
      </div>

      {/* Today's activity banner */}
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

      {/* Two-panel inbox */}
      <div className="inbox-panel">
        <ConversationList
          conversations={convData?.conversations ?? []}
          selectedPhone={selectedPhone}
          isLoading={convLoading}
          search={search}
          onSearchChange={handleSearchChange}
          onSelect={setSelectedPhone}
          onRefresh={refetchConvs}
        />

        <div className="inbox-panel__thread">
          {selectedPhone ? (
            <ConversationThread
              contactPhone={selectedPhone}
              messages={threadData?.messages ?? []}
              isLoading={threadLoading}
              onRefresh={refetchThread}
            />
          ) : (
            <div className="inbox-panel__placeholder">
              <MessageSquare className="w-14 h-14 opacity-20 mb-3" />
              <p className="text-text-secondary text-lg">Select a conversation</p>
              <p className="text-text-secondary text-sm mt-1">
                Choose a contact on the left to view the full thread.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Tiny helper component ────────────────────────────────────────────────────

function StatCard({
  icon,
  bg,
  value,
  label,
}: {
  icon: React.ReactNode
  bg: string
  value: number | string
  label: string
}) {
  return (
    <Card className="stat-card">
      <CardBody className="flex items-center gap-md p-md">
        <div className={`stat-icon ${bg}`}>{icon}</div>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-xs text-text-secondary">{label}</p>
        </div>
      </CardBody>
    </Card>
  )
}
