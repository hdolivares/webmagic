/**
 * Customer Portal Layout
 * 
 * Restricted layout for customers with limited access to:
 * - Custom Domains
 * - Support Tickets
 */
import React, { useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import './CustomerLayout.css'

const CustomerLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = () => {
    // Clear customer auth token
    localStorage.removeItem('customer_token')
    navigate('/customer/login')
  }

  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen)
  }

  // Get customer info from localStorage or context
  const customerEmail = localStorage.getItem('customer_email') || 'Customer'

  return (
    <div className="customer-layout">
      <header className="customer-header">
        <div className="customer-header-content">
          <div className="customer-logo">
            <h1>WebMagic</h1>
            <span className="customer-badge">Customer Portal</span>
          </div>

          <button 
            className="mobile-menu-toggle"
            onClick={toggleMobileMenu}
            aria-label="Toggle menu"
          >
            <span></span>
            <span></span>
            <span></span>
          </button>

          <nav className={`customer-nav ${mobileMenuOpen ? 'mobile-open' : ''}`}>
            <NavLink 
              to="/customer/sites" 
              className={({ isActive }) => isActive ? 'active' : ''}
              onClick={() => setMobileMenuOpen(false)}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <line x1="9" y1="3" x2="9" y2="21"/>
              </svg>
              <span>My Sites</span>
            </NavLink>

            <NavLink 
              to="/customer/domains" 
              className={({ isActive }) => isActive ? 'active' : ''}
              onClick={() => setMobileMenuOpen(false)}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                <line x1="12" y1="22.08" x2="12" y2="12"/>
              </svg>
              <span>Custom Domain</span>
            </NavLink>

            <NavLink 
              to="/customer/tickets" 
              className={({ isActive }) => isActive ? 'active' : ''}
              onClick={() => setMobileMenuOpen(false)}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
              </svg>
              <span>My Tickets</span>
            </NavLink>

            <div className="customer-user-info">
              <div className="customer-email">{customerEmail}</div>
              <button className="btn-logout" onClick={handleLogout}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                  <polyline points="16 17 21 12 16 7"/>
                  <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                Logout
              </button>
            </div>
          </nav>
        </div>
      </header>

      <main className="customer-main">
        <div className="customer-container">
          <Outlet />
        </div>
      </main>

      <footer className="customer-footer">
        <div className="customer-footer-content">
          <p>&copy; {new Date().getFullYear()} WebMagic. All rights reserved.</p>
          <div className="customer-footer-links">
            <a href="https://webmagic.com/support" target="_blank" rel="noopener noreferrer">
              Help Center
            </a>
            <a href="https://webmagic.com/terms" target="_blank" rel="noopener noreferrer">
              Terms of Service
            </a>
            <a href="https://webmagic.com/privacy" target="_blank" rel="noopener noreferrer">
              Privacy Policy
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default CustomerLayout

