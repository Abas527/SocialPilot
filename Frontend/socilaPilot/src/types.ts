export type ProjectSummary = {
  project_id: string
  name: string
  repository_url: string | null
  created_at: string
}

export type EvidenceClaim = {
  text: string
  status: 'supported' | 'needs_review' | 'unsupported'
  note?: string | null
  evidence?: {
    path: string
    start_line?: number | null
    end_line?: number | null
    excerpt?: string
    source_url?: string | null
  }[]
}

export type LinkedInDraft = {
  angle: string
  hook: string
  insight: string
  body: string
  takeaway: string
  question?: string | null
  needs_user_input?: string | null
  verified_claims?: EvidenceClaim[]
  review_status?: 'needs_review' | 'preliminary_support'
}

export type LinkedInFormat = 'standard' | 'concise' | 'technical_walkthrough' | 'project_update'

export const LINKEDIN_FORMATS: { id: LinkedInFormat; title: string; description: string }[] = [
  { id: 'standard', title: 'Full post', description: 'Hook, insight, story, and takeaway.' },
  { id: 'concise', title: 'Concise', description: 'A shorter version for a quick update.' },
  { id: 'technical_walkthrough', title: 'Technical walkthrough', description: 'Lead with the engineering detail.' },
  { id: 'project_update', title: 'Project update', description: 'Frame the work as an update and lesson.' },
]

export type CaseStudy = {
  title: string
  summary: string
  problem: string
  architecture: string
  implementation: string
  challenges: string
  results: string
  limitations: string
  future_work: string
  verified_claims?: EvidenceClaim[]
  review_status?: 'needs_review' | 'preliminary_support'
}

export type ProjectFinding = {
  finding_id: string
  kind: string
  text: string
  status: 'supported' | 'needs_review' | 'unsupported'
  note?: string | null
  evidence: {
    path: string
    start_line?: number | null
    end_line?: number | null
    source_url?: string | null
    excerpt: string
  }[]
}

export type ProjectProfile = {
  name: string
  summary: string
  problem?: string
  technologies?: string[]
  architecture?: string[]
  challenges?: string[]
  results?: string[]
  unknowns?: string[]
  findings?: ProjectFinding[]
}

export type Artifact<T> = {
  generated: T
  edited: T | null
  updated_at?: string
}

export type WorkflowArtifact<T> =
  | { status: 'generated'; artifact: T }
  | { status: 'failed'; error: string }

export type WorkflowGenerationResult = {
  project_id: string
  analysis: ProjectProfile
  outputs: {
    linkedin: Record<string, WorkflowArtifact<LinkedInDraft>>
    case_study: WorkflowArtifact<CaseStudy>
  }
}

export type ProjectDetail = ProjectSummary & {
  commit_sha?: string | null
  profile: ProjectProfile | null
  documents: { source_id: string; path: string; content: string; source_url?: string | null }[]
  artifacts: Record<string, Artifact<LinkedInDraft | CaseStudy>>
}

export type Page = 'Personal dashboard' | 'Overview' | 'Content studio' | 'Case studies' | 'Sources' | 'Community' | 'Marketplace' | 'Wallet'
export type AuthUser = {
  user_id: string
  email: string
  display_name: string
}
export type Availability = 'none' | 'open_to_work' | 'hiring' | 'open_to_collab'
export const AVAILABILITY_OPTIONS: { id: Availability; label: string; hint: string }[] = [
  { id: 'none', label: 'Not signalling', hint: 'No badge on your profile.' },
  { id: 'open_to_work', label: 'Open to work', hint: 'Show that you are looking for roles or contracts.' },
  { id: 'hiring', label: 'Hiring', hint: 'Show that you are hiring developers.' },
  { id: 'open_to_collab', label: 'Open to collaborate', hint: 'Invite open-source or side-project collaboration.' },
]
export type CreatorProfile = {
  user_id: string
  username: string
  display_name: string
  bio: string
  is_demo: boolean
  wallet_address?: string | null
  follower_count: number
  following_count: number
  is_following: boolean
  skills: string[]
  timezone: string
  availability: Availability
}
export type PostAuthor = {
  user_id: string
  username: string
  display_name: string
  bio: string
  is_demo: boolean
  availability: Availability
  follower_count: number
  is_following: boolean
}
export type Post = {
  post_id: string
  body: string
  format: 'plain' | 'markdown'
  created_at: string
  updated_at: string | null
  edited: boolean
  tags: string[]
  link_url: string | null
  project: { project_id: string; name: string; repository_url: string | null } | null
  evidence: PostEvidence | null
  like_count: number
  comment_count: number
  liked_by_me: boolean
  bookmarked_by_me: boolean
  tip_count: number
  tip_total_wei: string
  author: PostAuthor
}
export type SocialPost = Post
export type PostComment = {
  comment_id: string
  post_id: string
  body: string
  created_at: string
  author: { user_id: string; username: string; display_name: string }
}
export type AppNotification = {
  notification_id: string
  type: 'follow' | 'like' | 'comment' | 'tip'
  post_id: string | null
  post_excerpt: string | null
  ref_id: string | null
  created_at: string
  read: boolean
  actor: { user_id: string; username: string; display_name: string }
}
export type TrendingTag = { tag: string; post_count: number }
export type PostTip = {
  tip_id: string
  amount_wei: string
  message: string
  verified_at: string
  tx_hash: string
  sender_username: string
  sender_display_name: string
}
export type ChainConfig = {
  network: string
  chain_id: number
  asset: string
  min_confirmations: number
  max_tip_wei: string
  tip_intent_ttl_minutes: number
  max_tip_message_chars: number
}
export type JobKind =
  | 'analyze' | 'linkedin' | 'case_study' | 'community_post' | 'workflow'
  | 'improve_post' | 'suggest_tags' | 'summarize_thread'
export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
export type AiJob<R = unknown> = {
  job_id: string
  kind: JobKind
  project_id: string | null
  status: JobStatus
  progress: number
  step: string
  result: R | null
  error: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}
export type CommunityPostDraft = {
  body: string
  tags: string[]
  claims: string[]
  verified_claims: EvidenceClaim[]
  review_status: 'needs_review' | 'preliminary_support'
}
export type PreparedTip = {
  intent_id: string
  chain_id: number
  from: string
  to: string
  value: string
  amount_wei: string
  expires_at: string
  network: string
  asset: string
}
export type WalletProvider = {
  request(args: { method: string; params?: unknown[] | object }): Promise<unknown>
}

declare global {
  interface Window {
    ethereum?: WalletProvider
  }
}
export type LinkedInAngle = 'technical_lesson' | 'engineering_decision' | 'personal_reflection'
export type ExportFormat = 'markdown' | 'pdf'
export type EditableArtifact = LinkedInDraft | CaseStudy

export const LINKEDIN_ANGLES: {
  id: LinkedInAngle
  title: string
  description: string
  icon: string
}[] = [
  { id: 'technical_lesson', title: 'Technical lesson', description: 'Explain how it works and what you learned.', icon: '↗' },
  { id: 'engineering_decision', title: 'Engineering decision', description: 'Share a design choice and its trade-offs.', icon: '⌘' },
  { id: 'personal_reflection', title: 'Personal reflection', description: 'Tell the story behind the work.', icon: '✳' },
]

/** Summary of a post's evidence passport (full detail lives at /p/:publication_id). */
export type PostEvidence = {
  artifact: string | null
  supported: number
  total: number
  publication_id?: string
  kind?: 'case_study' | 'post'
  trust_level?: 'repository' | 'notes'
  ownership_verified?: boolean
  title?: string | null
}

export type PublicEvidenceItem = {
  path: string
  start_line: number | null
  end_line: number | null
  excerpt: string
  source_url: string | null
  permalink: string | null
}
export type PublicClaim = {
  section: string
  text: string
  status: 'supported' | 'needs_review' | 'unsupported'
  note: string | null
  evidence: PublicEvidenceItem[]
}
export type PublicPublication = {
  publication_id: string
  kind: 'case_study' | 'post'
  title: string
  created_at: string
  author: { username: string; display_name: string }
  content: Record<string, string>
  trust: {
    level: 'repository' | 'notes'
    label: string
    repository: { url: string; owner: string; name: string; commit_sha: string | null; commit_url: string | null } | null
    ownership_verified: boolean
    supported: number
    total: number
    method: string
  }
  claims: PublicClaim[]
  sources: { path: string; source_url: string | null; commit_sha: string | null; sha256: string }[]
  integrity: { algorithm: string; content_sha256: string; intact: boolean }
}
export type ReverifyResult = {
  checked_at: string
  commit_sha: string
  confirmed: number
  checked: number
  claims: { index: number; status: 'confirmed' | 'mismatch' | 'unreachable' | 'no_evidence' }[]
  files: Record<string, { status: string; matches_ingested_copy?: boolean }>
}
export type PublicationSummary = {
  publication_id: string
  kind: 'case_study' | 'post'
  title: string
  supported: number
  total: number
  trust_level: 'repository' | 'notes'
  ownership_verified: boolean
  created_at: string
  revoked: boolean
}
export type OwnershipStatus = { started: boolean; verified: boolean; verified_at: string | null; token: string | null }
export type OwnershipStart = { token: string; file: string; repository: string; instructions: string }
