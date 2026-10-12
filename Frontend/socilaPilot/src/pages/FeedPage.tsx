import { useEffect, useRef } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Bookmark, Hash, Sparkles, UsersRound } from 'lucide-react'
import { Composer } from '../components/community/Composer'
import { PostCard } from '../components/community/PostCard'
import { RightRail } from '../components/community/RightRail'
import { EmptyState, Spinner } from '../components/community/bits'
import { useInfinitePosts } from '../hooks/usePosts'
import { errorMessage } from '../lib/format'
import type { FeedParams } from '../services/community'

type Variant = 'home' | 'tag' | 'bookmarks'
const TABS = [
  { id: 'following', label: 'Following', params: { scope: 'following', sort: 'new' } },
  { id: 'latest', label: 'Latest', params: { scope: 'all', sort: 'new' } },
  { id: 'top', label: 'Top', params: { scope: 'all', sort: 'top' } },
] as const

export function FeedPage({ variant = 'home' }: { variant?: Variant }) {
  const { tag = '' } = useParams()
  const [search, setSearch] = useSearchParams()
  const navigate = useNavigate()
  const tab = TABS.find((t) => t.id === search.get('tab')) ?? TABS[1]

  const params: FeedParams = variant === 'bookmarks' ? { bookmarks: true }
    : variant === 'tag' ? { ...tab.params, tag }
    : tab.params
  const feed = useInfinitePosts(params)
  const posts = feed.data?.pages.flat() ?? []

  const sentinel = useRef<HTMLDivElement>(null)
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = feed
  useEffect(() => {
    const node = sentinel.current
    if (!node || !hasNextPage) return
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !isFetchingNextPage) void fetchNextPage()
    }, { rootMargin: '400px' })
    observer.observe(node)
    return () => observer.disconnect()
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])

  const heading = variant === 'bookmarks' ? { icon: <Bookmark size={20} />, title: 'Bookmarks', sub: 'Posts you saved to read later.' }
    : variant === 'tag' ? { icon: <Hash size={20} />, title: `#${tag}`, sub: `Posts tagged ${tag}.` }
    : { icon: <UsersRound size={20} />, title: 'Home', sub: 'What builders are shipping, learning and asking.' }

  return (
    <div className="dc-layout">
      <div className="dc-main">
        <header className="dc-page-head">
          <span className="dc-page-icon">{heading.icon}</span>
          <div><h1>{heading.title}</h1><p>{heading.sub}</p></div>
        </header>

        {variant === 'home' && <Composer compact />}

        {variant !== 'bookmarks' && (
          <div className="dc-tabs" role="tablist" aria-label="Feed">
            {TABS.map((t) => (
              <button key={t.id} role="tab" aria-selected={t.id === tab.id}
                onClick={() => setSearch(t.id === 'latest' ? {} : { tab: t.id }, { replace: true })}>{t.label}</button>
            ))}
          </div>
        )}

        {feed.isLoading ? <Spinner label="Loading posts…" />
          : feed.isError ? <p role="alert" className="dc-error">{errorMessage(feed.error, 'Could not load posts.')} <button className="dc-link" onClick={() => void feed.refetch()}>Retry</button></p>
          : posts.length === 0 ? (
            variant === 'bookmarks' ? (
              <EmptyState icon={<Bookmark size={22} />} title="Nothing saved yet">Tap the bookmark on any post to keep it here.</EmptyState>
            ) : tab.id === 'following' && variant === 'home' ? (
              <EmptyState icon={<UsersRound size={22} />} title="Your following feed is empty">
                Follow a few builders to see their posts here.{' '}
                <button className="dc-link" onClick={() => setSearch({}, { replace: true })}>Browse the latest posts</button>
              </EmptyState>
            ) : (
              <EmptyState icon={<Sparkles size={22} />} title={variant === 'tag' ? `No posts tagged #${tag} yet` : 'No posts yet'}>
                {variant === 'tag' ? <button className="dc-link" onClick={() => navigate('/app/feed')}>Back to home</button> : 'Be the first to share what you are working on.'}
              </EmptyState>
            )
          ) : (
            <>
              {posts.map((post) => <PostCard key={post.post_id} post={post} />)}
              <div ref={sentinel} />
              {feed.isFetchingNextPage && <Spinner label="Loading more…" />}
              {!hasNextPage && posts.length >= 10 && <p className="dc-end">You are all caught up.</p>}
            </>
          )}
      </div>
      <RightRail />
    </div>
  )
}
