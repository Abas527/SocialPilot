import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BadgeCheck, Copy, ExternalLink, FileCheck2, Share2, ShieldAlert, ShieldCheck, Trash2, X } from 'lucide-react'
import { errorMessage, timeAgo } from '../../lib/format'
import {
  useCheckOwnership, useOwnership, usePublications, useShareCaseStudy, useStartOwnership, useUnpublish,
} from '../../services/publications'
import type { OwnershipStart, ProjectDetail } from '../../types'
import { useFlash } from '../Flash'

const isRepoBacked = (project: ProjectDetail) => Boolean(project.repository_url && project.commit_sha)

/** Optional proof that the author controls the GitHub repository (a challenge file in the repo). */
export function OwnershipBox({ project }: { project: ProjectDetail }) {
  const ownership = useOwnership(project.project_id, isRepoBacked(project))
  const start = useStartOwnership(project.project_id)
  const check = useCheckOwnership(project.project_id)
  const [challenge, setChallenge] = useState<OwnershipStart | null>(null)
  const [message, setMessage] = useState('')
  if (!isRepoBacked(project)) return null
  if (ownership.data?.verified) {
    return <p className="dc-ok dc-ownership"><BadgeCheck size={15} aria-hidden="true" /> You verified ownership of this repository. Readers see a “verified owner” badge.</p>
  }
  return (
    <div className="dc-ownership-box">
      <p><ShieldAlert size={15} aria-hidden="true" /><span><strong>Prove this is your repository (recommended).</strong> Without it, readers are told ownership is unverified.</span></p>
      {!challenge && (
        <button className="dc-btn" disabled={start.isPending}
          onClick={() => start.mutate(undefined, { onSuccess: setChallenge, onError: (e) => setMessage(errorMessage(e)) })}>
          {start.isPending ? 'Preparing…' : 'Start verification'}
        </button>
      )}
      {challenge && (
        <div className="dc-challenge">
          <p>{challenge.instructions}</p>
          <code className="dc-token">{challenge.token}</code>
          <div className="dc-row">
            <button className="dc-btn" onClick={() => void navigator.clipboard?.writeText(challenge.token)}><Copy size={14} aria-hidden="true" /> Copy token</button>
            <button className="dc-btn dc-btn-primary" disabled={check.isPending}
              onClick={() => { setMessage(''); check.mutate(undefined, { onError: (e) => setMessage(errorMessage(e)) }) }}>
              {check.isPending ? 'Checking GitHub…' : 'I added it — check now'}
            </button>
          </div>
        </div>
      )}
      {message && <p role="alert" className="dc-error">{message}</p>}
    </div>
  )
}

export function ShareCaseStudyDialog({ project, onClose }: { project: ProjectDetail; onClose: () => void }) {
  const navigate = useNavigate()
  const flash = useFlash()
  const share = useShareCaseStudy(project.project_id)
  const [note, setNote] = useState('')
  const [tags, setTags] = useState('')
  const [agree, setAgree] = useState(false)
  const [error, setError] = useState('')
  const repo = isRepoBacked(project)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setError('')
    share.mutate({ note: note.trim(), tags: tags.split(/[\s,]+/).map((t) => t.replace(/^#/, '').toLowerCase()).filter(Boolean).slice(0, 5) }, {
      onSuccess: ({ post }) => { onClose(); flash.showNotice('Case study shared with its evidence.'); navigate(`/app/post/${post.post_id}`) },
      onError: (cause) => setError(errorMessage(cause)),
    })
  }

  return (
    <div className="dc-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <form className="dc-modal dc-share" role="dialog" aria-modal="true" aria-label="Share case study" onSubmit={submit}>
        <button type="button" className="dc-modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
        <h2><Share2 size={18} aria-hidden="true" /> Share this case study</h2>
        <p className="dc-muted">We post a short version to the Community feed and create a public <strong>evidence page</strong>: the full text, with every statement linked to the source text behind it.</p>

        <div className={`dc-share-trust ${repo ? 'is-repo' : 'is-notes'}`}>
          {repo ? <ShieldCheck size={18} aria-hidden="true" /> : <ShieldAlert size={18} aria-hidden="true" />}
          <span>{repo
            ? <>Readers will see: <strong>Repository-backed</strong>. Claims link to exact lines of {project.repository_url?.replace('https://github.com/', '')} at a pinned commit, and anyone can re-check them on GitHub.</>
            : <>Readers will see: <strong>Self-reported</strong>. This project came from pasted notes, so it cannot be independently checked. Import a GitHub repository to make it verifiable.</>}</span>
        </div>
        <OwnershipBox project={project} />

        <label className="dc-field"><span>Add a note (optional)</span>
          <textarea className="dc-textarea" rows={3} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} placeholder="What should people look at first?" /></label>
        <label className="dc-field"><span>Tags (up to 5)</span>
          <input className="dc-input" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="python, fastapi, remote" /></label>

        <label className="dc-check">
          <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
          <span>I understand the evidence page is <strong>public to anyone with the link</strong> and shows short excerpts from my project sources. I can unpublish it at any time.</span>
        </label>
        {error && <p role="alert" className="dc-error">{error}</p>}
        <div className="dc-row dc-end">
          <button type="button" className="dc-btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="dc-btn dc-btn-primary" disabled={!agree || share.isPending}>{share.isPending ? 'Checking evidence…' : 'Share with evidence'}</button>
        </div>
      </form>
    </div>
  )
}

/** What this project has published, with copyable public links and an unpublish button. */
export function PublicationsList({ project }: { project: ProjectDetail }) {
  const list = usePublications(project.project_id)
  const unpublish = useUnpublish(project.project_id)
  const flash = useFlash()
  const items = (list.data ?? []).filter((p) => !p.revoked)
  if (!items.length) return null
  const copy = (id: string) => {
    void navigator.clipboard?.writeText(`${window.location.origin}/p/${id}`)
    flash.showNotice('Public evidence link copied. Anyone with it can open the page, no login needed.')
  }
  return (
    <section className="dc-card dc-publications" aria-label="Published evidence pages">
      <h2><FileCheck2 size={15} aria-hidden="true" /> Published evidence pages</h2>
      <ul>
        {items.map((p) => (
          <li key={p.publication_id}>
            <div>
              <Link to={`/p/${p.publication_id}`}>{p.title || (p.kind === 'case_study' ? 'Case study' : 'Post')}</Link>
              <small>{p.kind === 'case_study' ? 'Case study' : 'Post'} · {p.supported} of {p.total} claims backed · {p.trust_level === 'repository' ? 'repository-backed' : 'self-reported'} · {timeAgo(p.created_at)}</small>
            </div>
            <div className="dc-row">
              <button className="dc-icon-btn" onClick={() => copy(p.publication_id)} aria-label="Copy public link" title="Copy public link"><Copy size={15} /></button>
              <Link className="dc-icon-btn" to={`/p/${p.publication_id}`} aria-label="Open public page" title="Open public page"><ExternalLink size={15} /></Link>
              <button className="dc-icon-btn danger" aria-label="Unpublish" title="Unpublish (removes the public page and the feed post)"
                disabled={unpublish.isPending}
                onClick={() => { if (window.confirm('Unpublish this? The public page stops working and the post is removed from the feed.')) unpublish.mutate(p.publication_id, { onError: (e) => flash.showError(errorMessage(e)) }) }}>
                <Trash2 size={15} /></button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
