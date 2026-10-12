import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useMatch, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bell, Bookmark, Database, FileText, FolderKanban, Home, LogOut, Moon, Plus, Sparkles, Store, Sun,
  UserRound, WalletCards,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { useUnreadCount } from '../../hooks/usePosts'
import { JobsTray } from '../../jobs/JobsTray'
import { api } from '../../services/api'
import { useAppTheme } from '../../theme/ThemeContext'
import type { ProjectSummary } from '../../types'
import { FlashMessages, useFlash } from '../Flash'
import { ImportProjectController } from '../ImportProjectController'
import { ComposeProvider } from '../community/ComposeContext'

const PROJECT_KEY = 'socialpilot_project'
export type LayoutContext = { openImport: () => void }

type NavItem = { to: string; label: string; icon: LucideIcon; end?: boolean; badge?: number; short?: string; mobileHidden?: boolean }

function rememberedProject(): string {
  try { return localStorage.getItem(PROJECT_KEY) ?? '' } catch { return '' }
}

export function AppLayout() {
  const { user, signOut } = useAuth()
  const { theme, toggle } = useAppTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const flash = useFlash()
  const [showImport, setShowImport] = useState(false)
  const projectMatch = useMatch('/app/projects/:projectId/*')
  const unread = useUnreadCount().data?.unread ?? 0

  const projects = useQuery({ queryKey: ['projects'], queryFn: () => api<ProjectSummary[]>('/projects') })
  const list = projects.data ?? []
  const routeProject = projectMatch?.params.projectId ?? ''
  const currentId = routeProject || (list.some((p) => p.project_id === rememberedProject()) ? rememberedProject() : list[0]?.project_id ?? '')

  useEffect(() => {
    if (!routeProject) return
    try { localStorage.setItem(PROJECT_KEY, routeProject) } catch { /* storage unavailable */ }
  }, [routeProject])

  // Messages belong to the page that raised them.
  useEffect(() => { flash.clear() }, [location.pathname]) // eslint-disable-line react-hooks/exhaustive-deps

  const base = currentId ? `/app/projects/${currentId}` : '/app/projects'
  const groups: { label: string; items: NavItem[] }[] = [
    {
      label: 'COMMUNITY',
      items: [
        { to: '/app/feed', label: 'Feed', icon: Home },
        { to: '/app/bookmarks', label: 'Bookmarks', icon: Bookmark, short: 'Saved' },
        { to: '/app/notifications', label: 'Notifications', icon: Bell, badge: unread, short: 'Alerts' },
        { to: '/app/marketplace', label: 'Marketplace', icon: Store, short: 'Shop' },
      ],
    },
    {
      label: 'CREATE',
      items: [
        { to: '/app/dashboard', label: 'My dashboard', icon: UserRound, short: 'Me' },
        { to: base, label: 'Project overview', icon: FolderKanban, end: true, mobileHidden: true },
        { to: `${base}/studio`, label: 'Content studio', icon: Sparkles, short: 'Studio' },
        { to: `${base}/case-study`, label: 'Case studies', icon: FileText, mobileHidden: true },
        { to: `${base}/sources`, label: 'Sources', icon: Database, mobileHidden: true },
      ],
    },
    { label: 'ACCOUNT', items: [{ to: '/app/wallet', label: 'Wallet', icon: WalletCards }] },
  ]

  const TITLES: Record<string, string> = { u: 'Profile', post: 'Post', tags: 'Tag', projects: 'Projects', feed: 'Home' }
  const segment = location.pathname.split('/').filter(Boolean)[1] ?? 'feed'
  const title = TITLES[segment] ?? segment.replace('-', ' ')

  return (
    <div className="app-shell" data-theme={theme}>
      <ComposeProvider>
        <a className="dc-skip" href="#main-content">Skip to content</a>
        <aside className="sidebar">
          <NavLink className="brand" to="/app/feed">
            <span className="brand-mark"><span>SP</span></span>
            <span className="brand-name">social<span>pilot</span><small>FOR BUILDERS</small></span>
          </NavLink>
          <button className="new-project" onClick={() => setShowImport(true)}>
            <Plus size={16} aria-hidden="true" /> New project
          </button>

          <div className="sidebar-scroll-area">
            <div className="nav-groups">
              {groups.map((group) => (
                <section className="nav-group" key={group.label}>
                  <div className="side-label">{group.label}</div>
                  <nav className="navigation" aria-label={`${group.label.toLowerCase()} navigation`}>
                    {group.items.map(({ to, label, icon: Icon, end, badge, short, mobileHidden }) => (
                      <NavLink key={label} to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}${mobileHidden ? ' mobile-hidden' : ''}`}>
                        <Icon className="nav-icon" size={17} strokeWidth={1.8} aria-hidden="true" />
                        <span className="nav-label">{label}</span>
                        <span className="mobile-nav-label">{short ?? label}</span>
                        {badge ? <span className="dc-badge" aria-label={`${badge} unread`}>{badge > 99 ? '99+' : badge}</span> : null}
                      </NavLink>
                    ))}
                  </nav>
                </section>
              ))}
            </div>

            <div className="side-label project-label">YOUR PROJECTS</div>
            {list.length ? (
              <div className="project-list">
                {list.slice(0, 6).map((project) => (
                  <NavLink
                    key={project.project_id}
                    to={`/app/projects/${project.project_id}`}
                    className={`project-link ${project.project_id === currentId ? 'selected' : ''}`}
                  >
                    <span className="project-dot" />{project.name}
                  </NavLink>
                ))}
              </div>
            ) : <p className="sidebar-empty">Import a repo to start creating.</p>}
          </div>

          <div className="sidebar-bottom">
            <div className="profile-chip">
              <div className="avatar">{user?.display_name.trim().charAt(0).toUpperCase()}</div>
              <NavLink className="profile-chip-open" to="/app/dashboard">
                <strong>{user?.display_name}</strong><small>Your dashboard</small>
              </NavLink>
              <button className="more" onClick={() => void signOut().then(() => navigate('/login'))} aria-label="Sign out"><LogOut size={16} /></button>
            </div>
          </div>
        </aside>

        <main className="main-area" id="main-content">
          <header className="topbar">
            <div className="breadcrumbs"><span>Workspace</span><b>/</b><strong style={{ textTransform: 'capitalize' }}>{title}</strong></div>
            <div className="top-actions">
              <NavLink className="workspace-home-link" to="/">← Product site</NavLink>
              <button className="theme-toggle" onClick={toggle} aria-pressed={theme === 'dark'} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
                {theme === 'dark' ? <Sun size={15} aria-hidden="true" /> : <Moon size={15} aria-hidden="true" />}
                <span className="theme-toggle-label">{theme === 'dark' ? 'Light' : 'Dark'}</span>
              </button>
              <NavLink to="/app/notifications" className="dc-bell" aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}>
                <Bell size={17} aria-hidden="true" />{unread > 0 && <span className="dc-dot" />}
              </NavLink>
            </div>
          </header>
          <div className="page-content">
            <FlashMessages />
            <Outlet context={{ openImport: () => setShowImport(true) } satisfies LayoutContext} />
          </div>
        </main>
        <JobsTray />
        {showImport && <ImportProjectController onClose={() => setShowImport(false)} />}
      </ComposeProvider>
    </div>
  )
}
