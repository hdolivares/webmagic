/**
 * Authentication hook
 */
import { create } from 'zustand'
import { api } from '@/services/api'
import type { User, LoginCredentials } from '@/types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
  clearError: () => void
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  login: async (credentials) => {
    set({ isLoading: true, error: null })
    try {
      await api.login(credentials)
      const user = await api.getCurrentUser()
      set({ user, isAuthenticated: true, isLoading: false })
    } catch (error: any) {
      let errorMessage = 'Login failed'
      
      // Handle different error response formats
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        // If detail is an array of validation errors
        if (Array.isArray(detail)) {
          errorMessage = detail.map((err: any) => err.msg).join(', ')
        } else if (typeof detail === 'string') {
          errorMessage = detail
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail)
        }
      } else if (error.message) {
        errorMessage = error.message
      }
      
      // Clear any existing token and reset auth state
      localStorage.removeItem('access_token')
      set({
        error: errorMessage,
        isLoading: false,
        isAuthenticated: false,
        user: null,
      })
      throw error
    }
  },

  logout: () => {
    api.logout()
    set({ user: null, isAuthenticated: false })
  },

  fetchUser: async () => {
    set({ isLoading: true })
    try {
      const user = await api.getCurrentUser()
      set({ user, isAuthenticated: true, isLoading: false })
    } catch (error) {
      set({ isAuthenticated: false, isLoading: false })
    }
  },

  clearError: () => set({ error: null }),
}))
