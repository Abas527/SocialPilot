import { useEffect, useState } from 'react'
import { ClaimSummary } from '../components/ClaimSummary'
import { PageHeading } from '../components/PageHeading'
import {
  LINKEDIN_ANGLES,
  LINKEDIN_FORMATS,
  type EvidenceClaim,
  type LinkedInAngle,
  type LinkedInDraft,
  type LinkedInFormat,
  type ProjectDetail,
} from '../types'

type StudioMode = 'linkedin' | 'readme'

function formatLinkedInDraft(draft: LinkedInDraft, format: LinkedInFormat): string {
  const paragraphs = {
    standard: [draft.hook, draft.insight, draft.body, draft.takeaway, draft.question],
    concise: [draft.hook, draft.body, draft.takeaway, draft.question],
    technical_walkthrough: [
      draft.hook,
      draft.insight && `The engineering detail: ${draft.insight}`,
      draft.body,
      draft.takeaway,
      draft.question,
    ],
    project_update: [
      draft.hook,
      `Project update:\n${draft.body}`,
      draft.takeaway && `What I learned:\n${draft.takeaway}`,
      draft.question,
    ],
  } satisfies Record<LinkedInFormat, (string | null | undefined | false)[]>

  return paragraphs[format]
    .filter((paragraph): paragraph is string => typeof paragraph === 'string' && Boolean(paragraph.trim()))
    .join('\n\n')
}

function buildReadmeDraft(project: ProjectDetail): string {
  const findings = (project.profile?.findings ?? [])
    .filter((finding) => finding.status === 'supported' && finding.evidence.length > 0)
  const section = (title: string, kinds: string[]) => {
    const rows = findings.filter((finding) => kinds.includes(finding.kind))
    if (!rows.length) return []
    return [
      `## ${title}`,
      '',
      ...rows.map((finding) => `- ${finding.text}`),
      '',
    ]
  }
  const sources = [...new Map(findings.flatMap((finding) => finding.evidence.map((item) => [
    `${item.path}:${item.start_line ?? ''}:${item.end_line ?? ''}`,
    item,
  ]))).values()]
  const overview = project.profile?.summary.trim()
  const sections = [
    `# ${project.name}`,
    '',
    ...(project.repository_url ? [`[Source repository](${project.repository_url})`, ''] : []),
    ...section('Overview', ['summary']),
    ...(!findings.some((finding) => finding.kind === 'summary') && overview ? [overview, ''] : []),
    ...section('Problem addressed', ['problem']),
    ...section('Technology stack', ['technology']),
    ...section('Architecture', ['architecture']),
    ...section('Implementation decisions', ['decision']),
    ...section('Engineering details', ['challenge', 'limitation']),
    ...section('Results', ['result']),
    ...(sources.length ? [
      '## Source references',
      '',
      ...sources.map(({ path, start_line, end_line, source_url }) => {
        const lineRange = start_line && end_line ? `, lines ${start_line}-${end_line}` : ''
        const label = `\`${path}${lineRange}\``
        return `- ${source_url ? `[${label}](${source_url})` : label}`
      }),
      '',
    ] : []),
    '## Setup and usage',
    '',
    '<!-- Add installation steps, prerequisites, and examples verified by the project maintainer. -->',
    '',
  ]
  return sections.join('\n')
}

type ContentStudioPageProps = {
  project: ProjectDetail
  angle: LinkedInAngle
  format: LinkedInFormat
  onFormatChange: (format: LinkedInFormat) => void
  onAngleChange: (angle: LinkedInAngle) => void
  userContext: string
  onUserContextChange: (value: string) => void
  draft: LinkedInDraft | null
  claims: EvidenceClaim[]
  loading: boolean
  onGenerate: () => void
  onSave: (draft: LinkedInDraft) => void
  onShare: (body: string) => void
}

export function ContentStudioPage({
  project,
  angle,
  format,
  onFormatChange,
  onAngleChange,
  userContext,
  onUserContextChange,
  draft,
  claims,
  loading,
  onGenerate,
  onSave,
  onShare,
}: ContentStudioPageProps) {
  const [draftState, setDraftState] = useState({ source: draft, edited: draft })
  if (draftState.source !== draft) setDraftState({ source: draft, edited: draft })
  const editedDraft = draftState.source === draft ? draftState.edited : draft
  const setEditedDraft = (edited: LinkedInDraft | null) => setDraftState({ source: draft, edited })
  const [copyMessage, setCopyMessage] = useState('')
  const [draftView, setDraftView] = useState<'preview' | 'edit'>('preview')
  const [studioMode, setStudioMode] = useState<StudioMode>('linkedin')
  const [postStage, setPostStage] = useState<'setup' | 'review'>('setup')
  const readmeSource = JSON.stringify({
    projectId: project.project_id,
    profile: project.profile,
  })
  const [readmeState, setReadmeState] = useState(() => ({
    source: readmeSource,
    projectId: project.project_id,
    text: buildReadmeDraft(project),
    edited: false,
  }))
  if (readmeState.source !== readmeSource && (!readmeState.edited || readmeState.projectId !== project.project_id)) {
    setReadmeState({
      source: readmeSource,
      projectId: project.project_id,
      text: buildReadmeDraft(project),
      edited: false,
    })
  }
  const readmeDraft = readmeState.source === readmeSource
    || (readmeState.edited && readmeState.projectId === project.project_id)
    ? readmeState.text
    : buildReadmeDraft(project)
  const [readmeMessage, setReadmeMessage] = useState('')

  const shareText = editedDraft ? formatLinkedInDraft(editedDraft, format) : ''

  useEffect(() => {
    if (!draft) return
    const frame = window.requestAnimationFrame(() => setPostStage('review'))
    return () => window.cancelAnimationFrame(frame)
  }, [draft])

  const downloadReadme = () => {
    const blob = new Blob([readmeDraft], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${project.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'project'}-README.md`
    link.click()
    URL.revokeObjectURL(url)
    setReadmeMessage('README draft downloaded. Review placeholders before publishing.')
  }

  return (
    <div className="studio-page">
      <PageHeading
        eyebrow="CONTENT STUDIO"
        title="Make your work visible."
        subtitle={studioMode === 'readme'
          ? `Build a README draft for ${project.name} from confirmed source findings, then fill in the setup details.`
          : `Turn the evidence in ${project.name} into a post that reflects your role, decisions, and real contribution.`}
      />
      <div className="studio-mode-tabs" role="tablist" aria-label="Developer content type">
        <button id="linkedin-mode-tab" role="tab" aria-controls="linkedin-mode-panel" aria-selected={studioMode === 'linkedin'} className={studioMode === 'linkedin' ? 'selected' : ''} onClick={() => setStudioMode('linkedin')}>Posts</button>
        <button id="readme-mode-tab" role="tab" aria-controls="readme-mode-panel" aria-selected={studioMode === 'readme'} className={studioMode === 'readme' ? 'selected' : ''} onClick={() => setStudioMode('readme')}>README / docs</button>
      </div>
      {studioMode === 'readme' ? (
        <section id="readme-mode-panel" role="tabpanel" aria-labelledby="readme-mode-tab" className="panel readme-studio">
          <div className="readme-studio-heading">
            <div><span className="panel-kicker">SOURCE-GROUNDED TEMPLATE</span><h2>README draft</h2>
              <p>Confirmed details come from supported project findings. Setup and usage stay as prompts until you add verified instructions.</p>
            </div>
            <div className="readme-actions">
              <button className="button button-secondary" onClick={async () => {
                try {
                  await navigator.clipboard.writeText(readmeDraft)
                  setReadmeMessage('README draft copied.')
                } catch {
                  setReadmeMessage('Clipboard access is unavailable in this browser.')
                }
              }}>Copy Markdown</button>
              <button className="button button-primary" onClick={downloadReadme}>Download .md</button>
            </div>
          </div>
          <label className="sr-only" htmlFor="readme-draft">Edit README Markdown draft</label>
          <textarea id="readme-draft" className="readme-editor" value={readmeDraft} onChange={(event) => setReadmeState({
            source: readmeSource,
            projectId: project.project_id,
            text: event.target.value,
            edited: true,
          })} spellCheck={false} />
          <p className="readme-review-note">Review the linked source references and add maintainer-verified installation and usage instructions before publishing.</p>
          {readmeMessage && <p role="status" className="readme-status">{readmeMessage}</p>}
        </section>
      ) : (
      <div id="linkedin-mode-panel" role="tabpanel" aria-labelledby="linkedin-mode-tab" className={`studio-layout ${postStage === 'setup' ? 'studio-stage-setup' : 'studio-stage-review'}`}>
        <div className="studio-workflow-tabs" role="tablist" aria-label="Post workflow">
          <button id="post-setup-tab" type="button" role="tab" aria-controls="post-setup-panel" aria-selected={postStage === 'setup'} onClick={() => setPostStage('setup')}>
            <span>1</span><strong>Set up your post</strong><small>Choose angle and add context</small>
          </button>
          <button id="post-review-tab" type="button" role="tab" aria-controls="post-review-panel" aria-selected={postStage === 'review'} disabled={!editedDraft} onClick={() => setPostStage('review')}>
            <span>2</span><strong>Review &amp; share</strong><small>{editedDraft ? 'Edit, save, or share your draft' : 'Generate a draft to continue'}</small>
          </button>
        </div>
        <div id="post-setup-panel" role="tabpanel" aria-labelledby="post-setup-tab" className="studio-controls" hidden={postStage !== 'setup'}>
          <section className="panel angle-panel">
            <div className="section-title"><span className="step-number">01</span><div><h2>Choose your angle</h2><p>Every good post starts with a point of view.</p></div></div>
            <div className="angle-options">
              {LINKEDIN_ANGLES.map((option) => (
                <button
                  key={option.id}
                  className={`angle-option ${angle === option.id ? 'chosen' : ''}`}
                  onClick={() => onAngleChange(option.id)}
                >
                  <span className="angle-icon">{option.icon}</span>
                  <span><strong>{option.title}</strong><small>{option.description}</small></span>
                  <span className="radio-dot" />
                </button>
              ))}
            </div>
          </section>
          <section className="panel format-panel">
            <div className="section-title"><span className="step-number">02</span><div><h2>Choose a post format</h2><p>Reshape the generated story without changing its evidence review.</p></div></div>
            <div className="format-options">
              {LINKEDIN_FORMATS.map((option) => (
                <button
                  key={option.id}
                  className={`format-option ${format === option.id ? 'chosen' : ''}`}
                  aria-pressed={format === option.id}
                  onClick={() => onFormatChange(option.id)}
                >
                  <strong>{option.title}</strong><small>{option.description}</small>
                </button>
              ))}
            </div>
          </section>
          <section className="panel context-panel">
            <div className="section-title"><span className="step-number">03</span><div><h2>Add your perspective</h2><p>Your role and personal context help distinguish your contribution from the project itself.</p></div></div>
            <label className="sr-only" htmlFor="post-context">Your personal context</label>
            <textarea
              id="post-context"
              value={userContext}
              onChange={(event) => onUserContextChange(event.target.value)}
              placeholder="What was your role? What did you own or collaborate on? What was challenging, and what outcome can you substantiate?"
              rows={4}
            />
            <div className="context-note"><span>✦</span> Especially helpful for personal reflections.</div>
          </section>
          <button className="button button-primary generate-button" onClick={onGenerate} disabled={loading || !project.profile}>
            {loading ? <><span className="spinner" /> Writing your draft…</> : <>Generate post draft <span>→</span></>}
          </button>
          {!project.profile && <p className="prerequisite-note">Analyze the project from Overview before generating content.</p>}
        </div>

        <section id="post-review-panel" role="tabpanel" aria-labelledby="post-review-tab" className="panel draft-panel" hidden={postStage !== 'review'}>
          <div className="draft-panel-header">
            <div><span className="panel-kicker">AI-GENERATED DRAFT</span><h2>{editedDraft ? 'Ready for your review' : 'Your next post starts here'}</h2></div>
            <span className="linkedin-badge" aria-hidden="true">✦</span>
          </div>
          {editedDraft ? (
            <>
              <div className="draft-regenerate-row">
                <p>SocialPilot drafted the post from your project sources. Review and personalize before sharing.</p>
                <button className="button button-secondary" onClick={onGenerate} disabled={loading || !project.profile}>
                  {loading ? <><span className="spinner" /> Regenerating…</> : 'Regenerate with AI'}
                </button>
              </div>
              <div className="draft-view-tabs" role="tablist" aria-label="Post review mode">
                <button id="draft-preview-tab" type="button" role="tab" aria-controls="draft-preview-panel" aria-selected={draftView === 'preview'} onClick={() => setDraftView('preview')}>Preview post</button>
                <button id="draft-edit-tab" type="button" role="tab" aria-controls="draft-edit-panel" aria-selected={draftView === 'edit'} onClick={() => setDraftView('edit')}>Edit content</button>
              </div>
              {draftView === 'preview' ? (
                <div id="draft-preview-panel" role="tabpanel" aria-labelledby="draft-preview-tab" className="linkedin-live-preview">
                  <span className="linkedin-preview-author">{project.name}</span>
                  <p>{shareText}</p>
                  <small>Preview only · nothing is published until you share it</small>
                </div>
              ) : (
              <div id="draft-edit-panel" role="tabpanel" aria-labelledby="draft-edit-tab" className="draft-editor">
                <label>OPENING HOOK<input value={editedDraft.hook} onChange={(event) => setEditedDraft({ ...editedDraft, hook: event.target.value })} /></label>
                <label>KEY INSIGHT<input value={editedDraft.insight} onChange={(event) => setEditedDraft({ ...editedDraft, insight: event.target.value })} /></label>
                <label>POST BODY<textarea rows={10} value={editedDraft.body} onChange={(event) => setEditedDraft({ ...editedDraft, body: event.target.value })} /></label>
                <label>TAKEAWAY<input value={editedDraft.takeaway} onChange={(event) => setEditedDraft({ ...editedDraft, takeaway: event.target.value })} /></label>
                {editedDraft.question && <label>CLOSING QUESTION<input value={editedDraft.question} onChange={(event) => setEditedDraft({ ...editedDraft, question: event.target.value })} /></label>}
              </div>
              )}
              <div className={`review-status ${editedDraft.review_status === 'preliminary_support' ? 'review-status-supported' : ''}`}>
                <strong>{editedDraft.review_status === 'preliminary_support' ? 'Evidence review: preliminary support' : 'Evidence review: needs review'}</strong>
                <span>Use the citations below to review the draft. This check is a guide, not publication approval.</span>
              </div>
              {editedDraft.needs_user_input && (
                <div className="review-note"><span>✳</span><p><strong>Add your voice</strong><br />{editedDraft.needs_user_input}</p></div>
              )}
              <ClaimSummary claims={claims} />
              <div className="draft-actions">
                <span className="draft-help">Make it yours before sharing. {shareText.length}/2000 characters for Community.</span>
                <div className="flex flex-wrap gap-2">
                  <button className="button button-secondary" onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(shareText)
                      setCopyMessage('Draft copied.')
                    } catch {
                      setCopyMessage('Clipboard access is unavailable in this browser.')
                    }
                  }}>Copy draft</button>
                  <button className="button button-secondary" onClick={() => onShare(shareText)} disabled={loading || !shareText.trim() || shareText.length > 8000}>Share to Community</button>
                  <button className="button button-primary" onClick={() => onSave(editedDraft)} disabled={loading}>
                    {loading ? 'Saving…' : 'Save draft'}
                  </button>
                </div>
              </div>
              {copyMessage && <p role="status" className="mt-2 text-xs text-slate-500">{copyMessage}</p>}
            </>
          ) : (
            <div className="draft-placeholder">
              <div className="paper-art"><span>✦</span><i /><i /><i /><b>in</b></div>
              <strong>Your source-backed draft will appear here.</strong>
              <p>Pick an angle and generate a draft to get started.</p>
              <div className="placeholder-footer"><span>✓ Evidence checked</span><span>◷ Ready to edit</span></div>
            </div>
          )}
        </section>
      </div>
      )}
    </div>
  )
}
