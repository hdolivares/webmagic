/**
 * Main layout with sidebar navigation
 */
import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useTheme } from '@/hooks/useTheme'
import {
  LayoutDashboard,
  Building2,
  Globe,
  Mail,
  Users,
  Settings,
  LogOut,
  Sun,
  Moon,
} from 'lucide-react'

export const Layout = () => {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/businesses', icon: Building2, label: 'Businesses' },
    { to: '/sites', icon: Globe, label: 'Sites' },
    { to: '/campaigns', icon: Mail, label: 'Campaigns' },
    { to: '/customers', icon: Users, label: 'Customers' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 bg-surface border-r border-border flex flex-col">
        {/* Logo */}
        <div className="px-lg py-xl border-b border-border">
          <h1 className="text-2xl font-bold text-gradient">WebMagic</h1>
          <p className="text-sm text-text-secondary mt-1">Admin Dashboard</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-md py-md space-y-1 overflow-y-auto scrollbar-thin">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? 'nav-link-active' : 'nav-link')}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="px-md py-md border-t border-border space-y-2">
          <button
            onClick={toggleTheme}
            className="nav-link w-full"
            aria-label="Toggle theme"
          >
            {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            {theme === 'light' ? 'Dark Mode' : 'Light Mode'}
          </button>

          <div className="px-md py-sm rounded-md bg-background-secondary">
            <p className="text-sm font-medium text-text-primary truncate">
              {user?.full_name || user?.email}
            </p>
            <p className="text-xs text-text-secondary truncate">{user?.email}</p>
          </div>

          <button onClick={logout} className="nav-link w-full text-error hover:bg-error/10">
            <LogOut className="w-5 h-5" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto scrollbar-thin">
        <Outlet />
      </main>
    </div>
  )
}
