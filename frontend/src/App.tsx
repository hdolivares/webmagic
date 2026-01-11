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

// Pages
import { LoginPage } from '@/pages/Auth/LoginPage'
import { DashboardPage } from '@/pages/Dashboard/DashboardPage'
import { BusinessesPage } from '@/pages/Businesses/BusinessesPage'
import { SitesPage } from '@/pages/Sites/SitesPage'
import { CampaignsPage } from '@/pages/Campaigns/CampaignsPage'
import { CustomersPage } from '@/pages/Customers/CustomersPage'
import { SettingsPage } from '@/pages/Settings/SettingsPage'

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
  const { isAuthenticated, isLoading, fetchUser } = useAuth()

  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      fetchUser()
    }
  }, [isAuthenticated, isLoading, fetchUser])

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
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected routes */}
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
            <Route path="campaigns" element={<CampaignsPage />} />
            <Route path="customers" element={<CustomersPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          {/* 404 */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
