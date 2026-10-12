import { useState } from 'react'
import { Navigate, Outlet, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../auth/AuthContext'
import { useCompose } from '../components/community/ComposeContext'
import { Spinner } from '../components/community/bits'
import { useFlash } from '../components/Flash'
import type { LayoutContext } from '../components/layout/AppLayout'
import { useJobs } from '../jobs/JobsProvider'
import { errorMessage } from '../lib/format'
import { CaseStudyPage } from '../pages/CaseStudyPage'
import { ContentStudioPage } from '../pages/ContentStudioPage'
import { EmptyOverview, ProjectOverview } from '../pages/OverviewPage'
import { PersonalDashboardPage } from '../pages/PersonalDashboardPage'
import { SourcesPage } from '../pages/SourcesPage'
import {
  api, caseStudyFilename, downloadFile, exportCaseStudy, saveCaseStudy, saveLinkedInDraft,
} from '../services/api'
import type {
  CaseStudy, ExportFormat, LinkedInAngle, LinkedInDraft, LinkedInFormat, Page, ProjectDetail,
  ProjectProfile, ProjectSummary, WorkflowGenerationResult,
} from '../types'

const PROJECT_KEY = 'socialpilot_project'
const isLinkedInDraft = (v: unknown): v is LinkedInDraft => Boolean(v && typeof v === 'object' && 'hook' in v)
const isCaseStudy = (v: unknown): v is CaseStudy => Boolean(v && typeof v === 'object' && 'title' in v)

function useProject(projectId: string) {
  return useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api<ProjectDetail>(`/projects/${projectId}`),
    enabled: Boolean(projectId),
  })
}

function usePreferredProjectId(): string {
  const projects = useQuery({ queryKey: ['projects'], queryFn: () => api<ProjectSummary[]>('/projects') })
  let remembered = ''
  try { remembered = localStorage.getItem(PROJECT_KEY) ?? '' } catch { /* storage unavailable */ }
  const list = projects.data ?? []
  return list.some((p) => p.project_id === remembered) ? remembered : list[0]?.project_id ?? ''
}

/** /app/projects: jump to the last project, or invite the user to import one. */
export function ProjectsIndex() {
  const { openImport } = useOutletContext<LayoutContext>()
  const projects = useQuery({ queryKey: ['projects'], queryFn: () => api<ProjectSummary[]>('/projects') })
  const preferred = usePreferredProjectId()
  if (projects.isLoading) return <Spinner label="Loading projects…" />
  if (preferred) return <Navigate to={`/app/projects/${preferred}`} replace />
  return <EmptyOverview onImport={openImport} page="Overview" loading={false} />
}

type ScopeContext = LayoutContext & { project: ProjectDetail }

/** Loads one project and hands it to the nested project pages. */
export function ProjectScope() {
  const { projectId = '' } = useParams()
  const layout = useOutletContext<LayoutContext>()
  const project = useProject(projectId)
  if (project.isLoading) return <Spinner label="Loading project…" />
  if (project.isError || !project.data) {
    return <EmptyOverview onImport={layout.openImport} page="Overview" loading={false} />
  }
  return <Outlet context={{ ...layout, project: project.data } satisfies ScopeContext} />
}

function useScope() {
  return useOutletContext<ScopeContext>()
}

/** Runs AI jobs for one project and reports problems/successes on the page. */
function useProjectAi(project: ProjectDetail) {
  const jobs = useJobs()
  const flash = useFlash()
  const [busy, setBusy] = useState('')
  const run = async <R,>(label: string, kind: Parameters<typeof jobs.run>[0]['kind'], extra: Record<string, unknown>, done: (result: R) => void, message?: string) => {
    setBusy(label)
    try {
      const job = await jobs.run<R>({ kind, project_id: project.project_id, ...extra }, { label })
      if (job.result) done(job.result)
      if (message) flash.showNotice(message)
    } catch (cause) {
      flash.showError(errorMessage(cause))
    } finally {
      setBusy('')
    }
  }
  return { busy, run, flash }
}

export function ProjectOverviewRoute() {
  const { project, openImport } = useScope()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { busy, run } = useProjectAi(project)
  const base = `/app/projects/${project.project_id}`
  return (
    <ProjectOverview
      project={project}
      loading={busy === 'Analyzing sources'}
      onAnalyze={() => void run<{ analysis: ProjectProfile }>('Analyzing sources', 'analyze', {},
        () => void qc.invalidateQueries({ queryKey: ['project', project.project_id] }),
        'Project analysis complete. Your source-backed profile is ready.')}
      onOpenStudio={() => navigate(`${base}/studio`)}
      onOpenCaseStudy={() => navigate(`${base}/case-study`)}
      onGenerateContent={() => void run<WorkflowGenerationResult>('Generating content', 'workflow',
        { angles: ['technical_lesson'], include_case_study: true, reanalyze: true },
        () => navigate(`${base}/studio`),
        'AI generated a source-backed post and case study. Review both before sharing.')}
      generatingContent={busy === 'Generating content'}
      onImport={openImport}
    />
  )
}

export function StudioRoute() {
  const { project } = useScope()
  const qc = useQueryClient()
  const { openComposer } = useCompose()
  const { busy, run, flash } = useProjectAi(project)
  const [angle, setAngle] = useState<LinkedInAngle>('technical_lesson')
  const [format, setFormat] = useState<LinkedInFormat>('standard')
  const [userContext, setUserContext] = useState('')
  const [generated, setGenerated] = useState<{ angle: LinkedInAngle; draft: LinkedInDraft } | null>(null)
  const [saving, setSaving] = useState(false)

  const artifact = project.artifacts[`linkedin:${angle}`]
  const saved = artifact?.edited ?? artifact?.generated
  const draft = generated?.angle === angle ? generated.draft : isLinkedInDraft(saved) ? saved : null

  return (
    <ContentStudioPage
      key={project.project_id}
      project={project}
      angle={angle}
      format={format}
      onFormatChange={setFormat}
      onAngleChange={setAngle}
      userContext={userContext}
      onUserContextChange={setUserContext}
      draft={draft}
      claims={draft?.verified_claims ?? []}
      loading={Boolean(busy) || saving}
      onGenerate={() => void run<{ artifact: LinkedInDraft }>('Writing draft', 'linkedin',
        { angle, user_context: userContext, post_format: format },
        (result) => setGenerated({ angle, draft: result.artifact }),
        'Draft generated with evidence checks.')}
      onSave={(content) => {
        setSaving(true)
        saveLinkedInDraft(project.project_id, angle, content)
          .then(() => { setGenerated({ angle, draft: content }); flash.showNotice('Your edits have been saved.'); void qc.invalidateQueries({ queryKey: ['project', project.project_id] }) })
          .catch((cause: unknown) => flash.showError(errorMessage(cause)))
          .finally(() => setSaving(false))
      }}
      onShare={(body) => openComposer({
        body, projectId: project.project_id, projectName: project.name, artifactRef: `linkedin:${angle}`,
      })}
    />
  )
}

export function CaseStudyRoute() {
  const { project } = useScope()
  const qc = useQueryClient()
  const { busy, run, flash } = useProjectAi(project)
  const [userContext, setUserContext] = useState('')
  const [generated, setGenerated] = useState<CaseStudy | null>(null)
  const [working, setWorking] = useState('')
  const artifact = project.artifacts.case_study
  const saved = artifact?.edited ?? artifact?.generated
  const content = generated ?? (isCaseStudy(saved) ? saved : null)

  return (
    <CaseStudyPage
      key={`${project.project_id}:${content?.title ?? 'new'}`}
      project={project}
      content={content}
      loading={Boolean(busy) || Boolean(working)}
      userContext={userContext}
      onUserContextChange={setUserContext}
      onGenerate={() => void run<{ artifact: CaseStudy }>('Creating case study', 'case_study',
        { user_context: userContext }, (result) => setGenerated(result.artifact),
        'Case study generated. Review claims before sharing.')}
      onSave={(next) => {
        setWorking('save')
        saveCaseStudy(project.project_id, next)
          .then(() => { setGenerated(next); flash.showNotice('Your edits have been saved.'); void qc.invalidateQueries({ queryKey: ['project', project.project_id] }) })
          .catch((cause: unknown) => flash.showError(errorMessage(cause)))
          .finally(() => setWorking(''))
      }}
      onExport={(format: ExportFormat, next) => {
        setWorking('export')
        exportCaseStudy(format, next, project.repository_url)
          .then((blob) => { downloadFile(blob, caseStudyFilename(next, format)); flash.showNotice(`${format === 'pdf' ? 'PDF' : 'Markdown'} exported.`) })
          .catch((cause: unknown) => flash.showError(errorMessage(cause)))
          .finally(() => setWorking(''))
      }}
    />
  )
}

export function SourcesRoute() {
  const { project } = useScope()
  const qc = useQueryClient()
  const { busy, run } = useProjectAi(project)
  return (
    <SourcesPage
      project={project}
      loading={busy === 'Analyzing sources'}
      onAnalyze={() => void run<{ analysis: ProjectProfile }>('Analyzing sources', 'analyze', {},
        () => void qc.invalidateQueries({ queryKey: ['project', project.project_id] }),
        'Project analysis complete. Your source-backed profile is ready.')}
    />
  )
}

const PAGE_PATH: Record<Page, string> = {
  'Personal dashboard': '/app/dashboard', Overview: '', 'Content studio': '/studio', 'Case studies': '/case-study',
  Sources: '/sources', Community: '/app/feed', Marketplace: '/app/marketplace', Wallet: '/app/wallet',
}

export function DashboardRoute() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { openImport } = useOutletContext<LayoutContext>()
  const projects = useQuery({ queryKey: ['projects'], queryFn: () => api<ProjectSummary[]>('/projects') })
  const projectId = usePreferredProjectId()
  const project = useProject(projectId).data ?? null
  if (!user) return null
  const draftArtifact = project?.artifacts['linkedin:technical_lesson']
  const draftValue = draftArtifact?.edited ?? draftArtifact?.generated
  const studyArtifact = project?.artifacts.case_study
  const studyValue = studyArtifact?.edited ?? studyArtifact?.generated

  return (
    <PersonalDashboardPage
      key={user.user_id}
      user={user}
      projects={projects.data ?? []}
      project={project}
      projectId={projectId}
      draft={isLinkedInDraft(draftValue) ? draftValue : null}
      caseStudy={isCaseStudy(studyValue) ? studyValue : null}
      onNavigate={(page) => {
        const suffix = PAGE_PATH[page]
        navigate(suffix.startsWith('/app') ? suffix : projectId ? `/app/projects/${projectId}${suffix}` : '/app/projects')
      }}
      onSelectProject={(id) => navigate(`/app/projects/${id}`)}
      onNewProject={openImport}
    />
  )
}
