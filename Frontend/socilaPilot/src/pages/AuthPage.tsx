import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../services/api'
import type { AuthUser } from '../types'

type AuthPageProps = {
  onAuthenticated: (token: string, user: AuthUser) => void
}

export function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setMessage('')
    try {
      if (mode === 'register') {
        const result = await api<{ message: string }>('/auth/register', {
          method: 'POST',
          body: JSON.stringify({ email, display_name: displayName, password }),
        })
        setMessage(result.message)
        setMode('login')
        return
      }
      const result = await api<{
        access_token: string
        user: AuthUser
      }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      onAuthenticated(result.access_token, result.user)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Authentication failed.')
    } finally {
      setLoading(false)
    }
  }

  const resendVerification = async () => {
    setLoading(true)
    setError('')
    setMessage('')
    try {
      const result = await api<{ message: string }>('/auth/resend-verification', {
        method: 'POST',
        body: JSON.stringify({ email }),
      })
      setMessage(result.message)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not resend email.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#080d18] px-5 py-12 text-slate-100">
      <section className="w-full max-w-md rounded-2xl border border-white/10 bg-[#101827] p-7 shadow-2xl sm:p-9">
        <a href="/" className="font-display text-xl font-bold tracking-tight text-white">
          social<span className="text-indigo-300">pilot</span>
        </a>
        <p className="mt-2 text-sm text-slate-400">Your project work, your community.</p>
        <div className="mt-7 grid grid-cols-2 rounded-lg bg-black/20 p-1 text-sm">
          {(['login', 'register'] as const).map((nextMode) => (
            <button
              key={nextMode}
              type="button"
              onClick={() => { setMode(nextMode); setError(''); setMessage('') }}
              className={`rounded-md px-3 py-2 capitalize ${mode === nextMode ? 'bg-indigo-400/15 text-indigo-100' : 'text-slate-500'}`}
            >
              {nextMode}
            </button>
          ))}
        </div>
        <form className="mt-6 space-y-4" onSubmit={submit}>
          {mode === 'register' && (
            <label className="block text-sm text-slate-300">
              Display name
              <input
                required
                maxLength={100}
                autoComplete="name"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                className="mt-1.5 w-full rounded-lg border border-white/10 bg-[#0a101d] px-3 py-2.5 text-white outline-none focus:border-indigo-300/50"
              />
            </label>
          )}
          <label className="block text-sm text-slate-300">
            Email
            <input
              required
              type="email"
              maxLength={254}
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1.5 w-full rounded-lg border border-white/10 bg-[#0a101d] px-3 py-2.5 text-white outline-none focus:border-indigo-300/50"
            />
          </label>
          <label className="block text-sm text-slate-300">
            Password
            <input
              required
              type="password"
              minLength={mode === 'register' ? 12 : 1}
              maxLength={128}
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1.5 w-full rounded-lg border border-white/10 bg-[#0a101d] px-3 py-2.5 text-white outline-none focus:border-indigo-300/50"
            />
            {mode === 'register' && <span className="mt-1 block text-xs text-slate-500">Use at least 12 characters.</span>}
          </label>
          {error && <p role="alert" className="rounded-lg border border-rose-400/20 bg-rose-400/5 p-3 text-sm text-rose-200">{error}</p>}
          {message && <p role="status" className="rounded-lg border border-emerald-300/20 bg-emerald-300/5 p-3 text-sm text-emerald-200">{message}</p>}
          <button
            disabled={loading}
            className="w-full rounded-lg bg-indigo-300 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-indigo-200 disabled:opacity-50"
          >
            {loading ? 'Please wait…' : mode === 'register' ? 'Create account' : 'Sign in'}
          </button>
        </form>
        {mode === 'login' && (
          <button
            type="button"
            disabled={loading || !email}
            onClick={resendVerification}
            className="mt-4 w-full text-center text-xs text-slate-500 hover:text-indigo-200 disabled:opacity-40"
          >
            Resend verification email
          </button>
        )}
        <p className="mt-6 text-center text-xs leading-5 text-slate-600">
          Sign in to manage projects, share updates, and prepare testnet tips.
        </p>
      </section>
    </main>
  )
}
