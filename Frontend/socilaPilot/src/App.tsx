import { Suspense, lazy } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { AppLayout } from './components/layout/AppLayout'
import { AuthPage } from './pages/AuthPage'
import { FeedPage } from './pages/FeedPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { PostDetailPage } from './pages/PostDetailPage'
import { PublicationPage } from './pages/PublicationPage'
import { ProfilePage } from './pages/ProfilePage'
import { Spinner } from './components/community/bits'
const HomePage = lazy(() => import('./pages/HomePage').then((m) => ({ default: m.HomePage })))
const MarketplacePage = lazy(() => import('./pages/MarketplacePage').then((m) => ({ default: m.MarketplacePage })))
const WalletPage = lazy(() => import('./pages/WalletPage').then((m) => ({ default: m.WalletPage })))
const project = () => import('./routes/ProjectRoutes')
const ProjectsIndex = lazy(() => project().then((m) => ({ default: m.ProjectsIndex })))
const ProjectScope = lazy(() => project().then((m) => ({ default: m.ProjectScope })))
const ProjectOverviewRoute = lazy(() => project().then((m) => ({ default: m.ProjectOverviewRoute })))
const StudioRoute = lazy(() => project().then((m) => ({ default: m.StudioRoute })))
const CaseStudyRoute = lazy(() => project().then((m) => ({ default: m.CaseStudyRoute })))
const SourcesRoute = lazy(() => project().then((m) => ({ default: m.SourcesRoute })))
const DashboardRoute = lazy(() => project().then((m) => ({ default: m.DashboardRoute })))

import './App.css'
import './theme.css'
import './community.css'

function RequireAuth() {
  const { user, checking } = useAuth()
  const location = useLocation()
  if (checking) return <main className="dc-boot"><Spinner label="Checking your session…" /></main>
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return <Outlet />
}

function LoginRoute() {
  const { user, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/app/feed'
  if (user) return <Navigate to={from} replace />
  return <AuthPage onAuthenticated={(token, next) => { signIn(token, next); navigate(from, { replace: true }) }} />
}

function WalletRoute() {
  const location = useLocation()
  const tab = (location.state as { tab?: 'account' | 'send' } | null)?.tab
  return <WalletPage initialTab={tab ?? 'account'} />
}

function MarketplaceRoute() {
  const navigate = useNavigate()
  return <MarketplacePage onOpenWallet={() => navigate('/app/wallet')} />
}

function Landing() {
  const navigate = useNavigate()
  return <HomePage onOpenWorkspace={() => navigate('/app/feed')} />
}

export default function App() {
  return (
    <Suspense fallback={<main className="dc-boot"><Spinner label="Loading…" /></main>}>
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/p/:publicationId" element={<PublicationPage />} />
      <Route path="/app" element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="feed" replace />} />
          <Route path="feed" element={<FeedPage />} />
          <Route path="bookmarks" element={<FeedPage variant="bookmarks" />} />
          <Route path="tags/:tag" element={<FeedPage variant="tag" />} />
          <Route path="post/:postId" element={<PostDetailPage />} />
          <Route path="u/:username" element={<ProfilePage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="dashboard" element={<DashboardRoute />} />
          <Route path="marketplace" element={<MarketplaceRoute />} />
          <Route path="wallet" element={<WalletRoute />} />
          <Route path="projects" element={<ProjectsIndex />} />
          <Route path="projects/:projectId" element={<ProjectScope />}>
            <Route index element={<ProjectOverviewRoute />} />
            <Route path="studio" element={<StudioRoute />} />
            <Route path="case-study" element={<CaseStudyRoute />} />
            <Route path="sources" element={<SourcesRoute />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  )
}
