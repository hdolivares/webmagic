/**
 * Customers portal page
 */
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge } from '@/components/ui'
import { Users, DollarSign, TrendingUp } from 'lucide-react'

export const CustomersPage = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['customers'],
    queryFn: () => api.getCustomers({ limit: 50 }),
  })

  const { data: stats } = useQuery({
    queryKey: ['customer-stats'],
    queryFn: () => api.getCustomerStats(),
  })

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      active: 'success',
      cancelled: 'error',
      past_due: 'warning',
      suspended: 'secondary',
    }
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>
  }

  return (
    <div className="p-xl">
      <div className="mb-xl">
        <h1 className="text-4xl font-bold text-text-primary mb-2">Customers</h1>
        <p className="text-text-secondary">Manage paying customers and subscriptions</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-md mb-md">
        <Card>
          <CardBody className="flex items-center gap-md">
            <Users className="w-6 h-6 text-primary-600" />
            <div>
              <p className="text-2xl font-bold">{stats?.total_customers || 0}</p>
              <p className="text-sm text-text-secondary">Total Customers</p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-md">
            <TrendingUp className="w-6 h-6 text-success" />
            <div>
              <p className="text-2xl font-bold">{stats?.active_customers || 0}</p>
              <p className="text-sm text-text-secondary">Active</p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-md">
            <DollarSign className="w-6 h-6 text-accent-600" />
            <div>
              <p className="text-2xl font-bold">
                Q{(stats?.total_lifetime_value || 0).toFixed(2)}
              </p>
              <p className="text-sm text-text-secondary">Total LTV</p>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Customers list */}
      <Card>
        <CardHeader>
          <CardTitle>All Customers ({data?.total || 0})</CardTitle>
        </CardHeader>
        <CardBody>
          {isLoading ? (
            <div className="flex items-center justify-center py-xl">
              <div className="spinner-lg" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table">
                <thead className="table-header">
                  <tr>
                    <th className="table-header-cell">Customer</th>
                    <th className="table-header-cell">Email</th>
                    <th className="table-header-cell">Status</th>
                    <th className="table-header-cell">LTV</th>
                    <th className="table-header-cell">Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.customers.map((customer) => (
                    <tr key={customer.id} className="table-row">
                      <td className="table-cell font-medium">
                        {customer.full_name || 'Unknown'}
                      </td>
                      <td className="table-cell text-text-secondary">{customer.email}</td>
                      <td className="table-cell">{getStatusBadge(customer.status)}</td>
                      <td className="table-cell">Q{customer.lifetime_value.toFixed(2)}</td>
                      <td className="table-cell text-text-secondary">
                        {new Date(customer.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
