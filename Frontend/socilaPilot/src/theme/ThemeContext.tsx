import { createContext, useContext } from 'react'
import type { ReactNode } from 'react'
import { useTheme } from '../hooks/useTheme'
import type { Theme } from '../hooks/useTheme'

type ThemeState = { theme: Theme; toggle: () => void }
const ThemeContext = createContext<ThemeState | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, toggle] = useTheme()
  return <ThemeContext.Provider value={{ theme, toggle }}>{children}</ThemeContext.Provider>
}

export function useAppTheme(): ThemeState {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useAppTheme must be used inside <ThemeProvider>')
  return ctx
}
