import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Bell, Heart, HeartHandshake, MessageCircle, UserPlus } from 'lucide-react'
import { EmptyState, Spinner } from '../components/community/bits'
import { useMarkAllRead, useNotifications } from '../hooks/usePosts'
import { timeAgo } from '../lib/format'
import type { AppNotification } from '../types'

const META = {
  follow: { Icon: UserPlus, verb: 'started following you' },
  like: { Icon: Heart, verb: 'liked your post' },
  comment: { Icon: MessageCircle, verb: 'commented on your post' },
  tip: { Icon: HeartHandshake, verb: 'tipped you' },
} as const

function destination(n: AppNotification): string {
  return n.post_id ? `/app/post/${n.post_id}${n.type === 'comment' ? '#comments' : n.type === 'tip' ? '#tips' : ''}` : `/app/u/${n.actor.username}`
}

export function NotificationsPage() {
  const list = useNotifications()
  const markAll = useMarkAllRead()
  const unread = list.data?.filter((n) => !n.read).length ?? 0
  const { mutate } = markAll

  // Let people see what is new before it is marked as read.
  useEffect(() => {
    if (!unread) return
    const timer = setTimeout(() => mutate(), 2500)
    return () => clearTimeout(timer)
  }, [unread, mutate])

  return (
    <div className="dc-main dc-narrow">
      <header className="dc-page-head">
        <span className="dc-page-icon"><Bell size={20} /></span>
        <div><h1>Notifications</h1><p>Follows, likes, comments and tips.</p></div>
        {unread > 0 && <button className="dc-btn dc-btn-small dc-push" onClick={() => mutate()}>Mark all read</button>}
      </header>
      {list.isLoading ? <Spinner /> : !list.data?.length ? (
        <EmptyState icon={<Bell size={22} />} title="You are all caught up">When someone interacts with you, it shows up here.</EmptyState>
      ) : (
        <ul className="dc-notes">
          {list.data.map((n) => {
            const { Icon, verb } = META[n.type]
            return (
              <li key={n.notification_id} className={n.read ? '' : 'unread'}>
                <Link to={destination(n)}>
                  <span className={`dc-note-icon dc-note-${n.type}`}><Icon size={15} aria-hidden="true" /></span>
                  <span className="dc-note-copy">
                    <span><strong>{n.actor.display_name}</strong> {verb}</span>
                    {n.post_excerpt && <small>“{n.post_excerpt}”</small>}
                  </span>
                  <time dateTime={n.created_at}>{timeAgo(n.created_at)}</time>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
