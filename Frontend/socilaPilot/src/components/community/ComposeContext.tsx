import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Composer } from './Composer'
import type { ComposerSeed } from './Composer'
import { useFlash } from '../Flash'

type ComposeState = { openComposer: (seed?: ComposerSeed) => void }
const ComposeContext = createContext<ComposeState | null>(null)

/** Lets any page open the post composer in a dialog, optionally pre-filled (e.g. from the studio). */
export function ComposeProvider({ children }: { children: ReactNode }) {
  const [seed, setSeed] = useState<ComposerSeed | null>(null)
  const navigate = useNavigate()
  const flash = useFlash()
  const openComposer = useCallback((next: ComposerSeed = {}) => setSeed(next), [])
  const value = useMemo(() => ({ openComposer }), [openComposer])
  return (
    <ComposeContext.Provider value={value}>
      {children}
      {seed && (
        <div className="dc-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSeed(null) }}>
          <div className="dc-modal dc-modal-wide" role="dialog" aria-modal="true" aria-label="Write a post">
            <button className="dc-modal-close" onClick={() => setSeed(null)} aria-label="Close"><X size={18} /></button>
            <Composer
              seed={seed}
              autoFocus
              onPosted={(post) => {
                setSeed(null)
                flash.showNotice('Your post is live.')
                navigate(`/app/post/${post.post_id}`)
              }}
            />
          </div>
        </div>
      )}
    </ComposeContext.Provider>
  )
}

export function useCompose(): ComposeState {
  const ctx = useContext(ComposeContext)
  if (!ctx) throw new Error('useCompose must be used inside <ComposeProvider>')
  return ctx
}
