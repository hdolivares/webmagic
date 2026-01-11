/**
 * Dashboard page with analytics overview
 */
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge } from '@/components/ui'
import { TrendingUp, Users, Globe, Mail, DollarSign, Target, Building2 } from 'lucide-react'

export const DashboardPage = () => {
  // Fetch stats
  const { data: campaignStats } = useQuery({
    queryKey: ['campaign-stats'],
    queryFn: () => api.getCampaignStats(),
  })

  const { data: customerStats } = useQuery({
    queryKey: ['customer-stats'],
    queryFn: () => api.getCustomerStats(),
  })

  const stats = [
    {
      label: 'Total Customers',
      value: customerStats?.total_customers || 0,
      icon: Users,
      color: 'primary',
    },
    {
      label: 'Active Subscriptions',
      value: customerStats?.active_customers || 0,
      icon: Target,
      color: 'success',
    },
    {
      label: 'Total Revenue',
      value: `Q${(customerStats?.total_lifetime_value || 0).toFixed(2)}`,
      icon: DollarSign,
      color: 'accent',
    },
    {
      label: 'Campaigns Sent',
      value: campaignStats?.sent || 0,
      icon: Mail,
      color: 'info',
    },
    {
      label: 'Open Rate',
      value: `${((campaignStats?.open_rate || 0) * 100).toFixed(1)}%`,
      icon: TrendingUp,
      color: 'warning',
    },
    {
      label: 'Click Rate',
      value: `${((campaignStats?.click_rate || 0) * 100).toFixed(1)}%`,
      icon: Globe,
      color: 'secondary',
    },
  ]

  return (
    <div className="p-xl">
      {/* Header */}
      <div className="mb-xl">
        <h1 className="text-4xl font-bold text-text-primary mb-2">Dashboard</h1>
        <p className="text-text-secondary">Welcome to WebMagic Admin</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-md mb-xl">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardBody className="flex items-center gap-md">
              <div className={`p-md rounded-lg bg-${stat.color}-100 dark:bg-${stat.color}-900`}>
                <stat.icon className={`w-6 h-6 text-${stat.color}-600`} />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{stat.value}</p>
                <p className="text-sm text-text-secondary">{stat.label}</p>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>

      {/* Quick actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
            <a href="/businesses" className="nav-link p-md border border-border rounded-md">
              <Building2 className="w-5 h-5" />
              <div>
                <p className="font-medium">View Businesses</p>
                <p className="text-xs text-text-secondary">Manage scraped leads</p>
              </div>
            </a>
            <a href="/sites" className="nav-link p-md border border-border rounded-md">
              <Globe className="w-5 h-5" />
              <div>
                <p className="font-medium">Generated Sites</p>
                <p className="text-xs text-text-secondary">View website gallery</p>
              </div>
            </a>
            <a href="/campaigns" className="nav-link p-md border border-border rounded-md">
              <Mail className="w-5 h-5" />
              <div>
                <p className="font-medium">Email Campaigns</p>
                <p className="text-xs text-text-secondary">Track outreach</p>
              </div>
            </a>
            <a href="/customers" className="nav-link p-md border border-border rounded-md">
              <Users className="w-5 h-5" />
              <div>
                <p className="font-medium">Customers</p>
                <p className="text-xs text-text-secondary">View payments</p>
              </div>
            </a>
          </div>
        </CardBody>
      </Card>
    </div>
  )
}
