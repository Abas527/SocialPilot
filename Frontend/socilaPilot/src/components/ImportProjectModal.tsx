import type { FormEvent } from 'react'

export type ImportMode = 'github' | 'readme'

type ImportProjectModalProps = {
  theme: 'light' | 'dark'
  mode: ImportMode
  repoUrl: string
  readme: string
  loading: boolean
  onModeChange: (mode: ImportMode) => void
  onRepoUrlChange: (value: string) => void
  onReadmeChange: (value: string) => void
  onClose: () => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export function ImportProjectModal({
  theme,
  mode,
  repoUrl,
  readme,
  loading,
  onModeChange,
  onRepoUrlChange,
  onReadmeChange,
  onClose,
  onSubmit,
}: ImportProjectModalProps) {
  return (
    <div className="modal-backdrop" data-theme={theme} onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section className="import-modal" role="dialog" aria-modal="true" aria-labelledby="import-title">
        <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        <div className="modal-eyebrow">START WITH YOUR WORK</div>
        <h2 id="import-title">Bring your work into focus.</h2>
        <p className="modal-description">Use a public code repository or add your own project and work notes. SocialPilot grounds drafts in the sources you provide.</p>
        <div className="import-tabs">
          <button className={mode === 'github' ? 'selected' : ''} onClick={() => onModeChange('github')}>GitHub repository</button>
          <button className={mode === 'readme' ? 'selected' : ''} onClick={() => onModeChange('readme')}>Add work notes</button>
        </div>
        <form onSubmit={onSubmit}>
          {mode === 'github' ? (
            <label className="field-label">Repository URL
              <input
                autoFocus
                type="url"
                placeholder="https://github.com/you/your-project"
                value={repoUrl}
                onChange={(event) => onRepoUrlChange(event.target.value)}
                required
              />
              <small>Public GitHub repositories are supported.</small>
            </label>
          ) : (
            <label className="field-label">Project or work notes
              <textarea
                autoFocus
                rows={7}
                placeholder={'# Internal support automation project\n\nRole: Remote customer operations specialist\nGoal: Reduce repetitive triage work\nWhat I did: Document the workflow, coordinate feedback, and build an automation with the team\nEvidence: Add only details and outcomes you can substantiate'}
                value={readme}
                onChange={(event) => onReadmeChange(event.target.value)}
                required
              />
              <small>Useful for remote work, client projects, and internal work. Do not paste confidential employer or client information.</small>
            </label>
          )}
          <button className="button button-primary modal-submit" type="submit" disabled={loading}>
            {loading ? <><span className="spinner" /> Importing…</> : <>Import project <span>→</span></>}
          </button>
        </form>
        <div className="privacy-note"><span>◇</span> Your content is only used to generate drafts for your workspace.</div>
      </section>
    </div>
  )
}
