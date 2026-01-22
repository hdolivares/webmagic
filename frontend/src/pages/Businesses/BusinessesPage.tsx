/**
 * Enhanced Businesses Management Page
 * 
 * Features:
 * - Advanced filtering with presets
 * - Bulk selection and actions
 * - CRM indicators (contact info, status badges, data quality)
 * - Responsive table with all enriched fields
 * 
 * @author WebMagic Team
 * @date January 22, 2026
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Button } from '@/components/ui'
import { 
  StatusBadge, 
  ContactIndicator, 
  DataCompleteness, 
  FilterBar,
  BusinessFilters 
} from '@/components/CRM'
import { Download, Mail, MessageSquare, Trash2 } from 'lucide-react'
import './BusinessesPage.css'

// Enhanced business type with all CRM fields
interface EnrichedBusiness {
  id: string
  name: string
  email?: string | null
  phone?: string | null
  category?: string
  city?: string
  state?: string
  rating?: number
  review_count?: number
  qualification_score?: number
  contact_status?: string
  website_status?: string
  
  // NEW: CRM enrichment fields (optional to handle API response)
  has_email?: boolean
  has_phone?: boolean
  was_contacted?: boolean
  contacted_via_email?: boolean
  contacted_via_sms?: boolean
  contact_bounced?: boolean
  is_unsubscribed?: boolean
  is_customer?: boolean
  total_campaigns?: number
  last_contact_date?: string | null
  last_contact_channel?: string | null
  has_generated_site?: boolean
  site_url?: string | null
  data_completeness?: number
  status_label?: string
  status_color?: string
}

export const BusinessesPage = () => {
  // Filters state
  const [filters, setFilters] = useState<BusinessFilters>({})
  
  // Bulk selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [selectAll, setSelectAll] = useState(false)

  // Fetch businesses with filters
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['businesses', filters],
    queryFn: () => api.getBusinesses({ ...filters, limit: 100 }),
  })

  const businesses = (data?.businesses as EnrichedBusiness[]) || []
  const total = data?.total || 0

  // ============================================
  // BULK SELECTION
  // ============================================
  const toggleSelectAll = () => {
    if (selectAll) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(businesses.map((b) => b.id)))
    }
    setSelectAll(!selectAll)
  }

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
    setSelectAll(newSelected.size === businesses.length)
  }

  const clearSelection = () => {
    setSelectedIds(new Set())
    setSelectAll(false)
  }

  // ============================================
  // BULK ACTIONS
  // ============================================
  const handleBulkExport = async () => {
    if (selectedIds.size === 0) {
      alert('Please select businesses to export')
      return
    }
    
    try {
      // Call bulk export API
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/businesses/bulk/export?format=csv`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
          body: JSON.stringify({
            business_ids: Array.from(selectedIds),
          }),
        }
      )

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `businesses-${new Date().toISOString().split('T')[0]}.csv`
        a.click()
        window.URL.revokeObjectURL(url)
      } else {
        alert('Export failed. Please try again.')
      }
    } catch (error) {
      console.error('Export error:', error)
      alert('Export failed. Please try again.')
    }
  }

  const handleBulkStatusUpdate = async () => {
    if (selectedIds.size === 0) {
      alert('Please select businesses to update')
      return
    }

    const newStatus = prompt('Enter new contact status (e.g., emailed, contacted):', 'emailed')
    if (!newStatus) return

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/businesses/bulk/update-status`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
          body: JSON.stringify({
            business_ids: Array.from(selectedIds),
            contact_status: newStatus,
          }),
        }
      )

      if (response.ok) {
        alert('Status updated successfully!')
        clearSelection()
        refetch()
      } else {
        alert('Update failed. Please try again.')
      }
    } catch (error) {
      console.error('Update error:', error)
      alert('Update failed. Please try again.')
    }
  }

  return (
    <div className="businesses-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Businesses</h1>
          <p className="page-subtitle">Manage your lead pipeline with advanced CRM tools</p>
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        filters={filters}
        onFiltersChange={setFilters}
        resultCount={total}
      />

      {/* Bulk Actions Bar */}
      {selectedIds.size > 0 && (
        <Card className="bulk-actions-bar">
          <CardBody className="flex items-center justify-between">
            <div className="flex items-center gap-md">
              <span className="selected-count">
                {selectedIds.size} selected
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={clearSelection}
              >
                Clear Selection
              </Button>
            </div>
            <div className="flex items-center gap-sm">
              <Button
                variant="outline"
                size="sm"
                onClick={handleBulkStatusUpdate}
                className="btn-icon"
              >
                <Mail className="w-4 h-4" />
                Update Status
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleBulkExport}
                className="btn-icon"
              >
                <Download className="w-4 h-4" />
                Export CSV
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Businesses Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            {total} Business{total !== 1 ? 'es' : ''}
          </CardTitle>
        </CardHeader>
        <CardBody>
          {isLoading ? (
            <div className="flex items-center justify-center py-xl">
              <div className="spinner-lg" />
            </div>
          ) : businesses.length === 0 ? (
            <div className="empty-state">
              <p>No businesses found matching your filters.</p>
              <Button onClick={() => setFilters({})} variant="outline">
                Clear Filters
              </Button>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="crm-table">
                <thead>
                  <tr>
                    <th className="th-checkbox">
                      <input
                        type="checkbox"
                        checked={selectAll}
                        onChange={toggleSelectAll}
                        aria-label="Select all"
                      />
                    </th>
                    <th>Business</th>
                    <th>Contact Info</th>
                    <th>Status</th>
                    <th className="text-center">Score</th>
                    <th className="text-center">Quality</th>
                    <th className="text-center">Campaigns</th>
                  </tr>
                </thead>
                <tbody>
                  {businesses.map((business) => (
                    <tr
                      key={business.id}
                      className={selectedIds.has(business.id) ? 'selected' : ''}
                    >
                      {/* Checkbox */}
                      <td className="td-checkbox">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(business.id)}
                          onChange={() => toggleSelect(business.id)}
                          aria-label={`Select ${business.name}`}
                        />
                      </td>

                      {/* Business Name & Location */}
                      <td className="td-business-info">
                        <div className="business-name">{business.name}</div>
                        <div className="business-meta">
                          {business.category && (
                            <span className="meta-item">{business.category}</span>
                          )}
                          {business.city && business.state && (
                            <span className="meta-item">
                              {business.city}, {business.state}
                            </span>
                          )}
                          {business.rating && (
                            <span className="meta-item">
                              ⭐ {business.rating.toFixed(1)} ({business.review_count || 0})
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Contact Info Indicators */}
                      <td className="td-contact">
                        <ContactIndicator
                          hasEmail={business.has_email || false}
                          hasPhone={business.has_phone || false}
                          email={business.email}
                          phone={business.phone}
                        />
                      </td>

                      {/* Status Badge */}
                      <td className="td-status">
                        <StatusBadge status={business.contact_status || 'pending'} />
                        {business.has_generated_site && (
                          <span className="site-indicator" title="Has generated site">
                            🌐
                          </span>
                        )}
                      </td>

                      {/* Qualification Score */}
                      <td className="td-score text-center">
                        <span className={`score-badge ${getScoreClass(business.qualification_score || 0)}`}>
                          {business.qualification_score || 0}
                        </span>
                      </td>

                      {/* Data Quality */}
                      <td className="td-quality">
                        <DataCompleteness score={business.data_completeness || 0} />
                      </td>

                      {/* Campaign Info */}
                      <td className="td-campaigns text-center">
                        <div className="campaigns-info">
                          <span className="campaign-count">
                            {business.total_campaigns || 0}
                          </span>
                          {business.last_contact_date && (
                            <span className="campaign-date">
                              {new Date(business.last_contact_date).toLocaleDateString()}
                            </span>
                          )}
                        </div>
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

// Helper function for score badge styling
function getScoreClass(score: number): string {
  if (score >= 80) return 'score-excellent'
  if (score >= 60) return 'score-good'
  if (score >= 40) return 'score-fair'
  return 'score-poor'
}
