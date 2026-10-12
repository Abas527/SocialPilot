import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, HeartHandshake, MessageCircle, Sparkles, Trash2 } from 'lucide-react'
import { useCurrentUser } from '../auth/AuthContext'
import { PostCard } from '../components/community/PostCard'
import { RightRail } from '../components/community/RightRail'
import { Avatar, EmptyState, Spinner } from '../components/community/bits'
import { useFlash } from '../components/Flash'
import { useAddComment, useComments, useDeleteComment, usePost, usePostTips } from '../hooks/usePosts'
import { useJobs } from '../jobs/JobsProvider'
import { errorMessage, formatEth, timeAgo } from '../lib/format'

type Summary = { tldr: string; key_points: string[]; open_questions: string[] }

export function PostDetailPage() {
  const { postId = '' } = useParams()
  const me = useCurrentUser()
  const flash = useFlash()
  const jobs = useJobs()
  const post = usePost(postId)
  const comments = useComments(postId)
  const tips = usePostTips(postId, Boolean(post.data?.tip_count))
  const add = useAddComment(postId)
  const del = useDeleteComment(postId)
  const [text, setText] = useState('')
  const [summary, setSummary] = useState<Summary | null>(null)
  const [summarizing, setSummarizing] = useState(false)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!text.trim()) return
    add.mutate(text.trim(), {
      onSuccess: () => setText(''),
      onError: (cause) => flash.showError(errorMessage(cause)),
    })
  }

  const summarize = async () => {
    setSummarizing(true)
    try {
      const job = await jobs.run<Summary>({ kind: 'summarize_thread', post_id: postId }, { label: 'Summarizing the discussion' })
      setSummary(job.result)
    } catch (cause) {
      flash.showError(errorMessage(cause))
    } finally {
      setSummarizing(false)
    }
  }

  if (post.isLoading) return <Spinner label="Loading post…" />
  if (post.isError || !post.data) {
    return <EmptyState icon={<MessageCircle size={22} />} title="Post not found">It may have been deleted. <Link className="dc-link" to="/app/feed">Back to home</Link></EmptyState>
  }
  const p = post.data

  return (
    <div className="dc-layout">
      <div className="dc-main">
        <Link to="/app/feed" className="dc-back"><ArrowLeft size={15} aria-hidden="true" /> Back</Link>
        <PostCard post={p} detail />

        {p.tip_count > 0 && (
          <section className="dc-card" id="tips" aria-label="Supporters">
            <h2><HeartHandshake size={15} aria-hidden="true" /> Supporters</h2>
            {tips.data?.map((tip) => (
              <div key={tip.tip_id} className="dc-supporter">
                <Link to={`/app/u/${tip.sender_username}`} className="dc-name">{tip.sender_display_name}</Link>
                <strong>{formatEth(tip.amount_wei)} ETH</strong>
                {tip.message && <q>{tip.message}</q>}
                <small>{timeAgo(tip.verified_at)}</small>
              </div>
            ))}
          </section>
        )}

        <section className="dc-card" id="comments" aria-label="Comments">
          <div className="dc-card-head">
            <h2><MessageCircle size={15} aria-hidden="true" /> {p.comment_count} {p.comment_count === 1 ? 'comment' : 'comments'}</h2>
            {p.comment_count >= 2 && (
              <button className="dc-btn dc-btn-small" onClick={() => void summarize()} disabled={summarizing}>
                <Sparkles size={13} aria-hidden="true" /> {summarizing ? 'Summarizing…' : 'Summarize thread'}
              </button>
            )}
          </div>
          {summary && (
            <div className="dc-suggestion" role="region" aria-label="AI summary">
              <strong>TL;DR</strong><p>{summary.tldr}</p>
              {summary.key_points.length > 0 && <ul>{summary.key_points.map((k) => <li key={k}>{k}</li>)}</ul>}
              {summary.open_questions.length > 0 && <><strong>Open questions</strong><ul>{summary.open_questions.map((k) => <li key={k}>{k}</li>)}</ul></>}
              <small className="dc-muted">AI-generated from the thread. It can miss nuance.</small>
            </div>
          )}
          <form className="dc-comment-form" onSubmit={submit}>
            <Avatar name={me.display_name} size={32} />
            <input value={text} maxLength={1000} placeholder="Add a comment…" aria-label="Add a comment" onChange={(event) => setText(event.target.value)} />
            <button className="dc-btn dc-btn-primary" disabled={!text.trim() || add.isPending}>Comment</button>
          </form>
          {comments.isLoading ? <Spinner /> : comments.data?.map((c) => (
            <div key={c.comment_id} className="dc-comment">
              <Link to={`/app/u/${c.author.username}`}><Avatar name={c.author.display_name} size={32} /></Link>
              <div>
                <div className="dc-comment-head">
                  <Link to={`/app/u/${c.author.username}`} className="dc-name">{c.author.display_name}</Link>
                  <small>{timeAgo(c.created_at)}</small>
                </div>
                <p>{c.body}</p>
              </div>
              {(c.author.user_id === me.user_id || p.author.user_id === me.user_id) && (
                <button className="dc-icon-btn" aria-label="Delete comment" onClick={() => del.mutate(c.comment_id)}><Trash2 size={14} /></button>
              )}
            </div>
          ))}
        </section>
      </div>
      <RightRail />
    </div>
  )
}
