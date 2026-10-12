import { useState } from 'react'
import { ClaimSummary } from '../components/ClaimSummary'
import { PageHeading } from '../components/PageHeading'
import { PublicationsList, ShareCaseStudyDialog } from '../components/community/EvidencePassport'
import type { CaseStudy, ExportFormat, ProjectDetail } from '../types'

type CaseStudyPageProps = {
  project: ProjectDetail
  content: CaseStudy | null
  loading: boolean
  userContext: string
  onUserContextChange: (value: string) => void
  onGenerate: () => void
  onSave: (content: CaseStudy) => void
  onExport: (format: ExportFormat, content: CaseStudy) => void
}

type CaseStudySection = Exclude<keyof CaseStudy, 'verified_claims'>
type CaseStudySectionGroup = 'story' | 'engineering' | 'outcomes'

const sections: { key: CaseStudySection; title: string }[] = [
  { key: 'summary', title: 'Executive summary' },
  { key: 'problem', title: 'Problem and motivation' },
  { key: 'architecture', title: 'Architecture and technologies' },
  { key: 'implementation', title: 'Implementation decisions' },
  { key: 'challenges', title: 'Engineering challenges' },
  { key: 'results', title: 'Results and evaluation' },
  { key: 'limitations', title: 'Limitations' },
  { key: 'future_work', title: 'Future work' },
]

const sectionGroups: { id: CaseStudySectionGroup; label: string; description: string; keys: CaseStudySection[] }[] = [
  { id: 'story', label: 'Story', description: 'Set the context and explain why the work mattered.', keys: ['summary', 'problem'] },
  { id: 'engineering', label: 'Engineering', description: 'Make the technical approach and decisions clear.', keys: ['architecture', 'implementation', 'challenges'] },
  { id: 'outcomes', label: 'Outcomes & next steps', description: 'Review results honestly and describe what remains.', keys: ['results', 'limitations', 'future_work'] },
]

export function CaseStudyPage({
  project,
  content,
  loading,
  userContext,
  onUserContextChange,
  onGenerate,
  onSave,
  onExport,
}: CaseStudyPageProps) {
  const [showShare, setShowShare] = useState(false)
  const [activeSectionGroup, setActiveSectionGroup] = useState<CaseStudySectionGroup>('story')
  const [caseStudyState, setCaseStudyState] = useState({ source: content, edited: content })
  if (caseStudyState.source !== content) {
    setCaseStudyState({ source: content, edited: content })
  }
  const editedCaseStudy = caseStudyState.source === content ? caseStudyState.edited : content
  const updateCaseStudy = (edited: CaseStudy) => setCaseStudyState({ source: content, edited })
  const dirty = JSON.stringify(editedCaseStudy) !== JSON.stringify(content)

  return (
    <div className="case-page">
      <PageHeading
        eyebrow="AI CASE STUDY"
        title="Review your case study."
        subtitle={`AI drafts an evidence-backed story from ${project.name}. Review the claims, then edit anything that needs your perspective.`}
      />
      {!editedCaseStudy ? (
        <div className="case-start panel">
          <div className="case-cover">
            <span className="case-cover-orbit orbit-one" />
            <span className="case-cover-orbit orbit-two" />
            <span className="case-cover-mark">SP<span>✳</span></span>
            <small>PROJECT STORY / 01</small>
          </div>
          <div className="case-start-content">
            <span className="panel-kicker">AI-GENERATED · YOURS TO REVIEW</span>
            <h2>Let AI draft the story. You make it yours.</h2>
            <p>SocialPilot creates the first draft from your project sources. Review the evidence, correct details, and refine the wording before you share or export it.</p>
            <label className="field-label">Optional context for the AI draft
              <textarea
                rows={3}
                value={userContext}
                onChange={(event) => onUserContextChange(event.target.value)}
                placeholder="Add your role, collaborators, constraints, or outcomes not captured by the sources. Leave this blank if you prefer."
              />
            </label>
            <button className="button button-primary" onClick={onGenerate} disabled={loading || !project.profile}>
              {loading ? <><span className="spinner" /> AI is drafting your case study…</> : <>Generate AI draft <span>→</span></>}
            </button>
            {!project.profile && <small className="prerequisite-note">Analyze the project first to generate a case study.</small>}
          </div>
        </div>
      ) : (
        <section className="panel case-editor">
          <div className="case-editor-top">
            <div>
              <span className="panel-kicker">AI DRAFT · EDITABLE REVIEW</span>
              <input
                className="case-title-input"
                value={editedCaseStudy.title}
                onChange={(event) => updateCaseStudy({ ...editedCaseStudy, title: event.target.value })}
              />
            </div>
            <div className="export-actions">
              <button className="button button-secondary" onClick={onGenerate} disabled={loading || !project.profile}>
                {loading ? 'Generating…' : 'Regenerate with AI'}
              </button>
              <button className="button button-secondary" onClick={() => onExport('markdown', editedCaseStudy)} disabled={loading}>↓ Markdown</button>
              <button className="button button-primary" onClick={() => onExport('pdf', editedCaseStudy)} disabled={loading}>↓ PDF</button>
            </div>
          </div>
          <p className="case-editor-intro">Shape the story in focused steps. Your edits stay private until you choose to share them.</p>
          <div className={`review-status ${editedCaseStudy.review_status === 'preliminary_support' ? 'review-status-supported' : ''}`}>
            <strong>{editedCaseStudy.review_status === 'preliminary_support' ? 'Evidence review: preliminary support' : 'Evidence review: needs review'}</strong>
            <span>Source checks are a review aid. Confirm claims and add your personal contribution before publishing.</span>
          </div>
          <div className="case-section-tabs" role="tablist" aria-label="Case study sections">
            {sectionGroups.map((group) => (
              <button
                key={group.id}
                id={`case-section-tab-${group.id}`}
                type="button"
                role="tab"
                aria-selected={activeSectionGroup === group.id}
                aria-controls="case-section-panel"
                onClick={() => setActiveSectionGroup(group.id)}
              >
                <strong>{group.label}</strong><small>{group.keys.length} sections</small>
              </button>
            ))}
          </div>
          <div id="case-section-panel" role="tabpanel" aria-labelledby={`case-section-tab-${activeSectionGroup}`} className="case-section-panel">
            <p className="case-section-description">{sectionGroups.find((group) => group.id === activeSectionGroup)?.description}</p>
            <div className="case-sections">
              {sections.filter(({ key }) => sectionGroups.find((group) => group.id === activeSectionGroup)?.keys.includes(key)).map(({ key, title }) => (
                <label key={key} className="case-section">
                  <span>{title}</span>
                  <textarea
                    rows={key === 'summary' ? 3 : 4}
                    value={editedCaseStudy[key] ?? ''}
                    onChange={(event) => updateCaseStudy({ ...editedCaseStudy, [key]: event.target.value })}
                  />
                </label>
              ))}
            </div>
          </div>
          <ClaimSummary claims={editedCaseStudy.verified_claims ?? []} />
          <div className="case-footer">
            <span>✳ Generated from {project.documents?.length ?? 0} project sources</span>
            <div className="flex flex-wrap gap-2">
              <button className="button button-secondary" onClick={() => setShowShare(true)}
                disabled={loading || dirty || !editedCaseStudy.summary.trim()}
                title={dirty ? 'Save your edits first: the shared version is your saved case study.' : 'Share the full case study with its evidence'}>
                Share to Community
              </button>
              <button className="button button-primary" onClick={() => onSave(editedCaseStudy)} disabled={loading}>
                {loading ? 'Saving…' : 'Save case study'}
              </button>
            </div>
          </div>
        </section>
      )}
      {editedCaseStudy && <PublicationsList project={project} />}
      {showShare && <ShareCaseStudyDialog project={project} onClose={() => setShowShare(false)} />}
    </div>
  )
}
