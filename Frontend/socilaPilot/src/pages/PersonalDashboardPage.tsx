import { useEffect, useState } from 'react'
import { ArrowRight, FileText, FolderKanban, Layers3, Plus, Sparkles, UserRound } from 'lucide-react'
import { api } from '../services/api'
import type { AuthUser, CaseStudy, CreatorProfile, LinkedInDraft, Page, ProjectDetail, ProjectSummary } from '../types'

type DashboardTab = 'overview' | 'projects' | 'content' | 'profile'

type PersonalDashboardPageProps = {
  user: AuthUser
  projects: ProjectSummary[]
  project: ProjectDetail | null
  projectId: string
  draft: LinkedInDraft | null
  caseStudy: CaseStudy | null
  onNavigate: (page: Page) => void
  onSelectProject: (projectId: string) => void
  onNewProject: () => void
}

const tabs: { id: DashboardTab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'projects', label: 'Projects' },
  { id: 'content', label: 'Content library' },
  { id: 'profile', label: 'Profile & account' },
]

export function PersonalDashboardPage({
  user,
  projects,
  project,
  projectId,
  draft,
  caseStudy,
  onNavigate,
  onSelectProject,
  onNewProject,
}: PersonalDashboardPageProps) {
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview')
  const [profile, setProfile] = useState<CreatorProfile | null>(null)
  const [username, setUsername] = useState('')
  const [bio, setBio] = useState('')
  const [profileLoading, setProfileLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [feedbackError, setFeedbackError] = useState('')

  useEffect(() => {
    let cancelled = false
    api<CreatorProfile>('/social/profile')
      .then((result) => {
        if (cancelled) return
        setProfile(result)
        setUsername(result.username)
        setBio(result.bio)
      })
      .catch((cause: unknown) => {
        if (!cancelled) setFeedbackError(cause instanceof Error ? cause.message : 'Could not load your creator profile.')
      })
      .finally(() => {
        if (!cancelled) setProfileLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const saveProfile = async () => {
    setSaving(true)
    setFeedback('')
    setFeedbackError('')
    try {
      const updated = await api<CreatorProfile>('/social/profile', {
        method: 'PUT',
        body: JSON.stringify({ username, bio }),
      })
      setProfile(updated)
      setUsername(updated.username)
      setBio(updated.bio)
      setFeedback('Your public creator profile has been updated.')
    } catch (cause) {
      setFeedbackError(cause instanceof Error ? cause.message : 'Could not save your creator profile.')
    } finally {
      setSaving(false)
    }
  }

  const openProject = (id: string) => {
    onSelectProject(id)
    onNavigate('Overview')
  }

  const artifactCount = Object.keys(project?.artifacts ?? {}).length
  const greetingName = profile?.display_name || user.display_name

  return (
    <section className="personal-dashboard" aria-labelledby="personal-dashboard-title">
      <header className="personal-dashboard-heading">
        <div>
          <span className="personal-dashboard-kicker"><UserRound size={14} /> YOUR PRIVATE WORKSPACE</span>
          <h1 id="personal-dashboard-title">Good to see you, {greetingName.split(' ')[0]}.</h1>
          <p>Your account, projects, and creative work — organized in one place.</p>
        </div>
        <button className="button button-primary" onClick={onNewProject}><Plus size={16} /> Add a project</button>
      </header>

      <div className="personal-dashboard-tabs" role="tablist" aria-label="Personal dashboard sections">
        {tabs.map((tab) => (
          <button
            id={`personal-tab-${tab.id}`}
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls="personal-dashboard-panel"
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {feedbackError && <p className="personal-feedback personal-feedback-error" role="alert">{feedbackError}</p>}
      {feedback && <p className="personal-feedback" role="status">{feedback}</p>}

      <div
        id="personal-dashboard-panel"
        className="personal-dashboard-panel"
        role="tabpanel"
        aria-labelledby={`personal-tab-${activeTab}`}
        tabIndex={0}
      >
        {activeTab === 'overview' && (
          <>
            <div className="personal-stat-grid">
              <article><span><FolderKanban size={18} /></span><strong>{projects.length}</strong><small>Projects connected</small></article>
              <article><span><Layers3 size={18} /></span><strong>{artifactCount}</strong><small>Saved assets in current project</small></article>
              <article><span><UserRound size={18} /></span><strong>{profile ? profile.follower_count : '—'}</strong><small>Community followers</small></article>
            </div>
            <div className="personal-overview-grid">
              <section className="personal-card personal-current-project">
                <div className="personal-card-heading">
                  <div><span className="personal-card-kicker">PICK UP WHERE YOU LEFT OFF</span><h2>Current project</h2></div>
                  <FolderKanban size={19} aria-hidden="true" />
                </div>
                {project ? (
                  <>
                    <h3>{project.profile?.name || project.name}</h3>
                    <p>{project.profile?.summary || 'Your project is connected. Analyze its sources to prepare it for content creation.'}</p>
                    <div className="personal-project-meta">
                      <span>{project.documents.length} sources</span>
                      <span>{artifactCount} saved {artifactCount === 1 ? 'asset' : 'assets'}</span>
                    </div>
                    <button className="personal-text-action" onClick={() => onNavigate('Overview')}>Open project overview <ArrowRight size={15} /></button>
                  </>
                ) : (
                  <div className="personal-empty">
                    <p>{projects.length ? 'Choose a project to see its progress and saved work.' : 'Connect a project to start building source-backed stories.'}</p>
                    <button className="personal-text-action" onClick={() => projects.length ? setActiveTab('projects') : onNewProject()}>
                      {projects.length ? 'Choose a project' : 'Connect your first project'} <ArrowRight size={15} />
                    </button>
                  </div>
                )}
              </section>
              <section className="personal-card personal-next-steps">
                <div className="personal-card-heading">
                  <div><span className="personal-card-kicker">CREATE FROM YOUR WORK</span><h2>Your next steps</h2></div>
                  <Sparkles size={19} aria-hidden="true" />
                </div>
                <button className="personal-action-row" onClick={() => onNavigate('Content studio')}>
                  <span className="personal-action-icon"><Sparkles size={17} /></span>
                  <span><strong>Write a post</strong><small>Draft and review before sharing</small></span><ArrowRight size={16} />
                </button>
                <button className="personal-action-row" onClick={() => onNavigate('Case studies')}>
                  <span className="personal-action-icon"><FileText size={17} /></span>
                  <span><strong>Build a case study</strong><small>Turn project details into a clear story</small></span><ArrowRight size={16} />
                </button>
              </section>
            </div>
          </>
        )}

        {activeTab === 'projects' && (
          <section className="personal-card">
            <div className="personal-card-heading">
              <div><span className="personal-card-kicker">YOUR PRIVATE PROJECTS</span><h2>Project library</h2></div>
              <button className="button button-secondary" onClick={onNewProject}><Plus size={15} /> Add project</button>
            </div>
            {projects.length ? (
              <div className="personal-project-list">
                {projects.map((item) => (
                  <article className="personal-project-row" key={item.project_id}>
                    <span className="personal-project-icon"><FolderKanban size={18} /></span>
                    <div><h3>{item.name}</h3><p>{item.repository_url || 'Private work sample'} · Added {new Date(item.created_at).toLocaleDateString()}</p></div>
                    {item.project_id === projectId
                      ? <span className="personal-current-badge">Current project</span>
                      : <button className="personal-text-action" onClick={() => openProject(item.project_id)}>Open project <ArrowRight size={15} /></button>}
                  </article>
                ))}
              </div>
            ) : (
              <div className="personal-empty"><p>Your connected projects will appear here.</p><button className="button button-primary" onClick={onNewProject}>Connect a project <ArrowRight size={15} /></button></div>
            )}
          </section>
        )}

        {activeTab === 'content' && (
          <section className="personal-card">
            <div className="personal-card-heading">
              <div><span className="personal-card-kicker">PRIVATE UNTIL YOU SHARE</span><h2>Saved content</h2></div>
              <span className="personal-content-project">{project?.name || 'Select a project'}</span>
            </div>
            {!project ? (
              <div className="personal-empty"><p>Select a project to view its saved posts and case study.</p><button className="personal-text-action" onClick={() => setActiveTab('projects')}>Browse projects <ArrowRight size={15} /></button></div>
            ) : (
              <div className="personal-content-list">
                {draft && (
                  <article className="personal-content-row">
                    <span className="personal-content-icon post-icon"><Sparkles size={18} /></span>
                    <div><span className="personal-card-kicker">POST DRAFT</span><h3>{draft.hook || 'Untitled post draft'}</h3><p>{draft.body.slice(0, 180) || 'This saved draft is ready for your review.'}</p></div>
                    <button className="personal-text-action" onClick={() => onNavigate('Content studio')}>Review draft <ArrowRight size={15} /></button>
                  </article>
                )}
                {caseStudy && (
                  <article className="personal-content-row">
                    <span className="personal-content-icon case-icon"><FileText size={18} /></span>
                    <div><span className="personal-card-kicker">CASE STUDY</span><h3>{caseStudy.title || 'Untitled case study'}</h3><p>{caseStudy.summary.slice(0, 180) || 'This case study is ready for your review.'}</p></div>
                    <button className="personal-text-action" onClick={() => onNavigate('Case studies')}>Review case study <ArrowRight size={15} /></button>
                  </article>
                )}
                {!draft && !caseStudy && <div className="personal-empty"><p>No saved content for this project yet. Create a post or case study; nothing is published without your approval.</p><button className="personal-text-action" onClick={() => onNavigate('Content studio')}>Create your first draft <ArrowRight size={15} /></button></div>}
              </div>
            )}
          </section>
        )}

        {activeTab === 'profile' && (
          <div className="personal-profile-layout">
            <section className="personal-card personal-account-card">
              <div className="personal-card-heading">
                <div><span className="personal-card-kicker">ACCOUNT DETAILS</span><h2>Your account</h2></div>
                <UserRound size={19} aria-hidden="true" />
              </div>
              <div className="personal-account-identity">
                <span>{user.display_name.trim().charAt(0).toUpperCase()}</span>
                <div><strong>{user.display_name}</strong><small>{user.email}</small></div>
              </div>
              <p className="personal-account-note">Your sign-in details are private and are not shown on your public creator profile.</p>
            </section>
            <section className="personal-card personal-public-profile">
              <div className="personal-card-heading">
                <div><span className="personal-card-kicker">COMMUNITY IDENTITY</span><h2>Public creator profile</h2></div>
                <span className="personal-public-badge">Shown in Community</span>
              </div>
              {profileLoading ? <p className="personal-muted">Loading your profile…</p> : (
                <>
                  <p className="personal-account-note">Manage how other builders see you. Profile details live here—not in your Community feed.</p>
                  <label className="personal-field-label" htmlFor="personal-username">Username</label>
                  <div className="personal-username-field"><span>@</span><input id="personal-username" value={username} maxLength={30} onChange={(event) => setUsername(event.target.value)} /></div>
                  <label className="personal-field-label" htmlFor="personal-bio">About you</label>
                  <textarea id="personal-bio" value={bio} maxLength={500} rows={4} onChange={(event) => setBio(event.target.value)} placeholder="What do you build? What are you learning?" />
                  <div className="personal-profile-footer"><span>{bio.length}/500</span><button className="button button-primary" disabled={saving} onClick={() => void saveProfile()}>{saving ? 'Saving…' : 'Save profile'}</button></div>
                </>
              )}
            </section>
          </div>
        )}
      </div>
    </section>
  )
}
