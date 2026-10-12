import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

type FlashState = {
  error: string
  notice: string
  showError: (message: string) => void
  showNotice: (message: string) => void
  clear: () => void
}

const FlashContext = createContext<FlashState | null>(null)

/** Page-level success/error messages, shown at the top of the workspace. */
export function FlashProvider({ children }: { children: ReactNode }) {
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const showError = useCallback((message: string) => { setNotice(''); setError(message) }, [])
  const showNotice = useCallback((message: string) => { setError(''); setNotice(message) }, [])
  const clear = useCallback(() => { setError(''); setNotice('') }, [])
  const value = useMemo(() => ({ error, notice, showError, showNotice, clear }), [error, notice, showError, showNotice, clear])
  return <FlashContext.Provider value={value}>{children}</FlashContext.Provider>
}

export function useFlash(): FlashState {
  const ctx = useContext(FlashContext)
  if (!ctx) throw new Error('useFlash must be used inside <FlashProvider>')
  return ctx
}

export function FlashMessages() {
  const { error, notice, clear } = useFlash()
  return (
    <>
      {error && (
        <div className="feedback error-feedback" role="alert">
          <span>!</span>
          <div><strong>Something needs attention</strong><p>{error.replace(/^"|"$/g, '')}</p></div>
          <button onClick={clear} aria-label="Dismiss error">×</button>
        </div>
      )}
      {notice && (
        <div className="feedback success-feedback" role="status">
          <span>✓</span><p>{notice}</p>
          <button onClick={clear} aria-label="Dismiss message">×</button>
        </div>
      )}
    </>
  )
}
