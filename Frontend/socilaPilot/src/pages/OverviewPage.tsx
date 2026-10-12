import type { Page, ProjectDetail } from '../types'
import { ArrowRight, Sparkles } from 'lucide-react'

type EmptyOverviewProps = {
  onImport: () => void
  page: Page
  loading: boolean
}

export function EmptyOverview({ onImport, page, loading }: EmptyOverviewProps) {
  return (
    <div className="welcome-view">
      <div className="welcome-copy">
        <div className="eyebrow"><span className="sparkle">✳</span> YOUR WORK, WELL TOLD</div>
        <h1>Make your work<br />visible, with <em>proof.</em></h1>
        <p>Turn code, project docs, or carefully written work notes into portfolio-ready case studies and thoughtful posts. Your role and outcomes stay yours to review and explain.</p>
        <button className="button button-primary" onClick={onImport} disabled={loading}>Add a project or work sample <span>→</span></button>
        <div className="trust-note"><span>✳</span> Built for developers, remote workers, and independent creators.</div>
      </div>
      <div className="welcome-visual">
        <div className="visual-glow" />
        <div className="floating-card source-card"><span className="mini-icon violet">⌘</span><div><strong>Your project</strong><small>README · source code</small></div><span className="check-mark">✓</span></div>
        <div className="visual-connector">·····················</div>
        <div className="floating-card insight-card"><span className="mini-icon amber">✦</span><div><strong>Real insights</strong><small>Analyzed with your sources</small></div><span className="check-mark">✓</span></div>
        <div className="visual-connector second">·····················</div>
        <div className="floating-card draft-card"><span className="mini-icon pink">↗</span><div><strong>Your next great post</strong><small>Post draft · claims checked</small></div><span className="draft-lines"><i /><i /><i /></span></div>
        <div className="visual-caption">FROM REAL WORK TO READY-TO-REVIEW</div>
      </div>
      <div className="welcome-features">
        <div><span className="feature-icon">⌘</span><strong>Bring your evidence</strong><p>Use a repository, project documentation, or non-confidential work notes.</p></div>
        <div><span className="feature-icon">✦</span><strong>Tell your part</strong><p>Add your role, decisions, and perspective to posts and case studies.</p></div>
        <div><span className="feature-icon">✓</span><strong>Review every claim</strong><p>Check generated statements against the sources before sharing.</p></div>
      </div>
      {page !== 'Overview' && <div className="empty-page-hint">{page} is ready when you import a project.</div>}
    </div>
  )
}

type ProjectOverviewProps = {
  project: ProjectDetail
  loading: boolean
  onAnalyze: () => void
  onOpenStudio: () => void
  onOpenCaseStudy: () => void
  onGenerateContent: () => void
  generatingContent: boolean
  onImport: () => void
}

export function ProjectOverview({
  project,
  loading,
  onAnalyze,
  onOpenStudio,
  onOpenCaseStudy,
  onGenerateContent,
  generatingContent,
  onImport,
}: ProjectOverviewProps) {
  const profile = project.profile
  const artifactCount = Object.keys(project.artifacts ?? {}).length
  const supportedFindings = profile?.findings?.filter((finding) => finding.status === 'supported') ?? []

  return (
    <div className="dashboard">
      <div className="dashboard-heading">
        <div>
          <div className="eyebrow">PROJECT OVERVIEW</div>
          <h1>{profile?.name || project.name}<span className="heading-spark">✳</span></h1>
          <p>{profile?.summary || 'Your project is connected. Analyze its sources to uncover the story behind the build.'}</p>
        </div>
        <div className="heading-buttons">
          <button className="button button-secondary" onClick={onImport}>＋ Add project</button>
          <button className="button button-primary" onClick={onAnalyze} disabled={loading}>
            {loading ? <><span className="spinner" /> Analyzing…</> : <>{profile ? 'Refresh analysis' : 'Analyze project'} <span>→</span></>}
          </button>
        </div>
      </div>
      <div className="stats-row">
        <div className="stat-card"><span className="stat-label">SOURCES IN YOUR PORTFOLIO</span><strong>{project.documents?.length ?? 0}</strong><small>documents indexed for retrieval</small><span className="stat-decoration lilac">◫</span></div>
        <div className="stat-card"><span className="stat-label">SAVED STORY ASSETS</span><strong>{artifactCount}</strong><small>{artifactCount === 1 ? 'saved draft or case study' : 'saved drafts and case studies'}</small><span className="stat-decoration peach">✦</span></div>
        <div className="stat-card"><span className="stat-label">SOURCE-BACKED FINDINGS</span><strong>{supportedFindings.length}</strong><small>{profile ? 'review citations before sharing' : 'analyze sources to map your work'}</small><span className="stat-decoration mint">✓</span></div>
      </div>
      <div className="dashboard-grid">
        <section className="panel project-panel">
          <div className="panel-heading"><div><span className="panel-kicker">PROJECT SNAPSHOT</span><h2>A clearer view of your work</h2></div><span className="panel-symbol">✳</span></div>
          {profile ? (
            <div className="snapshot-content">
              <div className="snapshot-block"><span>PROJECT OR WORK SUMMARY</span><p>{profile.summary || 'No summary found yet.'}</p></div>
              <div className="snapshot-block"><span>THE PROBLEM</span><p>{profile.problem || 'Add more source notes about the problem you worked on.'}</p></div>
              <div className="snapshot-block"><span>TECHNOLOGIES</span><div className="tag-list">{profile.technologies?.length ? profile.technologies.map((tech) => <span className="tag" key={tech}>{tech}</span>) : <small>Not identified yet</small>}</div></div>
              <div className="snapshot-block"><span>ARCHITECTURE</span><p>{profile.architecture?.slice(0, 3).join(' · ') || 'Explore your architecture in the project profile.'}</p></div>
              {supportedFindings.length > 0 && (
                <div className="snapshot-block">
                  <span>YOUR SOURCE-BACKED STORY POINTS</span>
                  <div className="grounded-finding-list">
                    {supportedFindings.slice(0, 3).map((finding) => (
                      <article key={finding.finding_id}>
                        <p>{finding.text}</p>
                        {finding.evidence[0] && (
                          <small>{finding.evidence[0].path}{finding.evidence[0].start_line ? `:${finding.evidence[0].start_line}` : ''}</small>
                        )}
                      </article>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="analyze-callout"><div className="callout-art"><span>⌘</span><i>✦</i></div><div><strong>Map the work before you tell the story</strong><p>Analyze the indexed code, project docs, or work notes to surface the goal, tools, decisions, and what your sources do not yet prove.</p><button className="text-button" onClick={onAnalyze} disabled={loading}>Analyze sources <span>→</span></button></div></div>
          )}
          <div className="panel-footer"><span>◫</span> {project.repository_url || 'Private work notes'} <a href={project.repository_url || undefined} target="_blank" rel="noreferrer">{project.repository_url ? 'View repository ↗' : ''}</a></div>
        </section>
        <section className="panel next-panel">
          <div className="panel-heading"><div><span className="panel-kicker">MAKE SOMETHING OF IT</span><h2>What will you create?</h2></div></div>
          <button className="generate-suite-card" onClick={onGenerateContent} disabled={generatingContent}>
            <span className="generate-suite-icon"><Sparkles size={19} aria-hidden="true" /></span>
            <span className="generate-suite-copy">
              <strong>{generatingContent ? 'Creating your content pack…' : 'Generate my content with AI'}</strong>
              <small>One click creates a source-backed post and full case study.</small>
            </span>
            {generatingContent ? <span className="spinner" aria-label="Generating" /> : <ArrowRight size={18} aria-hidden="true" />}
          </button>
          <button className="action-tile" onClick={onOpenStudio}><span className="action-icon lilac">↗</span><span><strong>Posts</strong><small>Turn a technical insight into a post</small></span><b>→</b></button>
          <button className="action-tile" onClick={onOpenCaseStudy}><span className="action-icon peach">▤</span><span><strong>Project case study</strong><small>Tell the full story, from problem to impact</small></span><b>→</b></button>
          <div className="evidence-tip"><span>✳</span><p><strong>Your work is more than the repo</strong><br />Add your role, constraints, collaboration, and outcomes in the perspective field. The RAG sources ground project claims; your context brings in your contribution.</p></div>
        </section>
      </div>
    </div>
  )
}
