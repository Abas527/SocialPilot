import { Link } from 'react-router-dom'
import { BadgeCheck, Briefcase, FileText, Handshake, ShieldAlert, ShieldCheck, Users } from 'lucide-react'
import { initial } from '../../lib/format'
import type { Availability, PostEvidence } from '../../types'

export function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  return (
    <span className="dc-avatar" style={{ width: size, height: size, fontSize: size * 0.4 }} aria-hidden="true">
      {initial(name)}
    </span>
  )
}

const AVAILABILITY_META: Record<Exclude<Availability, 'none'>, { label: string; Icon: typeof Briefcase; tone: string }> = {
  open_to_work: { label: 'Open to work', Icon: Briefcase, tone: 'green' },
  hiring: { label: 'Hiring', Icon: Users, tone: 'amber' },
  open_to_collab: { label: 'Open to collaborate', Icon: Handshake, tone: 'violet' },
}

export function AvailabilityPill({ value }: { value: Availability }) {
  if (value === 'none') return null
  const { label, Icon, tone } = AVAILABILITY_META[value]
  return <span className={`dc-pill dc-pill-${tone}`}><Icon size={12} aria-hidden="true" />{label}</span>
}

export function TagChips({ tags }: { tags: string[] }) {
  if (!tags.length) return null
  return (
    <ul className="dc-tags" aria-label="Tags">
      {tags.map((tag) => (
        <li key={tag}><Link to={`/app/tags/${encodeURIComponent(tag)}`}>#{tag}</Link></li>
      ))}
    </ul>
  )
}

export function EvidenceBadge({ supported, total }: { supported: number; total: number }) {
  if (!total) return null
  const all = supported === total
  return (
    <span
      className={`dc-evidence ${all ? 'dc-evidence-full' : 'dc-evidence-partial'}`}
      title="Claims in this post were checked against the author's project sources when it was published. This is a lexical check, not proof."
    >
      <BadgeCheck size={14} aria-hidden="true" />
      {supported} of {total} claims backed by project sources
    </span>
  )
}

/** Badge on a post. With an evidence passport it links to the public page anyone can inspect. */
export function PassportBadge({ evidence }: { evidence: PostEvidence }) {
  if (!evidence.publication_id) return <EvidenceBadge supported={evidence.supported} total={evidence.total} />
  const repo = evidence.trust_level === 'repository'
  const Icon = repo ? ShieldCheck : ShieldAlert
  const ratio = evidence.total ? `${evidence.supported} of ${evidence.total} claims ` : ''
  const label = repo
    ? `${ratio}linked to repository code${evidence.ownership_verified ? ' · owner verified' : ''}`
    : `${ratio || 'Statements '}matched to the author's notes · self-reported`
  return (
    <Link to={`/p/${evidence.publication_id}`} className={`dc-evidence ${repo ? 'dc-evidence-full' : 'dc-evidence-notes'}`}
      title="Open the evidence passport: every statement with the source text behind it. This is a keyword match, not proof.">
      <Icon size={14} aria-hidden="true" />{label} · View evidence
    </Link>
  )
}

export function CaseStudyRibbon({ evidence }: { evidence: PostEvidence }) {
  if (evidence.kind !== 'case_study' || !evidence.publication_id) return null
  return <span className="dc-ribbon"><FileText size={13} aria-hidden="true" /> Case study</span>
}

export function EmptyState({ icon, title, children }: { icon: React.ReactNode; title: string; children?: React.ReactNode }) {
  return (
    <div className="dc-empty" role="status">
      <span className="dc-empty-icon">{icon}</span>
      <h3>{title}</h3>
      {children && <p>{children}</p>}
    </div>
  )
}

export function Spinner({ label }: { label?: string }) {
  return <div className="dc-loading" role="status"><span className="spinner" />{label ?? 'Loading…'}</div>
}
