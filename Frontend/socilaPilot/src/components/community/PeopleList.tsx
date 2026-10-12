import { Link } from 'react-router-dom'
import { useCurrentUser } from '../../auth/AuthContext'
import { useFollowMutation } from '../../hooks/usePosts'
import type { CreatorProfile } from '../../types'
import { Avatar, AvailabilityPill } from './bits'

export function PersonRow({ person, compact = false }: { person: CreatorProfile; compact?: boolean }) {
  const me = useCurrentUser()
  const follow = useFollowMutation()
  return (
    <div className="dc-person">
      <Link to={`/app/u/${person.username}`} aria-label={`${person.display_name}'s profile`}><Avatar name={person.display_name} size={compact ? 34 : 42} /></Link>
      <div className="dc-person-copy">
        <Link to={`/app/u/${person.username}`} className="dc-name">{person.display_name}</Link>
        <span className="dc-handle">@{person.username}</span>
        {!compact && person.bio && <p>{person.bio}</p>}
        {!compact && <AvailabilityPill value={person.availability} />}
      </div>
      {person.user_id !== me.user_id && (
        <button
          className={person.is_following ? 'dc-btn dc-btn-small dc-following' : 'dc-btn dc-btn-small dc-btn-primary'}
          disabled={follow.isPending}
          aria-pressed={person.is_following}
          onClick={() => follow.mutate({ username: person.username, on: !person.is_following })}
        >
          {person.is_following ? 'Following' : 'Follow'}
        </button>
      )}
    </div>
  )
}
