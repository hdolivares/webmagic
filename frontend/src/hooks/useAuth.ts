/**
 * Authentication hook
 */
import { create } from 'zustand'
import { api } from '@/services/api'
import type { User, LoginCredentials } from '@/types'

interface AuthState {
  user: User | null
  userType: 'admin' | 'customer' | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (credentials: LoginCredentials) => Promise<void>
  unifiedLogin: (credentials: LoginCredentials) => Promise<'admin' | 'customer'>
  logout: () => void
  fetchUser: () => Promise<void>
  clearError: () => void
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  userType: (localStorage.getItem('user_type') as 'admin' | 'customer' | null),
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
        userType: null,
      })
      throw error
    }
  },

  unifiedLogin: async (credentials) => {
    set({ isLoading: true, error: null })
    try {
      const response = await api.unifiedLogin(credentials)
      
      // Fetch user profile based on user type
      let userProfile
      if (response.user_type === 'customer') {
        userProfile = await api.getCurrentCustomer()
      } else {
        userProfile = await api.getCurrentUser()
      }
      
      set({ 
        user: userProfile, 
        userType: response.user_type,
        isAuthenticated: true, 
        isLoading: false 
      })
      return response.user_type
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
      localStorage.removeItem('user_type')
      localStorage.removeItem('user')
      set({
        error: errorMessage,
        isLoading: false,
        isAuthenticated: false,
        user: null,
        userType: null,
      })
      throw error
    }
  },

  logout: () => {
    api.logout()
    localStorage.removeItem('user_type')
    localStorage.removeItem('user')
    set({ user: null, userType: null, isAuthenticated: false })
  },

  fetchUser: async () => {
    set({ isLoading: true })
    try {
      const userType = localStorage.getItem('user_type') as 'admin' | 'customer' | null
      let user
      
      if (userType === 'customer') {
        user = await api.getCurrentCustomer()
      } else {
        user = await api.getCurrentUser()
      }
      
      set({ user, userType, isAuthenticated: true, isLoading: false })
    } catch (error) {
      set({ isAuthenticated: false, isLoading: false, userType: null })
    }
  },

  clearError: () => set({ error: null }),
}))
