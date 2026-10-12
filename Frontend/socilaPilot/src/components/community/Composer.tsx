import { useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Bold, Code2, FileCode2, Link2, Send, Sparkles, Tag, Wand2, X } from 'lucide-react'
import { useCurrentUser } from '../../auth/AuthContext'
import { useCreatePost } from '../../hooks/usePosts'
import { useJobs } from '../../jobs/JobsProvider'
import { errorMessage } from '../../lib/format'
import { api } from '../../services/api'
import type { CommunityPostDraft, Post, ProjectSummary } from '../../types'
import { Markdown } from '../Markdown'
import { Avatar } from './bits'

export const MAX_POST = 8000
const MAX_TAGS = 5
const STYLES = [
  { id: 'show_and_tell', label: 'Show & tell' },
  { id: 'devlog', label: 'Devlog' },
  { id: 'til', label: 'TIL' },
  { id: 'ask', label: 'Ask the community' },
] as const
const GOALS = [
  { id: 'clarity', label: 'Clearer' },
  { id: 'concise', label: 'Shorter' },
  { id: 'friendly', label: 'Friendlier' },
  { id: 'technical', label: 'More technical' },
] as const

export type ComposerSeed = {
  body?: string
  tags?: string[]
  projectId?: string
  projectName?: string
  /** 'case_study', 'community_post' or 'linkedin:<angle>' - enables the evidence badge. */
  artifactRef?: string
}

const cleanTag = (value: string) => value.trim().replace(/^#/, '').toLowerCase().replace(/[^a-z0-9+#._-]/g, '')

export function Composer({ seed, autoFocus, compact, onPosted }: {
  seed?: ComposerSeed
  autoFocus?: boolean
  compact?: boolean
  onPosted?: (post: Post) => void
}) {
  const user = useCurrentUser()
  const jobs = useJobs()
  const create = useCreatePost()
  const area = useRef<HTMLTextAreaElement>(null)
  const [body, setBody] = useState(seed?.body ?? '')
  const [seedBody] = useState(seed?.body ?? '')
  const [tags, setTags] = useState<string[]>(seed?.tags ?? [])
  const [tagInput, setTagInput] = useState('')
  const [link, setLink] = useState('')
  const [showLink, setShowLink] = useState(false)
  const [tab, setTab] = useState<'write' | 'preview'>('write')
  const [project, setProject] = useState(seed?.projectId ? { id: seed.projectId, name: seed.projectName ?? 'Project', ref: seed.artifactRef } : null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [suggestion, setSuggestion] = useState<{ text: string; notes: string[] } | null>(null)
  const [goal, setGoal] = useState<(typeof GOALS)[number]['id']>('clarity')
  const [style, setStyle] = useState<(typeof STYLES)[number]['id']>('show_and_tell')
  const [draftProject, setDraftProject] = useState('')
  const [reviewWarning, setReviewWarning] = useState(false)

  const projects = useQuery({ queryKey: ['projects'], queryFn: () => api<ProjectSummary[]>('/projects') })
  // The evidence badge describes the AI draft; once the text is edited it no longer applies.
  const evidenceApplies = Boolean(project?.ref) && body === seedBody && seedBody !== ''
  const trimmed = body.trim()
  const canPost = trimmed.length > 0 && body.length <= MAX_POST && !create.isPending && !busy

  const insert = (before: string, after = before, placeholder = 'text') => {
    const el = area.current
    if (!el) return
    const { selectionStart: start, selectionEnd: end } = el
    const selected = body.slice(start, end) || placeholder
    const next = `${body.slice(0, start)}${before}${selected}${after}${body.slice(end)}`
    setBody(next)
    requestAnimationFrame(() => { el.focus(); el.setSelectionRange(start + before.length, start + before.length + selected.length) })
  }

  const addTag = (raw: string) => {
    // Pasted text like "a, #b c" becomes three tags.
    const next = [...tags]
    for (const piece of raw.split(/[\s,]+/)) {
      const tag = cleanTag(piece)
      if (tag && !next.includes(tag) && next.length < MAX_TAGS) next.push(tag)
    }
    setTags(next)
    setTagInput('')
  }

  const runAi = async (label: string, task: () => Promise<void>) => {
    setError('')
    setBusy(label)
    try { await task() } catch (cause) { setError(errorMessage(cause)) } finally { setBusy('') }
  }

  const improve = () => runAi('improve', async () => {
    const job = await jobs.run<{ text: string; notes: string[] }>(
      { kind: 'improve_post', text: body, goal }, { label: 'Improving your draft' })
    setSuggestion(job.result)
  })

  const suggestTags = () => runAi('tags', async () => {
    const job = await jobs.run<{ tags: string[] }>({ kind: 'suggest_tags', text: body }, { label: 'Suggesting tags' })
    const merged = [...tags]
    for (const tag of job.result?.tags ?? []) if (!merged.includes(tag) && merged.length < MAX_TAGS) merged.push(tag)
    setTags(merged)
  })

  const draftFromProject = () => runAi('draft', async () => {
    const chosen = projects.data?.find((p) => p.project_id === draftProject)
    if (!chosen) throw new Error('Choose a project to draft from.')
    const job = await jobs.run<{ artifact: CommunityPostDraft }>(
      { kind: 'community_post', project_id: chosen.project_id, style }, { label: `Drafting a post about ${chosen.name}` })
    const draft = job.result?.artifact
    if (!draft) throw new Error('The AI returned no draft.')
    setBody(draft.body)
    setTags(draft.tags.slice(0, MAX_TAGS))
    setProject({ id: chosen.project_id, name: chosen.name, ref: 'community_post' })
    setReviewWarning(draft.review_status !== 'preliminary_support')
    setSuggestion(null)
    setTab('write')
  })

  const publish = () => {
    if (!canPost) return
    setError('')
    create.mutate({
      body: trimmed,
      format: 'markdown',
      tags,
      link_url: link.trim() || null,
      project_id: project?.id ?? null,
      artifact_ref: evidenceApplies ? project?.ref ?? null : null,
    }, {
      onSuccess: (post) => {
        setBody(''); setTags([]); setLink(''); setProject(null); setSuggestion(null); setReviewWarning(false)
        onPosted?.(post)
      },
      onError: (cause) => setError(errorMessage(cause)),
    })
  }

  const remaining = MAX_POST - body.length
  const counter = useMemo(() => (remaining < 0 ? 'dc-count dc-count-over' : remaining < 400 ? 'dc-count dc-count-near' : 'dc-count'), [remaining])

  return (
    <section className={`dc-composer ${compact ? 'dc-composer-compact' : ''}`} aria-label="Write a post">
      <div className="dc-composer-head">
        <Avatar name={user.display_name} size={36} />
        <div className="dc-tabs-inline" role="tablist" aria-label="Editor mode">
          <button role="tab" aria-selected={tab === 'write'} onClick={() => setTab('write')}>Write</button>
          <button role="tab" aria-selected={tab === 'preview'} onClick={() => setTab('preview')}>Preview</button>
        </div>
        <div className="dc-toolbar" aria-label="Formatting">
          <button type="button" onClick={() => insert('**')} aria-label="Bold" title="Bold"><Bold size={15} /></button>
          <button type="button" onClick={() => insert('`')} aria-label="Inline code" title="Inline code"><Code2 size={15} /></button>
          <button type="button" onClick={() => insert('\n```ts\n', '\n```\n', 'code')} aria-label="Code block" title="Code block"><FileCode2 size={15} /></button>
          <button type="button" onClick={() => setShowLink((v) => !v)} aria-label="Attach link" aria-pressed={showLink} title="Attach link"><Link2 size={15} /></button>
        </div>
      </div>

      {tab === 'write' ? (
        <textarea
          ref={area}
          className="dc-textarea"
          value={body}
          autoFocus={autoFocus}
          rows={compact ? 4 : 8}
          aria-label="Post text (Markdown supported)"
          placeholder={'What are you building or learning? Markdown and ```code``` blocks are supported.'}
          onChange={(event) => setBody(event.target.value)}
          onKeyDown={(event) => { if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') publish() }}
        />
      ) : (
        <div className="dc-preview">{trimmed ? <Markdown>{body}</Markdown> : <p className="dc-muted">Nothing to preview yet.</p>}</div>
      )}

      {showLink && (
        <input className="dc-input" type="url" value={link} maxLength={2048} placeholder="https://github.com/you/repo"
          aria-label="Link" onChange={(event) => setLink(event.target.value)} />
      )}

      <div className="dc-tag-editor">
        <Tag size={14} aria-hidden="true" />
        {tags.map((tag) => (
          <span key={tag} className="dc-chip">#{tag}<button type="button" onClick={() => setTags(tags.filter((t) => t !== tag))} aria-label={`Remove tag ${tag}`}><X size={12} /></button></span>
        ))}
        {tags.length < MAX_TAGS && (
          <input
            value={tagInput}
            aria-label="Add tag"
            placeholder={tags.length ? 'Add tag' : 'Add up to 5 tags (python, fastapi…)'}
            onChange={(event) => setTagInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ',' || event.key === ' ') { event.preventDefault(); addTag(tagInput) }
              if (event.key === 'Backspace' && !tagInput && tags.length) setTags(tags.slice(0, -1))
            }}
            onBlur={() => tagInput && addTag(tagInput)}
          />
        )}
      </div>

      {project && (
        <div className="dc-attached">
          <span>Linked project: <strong>{project.name}</strong></span>
          {evidenceApplies
            ? <small>An evidence badge from this draft will be attached.</small>
            : project.ref && <small>Edited since drafting — the evidence badge will be left off.</small>}
          <button type="button" onClick={() => setProject(null)} aria-label="Remove linked project"><X size={13} /></button>
        </div>
      )}
      {reviewWarning && (
        <p className="dc-warn" role="status"><AlertTriangle size={14} aria-hidden="true" /> Some statements in this draft were not matched to your project sources. Review them before publishing.</p>
      )}

      {suggestion && (
        <div className="dc-suggestion" role="region" aria-label="AI suggestion">
          <strong><Wand2 size={14} aria-hidden="true" /> Suggested version</strong>
          <Markdown>{suggestion.text}</Markdown>
          {suggestion.notes.length > 0 && <ul>{suggestion.notes.map((note) => <li key={note}>{note}</li>)}</ul>}
          <div className="dc-row">
            <button type="button" className="dc-btn dc-btn-primary" onClick={() => { setBody(suggestion.text); setSuggestion(null) }}>Use this</button>
            <button type="button" className="dc-btn" onClick={() => setSuggestion(null)}>Keep mine</button>
          </div>
        </div>
      )}

      {error && <p role="alert" className="dc-error">{error}</p>}

      <div className="dc-composer-foot">
        <div className="dc-ai">
          <select aria-label="Project to draft from" value={draftProject} onChange={(event) => setDraftProject(event.target.value)}>
            <option value="">Draft from project…</option>
            {projects.data?.map((p) => <option key={p.project_id} value={p.project_id}>{p.name}</option>)}
          </select>
          {draftProject && (
            <select aria-label="Draft style" value={style} onChange={(event) => setStyle(event.target.value as typeof style)}>
              {STYLES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          )}
          <button type="button" className="dc-btn" disabled={!draftProject || Boolean(busy)} onClick={draftFromProject}>
            <Sparkles size={14} aria-hidden="true" /> {busy === 'draft' ? 'Drafting…' : 'Draft'}
          </button>
          <span className="dc-sep" aria-hidden="true" />
          <select aria-label="Improvement goal" value={goal} onChange={(event) => setGoal(event.target.value as typeof goal)}>
            {GOALS.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
          </select>
          <button type="button" className="dc-btn" disabled={!trimmed || Boolean(busy)} onClick={improve}>
            <Wand2 size={14} aria-hidden="true" /> {busy === 'improve' ? 'Improving…' : 'Improve'}
          </button>
          <button type="button" className="dc-btn" disabled={!trimmed || Boolean(busy)} onClick={suggestTags}>
            <Tag size={14} aria-hidden="true" /> {busy === 'tags' ? 'Finding…' : 'Suggest tags'}
          </button>
        </div>
        <div className="dc-publish">
          <span className={counter} aria-live="polite">{remaining.toLocaleString()}</span>
          <button type="button" className="dc-btn dc-btn-primary" disabled={!canPost} onClick={publish} title="Publish (Ctrl/⌘ + Enter)">
            <Send size={14} aria-hidden="true" /> {create.isPending ? 'Publishing…' : 'Publish'}
          </button>
        </div>
      </div>
    </section>
  )
}
