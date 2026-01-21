/**
 * SiteEditsPage - Customer Dashboard
 * 
 * Page where customers can request and manage AI-powered site edits.
 * 
 * Author: WebMagic Team
 * Date: January 21, 2026
 */
import { useState } from 'react'
import { EditRequestForm, EditRequestList } from '@/components/EditRequests'
import './SiteEditsPage.css'

interface SiteEditsPageProps {
  siteId: string
  siteName?: string
}

export function SiteEditsPage({ siteId, siteName }: SiteEditsPageProps) {
  const [showForm, setShowForm] = useState(false)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleSuccess = (editRequest: any) => {
    // Show success message
    alert(`Edit request submitted successfully! You'll receive an email when the preview is ready.`)
    
    // Hide form and refresh list
    setShowForm(false)
    setRefreshTrigger(prev => prev + 1)
  }

  const handleViewPreview = (request: any) => {
    // Open preview in new tab
    if (request.preview_url) {
      window.open(request.preview_url, '_blank')
    }
  }

  return (
    <div className="site-edits-page">
      {/* Page Header */}
      <div className="page-header">
        <div className="header-content">
          <h1 className="page-title">Site Edits</h1>
          {siteName && (
            <p className="page-subtitle">Managing edits for {siteName}</p>
          )}
        </div>
        
        {!showForm && (
          <button
            className="btn-new-request"
            onClick={() => setShowForm(true)}
          >
            <svg className="btn-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Edit Request
          </button>
        )}
      </div>

      {/* Main Content */}
      <div className="page-content">
        {showForm ? (
          <div className="form-section">
            <EditRequestForm
              siteId={siteId}
              onSuccess={handleSuccess}
              onCancel={() => setShowForm(false)}
            />
          </div>
        ) : (
          <div className="list-section">
            <div className="section-header">
              <h2 className="section-title">Request History</h2>
              <p className="section-description">
                View and manage your edit requests. Click on any ready preview to review changes.
              </p>
            </div>
            
            <EditRequestList
              siteId={siteId}
              refreshTrigger={refreshTrigger}
              onViewPreview={handleViewPreview}
            />
          </div>
        )}
      </div>

      {/* Help Section */}
      {!showForm && (
        <div className="help-section">
          <h3 className="help-title">How AI-Powered Edits Work</h3>
          <div className="help-cards">
            <div className="help-card">
              <div className="help-icon">1</div>
              <h4>Describe Changes</h4>
              <p>Tell us what you want to change in plain English</p>
            </div>
            <div className="help-card">
              <div className="help-icon">2</div>
              <h4>AI Generates Preview</h4>
              <p>Our AI creates a preview in 2-5 minutes</p>
            </div>
            <div className="help-card">
              <div className="help-icon">3</div>
              <h4>Review & Approve</h4>
              <p>Compare side-by-side and approve or reject</p>
            </div>
            <div className="help-card">
              <div className="help-icon">4</div>
              <h4>Goes Live</h4>
              <p>Approved changes are deployed instantly</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

