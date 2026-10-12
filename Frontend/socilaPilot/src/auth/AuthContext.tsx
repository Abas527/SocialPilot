import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, hasAccessToken, setAccessToken, setUnauthorizedHandler } from '../services/api'
import type { AuthUser } from '../types'

type AuthState = {
  user: AuthUser | null
  checking: boolean
  signIn: (token: string, user: AuthUser) => void
  signOut: () => Promise<void>
  updateUser: (patch: Partial<AuthUser>) => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [checking, setChecking] = useState(hasAccessToken())

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null)
      queryClient.clear()
    })
    return () => setUnauthorizedHandler(null)
  }, [queryClient])

  useEffect(() => {
    if (!hasAccessToken()) return
    let cancelled = false
    api<AuthUser>('/auth/me')
      .then((me) => { if (!cancelled) setUser(me) })
      .catch(() => setAccessToken(null))
      .finally(() => { if (!cancelled) setChecking(false) })
    return () => { cancelled = true }
  }, [])

  const signIn = useCallback((token: string, next: AuthUser) => {
    setAccessToken(token)
    queryClient.clear()
    setUser(next)
  }, [queryClient])

  const signOut = useCallback(async () => {
    try {
      await api<void>('/auth/logout', { method: 'POST' })
    } catch {
      // The token is cleared locally even if the API is unreachable; it expires server-side.
    } finally {
      setAccessToken(null)
      queryClient.clear()
      setUser(null)
    }
  }, [queryClient])

  const updateUser = useCallback((patch: Partial<AuthUser>) => {
    setUser((current) => (current ? { ...current, ...patch } : current))
  }, [])

  const value = useMemo(() => ({ user, checking, signIn, signOut, updateUser }), [user, checking, signIn, signOut, updateUser])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

export function useCurrentUser(): AuthUser {
  const { user } = useAuth()
  if (!user) throw new Error('useCurrentUser requires a signed-in user')
  return user
}
