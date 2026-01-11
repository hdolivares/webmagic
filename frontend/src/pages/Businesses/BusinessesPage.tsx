/**
 * Businesses management page
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge, Button } from '@/components/ui'
import { Search, Filter } from 'lucide-react'

export const BusinessesPage = () => {
  const [status, setStatus] = useState<string>('')
  const [hasWebsite, setHasWebsite] = useState<boolean | undefined>(undefined)

  const { data, isLoading } = useQuery({
    queryKey: ['businesses', status, hasWebsite],
    queryFn: () =>
      api.getBusinesses({
        limit: 50,
        status: status || undefined,
        has_website: hasWebsite,
      }),
  })

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      qualified: 'success',
      disqualified: 'error',
      contacted: 'info',
      converted: 'primary',
      scraped: 'secondary',
    }
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>
  }

  return (
    <div className="p-xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-xl">
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">Businesses</h1>
          <p className="text-text-secondary">Manage scraped business leads</p>
        </div>
      </div>

      {/* Filters */}
      <Card className="mb-md">
        <CardBody className="flex gap-md items-center">
          <Filter className="w-5 h-5 text-text-secondary" />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="select flex-1"
          >
            <option value="">All Statuses</option>
            <option value="scraped">Scraped</option>
            <option value="qualified">Qualified</option>
            <option value="disqualified">Disqualified</option>
            <option value="contacted">Contacted</option>
            <option value="converted">Converted</option>
          </select>
          <select
            value={hasWebsite === undefined ? '' : hasWebsite.toString()}
            onChange={(e) =>
              setHasWebsite(e.target.value === '' ? undefined : e.target.value === 'true')
            }
            className="select flex-1"
          >
            <option value="">All</option>
            <option value="false">No Website</option>
            <option value="true">Has Website</option>
          </select>
        </CardBody>
      </Card>

      {/* Businesses list */}
      <Card>
        <CardHeader>
          <CardTitle>
            {data?.total || 0} Business{data?.total !== 1 ? 'es' : ''}
          </CardTitle>
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
                    <th className="table-header-cell">Name</th>
                    <th className="table-header-cell">Category</th>
                    <th className="table-header-cell">Location</th>
                    <th className="table-header-cell">Status</th>
                    <th className="table-header-cell">Website</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.businesses.map((business) => (
                    <tr key={business.id} className="table-row">
                      <td className="table-cell font-medium">{business.name}</td>
                      <td className="table-cell text-text-secondary">{business.category}</td>
                      <td className="table-cell text-text-secondary">
                        {business.city}, {business.state}
                      </td>
                      <td className="table-cell">{getStatusBadge(business.status)}</td>
                      <td className="table-cell">
                        <Badge variant={business.has_website ? 'error' : 'success'}>
                          {business.has_website ? 'Yes' : 'No'}
                        </Badge>
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
