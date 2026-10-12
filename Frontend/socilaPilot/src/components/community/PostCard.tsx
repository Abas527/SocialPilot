import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Bookmark, ExternalLink, FolderGit2, Heart, HeartHandshake, Link2, MessageCircle, MoreHorizontal, Share2, UserPlus,
} from 'lucide-react'
import { useCurrentUser } from '../../auth/AuthContext'
import {
  useBookmarkMutation, useDeletePost, useEditPost, useFollowMutation, useLikeMutation,
} from '../../hooks/usePosts'
import { compactNumber, errorMessage, formatEth, fullDate, hostOf, timeAgo } from '../../lib/format'
import type { Post } from '../../types'
import { useFlash } from '../Flash'
import { Markdown } from '../Markdown'
import { Avatar, AvailabilityPill, CaseStudyRibbon, PassportBadge, TagChips } from './bits'
import { TipModal } from './TipModal'

const CLAMP_CHARS = 700

export function PostCard({ post, detail = false }: { post: Post; detail?: boolean }) {
  const me = useCurrentUser()
  const navigate = useNavigate()
  const flash = useFlash()
  const like = useLikeMutation()
  const bookmark = useBookmarkMutation()
  const follow = useFollowMutation()
  const remove = useDeletePost()
  const edit = useEditPost()
  const [tipping, setTipping] = useState(false)
  const [menu, setMenu] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(post.body)
  const [expanded, setExpanded] = useState(detail)
  const mine = post.author.user_id === me.user_id
  const long = !expanded && post.body.length > CLAMP_CHARS
  const tipsTotal = BigInt(post.tip_total_wei || '0')

  // Whole-card click opens the thread, but never steals clicks on links, buttons,
  // code blocks or an active text selection.
  const openThread = (event: React.MouseEvent<HTMLElement>) => {
    if (detail) return
    const target = event.target as HTMLElement
    if (target.closest('a,button,pre,code,input,textarea,select')) return
    if (window.getSelection()?.toString()) return
    navigate(`/app/post/${post.post_id}`)
  }

  const share = async () => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/app/post/${post.post_id}`)
      flash.showNotice('Link copied.')
    } catch { flash.showError('Could not copy the link.') }
  }

  const saveEdit = () => edit.mutate({ id: post.post_id, patch: { body: draft.trim() } }, {
    onSuccess: () => setEditing(false),
    onError: (cause) => flash.showError(errorMessage(cause)),
  })

  const del = () => {
    if (!window.confirm('Delete this post? Its comments and likes will be removed too.')) return
    remove.mutate(post.post_id, {
      onSuccess: () => { if (detail) navigate('/app/feed') },
      onError: (cause) => flash.showError(errorMessage(cause)),
    })
  }

  return (
    <article className="dc-post" aria-label={`Post by ${post.author.display_name}`}>
      <header className="dc-post-head">
        <Link to={`/app/u/${post.author.username}`} aria-label={`${post.author.display_name}'s profile`}><Avatar name={post.author.display_name} /></Link>
        <div className="dc-post-who">
          <Link to={`/app/u/${post.author.username}`} className="dc-name">{post.author.display_name}</Link>
          <span className="dc-handle">@{post.author.username}</span>
          <AvailabilityPill value={post.author.availability} />
          {post.author.is_demo && <span className="dc-pill">Sample</span>}
        </div>
        <Link to={`/app/post/${post.post_id}`} className="dc-time" title={fullDate(post.created_at)}>
          <time dateTime={post.created_at}>{timeAgo(post.created_at)}</time>{post.edited && ' · edited'}
        </Link>
        {!mine && !post.author.is_following && (
          <button className="dc-btn dc-btn-small" disabled={follow.isPending}
            onClick={() => follow.mutate({ username: post.author.username, on: true })}>
            <UserPlus size={13} aria-hidden="true" /> Follow
          </button>
        )}
        {mine && (
          <div className="dc-menu-wrap">
            <button className="dc-icon-btn" aria-label="Post options" aria-expanded={menu} onClick={() => setMenu((v) => !v)}><MoreHorizontal size={17} /></button>
            {menu && (
              <div className="dc-menu" role="menu" onMouseLeave={() => setMenu(false)}>
                <button role="menuitem" onClick={() => { setEditing(true); setDraft(post.body); setMenu(false) }}>Edit</button>
                <button role="menuitem" className="danger" onClick={() => { setMenu(false); del() }}>Delete</button>
              </div>
            )}
          </div>
        )}
      </header>

      {post.evidence && <CaseStudyRibbon evidence={post.evidence} />}
      {editing ? (
        <div className="dc-edit">
          <textarea className="dc-textarea" value={draft} rows={6} maxLength={8000} aria-label="Edit post" onChange={(event) => setDraft(event.target.value)} />
          <div className="dc-row">
            <button className="dc-btn dc-btn-primary" disabled={!draft.trim() || edit.isPending} onClick={saveEdit}>Save</button>
            <button className="dc-btn" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <div className={`${long ? 'dc-body dc-body-clamped' : 'dc-body'}${detail ? '' : ' dc-body-link'}`} onClick={openThread}>
          {post.format === 'markdown' ? <Markdown>{post.body}</Markdown> : <p className="dc-plain">{post.body}</p>}
          {long && <button className="dc-more" onClick={() => setExpanded(true)}>Show more</button>}
        </div>
      )}

      {post.evidence?.kind === 'case_study' && post.evidence.publication_id && (
        <Link to={`/p/${post.evidence.publication_id}`} className="dc-case-link">Read the full case study with its evidence →</Link>
      )}
      {post.link_url && (
        <a className="dc-link-card" href={post.link_url} target="_blank" rel="noopener noreferrer nofollow ugc">
          <Link2 size={15} aria-hidden="true" /><span>{hostOf(post.link_url)}</span><ExternalLink size={13} aria-hidden="true" />
        </a>
      )}
      <TagChips tags={post.tags} />
      <div className="dc-meta">
        {post.project && (
          <span className="dc-project"><FolderGit2 size={13} aria-hidden="true" />
            {post.project.repository_url
              ? <a href={post.project.repository_url} target="_blank" rel="noopener noreferrer">{post.project.name}</a>
              : post.project.name}
          </span>
        )}
        {post.evidence && <PassportBadge evidence={post.evidence} />}
      </div>

      <footer className="dc-actions">
        <button className={post.liked_by_me ? 'on like' : ''} aria-pressed={post.liked_by_me} aria-label={`${post.liked_by_me ? 'Unlike' : 'Like'}, ${post.like_count} likes`}
          onClick={() => like.mutate({ post, on: !post.liked_by_me })}>
          <Heart size={17} fill={post.liked_by_me ? 'currentColor' : 'none'} aria-hidden="true" /> {compactNumber(post.like_count)}
        </button>
        <Link to={`/app/post/${post.post_id}#comments`} aria-label={`${post.comment_count} comments`}>
          <MessageCircle size={17} aria-hidden="true" /> {compactNumber(post.comment_count)}
        </Link>
        <button className={post.bookmarked_by_me ? 'on' : ''} aria-pressed={post.bookmarked_by_me} aria-label={post.bookmarked_by_me ? 'Remove bookmark' : 'Bookmark'}
          onClick={() => bookmark.mutate({ post, on: !post.bookmarked_by_me })}>
          <Bookmark size={17} fill={post.bookmarked_by_me ? 'currentColor' : 'none'} aria-hidden="true" />
        </button>
        <button onClick={() => void share()} aria-label="Copy link"><Share2 size={17} aria-hidden="true" /></button>
        <span className="dc-grow" />
        {post.tip_count > 0 && (
          <Link to={`/app/post/${post.post_id}#tips`} className="dc-tip-total" title="Verified on-chain tips">
            {formatEth(tipsTotal)} ETH · {post.tip_count} {post.tip_count === 1 ? 'tip' : 'tips'}
          </Link>
        )}
        {!mine && !post.author.is_demo && (
          <button className="dc-tip-btn" onClick={() => setTipping(true)}><HeartHandshake size={16} aria-hidden="true" /> Tip</button>
        )}
      </footer>
      {tipping && <TipModal post={post} onClose={() => setTipping(false)} />}
    </article>
  )
}
