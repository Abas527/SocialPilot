import { Link } from 'react-router-dom'
import { Flame, Users } from 'lucide-react'
import { useSuggestedProfiles, useTrendingTags } from '../../hooks/usePosts'
import { PersonRow } from './PeopleList'

export function RightRail() {
  const tags = useTrendingTags()
  const people = useSuggestedProfiles()
  const suggestions = (people.data ?? []).filter((person) => !person.is_following)
  return (
    <aside className="dc-rail" aria-label="Discover">
      <section className="dc-card">
        <h2><Flame size={15} aria-hidden="true" /> Trending this week</h2>
        {tags.isLoading ? <p className="dc-muted">Loading…</p> : tags.data?.length ? (
          <ul className="dc-trending">
            {tags.data.map((item) => (
              <li key={item.tag}>
                <Link to={`/app/tags/${encodeURIComponent(item.tag)}`}>#{item.tag}</Link>
                <small>{item.post_count} {item.post_count === 1 ? 'post' : 'posts'}</small>
              </li>
            ))}
          </ul>
        ) : <p className="dc-muted">Tags show up here once people start using them.</p>}
      </section>
      <section className="dc-card">
        <h2><Users size={15} aria-hidden="true" /> Who to follow</h2>
        {people.isLoading ? <p className="dc-muted">Loading…</p> : suggestions.length ? (
          suggestions.map((person) => <PersonRow key={person.user_id} person={person} compact />)
        ) : <p className="dc-muted">You follow everyone here. Search the Latest feed to find more builders.</p>}
      </section>
    </aside>
  )
}
