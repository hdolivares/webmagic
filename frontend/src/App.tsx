/**
 * Main App component with routing
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useApplyTheme } from '@/hooks/useTheme'
import { useAuth } from '@/hooks/useAuth'
import { useEffect } from 'react'

// Layout
import { Layout } from '@/components/layout/Layout'
import CustomerLayout from '@/layouts/CustomerLayout'

// Auth Pages
import { LoginPage } from '@/pages/Auth/LoginPage'
import ForgotPasswordPage from '@/pages/Auth/ForgotPasswordPage'
import ResetPasswordPage from '@/pages/Auth/ResetPasswordPage'

// Admin Pages
import { DashboardPage } from '@/pages/Dashboard/DashboardPage'
import { BusinessesPage } from '@/pages/Businesses/BusinessesPage'
import { SitesPage } from '@/pages/Sites/SitesPage'
import { GeneratedSitesPage } from '@/pages/Sites/GeneratedSitesPage'
import { GeneratedSiteDetailPage } from '@/pages/Sites/GeneratedSiteDetailPage'
import { CampaignsPage } from '@/pages/Campaigns/CampaignsPage'
import { CustomersPage } from '@/pages/Customers/CustomersPage'
import { CoveragePage } from '@/pages/Coverage/CoveragePage'
import { SettingsPage } from '@/pages/Settings/SettingsPage'
import { ImageGenerationPage } from '@/pages/ImageGeneration/ImageGenerationPage'
import { MessagesPage } from '@/pages/Messages/MessagesPage'
import AdminTicketsPage from '@/pages/Tickets/AdminTicketsPage'
import AdminTicketDetailPage from '@/pages/Tickets/AdminTicketDetailPage'
import { VerificationPage } from '@/pages/Verification/VerificationPage'

// Customer Pages
import MySitesPage from '@/pages/CustomerPortal/MySitesPage'
import DomainsPage from '@/pages/CustomerPortal/DomainsPage'
import TicketsPage from '@/pages/CustomerPortal/TicketsPage'
import TicketDetailPage from '@/pages/CustomerPortal/TicketDetailPage'
import AccountSettingsPage from '@/pages/CustomerPortal/AccountSettingsPage'

// Public Pages
import SitePreviewPage from '@/pages/Public/SitePreviewPage'
import PurchaseSuccessPage from '@/pages/Public/PurchaseSuccessPage'
import HowItWorksPage from '@/pages/Public/HowItWorksPage'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// Protected route wrapper
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, user, fetchUser } = useAuth()

  // Fetch user profile once when authenticated (e.g. after page refresh).
  // Only depend on `isAuthenticated` — NOT on `isLoading` or `fetchUser` —
  // to avoid an infinite loop where fetchUser toggling isLoading re-triggers
  // the effect on every completion.
  useEffect(() => {
    if (isAuthenticated && !user) {
      fetchUser()
    }
  }, [isAuthenticated]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  // Apply theme to document
  useApplyTheme()

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          
          {/* Public site preview & purchase */}
          <Route path="/site-preview/:slug" element={<SitePreviewPage />} />
          <Route path="/purchase-success" element={<PurchaseSuccessPage />} />
          <Route path="/how-it-works" element={<HowItWorksPage />} />

          {/* Admin Protected routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="businesses" element={<BusinessesPage />} />
            <Route path="sites" element={<SitesPage />} />
            <Route path="sites/generated" element={<GeneratedSitesPage />} />
            <Route path="sites/generated/:siteId" element={<GeneratedSiteDetailPage />} />
            <Route path="sites/image-generator" element={<ImageGenerationPage />} />
            <Route path="campaigns" element={<CampaignsPage />} />
            <Route path="messages" element={<MessagesPage />} />
            <Route path="customers" element={<CustomersPage />} />
            <Route path="coverage" element={<CoveragePage />} />
            <Route path="tickets" element={<AdminTicketsPage />} />
            <Route path="tickets/:ticketId" element={<AdminTicketDetailPage />} />
            <Route path="verification" element={<VerificationPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          {/* Customer Protected routes */}
          <Route
            path="/customer"
            element={
              <ProtectedRoute>
                <CustomerLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/customer/sites" replace />} />
            <Route path="sites" element={<MySitesPage />} />
            <Route path="domains" element={<DomainsPage />} />
            <Route path="tickets" element={<TicketsPage />} />
            <Route path="tickets/:ticketId" element={<TicketDetailPage />} />
            <Route path="settings" element={<AccountSettingsPage />} />
          </Route>

          {/* 404 - redirect to login for unauthenticated, or dashboard for authenticated */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
