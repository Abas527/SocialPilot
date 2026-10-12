import { useState } from 'react'
import type { FormEvent } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BadgeCheck, Clock, Pencil, UserRound } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { PostCard } from '../components/community/PostCard'
import { PersonRow } from '../components/community/PeopleList'
import { Avatar, AvailabilityPill, EmptyState, Spinner } from '../components/community/bits'
import { useFlash } from '../components/Flash'
import { useFollowMutation, useInfinitePosts, useProfile } from '../hooks/usePosts'
import { errorMessage, localTimeIn, shortAddress } from '../lib/format'
import { getFollows, updateProfile } from '../services/community'
import type { Availability, CreatorProfile } from '../types'

const TABS = ['posts', 'followers', 'following'] as const

function EditProfile({ profile, onClose }: { profile: CreatorProfile; onClose: () => void }) {
  const qc = useQueryClient()
  const flash = useFlash()
  const auth = useAuth()
  const [displayName, setDisplayName] = useState(profile.display_name)
  const [bio, setBio] = useState(profile.bio)
  const [skills, setSkills] = useState(profile.skills.join(', '))
  const [timezone, setTimezone] = useState(profile.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone)
  const [availability, setAvailability] = useState<Availability>(profile.availability)

  const save = useMutation({
    mutationFn: () => updateProfile({
      display_name: displayName.trim(),
      bio,
      skills: skills.split(',').map((s) => s.trim()).filter(Boolean),
      timezone,
      availability,
    }),
    onSuccess: (updated) => {
      qc.setQueryData(['profile', updated.username], updated)
      qc.setQueryData(['profile', 'me'], updated)
      void qc.invalidateQueries({ queryKey: ['posts'] })
      auth.updateUser({ display_name: updated.display_name })
      flash.showNotice('Profile updated.')
      onClose()
    },
    onError: (cause) => flash.showError(errorMessage(cause)),
  })

  return (
    <div className="dc-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <form className="dc-modal" role="dialog" aria-modal="true" aria-label="Edit profile"
        onSubmit={(event: FormEvent) => { event.preventDefault(); save.mutate() }}>
        <h2>Edit profile</h2>
        <label className="dc-field">Display name<input value={displayName} maxLength={100} required onChange={(e) => setDisplayName(e.target.value)} /></label>
        <label className="dc-field">Bio<textarea className="dc-textarea" rows={3} maxLength={500} value={bio} onChange={(e) => setBio(e.target.value)} /></label>
        <label className="dc-field">Skills <small>comma separated, up to 15</small>
          <input value={skills} placeholder="python, react, devops" onChange={(e) => setSkills(e.target.value)} /></label>
        <label className="dc-field">Timezone <small>e.g. Asia/Kathmandu or UTC+5:45</small>
          <input value={timezone} maxLength={64} onChange={(e) => setTimezone(e.target.value)} /></label>
        <label className="dc-field">Availability
          <select value={availability} onChange={(e) => setAvailability(e.target.value as Availability)}>
            <option value="none">Not specified</option>
            <option value="open_to_work">Open to work</option>
            <option value="hiring">Hiring</option>
            <option value="open_to_collab">Open to collaborate</option>
          </select>
        </label>
        <div className="dc-row">
          <button className="dc-btn dc-btn-primary" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save'}</button>
          <button type="button" className="dc-btn" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </div>
  )
}

function PeopleTab({ username, kind }: { username: string; kind: 'followers' | 'following' }) {
  const list = useQuery({ queryKey: ['follows', username, kind], queryFn: () => getFollows(username, kind) })
  if (list.isLoading) return <Spinner />
  if (!list.data?.length) return <EmptyState icon={<UserRound size={22} />} title={kind === 'followers' ? 'No followers yet' : 'Not following anyone yet'} />
  return <div className="dc-card">{list.data.map((person) => <PersonRow key={person.user_id} person={person} />)}</div>
}

export function ProfilePage() {
  const { username = '' } = useParams()
  const [search, setSearch] = useSearchParams()
  const { user } = useAuth()
  const profile = useProfile(username)
  const follow = useFollowMutation()
  const [editing, setEditing] = useState(false)
  const tab = TABS.find((t) => t === search.get('tab')) ?? 'posts'
  const posts = useInfinitePosts({ author: username })

  if (profile.isLoading) return <Spinner label="Loading profile…" />
  if (profile.isError || !profile.data) return <EmptyState icon={<UserRound size={22} />} title="Profile not found">Check the username and try again.</EmptyState>
  const p = profile.data
  const mine = p.user_id === user?.user_id
  const localTime = localTimeIn(p.timezone)
  const items = posts.data?.pages.flat() ?? []

  return (
    <div className="dc-main dc-profile">
      <section className="dc-card dc-profile-head">
        <Avatar name={p.display_name} size={72} />
        <div className="dc-profile-copy">
          <h1>{p.display_name}{p.is_demo && <span className="dc-pill">Sample</span>}</h1>
          <span className="dc-handle">@{p.username}</span>
          <AvailabilityPill value={p.availability} />
          {p.bio && <p>{p.bio}</p>}
          <div className="dc-profile-facts">
            {p.timezone && <span><Clock size={13} aria-hidden="true" /> {p.timezone}{localTime && ` · ${localTime} local`}</span>}
            {p.wallet_address && <span title="Wallet ownership verified by signature"><BadgeCheck size={13} aria-hidden="true" /> Wallet {shortAddress(p.wallet_address)}</span>}
          </div>
          {p.skills.length > 0 && <ul className="dc-tags" aria-label="Skills">{p.skills.map((s) => <li key={s}><span>{s}</span></li>)}</ul>}
        </div>
        <div className="dc-profile-actions">
          {mine ? (
            <button className="dc-btn" onClick={() => setEditing(true)}><Pencil size={14} aria-hidden="true" /> Edit profile</button>
          ) : (
            <button className={p.is_following ? 'dc-btn dc-following' : 'dc-btn dc-btn-primary'} aria-pressed={p.is_following} disabled={follow.isPending}
              onClick={() => follow.mutate({ username: p.username, on: !p.is_following })}>
              {p.is_following ? 'Following' : 'Follow'}
            </button>
          )}
        </div>
      </section>

      <div className="dc-tabs" role="tablist" aria-label="Profile sections">
        <button role="tab" aria-selected={tab === 'posts'} onClick={() => setSearch({}, { replace: true })}>Posts</button>
        <button role="tab" aria-selected={tab === 'followers'} onClick={() => setSearch({ tab: 'followers' }, { replace: true })}>{p.follower_count} followers</button>
        <button role="tab" aria-selected={tab === 'following'} onClick={() => setSearch({ tab: 'following' }, { replace: true })}>{p.following_count} following</button>
      </div>

      {tab === 'posts' ? (
        posts.isLoading ? <Spinner /> : items.length === 0 ? (
          <EmptyState icon={<UserRound size={22} />} title={mine ? 'You have not posted yet' : 'No posts yet'}>
            {mine ? 'Share what you are building from the Home feed.' : undefined}
          </EmptyState>
        ) : (
          <>
            {items.map((post) => <PostCard key={post.post_id} post={post} />)}
            {posts.hasNextPage && <button className="dc-btn dc-center" onClick={() => void posts.fetchNextPage()} disabled={posts.isFetchingNextPage}>Load more</button>}
          </>
        )
      ) : <PeopleTab username={p.username} kind={tab} />}

      {editing && <EditProfile profile={p} onClose={() => setEditing(false)} />}
    </div>
  )
}
