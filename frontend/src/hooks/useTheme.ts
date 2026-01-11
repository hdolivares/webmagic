/**
 * Theme management hook
 * Handles light/dark mode toggling
 */
import { create } from 'zustand'
import { useEffect } from 'react'

type Theme = 'light' | 'dark'

interface ThemeState {
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
}

export const useTheme = create<ThemeState>((set) => ({
  theme: (localStorage.getItem('theme') as Theme) || 'light',

  toggleTheme: () =>
    set((state) => {
      const newTheme = state.theme === 'light' ? 'dark' : 'light'
      localStorage.setItem('theme', newTheme)
      return { theme: newTheme }
    }),

  setTheme: (theme) => {
    localStorage.setItem('theme', theme)
    set({ theme })
  },
}))

/**
 * Hook to apply theme to document
 */
export const useApplyTheme = () => {
  const theme = useTheme((state) => state.theme)

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }, [theme])
}
